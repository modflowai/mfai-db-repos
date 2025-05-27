#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { neon } from '@neondatabase/serverless';
import { OpenAI } from 'openai';

// Configuration from environment variables
const MODFLOW_AI_MCP_00_CONNECTION_STRING = process.env.MODFLOW_AI_MCP_00_CONNECTION_STRING;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// Validate required environment variables
if (!MODFLOW_AI_MCP_00_CONNECTION_STRING) {
  process.exit(1);
}

// Database connection
const sql = neon(MODFLOW_AI_MCP_00_CONNECTION_STRING);

// OpenAI client (optional)
const openai = OPENAI_API_KEY ? new OpenAI({ apiKey: OPENAI_API_KEY }) : null;

// Tool input schemas
const ListReposSchema = z.object({
  limit: z.number().optional().default(10),
});

const FtsSearchSchema = z.object({
  query: z.string(),
  limit: z.number().optional().default(5),
});

const VectorSearchSchema = z.object({
  query: z.string(),
  limit: z.number().optional().default(5),
});

const RepoSearchSchema = z.object({
  repo_name: z.string(),
  query: z.string(),
  limit: z.number().optional().default(5),
});

// Create server
const server = new Server(
  {
    name: 'modflow-ai-mcp-00-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List repositories tool
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'modflow_ai_mcp_00_list_repos',
        description: 'Get a list of all repositories available in MODFLOW_AI_mcp_00.',
        inputSchema: {
          type: 'object',
          properties: {
            limit: {
              type: 'number',
              description: 'Maximum number of repositories to return',
              default: 10,
            },
          },
        },
      },
      {
        name: 'modflow_ai_mcp_00_fts',
        description: 'Search MODFLOW_AI_mcp_00 documentation using full-text search (FTS) for technical terms, error messages, or specific API references.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The search query text',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results to return',
              default: 5,
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'modflow_ai_mcp_00_vec',
        description: 'Search MODFLOW_AI_mcp_00 documentation using semantic search for conceptual queries or questions about how MODFLOW_AI_mcp_00 works.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The search query text',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results to return',
              default: 5,
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'modflow_ai_mcp_00_repo_search',
        description: 'Search within a specific repository.',
        inputSchema: {
          type: 'object',
          properties: {
            repo_name: {
              type: 'string',
              description: 'Name of the repository to search in',
            },
            query: {
              type: 'string',
              description: 'The search query text',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results to return',
              default: 5,
            },
          },
          required: ['repo_name', 'query'],
        },
      },
    ],
  };
});

// Tool call handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'modflow_ai_mcp_00_list_repos': {
        const { limit } = ListReposSchema.parse(args);
        const results = await sql`
          SELECT 
            id, name, url, default_branch, last_commit_hash, 
            last_indexed_at, file_count, created_at, updated_at
          FROM repositories
          ORDER BY updated_at DESC
          LIMIT ${limit}
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

      case 'modflow_ai_mcp_00_fts': {
        const { query, limit } = FtsSearchSchema.parse(args);
        const queryWords = query.split(' ').filter(word => word.length > 0);
        const tsQuery = queryWords.map(word => `${word}:*`).join(' & ');
        
        const results = await sql`
          SELECT 
            id, repo_id, repo_name, repo_url, filepath, filename, 
            extension, file_type, content,
            ts_rank_cd(content_tsvector, to_tsquery('english', ${tsQuery})) as rank,
            ts_headline('english', content, to_tsquery('english', ${tsQuery}), 'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20') as snippet
          FROM repository_files
          WHERE content_tsvector @@ to_tsquery('english', ${tsQuery})
          ORDER BY rank DESC
          LIMIT ${limit}
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

      case 'modflow_ai_mcp_00_vec': {
        const { query, limit } = VectorSearchSchema.parse(args);
        
        if (!openai) {
          // Fallback to full-text search if no OpenAI API key
          const queryWords = query.split(' ').filter(word => word.length > 0);
          const tsQuery = queryWords.map(word => `${word}:*`).join(' & ');
          
          const results = await sql`
            SELECT 
              id, repo_id, repo_name, repo_url, filepath, filename, 
              extension, file_type, content,
              ts_rank_cd(content_tsvector, to_tsquery('english', ${tsQuery})) as similarity,
              substring(content from 1 for 500) as snippet
            FROM repository_files
            WHERE content_tsvector @@ to_tsquery('english', ${tsQuery})
            ORDER BY similarity DESC
            LIMIT ${limit}
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
        
        // Generate embedding for vector search
        const embeddingResponse = await openai.embeddings.create({
          model: 'text-embedding-3-small',
          input: query,
        });
        
        const embedding = embeddingResponse.data[0].embedding;
        const pgVector = `[${embedding.join(',')}]`;
        
        const results = await sql`
          SELECT 
            id, repo_id, repo_name, repo_url, filepath, filename, 
            extension, file_type, content,
            1 - (embedding <=> ${pgVector}::vector) as similarity,
            substring(content from 1 for 500) as snippet
          FROM repository_files
          WHERE embedding IS NOT NULL
          ORDER BY embedding <=> ${pgVector}::vector
          LIMIT ${limit}
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

      case 'modflow_ai_mcp_00_repo_search': {
        const { repo_name, query, limit } = RepoSearchSchema.parse(args);
        const queryWords = query.split(' ').filter(word => word.length > 0);
        const tsQuery = queryWords.map(word => `${word}:*`).join(' & ');
        
        const results = await sql`
          SELECT 
            id, repo_id, repo_name, repo_url, filepath, filename, 
            extension, file_type, content,
            ts_rank_cd(content_tsvector, to_tsquery('english', ${tsQuery})) as rank,
            ts_headline('english', content, to_tsquery('english', ${tsQuery}), 'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20') as snippet
          FROM repository_files
          WHERE repo_name = ${repo_name}
            AND content_tsvector @@ to_tsquery('english', ${tsQuery})
          ORDER BY rank DESC
          LIMIT ${limit}
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

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  process.exit(1);
});
