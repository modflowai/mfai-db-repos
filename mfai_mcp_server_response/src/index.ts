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
import { DocumentSearchService } from './lib/services/document-search-service.js';
import { GeminiCompressionService } from './lib/services/gemini-response-service.js';
import { ToolRegistry } from './lib/tools/index.js';

// Environment configuration
const DATABASE_URL = process.env.MODFLOW_AI_MCP_00_CONNECTION_STRING;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const GOOGLE_GENAI_API_KEY = process.env.GOOGLE_GENAI_API_KEY;

if (!DATABASE_URL) {
  console.error('Error: MODFLOW_AI_MCP_00_CONNECTION_STRING environment variable is required');
  process.exit(1);
}

if (!GOOGLE_GENAI_API_KEY) {
  console.error('Error: GOOGLE_GENAI_API_KEY environment variable is required');
  process.exit(1);
}

// Initialize connections
const sql = neon(DATABASE_URL);
const openai = OPENAI_API_KEY ? new OpenAI({ apiKey: OPENAI_API_KEY }) : null;

// Initialize services and tool registry
const searchService = new DocumentSearchService(sql, openai);
const compressionService = new GeminiCompressionService(GOOGLE_GENAI_API_KEY);
const toolRegistry = new ToolRegistry(searchService, compressionService, sql);

// Create MCP server
const server = new Server(
  {
    name: 'mfai-document-retrieval',
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
    tools: toolRegistry.getToolDefinitions(),
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (toolRegistry.hasTool(name)) {
      const result = await toolRegistry.executeTool(name, args);
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } else {
      throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    console.error(`Error handling tool call ${name}:`, error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${errorMessage}`,
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
  console.error('MFAI Document Retrieval MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error in main():', error);
  process.exit(1);
});