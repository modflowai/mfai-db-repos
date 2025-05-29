import EventSource from 'eventsource';

// Based on test-sse-prod.js authentication patterns
export interface ClientConfig {
  apiKey: string;
  serverUrl: string;
  timeout?: number;
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: any;
}

export interface MCPClient {
  listTools(): Promise<MCPTool[]>;
  callTool(name: string, args: any): Promise<{ content: Array<{ text: string }> }>;
  close(): Promise<void>;
}

class SSEMCPClient implements MCPClient {
  private eventSource: EventSource | null = null;
  private messagesUrl: string | null = null;
  private config: ClientConfig;

  constructor(config: ClientConfig) {
    this.config = config;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const headers = {
        'Authorization': `Bearer ${this.config.apiKey}`,
      };

      this.eventSource = new EventSource(`${this.config.serverUrl}/sse`, {
        headers,
      });

      this.eventSource.addEventListener('endpoint', (event) => {
        this.messagesUrl = event.data;
        resolve();
      });

      this.eventSource.onerror = (error) => {
        reject(new Error('Failed to connect to SSE endpoint'));
      };

      if (this.config.timeout) {
        setTimeout(() => {
          if (!this.messagesUrl) {
            this.eventSource?.close();
            reject(new Error('Connection timeout'));
          }
        }, this.config.timeout);
      }
    });
  }

  async listTools(): Promise<MCPTool[]> {
    if (!this.messagesUrl) {
      throw new Error('Not connected. Call connect() first.');
    }

    const response = await fetch(this.messagesUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/list',
        params: {},
        id: Date.now(),
      }),
    });

    const result = await response.json();
    if (result.error) {
      throw new Error(result.error.message);
    }

    return result.result.tools;
  }

  async callTool(name: string, args: any): Promise<{ content: Array<{ text: string }> }> {
    if (!this.messagesUrl) {
      throw new Error('Not connected. Call connect() first.');
    }

    const response = await fetch(this.messagesUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
          name,
          arguments: args,
        },
        id: Date.now(),
      }),
    });

    const result = await response.json();
    if (result.error) {
      throw new Error(result.error.message);
    }

    return result.result;
  }

  async close(): Promise<void> {
    this.eventSource?.close();
    this.eventSource = null;
    this.messagesUrl = null;
  }
}

export async function createSSEClient(config: ClientConfig): Promise<MCPClient> {
  const client = new SSEMCPClient(config);
  await client.connect();
  return client;
}

// Helper function to validate connection
export async function validateConnection(client: MCPClient): Promise<boolean> {
  try {
    const tools = await client.listTools();
    return tools.length > 0;
  } catch (error) {
    console.error('Connection validation failed:', error);
    return false;
  }
}