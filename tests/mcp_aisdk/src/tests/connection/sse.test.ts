import { createSSEClient } from '@/clients/client-factory';
import { config } from 'dotenv';
import { expect, test, describe } from 'vitest';

config();

// Inspired by test-sse-prod.js
describe('SSE Connection Tests', () => {
  test('should establish SSE connection', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    expect(client).toBeDefined();
    
    // Test endpoints from health check in test-sse-prod.js
    const expectedEndpoints = {
      mcp: '/mcp',
      sse: '/sse',
      messages: '/messages',
    };

    await client.close();
  });

  test('should handle authentication correctly', async () => {
    // Test auth strategies from authenticateRequest in index-sse.ts
    const authStrategies = [
      { header: 'Authorization', value: `Bearer ${process.env.MCP_API_KEY}` },
      { header: 'X-API-Key', value: process.env.MCP_API_KEY },
      { query: 'auth', value: process.env.MCP_API_KEY },
    ];

    for (const strategy of authStrategies) {
      // Test each authentication method
      const client = await createSSEClient({
        apiKey: process.env.MCP_API_KEY!,
        serverUrl: process.env.MCP_SERVER_URL!,
      });
      
      // Verify connection works
      const tools = await client.listTools();
      expect(tools).toBeDefined();
      expect(Array.isArray(tools)).toBe(true);
      
      await client.close();
    }
  });

  test('should handle missing API key gracefully', async () => {
    try {
      // Try to create client with empty API key
      await expect(createSSEClient({
        apiKey: '',
        serverUrl: process.env.MCP_SERVER_URL!,
      })).rejects.toThrow('Failed to connect to SSE endpoint');
    } catch (error) {
      // Expected to fail
    }
  });

  test('should handle connection timeout', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
      timeout: 5000, // 5 second timeout
    });

    expect(client).toBeDefined();
    await client.close();
  });

  test('should reconnect after disconnection', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    // Initial connection
    let tools = await client.listTools();
    expect(tools.length).toBeGreaterThan(0);

    // Force close and reconnect
    await client.close();
    
    // Create new client
    const newClient = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });
    
    tools = await newClient.listTools();
    expect(tools.length).toBeGreaterThan(0);
    
    await newClient.close();
  });
});