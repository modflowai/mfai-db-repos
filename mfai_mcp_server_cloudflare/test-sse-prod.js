// Test script for production SSE MCP server endpoint
import EventSource from 'eventsource';

async function testSSEEndpoint() {
  const baseUrl = 'https://mfai-repository-navigator.little-grass-273a.workers.dev';
  // Set this to your API key if you've configured one
  const apiKey = process.env.MCP_API_KEY || '';
  
  console.log('Testing SSE MCP Server at:', baseUrl);
  if (apiKey) {
    console.log('Using API key authentication');
  } else {
    console.log('⚠️  No API key provided - set MCP_API_KEY environment variable');
  }
  console.log('---');
  
  // Test 1: Health endpoint first
  console.log('1. Testing health endpoint (/health):');
  try {
    const healthResponse = await fetch(`${baseUrl}/health`);
    const healthResult = await healthResponse.json();
    console.log('Health check:', JSON.stringify(healthResult, null, 2));
  } catch (error) {
    console.error('Health check error:', error.message);
    return;
  }
  
  console.log('\n---');
  
  // Test 2: SSE endpoint
  console.log('2. Testing SSE endpoint (/sse):');
  
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
  
  eventSource.addEventListener('message', function(event) {
    console.log('📥 Received message:', event.data);
  });
  
  eventSource.onerror = function(event) {
    console.error('❌ SSE error:', event);
    if (event.status) {
      console.error('Status:', event.status);
    }
    if (event.data) {
      console.error('Data:', event.data);
    }
    eventSource.close();
  };
  
  // Keep connection alive for testing
  setTimeout(() => {
    console.log('🔌 Closing SSE connection after 15 seconds');
    eventSource.close();
  }, 15000);
}

async function testMessagesEndpoint(messagesUrl, apiKey) {
  console.log('\n3. Testing messages endpoint:', messagesUrl);
  
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
    
    if (!initResponse.ok) {
      console.error(`  ❌ Initialize failed with status: ${initResponse.status}`);
      const errorText = await initResponse.text();
      console.error('  Error response:', errorText);
      return;
    }
    
    const initResult = await initResponse.json();
    console.log('  ✅ Initialize response received');
    console.log('  Server info:', initResult.result?.serverInfo);
  } catch (error) {
    console.error('  ❌ Initialize error:', error.message);
    return;
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
    
    if (!listResponse.ok) {
      console.error(`  ❌ Tools list failed with status: ${listResponse.status}`);
      return;
    }
    
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
    
    if (!callResponse.ok) {
      console.error(`  ❌ Tool call failed with status: ${callResponse.status}`);
      return;
    }
    
    const callResult = await callResponse.json();
    console.log('  ✅ Tool call response received');
    console.log('  Repositories found:', callResult.result?.content?.[0]?.text ? 'Yes' : 'No');
  } catch (error) {
    console.error('  ❌ Tool call error:', error.message);
  }
}

// Test with mcp-remote simulation
async function testMcpRemoteCompatibility() {
  console.log('\n4. Testing mcp-remote compatibility:');
  console.log('   This simulates how mcp-remote would connect to the SSE endpoint');
  
  const baseUrl = 'https://mfai-repository-navigator.little-grass-273a.workers.dev';
  const apiKey = process.env.MCP_API_KEY || '';
  
  if (!apiKey) {
    console.log('   ⚠️  Skipping - requires API key');
    return;
  }
  
  // Simulate the mcp-remote connection flow
  console.log('   Step 1: Connect to SSE endpoint with Bearer token');
  console.log(`   Command: npx mcp-remote ${baseUrl}/sse --header "Authorization:Bearer ${apiKey.substring(0, 8)}..."`);
  
  // Test that the header authentication works
  try {
    const testResponse = await fetch(`${baseUrl}/sse`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    });
    
    if (testResponse.ok) {
      console.log('   ✅ Bearer token authentication successful');
    } else {
      console.log(`   ❌ Authentication failed: ${testResponse.status}`);
    }
  } catch (error) {
    console.error('   ❌ Connection error:', error.message);
  }
}

// Run the tests
console.log('🧪 Starting Production SSE MCP Server Tests');
console.log('Set MCP_API_KEY environment variable for authenticated testing\n');

testSSEEndpoint();
setTimeout(testMcpRemoteCompatibility, 5000);