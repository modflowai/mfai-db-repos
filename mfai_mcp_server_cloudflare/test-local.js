// Test script for local MCP server
async function testMCPServer() {
  const baseUrl = 'http://localhost:8787/mcp';
  // Set this to your API key if you've configured one
  const apiKey = process.env.MCP_API_KEY || '';
  
  console.log('Testing MCP Server at:', baseUrl);
  if (apiKey) {
    console.log('Using API key authentication');
  }
  console.log('---');
  
  // Prepare headers for all requests
  const headers = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }
  
  // Test 0: Initialize connection
  console.log('0. Initializing MCP connection:');
  try {
    
    const initResponse = await fetch(baseUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: {
            name: 'test-client',
            version: '1.0.0',
          },
        },
        id: 0,
      }),
    });
    
    const initResult = await initResponse.json();
    console.log('Response:', JSON.stringify(initResult, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
  
  console.log('\n---');
  
  // Test 1: List tools
  console.log('1. Testing tools/list:');
  try {
    const listResponse = await fetch(baseUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/list',
        id: 1,
      }),
    });
    
    const listResult = await listResponse.json();
    console.log('Response:', JSON.stringify(listResult, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
  
  console.log('\n---');
  
  // Test 2: Call list_repositories_with_navigation
  console.log('2. Testing list_repositories_with_navigation:');
  try {
    const callResponse = await fetch(baseUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
          name: 'list_repositories_with_navigation',
          arguments: {
            include_navigation: true,
          },
        },
        id: 2,
      }),
    });
    
    const callResult = await callResponse.json();
    console.log('Response:', JSON.stringify(callResult, null, 2).substring(0, 500) + '...');
  } catch (error) {
    console.error('Error:', error.message);
  }
  
  console.log('\n---');
  
  // Test 3: Text search
  console.log('3. Testing text search for "modflow":');
  try {
    const searchResponse = await fetch(baseUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
          name: 'mfai_search',
          arguments: {
            query: 'modflow',
            search_type: 'text',
          },
        },
        id: 3,
      }),
    });
    
    const searchResult = await searchResponse.json();
    console.log('Response:', JSON.stringify(searchResult, null, 2).substring(0, 500) + '...');
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Run the tests
testMCPServer();