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

// Environment configuration
const DATABASE_URL = process.env.MODFLOW_AI_MCP_00_CONNECTION_STRING;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!DATABASE_URL) {
  console.error('Error: MODFLOW_AI_MCP_00_CONNECTION_STRING environment variable is required');
  process.exit(1);
}

// Initialize connections
const sql = neon(DATABASE_URL);
const openai = OPENAI_API_KEY ? new OpenAI({ apiKey: OPENAI_API_KEY }) : null;

// Input schemas
const ListRepositoriesSchema = z.object({
  include_navigation: z.boolean().optional().default(true).describe('Include navigation guides in response'),
});

const SearchFilesSchema = z.object({
  query: z.string().describe('Search query'),
  search_type: z.enum(['text', 'semantic']).describe('Type of search to perform'),
  repositories: z.array(z.string()).optional().describe('Filter by repository names'),
});

// Create MCP server
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

// Register available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
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
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'list_repositories_with_navigation': {
        const { include_navigation } = ListRepositoriesSchema.parse(args);
        
        // Simple query - just get the data
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
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MFAI Repository Navigator MCP Server started');
}

main().catch((error) => {
  console.error('Fatal error starting server:', error);
  process.exit(1);
});