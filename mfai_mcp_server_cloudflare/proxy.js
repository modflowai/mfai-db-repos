#!/usr/bin/env node

import readline from 'readline';
import fetch from 'node-fetch';

// Get configuration from environment or command line
const serverUrl = process.argv[2] || process.env.MCP_SERVER_URL || 'https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp';
const apiKey = process.env.MCP_API_KEY || process.env.MCP_SERVER_AUTH?.replace('Bearer ', '') || '';

// Create readline interface for stdio
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Buffer for incomplete JSON
let buffer = '';

// Process each line of input
rl.on('line', async (line) => {
  try {
    buffer += line;
    
    // Try to parse the JSON
    let request;
    try {
      request = JSON.parse(buffer);
      buffer = ''; // Clear buffer on successful parse
    } catch (e) {
      // If parse fails, we might have incomplete JSON, wait for more
      return;
    }

    // Prepare headers
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (apiKey) {
      headers['Authorization'] = apiKey.startsWith('Bearer ') ? apiKey : `Bearer ${apiKey}`;
    }

    // Make HTTP request to the remote server
    const response = await fetch(serverUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.log(JSON.stringify({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: `HTTP ${response.status}: ${errorText}`,
        },
        id: request.id || null,
      }));
      return;
    }

    const result = await response.json();
    console.log(JSON.stringify(result));
  } catch (error) {
    console.log(JSON.stringify({
      jsonrpc: '2.0',
      error: {
        code: -32603,
        message: `Proxy error: ${error.message}`,
      },
      id: null,
    }));
  }
});

// Handle errors
rl.on('error', (error) => {
  console.error('Readline error:', error);
  process.exit(1);
});

// Log startup info to stderr
console.error(`MCP HTTP Proxy started`);
console.error(`Server URL: ${serverUrl}`);
console.error(`API Key: ${apiKey ? 'Configured' : 'Not configured'}`);