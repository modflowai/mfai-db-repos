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

// Client sessions for SSE
const sessions = new Map<string, {
  clientId: string;
  messagesUrl: string;
  encoder: TextEncoder;
  writer?: WritableStreamDefaultWriter;
}>();

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

  // Store handlers
  handlers.set('initialize', (params: any) => server.handleInitialize(params));
  handlers.set('tools/list', () => server.handleListTools());
  
  // Tool: List repositories with navigation
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
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
              items: {
                type: 'string',
              },
              description: 'Optional: Filter to specific repository names',
            },
          },
          required: ['query', 'search_type'],
        },
      },
    ],
  }));

  // Tool handlers
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    
    handlers.set('tools/call', async () => {
      switch (name) {
        case 'list_repositories_with_navigation': {
          const { include_navigation } = ListRepositoriesSchema.parse(args);
          
          try {
            const repositories = await sql`
              SELECT id, name, url, file_count, navigation_guide
              FROM repositories
              ORDER BY name
            `;
            
            const results = repositories.map(repo => ({
              ...repo,
              navigation_guide: include_navigation ? repo.navigation_guide : undefined,
            }));
            
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(results, null, 2),
                },
              ],
            };
          } catch (error) {
            throw new McpError(
              ErrorCode.InternalError,
              `Database error: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
          }
        }

        case 'mfai_search': {
          const { query, search_type, repositories } = SearchFilesSchema.parse(args);
          
          if (search_type === 'text') {
            const tsQuery = query.split(/\s+/).join(' & ');
            
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
    });
    
    const handler = handlers.get('tools/call');
    if (!handler) {
      throw new McpError(ErrorCode.MethodNotFound, `Unknown method: tools/call`);
    }
    return handler();
  });

  return server;
}

// Handle JSON-RPC requests directly
async function handleJsonRpcRequest(server: Server, request: any, clientId: string) {
  const { method, params, id } = request;
  
  const handler = handlers.get(method);
  if (!handler) {
    return {
      jsonrpc: '2.0',
      error: {
        code: ErrorCode.MethodNotFound,
        message: `Unknown method: ${method}`,
      },
      id,
    };
  }
  
  try {
    const result = await handler(params);
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

// Generate a unique client ID
function generateClientId(): string {
  return crypto.randomUUID();
}

// Cloudflare Worker handler
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // Handle SSE endpoint
    if (request.method === 'GET' && url.pathname === '/sse') {
      // Check API key authentication if configured
      if (env.MCP_API_KEY) {
        const authHeader = request.headers.get('Authorization');
        if (!authHeader || authHeader !== `Bearer ${env.MCP_API_KEY}`) {
          return new Response('Unauthorized', {
            status: 401,
            headers: { 
              'Content-Type': 'text/plain',
              'WWW-Authenticate': 'Bearer',
            },
          });
        }
      }
      
      // Create a new client session
      const clientId = generateClientId();
      const messagesUrl = `${url.origin}/messages?client_id=${clientId}`;
      
      // Create SSE stream
      const { readable, writable } = new TransformStream();
      const writer = writable.getWriter();
      const encoder = new TextEncoder();
      
      // Store session
      sessions.set(clientId, {
        clientId,
        messagesUrl,
        encoder,
        writer,
      });
      
      // Send initial endpoint event
      const endpointEvent = `event: endpoint\ndata: ${messagesUrl}\n\n`;
      await writer.write(encoder.encode(endpointEvent));
      
      // Keep connection alive with periodic pings
      const pingInterval = setInterval(async () => {
        try {
          await writer.write(encoder.encode(':ping\n\n'));
        } catch (error) {
          clearInterval(pingInterval);
          sessions.delete(clientId);
        }
      }, 30000);
      
      // Clean up on disconnect
      request.signal.addEventListener('abort', () => {
        clearInterval(pingInterval);
        sessions.delete(clientId);
        writer.close();
      });
      
      return new Response(readable, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }
    
    // Handle messages endpoint
    if (request.method === 'POST' && url.pathname === '/messages') {
      const clientId = url.searchParams.get('client_id');
      if (!clientId || !sessions.has(clientId)) {
        return new Response('Invalid client ID', { status: 400 });
      }
      
      const session = sessions.get(clientId)!;
      
      try {
        // Parse the request body
        const body = await request.json();
        console.log('Received message:', JSON.stringify(body));
        
        // Create server instance
        const server = createServer(env);
        
        // Handle the JSON-RPC request
        const response = await handleJsonRpcRequest(server, body, clientId);
        
        // Send response through SSE
        const messageEvent = `event: message\ndata: ${JSON.stringify(response)}\n\n`;
        await session.writer?.write(session.encoder.encode(messageEvent));
        
        // Also return response for HTTP compatibility
        return new Response(JSON.stringify(response), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
        });
      } catch (error) {
        console.error('Error handling message:', error);
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
    
    // Handle regular /mcp endpoint (backward compatibility)
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
        const response = await handleJsonRpcRequest(server, body, 'direct');
        
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
    
    // Default 404 response
    return new Response('Not Found', { 
      status: 404,
      headers: { 'Content-Type': 'text/plain' },
    });
  },
};