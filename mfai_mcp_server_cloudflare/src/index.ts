import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  InitializeRequestSchema,
  ErrorCode,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { neon } from '@neondatabase/serverless';
import { OpenAI } from 'openai';

// Environment type
interface Env {
  MODFLOW_AI_MCP_00_CONNECTION_STRING: string;
  OPENAI_API_KEY?: string;
  MCP_API_KEY?: string;
}

// Input schemas
const ListRepositoriesSchema = z.object({
  include_navigation: z.boolean().optional().default(true).describe('Include navigation guides in response'),
});

const SearchFilesSchema = z.object({
  query: z.string().describe('Search query'),
  search_type: z.enum(['text', 'semantic']).describe('Type of search to perform'),
  repositories: z.array(z.string()).optional().describe('Filter by repository names'),
});

// Store handlers globally for easy access
const handlers: Map<string, Function> = new Map();

// Create and configure MCP server
function createServer(env: Env) {
  const server = new Server(
    {
      name: 'mfai-repository-navigator',
      version: '3.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // Initialize connections
  const sql = neon(env.MODFLOW_AI_MCP_00_CONNECTION_STRING);
  const openai = env.OPENAI_API_KEY ? new OpenAI({ apiKey: env.OPENAI_API_KEY }) : null;

  // Handle initialization
  const initHandler = async (request: any) => {
    return {
      protocolVersion: '2024-11-05',
      capabilities: {
        tools: {},
      },
      serverInfo: {
        name: 'mfai-repository-navigator',
        version: '3.0.0',
      },
    };
  };
  server.setRequestHandler(InitializeRequestSchema, initHandler);
  handlers.set('initialize', initHandler);

  // Register available tools
  const listToolsHandler = async () => {
    return {
      tools: [
        {
          name: 'list_repositories_with_navigation',
          description: 'Get all repositories with their navigation guides that explain what each repository does and how to search it effectively.',
          inputSchema: {
            type: 'object',
            properties: {
              include_navigation: {
                type: 'boolean',
                description: 'Include full navigation guides (default: true)',
                default: true,
              },
            },
          },
        },
        {
          name: 'mfai_search',
          description: 'Search across all MFAI indexed repositories in the database. No path needed. Use text search for exact terms/keywords or semantic search for concepts/questions.',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Your search query',
              },
              search_type: {
                type: 'string',
                enum: ['text', 'semantic'],
                description: 'Choose text for exact matches, semantic for conceptual search',
              },
              repositories: {
                type: 'array',
                items: { type: 'string' },
                description: 'Optional: Filter to specific repository names',
              },
            },
            required: ['query', 'search_type'],
          },
        },
      ],
    };
  };
  server.setRequestHandler(ListToolsRequestSchema, listToolsHandler);
  handlers.set('tools/list', listToolsHandler);

  // Handle tool calls
  const callToolHandler = async (request: any) => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case 'list_repositories_with_navigation': {
          const { include_navigation } = ListRepositoriesSchema.parse(args);
          
          const repositories = include_navigation
            ? await sql`
                SELECT 
                  id, 
                  name, 
                  url, 
                  file_count,
                  metadata->>'navigation_guide' as navigation_guide,
                  metadata->>'repository_type' as repository_type,
                  created_at, 
                  updated_at
                FROM repositories
                ORDER BY id ASC
                LIMIT 50
              `
            : await sql`
                SELECT 
                  id, 
                  name, 
                  url, 
                  file_count,
                  created_at, 
                  updated_at
                FROM repositories
                ORDER BY id ASC
                LIMIT 50
              `;

          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(repositories, null, 2),
              },
            ],
          };
        }

        case 'mfai_search': {
          const { query, search_type, repositories } = SearchFilesSchema.parse(args);
          
          if (search_type === 'text') {
            // Text search using PostgreSQL full-text search
            const queryWords = query.split(' ').filter(word => word.length > 0);
            const tsQuery = queryWords.map(word => `${word}:*`).join(' & ');
            
            const results = repositories?.length
              ? await sql`
                  SELECT DISTINCT ON (rf.repo_name)
                    rf.id,
                    rf.repo_id,
                    rf.repo_name,
                    rf.repo_url,
                    rf.filepath,
                    rf.filename,
                    rf.extension,
                    rf.file_type,
                    rf.content,
                    ts_rank_cd(rf.content_tsvector, to_tsquery('english', ${tsQuery})) as rank,
                    ts_headline(
                      'english', 
                      rf.content, 
                      to_tsquery('english', ${tsQuery}), 
                      'StartSel=<<<, StopSel=>>>, MaxWords=50, MinWords=20'
                    ) as snippet
                  FROM repository_files rf
                  WHERE rf.content_tsvector @@ to_tsquery('english', ${tsQuery})
                    AND rf.repo_name = ANY(${repositories})
                  ORDER BY rf.repo_name, rank DESC
                `
              : await sql`
                  SELECT 
                    rf.id,
                    rf.repo_id,
                    rf.repo_name,
                    rf.repo_url,
                    rf.filepath,
                    rf.filename,
                    rf.extension,
                    rf.file_type,
                    rf.content,
                    ts_rank_cd(rf.content_tsvector, to_tsquery('english', ${tsQuery})) as rank,
                    ts_headline(
                      'english', 
                      rf.content, 
                      to_tsquery('english', ${tsQuery}), 
                      'StartSel=<<<, StopSel=>>>, MaxWords=50, MinWords=20'
                    ) as snippet
                  FROM repository_files rf
                  WHERE rf.content_tsvector @@ to_tsquery('english', ${tsQuery})
                  ORDER BY rank DESC
                  LIMIT 1
                `;
            
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(results, null, 2),
                },
              ],
            };
          } else {
            // Semantic search using OpenAI embeddings
            if (!openai) {
              throw new Error('Semantic search requires OPENAI_API_KEY environment variable');
            }
            
            // Generate embedding
            const embeddingResponse = await openai.embeddings.create({
              model: 'text-embedding-3-small',
              input: query,
            });
            
            const embedding = embeddingResponse.data[0].embedding;
            const pgVector = `[${embedding.join(',')}]`;
            
            const results = repositories?.length
              ? await sql`
                  SELECT DISTINCT ON (rf.repo_name)
                    rf.id,
                    rf.repo_id,
                    rf.repo_name,
                    rf.repo_url,
                    rf.filepath,
                    rf.filename,
                    rf.extension,
                    rf.file_type,
                    rf.content,
                    1 - (rf.embedding <=> ${pgVector}::vector) as similarity,
                    substring(rf.content from 1 for 500) as snippet
                  FROM repository_files rf
                  WHERE rf.embedding IS NOT NULL
                    AND rf.repo_name = ANY(${repositories})
                  ORDER BY rf.repo_name, rf.embedding <=> ${pgVector}::vector
                `
              : await sql`
                  SELECT 
                    rf.id,
                    rf.repo_id,
                    rf.repo_name,
                    rf.repo_url,
                    rf.filepath,
                    rf.filename,
                    rf.extension,
                    rf.file_type,
                    rf.content,
                    1 - (rf.embedding <=> ${pgVector}::vector) as similarity,
                    substring(rf.content from 1 for 500) as snippet
                  FROM repository_files rf
                  WHERE rf.embedding IS NOT NULL
                  ORDER BY rf.embedding <=> ${pgVector}::vector
                  LIMIT 1
                `;
            
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(results, null, 2),
                },
              ],
            };
          }
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              error: error instanceof Error ? error.message : 'Unknown error occurred',
              tool: name,
            }, null, 2),
          },
        ],
        isError: true,
      };
    }
  };
  server.setRequestHandler(CallToolRequestSchema, callToolHandler);
  handlers.set('tools/call', callToolHandler);

  return server;
}

