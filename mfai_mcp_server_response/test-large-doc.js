#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');

// Load environment variables
require('dotenv').config();

// Test the MCP server with a large document query
function testLargeDocument() {
  console.log('🧪 Testing Large Document Compression...\n');

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
    console.log('📤 Server Response:', data.toString().substring(0, 1000) + '...');
  });

  server.stderr.on('data', (data) => {
    console.log('📝 Server Log:', data.toString());
  });

  server.on('close', (code) => {
    console.log(`\n🏁 Server process exited with code ${code}`);
  });

  // Test: Query for PESTPP-IES which should return a large document
  setTimeout(() => {
    console.log('\n🔍 Testing large document compression (PESTPP-IES)...');
    const callToolRequest = {
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/call',
      params: {
        name: 'mfai_document_retrieval',
        arguments: {
          query: 'PESTPP-IES ensemble smoother',
          repository: 'pestpp',
          search_type: 'text',
          context: 'I need to understand how to configure and run PESTPP-IES for parameter estimation in groundwater models, including key control file settings and iteration parameters'
        }
      }
    };

    server.stdin.write(JSON.stringify(callToolRequest) + '\n');

    // Close after test
    setTimeout(() => {
      console.log('\n✅ Large document test completed!');
      server.kill();
    }, 15000);
  }, 1000);
}

// Check if build directory exists
if (!fs.existsSync('build/index.js')) {
  console.error('❌ Build not found. Run "npm run build" first.');
  process.exit(1);
}

testLargeDocument();