#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');

// Load environment variables
require('dotenv').config();

// Test both MCP tools
function testBothTools() {
  console.log('🧪 Testing Both MCP Tools...\n');

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
    const output = data.toString();
    if (output.length > 1000) {
      console.log('📤 Server Response:', output.substring(0, 500) + '... [truncated] ...' + output.substring(output.length - 200));
    } else {
      console.log('📤 Server Response:', output);
    }
  });

  server.stderr.on('data', (data) => {
    console.log('📝 Server Log:', data.toString());
  });

  server.on('close', (code) => {
    console.log(`\n🏁 Server process exited with code ${code}`);
  });

  // Test 1: List tools
  setTimeout(() => {
    console.log('📋 Test 1: Listing available tools...');
    const listToolsRequest = {
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/list',
      params: {}
    };

    server.stdin.write(JSON.stringify(listToolsRequest) + '\n');
  }, 1000);

  // Test 2: List repositories
  setTimeout(() => {
    console.log('\n📚 Test 2: Listing repositories...');
    const repoListRequest = {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/call',
      params: {
        name: 'list_repositories_with_navigation',
        arguments: {
          include_navigation: true
        }
      }
    };

    server.stdin.write(JSON.stringify(repoListRequest) + '\n');
  }, 3000);

  // Test 3: Document retrieval with context
  setTimeout(() => {
    console.log('\n🔍 Test 3: Document retrieval with context...');
    const docRetrievalRequest = {
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: {
        name: 'mfai_document_retrieval',
        arguments: {
          query: 'PESTPP-IES configuration',
          repository: 'pestpp',
          search_type: 'text',
          context: 'I need to understand the key control file parameters for running PESTPP-IES iterative ensemble smoother'
        }
      }
    };

    server.stdin.write(JSON.stringify(docRetrievalRequest) + '\n');

    // Close after tests
    setTimeout(() => {
      console.log('\n✅ All tests completed!');
      server.kill();
    }, 15000);
  }, 6000);
}

// Check if build directory exists
if (!fs.existsSync('build/index.js')) {
  console.error('❌ Build not found. Run "npm run build" first.');
  process.exit(1);
}

testBothTools();