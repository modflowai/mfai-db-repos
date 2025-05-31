#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');

// Load environment variables
require('dotenv').config();

// Test the MCP server with a simple request
function testMCPServer() {
  console.log('🧪 Testing MFAI Document Retrieval MCP Server...\n');

  const server = spawn('node', ['build/index.js'], {
    stdio: 'pipe',
    env: {
      ...process.env,
      MODFLOW_AI_MCP_00_CONNECTION_STRING: process.env.MODFLOW_AI_MCP_00_CONNECTION_STRING,
      GOOGLE_GENAI_API_KEY: process.env.GOOGLE_GENAI_API_KEY,
      OPENAI_API_KEY: process.env.OPENAI_API_KEY || ''
    }
  });

  let buffer = '';

  server.stdout.on('data', (data) => {
    buffer += data.toString();
    console.log('📤 Server Response:', data.toString());
  });

  server.stderr.on('data', (data) => {
    console.log('📝 Server Log:', data.toString());
  });

  server.on('close', (code) => {
    console.log(`\n🏁 Server process exited with code ${code}`);
  });

  // Test 1: List tools
  console.log('📋 Test 1: Listing available tools...');
  const listToolsRequest = {
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list',
    params: {}
  };

  server.stdin.write(JSON.stringify(listToolsRequest) + '\n');

  // Test 2: Call document retrieval tool (text search)
  setTimeout(() => {
    console.log('\n🔍 Test 2: Testing document retrieval tool (text search)...');
    const callToolRequest = {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/call',
      params: {
        name: 'mfai_document_retrieval',
        arguments: {
          query: 'PEST-IES',
          repository: 'pestpp',
          search_type: 'text'
        }
      }
    };

    server.stdin.write(JSON.stringify(callToolRequest) + '\n');

    // Test 3: Try semantic search (will fallback to text)
    setTimeout(() => {
      console.log('\n🔍 Test 3: Testing semantic search fallback...');
      const semanticRequest = {
        jsonrpc: '2.0',
        id: 3,
        method: 'tools/call',
        params: {
          name: 'mfai_document_retrieval',
          arguments: {
            query: 'iterative ensemble smoother',
            repository: 'pestpp',
            search_type: 'semantic'
          }
        }
      };

      server.stdin.write(JSON.stringify(semanticRequest) + '\n');

      // Close after tests
      setTimeout(() => {
        console.log('\n✅ Tests completed!');
        server.kill();
      }, 8000);
    }, 5000);
  }, 2000);
}

// Check if build directory exists
if (!fs.existsSync('build/index.js')) {
  console.error('❌ Build not found. Run "npm run build" first.');
  process.exit(1);
}

testMCPServer();