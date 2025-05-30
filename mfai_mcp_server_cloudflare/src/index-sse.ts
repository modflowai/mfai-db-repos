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
    // Accept both protocol versions for compatibility
    const clientProtocolVersion = request.params?.protocolVersion || '2024-11-05';
    const supportedVersions = ['2024-11-05', '2025-03-26'];
    
    // Use the client's version if supported, otherwise default to 2024-11-05
    const protocolVersion = supportedVersions.includes(clientProtocolVersion) 
      ? clientProtocolVersion 
      : '2024-11-05';
    
    return {
      protocolVersion,
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

// Authentication helper function - supports multiple auth strategies
function authenticateRequest(request: Request, env: Env): boolean {
  if (!env.MCP_API_KEY) {
    console.log('No MCP_API_KEY configured, authentication disabled');
    return true; // No authentication required
  }

  console.log('MCP_API_KEY is configured, checking authentication...');

  // Strategy 1: Check Authorization header (standard Bearer token)
  const authHeader = request.headers.get('Authorization');
  console.log('Authorization header:', authHeader);
  console.log('Expected:', `Bearer ${env.MCP_API_KEY}`);
  if (authHeader === `Bearer ${env.MCP_API_KEY}`) {
    console.log('Auth successful via Authorization header');
    return true;
  }

  // Strategy 2: Check X-API-Key header (alternative)
  const apiKeyHeader = request.headers.get('X-API-Key');
  if (apiKeyHeader === env.MCP_API_KEY) {
    console.log('Auth successful via X-API-Key header');
    return true;
  }

  // Strategy 3: Check query parameter (for SSE URLs that can't use headers easily)
  const url = new URL(request.url);
  const queryAuth = url.searchParams.get('auth');
  if (queryAuth === env.MCP_API_KEY) {
    console.log('Auth successful via query parameter');
    return true;
  }

  console.log('All authentication strategies failed');
  return false;
}

// Cloudflare Worker handler with SSE support
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // Dynamic client registration endpoint
    if (request.method === 'POST' && url.pathname === '/register') {
      console.log('Client registration request received');
      
      // For now, we'll accept any registration request
      // In production, you might want to validate the request
      const clientId = crypto.randomUUID();
      
      return new Response(JSON.stringify({
        client_id: clientId,
        client_id_issued_at: Math.floor(Date.now() / 1000),
        grant_types: ['authorization_code', 'refresh_token'],
        response_types: ['code'],
        token_endpoint_auth_method: 'none',
        // Add any other fields that mcp-remote expects
      }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // SSE endpoint for MCP-remote compatibility
    if (request.method === 'GET' && url.pathname === '/sse') {
      // Authenticate request
      if (!authenticateRequest(request, env)) {
        return new Response('Unauthorized', {
          status: 401,
          headers: {
            'WWW-Authenticate': 'Bearer realm="MCP API"',
            'Content-Type': 'text/plain',
          },
        });
      }

      // Create SSE stream with ReadableStream
      const encoder = new TextEncoder();
      const messagesUrl = `${url.origin}/sse/messages`;
      
      const stream = new ReadableStream({
        start(controller) {
          // Send endpoint event with the SSE messages endpoint
          controller.enqueue(encoder.encode(`event: endpoint\ndata: ${messagesUrl}\n\n`));
          
          // Keep connection alive with ping messages
          const pingInterval = setInterval(() => {
            try {
              controller.enqueue(encoder.encode(': ping\n\n'));
            } catch (error) {
              clearInterval(pingInterval);
              controller.close();
            }
          }, 30000); // Ping every 30 seconds

          // Close after 5 minutes
          setTimeout(() => {
            clearInterval(pingInterval);
            try {
              controller.close();
            } catch (error) {
              // Controller already closed
            }
          }, 300000);
        }
      });

      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Headers': 'Authorization, X-API-Key',
        },
      });
    }

    // SSE messages endpoint - handles client-to-server messages for SSE transport
    if (request.method === 'POST' && url.pathname === '/sse/messages') {
      console.log('SSE messages endpoint hit, headers:', Object.fromEntries(request.headers.entries()));
      
      // Authenticate request
      if (!authenticateRequest(request, env)) {
        console.log('Authentication failed');
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
            'WWW-Authenticate': 'Bearer realm="MCP API"',
            'Access-Control-Allow-Origin': '*',
          },
        });
      }

      console.log('Authentication successful');

      try {
        // Parse the request body
        const body = await request.json();
        console.log('Received SSE message request:', JSON.stringify(body));
        
        // Create server instance
        const server = createServer(env);
        
        // Handle the JSON-RPC request
        const response = await handleJsonRpcRequest(server, body);
        console.log('Sending response:', JSON.stringify(response));
        
        return new Response(JSON.stringify(response), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization, X-API-Key, Content-Type',
          },
        });
      } catch (error) {
        console.error('Error handling SSE message request:', error);
        return new Response(JSON.stringify({
          jsonrpc: '2.0',
          error: {
            code: -32603,
            message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
          id: null,
        }), {
          status: 500,
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        });
      }
    }

    // Messages endpoint for SSE - forwards to existing MCP logic
    if (request.method === 'POST' && url.pathname === '/messages') {
      console.log('Messages endpoint hit, headers:', Object.fromEntries(request.headers.entries()));
      
      // Authenticate request
      if (!authenticateRequest(request, env)) {
        console.log('Authentication failed');
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
            'WWW-Authenticate': 'Bearer realm="MCP API"',
            'Access-Control-Allow-Origin': '*',
          },
        });
      }

      console.log('Authentication successful');

      try {
        // Parse the request body
        const body = await request.json();
        console.log('Received SSE message request:', JSON.stringify(body));
        
        // Create server instance
        const server = createServer(env);
        
        // Handle the JSON-RPC request
        const response = await handleJsonRpcRequest(server, body);
        console.log('Sending response:', JSON.stringify(response));
        
        return new Response(JSON.stringify(response), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization, X-API-Key, Content-Type',
          },
        });
      } catch (error) {
        console.error('Error handling SSE message request:', error);
        return new Response(JSON.stringify({
          jsonrpc: '2.0',
          error: {
            code: -32603,
            message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
          id: null,
        }), {
          status: 500,
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        });
      }
    }

    // Handle OPTIONS requests for CORS (handle early for all paths)
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 200,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Authorization, X-API-Key, Content-Type, Accept, Accept-Encoding, Accept-Language',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // Existing HTTP/JSON-RPC endpoint (backward compatibility)
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
    
    // Return 405 for GET/DELETE on /mcp
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
    
    // Health check endpoint
    if (request.method === 'GET' && url.pathname === '/health') {
      return new Response(JSON.stringify({
        status: 'healthy',
        version: '3.0.0',
        endpoints: {
          mcp: '/mcp',
          sse: '/sse',
          messages: '/messages',
          register: '/register',
        },
        authentication: env.MCP_API_KEY ? 'required' : 'disabled',
        sseSupport: true,
      }), {
        status: 200,
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