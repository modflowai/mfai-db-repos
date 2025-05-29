// Test script for SSE MCP server endpoint
import { EventSource } from 'eventsource';

async function testSSEEndpoint() {
  const baseUrl = 'http://localhost:8787';
  // Set this to your API key if you've configured one
  const apiKey = process.env.MCP_API_KEY || '';
  
  console.log('Testing SSE MCP Server at:', baseUrl);
  if (apiKey) {
    console.log('Using API key authentication');
  }
  console.log('---');
  
  // Test 1: SSE endpoint
  console.log('1. Testing SSE endpoint (/sse):');
  
  const sseHeaders = {};
  if (apiKey) {
    sseHeaders['Authorization'] = `Bearer ${apiKey}`;
  }
  
  const eventSource = new EventSource(`${baseUrl}/sse`, {
    headers: sseHeaders,
  });
  
  let messagesUrl = null;
  
  eventSource.onopen = function(event) {
    console.log('✅ SSE connection opened');
  };
  
  eventSource.addEventListener('endpoint', function(event) {
    messagesUrl = event.data;
    console.log('📡 Received endpoint URL:', messagesUrl);
    
    // Test the messages endpoint once we have the URL
    testMessagesEndpoint(messagesUrl, apiKey);
  });
  
  eventSource.onerror = function(event) {
    console.error('❌ SSE error:', event);
    eventSource.close();
  };
  
  // Keep connection alive for testing
  setTimeout(() => {
    console.log('🔌 Closing SSE connection after 10 seconds');
    eventSource.close();
  }, 10000);
}

async function testMessagesEndpoint(messagesUrl, apiKey) {
  console.log('\n2. Testing messages endpoint:', messagesUrl);
  
  const headers = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }
  
  // Test initialize
  console.log('  Testing initialize...');
  try {
    const initResponse = await fetch(messagesUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: {
            name: 'sse-test-client',
            version: '1.0.0',
          },
        },
        id: 0,
      }),
    });
    
    const initResult = await initResponse.json();
    console.log('  ✅ Initialize response received');
  } catch (error) {
    console.error('  ❌ Initialize error:', error.message);
  }
  
  // Test list tools
  console.log('  Testing tools/list...');
  try {
    const listResponse = await fetch(messagesUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/list',
        id: 1,
      }),
    });
    
    const listResult = await listResponse.json();
    console.log('  ✅ Tools list response received');
    console.log('  Tools available:', listResult.result?.tools?.map(t => t.name) || []);
  } catch (error) {
    console.error('  ❌ Tools list error:', error.message);
  }
  
  // Test tool call
  console.log('  Testing tool call...');
  try {
    const callResponse = await fetch(messagesUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
          name: 'list_repositories_with_navigation',
          arguments: {
            include_navigation: false, // Keep response smaller for testing
          },
        },
        id: 2,
      }),
    });
    
    const callResult = await callResponse.json();
    console.log('  ✅ Tool call response received');
  } catch (error) {
    console.error('  ❌ Tool call error:', error.message);
  }
}

async function testHealthEndpoint() {
  const baseUrl = 'http://localhost:8787';
  
  console.log('\n3. Testing health endpoint (/health):');
  try {
    const healthResponse = await fetch(`${baseUrl}/health`);
    const healthResult = await healthResponse.json();
    console.log('Health check:', JSON.stringify(healthResult, null, 2));
  } catch (error) {
    console.error('Health check error:', error.message);
  }
}

// Run the tests
console.log('🧪 Starting SSE MCP Server Tests');
console.log('Make sure to run: npm run dev\n');

testHealthEndpoint();
testSSEEndpoint();