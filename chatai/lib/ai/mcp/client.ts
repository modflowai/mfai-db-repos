/**
 * MCP Client for connecting to MFAI Repository Navigator
 */

export interface MCPToolResult {
  content: Array<{
    type: 'text';
    text: string;
  }>;
}

export interface MCPConnection {
  serverUrl: string;
  apiKey: string;
}

export class MCPClient {
  private connection: MCPConnection | null = null;

  async connect(config: MCPConnection): Promise<void> {
    this.connection = config;
    // Test connection
    await this.testConnection();
  }

  async close(): Promise<void> {
    this.connection = null;
  }

  async callTool(toolName: string, parameters: Record<string, any>): Promise<MCPToolResult> {
    if (!this.connection) {
      throw new Error('MCP client not connected');
    }

    const response = await fetch(`${this.connection.serverUrl}/mcp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.connection.apiKey}`,
      },
      body: JSON.stringify({
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: parameters,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`MCP call failed: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.error) {
      throw new Error(`MCP tool error: ${result.error.message}`);
    }

    return result.result;
  }

  private async testConnection(): Promise<void> {
    if (!this.connection) {
      throw new Error('No connection configuration');
    }

    try {
      const response = await fetch(`${this.connection.serverUrl}/health`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.connection.apiKey}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Connection test failed: ${response.status}`);
      }
    } catch (error) {
      throw new Error(`Failed to connect to MCP server: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}

export class MCPError extends Error {
  constructor(
    message: string,
    public readonly code: 'CONNECTION_FAILED' | 'AUTH_FAILED' | 'TOOL_NOT_FOUND' | 'EXECUTION_FAILED'
  ) {
    super(message);
    this.name = 'MCPError';
  }
}

export function withMCPErrorHandling<T>(operation: () => Promise<T>): Promise<T> {
  return operation().catch((error) => {
    if (error instanceof MCPError) {
      throw error;
    }
    
    // Convert common errors to MCPError
    if (error.message.includes('Failed to connect')) {
      throw new MCPError('MCP server is currently unavailable', 'CONNECTION_FAILED');
    }
    
    if (error.message.includes('Unauthorized') || error.message.includes('401')) {
      throw new MCPError('Invalid MCP API key', 'AUTH_FAILED');
    }
    
    if (error.message.includes('Tool not found')) {
      throw new MCPError('Requested tool not available', 'TOOL_NOT_FOUND');
    }
    
    throw new MCPError(`MCP operation failed: ${error.message}`, 'EXECUTION_FAILED');
  });
}