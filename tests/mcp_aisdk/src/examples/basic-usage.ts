import { createSSEClient } from '@/clients/client-factory';
import { config } from 'dotenv';

config();

async function basicUsageExample() {
  console.log('🚀 MCP AI SDK Basic Usage Example\n');
  
  // Create client
  const client = await createSSEClient({
    apiKey: process.env.MCP_API_KEY!,
    serverUrl: process.env.MCP_SERVER_URL!,
  });

  try {
    // 1. List available tools
    console.log('📋 Available Tools:');
    const tools = await client.listTools();
    tools.forEach(tool => {
      console.log(`  - ${tool.name}: ${tool.description}`);
    });
    console.log();

    // 2. List repositories
    console.log('📚 Repositories:');
    const repoResult = await client.callTool('list_repositories_with_navigation', {
      include_navigation: false,
    });
    
    const repositories = JSON.parse(repoResult.content[0].text);
    repositories.forEach(repo => {
      console.log(`  - ${repo.name} (${repo.file_count} files) - ${repo.url}`);
    });
    console.log();

    // 3. Perform a simple text search
    console.log('🔍 Text Search Example:');
    console.log('Searching for "groundwater model"...\n');
    
    const searchResult = await client.callTool('mfai_search', {
      query: 'groundwater model',
      search_type: 'text',
    });
    
    const searchResults = JSON.parse(searchResult.content[0].text);
    console.log(`Found ${searchResults.length} results\n`);
    
    // Show first 5 results
    searchResults.slice(0, 5).forEach((result, idx) => {
      console.log(`${idx + 1}. ${result.filepath}`);
      console.log(`   Repository: ${result.repo_name}`);
      console.log(`   File type: ${result.file_type}`);
      console.log(`   Snippet: ${result.snippet.substring(0, 100)}...`);
      console.log();
    });

    // 4. Perform a semantic search
    console.log('🧠 Semantic Search Example:');
    console.log('Searching for "How to simulate aquifer pumping?"...\n');
    
    const semanticResult = await client.callTool('mfai_search', {
      query: 'How to simulate aquifer pumping?',
      search_type: 'semantic',
    });
    
    const semanticResults = JSON.parse(semanticResult.content[0].text);
    console.log(`Found ${semanticResults.length} results\n`);
    
    // Show top 3 results with similarity scores
    semanticResults.slice(0, 3).forEach((result, idx) => {
      console.log(`${idx + 1}. ${result.filepath}`);
      console.log(`   Repository: ${result.repo_name}`);
      console.log(`   Similarity: ${result.similarity.toFixed(4)}`);
      console.log(`   Snippet: ${result.snippet.substring(0, 150)}...`);
      console.log();
    });

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await client.close();
    console.log('✅ Done!');
  }
}

// Run the example
if (require.main === module) {
  basicUsageExample().catch(console.error);
}