// Handle JSON-RPC requests directly without StreamableHTTPServerTransport
async function handleJsonRpcRequest(server: Server, request: any) {
  const { method, params, id } = request;
  
  try {
    // Map JSON-RPC method to handler
    let result;
    
    switch (method) {
      case 'initialize':
        result = await handlers.get('initialize')?.(
          { method, params: params || {} },
          {}
        );
        break;
      
      case 'tools/list':
        result = await handlers.get('tools/list')?.(
          { method, params: {} },
          {}
        );
        break;
      
      case 'tools/call':
        result = await handlers.get('tools/call')?.(
          { method, params },
          {}
        );
        break;
      
      default:
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Method not found: ${method}`
        );
    }
    
    return {
      jsonrpc: '2.0',
      result,
      id,
    };
  } catch (error) {
    console.error('Handler error:', error);
    
    if (error instanceof McpError) {
      return {
        jsonrpc: '2.0',
        error: {
          code: error.code,
          message: error.message,
          data: error.data,
        },
        id,
      };
    }
    
    return {
      jsonrpc: '2.0',
      error: {
        code: ErrorCode.InternalError,
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      id,
    };
  }
}

// Cloudflare Worker handler
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // Only handle POST /mcp
    if (request.method === 'POST' && url.pathname === '/mcp') {
      // Check API key authentication if configured
      if (env.MCP_API_KEY) {
        const authHeader = request.headers.get('Authorization');
        if (!authHeader || authHeader !== `Bearer ${env.MCP_API_KEY}`) {
          return new Response(JSON.stringify({
            jsonrpc: '2.0',
            error: {
              code: -32001,
              message: 'Unauthorized - Invalid or missing API key',
            },
            id: null,
          }), {
            status: 401,
            headers: { 
              'Content-Type': 'application/json',
              'WWW-Authenticate': 'Bearer',
            },
          });
        }
      }
      
      try {
        // Parse the request body
        const body = await request.json();
        console.log('Received request:', JSON.stringify(body));
        
        // Create server instance
        const server = createServer(env);
        
        // Handle the JSON-RPC request
        const response = await handleJsonRpcRequest(server, body);
        
        return new Response(JSON.stringify(response), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
        });
      } catch (error) {
        console.error('Error handling MCP request:', error);
        return new Response(JSON.stringify({
          jsonrpc: '2.0',
          error: {
            code: -32603,
            message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
          id: null,
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }
    
    // Return 405 for GET/DELETE
    if ((request.method === 'GET' || request.method === 'DELETE') && url.pathname === '/mcp') {
      return new Response(JSON.stringify({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Method not allowed - only POST is supported',
        },
        id: null,
      }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    
    // Default 404 response
    return new Response('Not Found', { 
      status: 404,
      headers: { 'Content-Type': 'text/plain' },
    });
  },
};