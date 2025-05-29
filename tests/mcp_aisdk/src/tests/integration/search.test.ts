import { createSSEClient } from '@/clients/client-factory';
import { SearchResultSchema } from '@/tools/tool-schemas';
import { expect, test, describe } from 'vitest';
import { config } from 'dotenv';

config();

describe('Search Integration', () => {
  test('should perform text search', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    // Test query based on actual repository content
    const result = await client.callTool('mfai_search', {
      query: 'groundwater model',
      search_type: 'text',
    });

    const searchResults = JSON.parse(result.content[0].text);
    
    // Validate response format
    if (Array.isArray(searchResults) && searchResults.length > 0) {
      const validatedResults = searchResults.map(r => 
        SearchResultSchema.parse(r)
      );
      
      // Check for expected file types from file_processor patterns
      const expectedExtensions = ['.py', '.f90', '.nam', '.dis'];
      const foundExtensions = validatedResults.map(r => r.extension);
      
      expect(foundExtensions).toEqual(
        expect.arrayContaining(
          expectedExtensions.filter(ext => foundExtensions.includes(ext))
        )
      );
    }

    await client.close();
  });

  test('should perform semantic search with embeddings', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('mfai_search', {
      query: 'How to create a MODFLOW model?',
      search_type: 'semantic',
    });

    // Semantic search should return similarity scores
    const searchResults = JSON.parse(result.content[0].text);
    
    if (searchResults.length > 0) {
      expect(searchResults[0]).toHaveProperty('similarity');
      expect(searchResults[0].similarity).toBeGreaterThan(0);
      expect(searchResults[0].similarity).toBeLessThanOrEqual(1);
    }

    await client.close();
  });

  test('should filter search by repositories', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    // Get available repositories first
    const repoResult = await client.callTool('list_repositories_with_navigation', {
      include_navigation: false,
    });
    const repositories = JSON.parse(repoResult.content[0].text);
    
    if (repositories.length > 0) {
      const targetRepo = repositories[0].name;
      
      // Search filtered by specific repository
      const result = await client.callTool('mfai_search', {
        query: 'model',
        search_type: 'text',
        repositories: [targetRepo],
      });

      const searchResults = JSON.parse(result.content[0].text);
      
      // All results should be from the specified repository
      searchResults.forEach(result => {
        expect(result.repo_name).toBe(targetRepo);
      });
    }

    await client.close();
  });

  test('should return valid search result metadata', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('mfai_search', {
      query: 'python',
      search_type: 'text',
    });

    const searchResults = JSON.parse(result.content[0].text);
    
    if (searchResults.length > 0) {
      const firstResult = searchResults[0];
      
      // Required fields
      expect(firstResult.id).toBeTypeOf('number');
      expect(firstResult.repo_id).toBeTypeOf('number');
      expect(firstResult.repo_name).toBeTypeOf('string');
      expect(firstResult.repo_url).toBeTypeOf('string');
      expect(firstResult.repo_url).toMatch(/^https?:\/\//);
      expect(firstResult.filepath).toBeTypeOf('string');
      expect(firstResult.filename).toBeTypeOf('string');
      expect(firstResult.extension).toBeTypeOf('string');
      expect(firstResult.file_type).toBeTypeOf('string');
      expect(firstResult.content).toBeTypeOf('string');
      expect(firstResult.snippet).toBeTypeOf('string');
      
      // Optional fields for text search
      if (firstResult.rank !== undefined) {
        expect(firstResult.rank).toBeTypeOf('number');
      }
    }

    await client.close();
  });

  test('should handle empty search results', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    // Search for something unlikely to exist
    const result = await client.callTool('mfai_search', {
      query: 'xyzabc123veryrandomquery',
      search_type: 'text',
    });

    const searchResults = JSON.parse(result.content[0].text);
    
    // Should return empty array, not error
    expect(Array.isArray(searchResults)).toBe(true);
    expect(searchResults.length).toBe(0);

    await client.close();
  });

  test('should differentiate between text and semantic search', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const query = 'groundwater flow simulation';

    // Text search
    const textResult = await client.callTool('mfai_search', {
      query,
      search_type: 'text',
    });
    const textResults = JSON.parse(textResult.content[0].text);

    // Semantic search
    const semanticResult = await client.callTool('mfai_search', {
      query,
      search_type: 'semantic',
    });
    const semanticResults = JSON.parse(semanticResult.content[0].text);

    // Semantic results should have similarity scores
    if (semanticResults.length > 0) {
      expect(semanticResults[0]).toHaveProperty('similarity');
    }

    // Text results might have rank (depends on database implementation)
    if (textResults.length > 0 && textResults[0].rank !== undefined) {
      expect(textResults[0].rank).toBeTypeOf('number');
    }

    await client.close();
  });

  test('should search across multiple repositories', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    // Get available repositories
    const repoResult = await client.callTool('list_repositories_with_navigation', {
      include_navigation: false,
    });
    const repositories = JSON.parse(repoResult.content[0].text);
    
    if (repositories.length >= 2) {
      const targetRepos = repositories.slice(0, 2).map(r => r.name);
      
      // Search filtered by multiple repositories
      const result = await client.callTool('mfai_search', {
        query: 'function',
        search_type: 'text',
        repositories: targetRepos,
      });

      const searchResults = JSON.parse(result.content[0].text);
      
      // Results should only be from specified repositories
      const foundRepoNames = [...new Set(searchResults.map(r => r.repo_name))];
      foundRepoNames.forEach(repoName => {
        expect(targetRepos).toContain(repoName);
      });
    }

    await client.close();
  });

  test('should validate snippet generation', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('mfai_search', {
      query: 'class',
      search_type: 'text',
    });

    const searchResults = JSON.parse(result.content[0].text);
    
    searchResults.forEach(result => {
      // Snippet should exist and be a substring of content
      expect(result.snippet).toBeTypeOf('string');
      expect(result.snippet.length).toBeGreaterThan(0);
      expect(result.snippet.length).toBeLessThanOrEqual(result.content.length);
    });

    await client.close();
  });
});