import { createSSEClient } from '@/clients/client-factory';
import { TOOL_DEFINITIONS } from '@/tools/tool-schemas';
import { expect, test, describe } from 'vitest';
import { config } from 'dotenv';

config();

describe('Tool Discovery', () => {
  test('should discover expected MCP tools', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const tools = await client.listTools();
    
    // Expected tools from listToolsHandler in index-sse.ts
    const expectedTools = [
      'list_repositories_with_navigation',
      'mfai_search',
    ];

    expect(tools.map(t => t.name)).toEqual(expect.arrayContaining(expectedTools));

    // Validate tool schemas match our definitions
    const listRepoTool = tools.find(t => t.name === 'list_repositories_with_navigation');
    expect(listRepoTool?.inputSchema).toMatchObject({
      type: 'object',
      properties: {
        include_navigation: {
          type: 'boolean',
          description: expect.any(String),
          default: true,
        },
      },
    });

    await client.close();
  });

  test('should have correct tool descriptions', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const tools = await client.listTools();
    
    // Check list_repositories_with_navigation tool
    const listRepoTool = tools.find(t => t.name === 'list_repositories_with_navigation');
    expect(listRepoTool).toBeDefined();
    expect(listRepoTool?.description).toContain('repositories');
    expect(listRepoTool?.description).toContain('navigation guides');
    
    // Check mfai_search tool
    const searchTool = tools.find(t => t.name === 'mfai_search');
    expect(searchTool).toBeDefined();
    expect(searchTool?.description).toContain('Search across all MFAI indexed repositories');
    
    await client.close();
  });

  test('should validate search tool schema', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const tools = await client.listTools();
    const searchTool = tools.find(t => t.name === 'mfai_search');
    
    expect(searchTool?.inputSchema).toMatchObject({
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: expect.any(String),
        },
        search_type: {
          type: 'string',
          enum: ['text', 'semantic'],
          description: expect.any(String),
        },
        repositories: {
          type: 'array',
          items: { type: 'string' },
          description: expect.any(String),
        },
      },
      required: ['query', 'search_type'],
    });
    
    await client.close();
  });

  test('should match tool count', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const tools = await client.listTools();
    
    // Should have exactly 2 tools based on server implementation
    expect(tools).toHaveLength(2);
    
    // Verify against our local definitions
    const definedToolCount = Object.keys(TOOL_DEFINITIONS).length;
    expect(tools).toHaveLength(definedToolCount);
    
    await client.close();
  });

  test('tool names should match server implementation', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const tools = await client.listTools();
    const toolNames = tools.map(t => t.name).sort();
    const expectedNames = Object.keys(TOOL_DEFINITIONS).sort();
    
    expect(toolNames).toEqual(expectedNames);
    
    await client.close();
  });
});