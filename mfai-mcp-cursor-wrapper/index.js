#!/usr/bin/env node

/**
 * MCP Wrapper for Cursor IDE
 * 
 * This wrapper enables Cursor IDE to connect to the MFAI Repository Navigator
 * MCP server using HTTP transport. It works around known compatibility issues
 * between Cursor and mcp-remote.
 * 
 * Usage in Cursor's mcp.json:
 * {
 *   "mcpServers": {
 *     "mfai": {
 *       "command": "npx",
 *       "args": ["-y", "@modflowai/mcp-cursor-wrapper"],
 *       "env": {
 *         "MFAI_API_KEY": "your_api_key_here",
 *         "MFAI_SERVER_URL": "https://your-server.workers.dev/mcp" // optional
 *       }
 *     }
 *   }
 * }
 */

import { spawn } from 'child_process';

// Configuration
const SERVER_URL = process.env.MFAI_SERVER_URL || 'https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp';
const API_KEY = process.env.MFAI_API_KEY;

// Validate API key
if (!API_KEY) {
  console.error('[ERROR] MFAI_API_KEY environment variable is required');
  console.error('[ERROR] Please set it in your Cursor MCP configuration');
  console.error('[ERROR] Example:');
  console.error('[ERROR] {');
  console.error('[ERROR]   "mcpServers": {');
  console.error('[ERROR]     "mfai": {');
  console.error('[ERROR]       "command": "npx",');
  console.error('[ERROR]       "args": ["-y", "@modflowai/mcp-cursor-wrapper"],');
  console.error('[ERROR]       "env": {');
  console.error('[ERROR]         "MFAI_API_KEY": "your_api_key_here"');
  console.error('[ERROR]       }');
  console.error('[ERROR]     }');
  console.error('[ERROR]   }');
  console.error('[ERROR] }');
  process.exit(1);
}

// Build mcp-remote arguments
const args = [
  '-y',
  'mcp-remote@latest',
  SERVER_URL,
  '--header',
  `Authorization:Bearer ${API_KEY}`,
  '--transport',
  'http-only'
];

// Optional verbose logging
if (process.env.MFAI_DEBUG === 'true') {
  console.error(`[DEBUG] Starting mcp-remote with URL: ${SERVER_URL}`);
  console.error(`[DEBUG] API Key: ${API_KEY.substring(0, 8)}...`);
}

// Spawn mcp-remote
const child = spawn('npx', args, {
  stdio: 'inherit',
  env: {
    ...process.env,
    // Ensure npx uses the correct npm registry
    npm_config_registry: 'https://registry.npmjs.org/'
  }
});

// Handle errors
child.on('error', (error) => {
  console.error(`[ERROR] Failed to start mcp-remote: ${error.message}`);
  console.error('[ERROR] Make sure Node.js and npm are installed');
  process.exit(1);
});

// Pass through exit code
child.on('exit', (code, signal) => {
  if (signal) {
    process.exit(1);
  }
  process.exit(code || 0);
});

// Handle termination signals
process.on('SIGINT', () => {
  child.kill('SIGINT');
});

process.on('SIGTERM', () => {
  child.kill('SIGTERM');
});