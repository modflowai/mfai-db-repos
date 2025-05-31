#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { neon } from '@neondatabase/serverless';
import { GeminiService } from './lib/services/gemini-service.js';
import { RepositorySelectorHandler } from './lib/handlers/repository-selector.js';

// Environment configuration
const DATABASE_URL = process.env.MODFLOW_AI_MCP_00_CONNECTION_STRING;
const GOOGLE_GENAI_API_KEY = process.env.GOOGLE_GENAI_API_KEY;

if (!DATABASE_URL) {
  console.error('Error: MODFLOW_AI_MCP_00_CONNECTION_STRING environment variable is required');
  process.exit(1);
}

if (!GOOGLE_GENAI_API_KEY) {
  console.error('Error: GOOGLE_GENAI_API_KEY environment variable is required');
  process.exit(1);
}

// Initialize connections and services
const sql = neon(DATABASE_URL);
const geminiService = new GeminiService(GOOGLE_GENAI_API_KEY);
const repositorySelectorHandler = new RepositorySelectorHandler(geminiService, sql);

// Create MCP server
const server = new Server(
  {
    name: 'mfai-repository-selector',
    version: '1.0.0',
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
      RepositorySelectorHandler.getToolDefinition(),
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'mfai_repository_selector': {
        const selection = await repositorySelectorHandler.handle(args as { query: string; context?: string });
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(selection, null, 2),
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
          text: JSON.stringify({
            error: error instanceof Error ? error.message : 'Unknown error',
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
  console.error('MFAI Repository Selector MCP Server started');
}

main().catch((error) => {
  console.error('Fatal error starting server:', error);
  process.exit(1);
});