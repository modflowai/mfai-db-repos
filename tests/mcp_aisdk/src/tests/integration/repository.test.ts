import { createSSEClient } from '@/clients/client-factory';
import { RepositorySchema } from '@/tools/tool-schemas';
import { expect, test, describe } from 'vitest';
import { config } from 'dotenv';

config();

describe('Repository Integration', () => {
  test('should list repositories with navigation guides', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('list_repositories_with_navigation', {
      include_navigation: true,
    });

    // Parse and validate response
    const repositories = JSON.parse(result.content[0].text);
    
    // Validate against schema
    const validatedRepos = repositories.map(repo => 
      RepositorySchema.parse(repo)
    );

    // Check for expected repositories from our database
    const expectedRepos = ['modflowapi', 'flopy', 'modflow6'];
    const foundRepoNames = validatedRepos.map(r => r.name);
    
    expect(foundRepoNames).toEqual(
      expect.arrayContaining(expectedRepos.filter(name => 
        foundRepoNames.includes(name)
      ))
    );

    // Verify navigation guides are included
    const reposWithGuides = validatedRepos.filter(r => r.navigation_guide);
    expect(reposWithGuides.length).toBeGreaterThan(0);

    await client.close();
  });

  test('should list repositories without navigation guides', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('list_repositories_with_navigation', {
      include_navigation: false,
    });

    const repositories = JSON.parse(result.content[0].text);
    
    // When include_navigation is false, navigation_guide should not be included
    repositories.forEach(repo => {
      expect(repo).not.toHaveProperty('navigation_guide');
    });

    // Should still have basic repository info
    repositories.forEach(repo => {
      expect(repo).toHaveProperty('id');
      expect(repo).toHaveProperty('name');
      expect(repo).toHaveProperty('url');
      expect(repo).toHaveProperty('file_count');
    });

    await client.close();
  });

  test('should return valid repository metadata', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('list_repositories_with_navigation', {
      include_navigation: true,
    });

    const repositories = JSON.parse(result.content[0].text);
    
    // Check first repository has all expected fields
    if (repositories.length > 0) {
      const firstRepo = repositories[0];
      
      // Required fields
      expect(firstRepo.id).toBeTypeOf('number');
      expect(firstRepo.name).toBeTypeOf('string');
      expect(firstRepo.url).toBeTypeOf('string');
      expect(firstRepo.url).toMatch(/^https?:\/\//);
      expect(firstRepo.file_count).toBeTypeOf('number');
      expect(firstRepo.file_count).toBeGreaterThanOrEqual(0);
      
      // Timestamps
      expect(firstRepo.created_at).toBeTypeOf('string');
      expect(new Date(firstRepo.created_at).toString()).not.toBe('Invalid Date');
      expect(firstRepo.updated_at).toBeTypeOf('string');
      expect(new Date(firstRepo.updated_at).toString()).not.toBe('Invalid Date');
      
      // Optional fields
      if (firstRepo.navigation_guide) {
        expect(firstRepo.navigation_guide).toBeTypeOf('string');
        expect(firstRepo.navigation_guide.length).toBeGreaterThan(0);
      }
      
      if (firstRepo.repository_type) {
        expect(firstRepo.repository_type).toBeTypeOf('string');
      }
    }

    await client.close();
  });

  test('should handle empty repository list gracefully', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('list_repositories_with_navigation', {
      include_navigation: true,
    });

    const repositories = JSON.parse(result.content[0].text);
    
    // Should always return an array, even if empty
    expect(Array.isArray(repositories)).toBe(true);

    await client.close();
  });

  test('should return repositories in consistent order', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    // First call
    const result1 = await client.callTool('list_repositories_with_navigation', {
      include_navigation: false,
    });
    const repos1 = JSON.parse(result1.content[0].text);

    // Second call
    const result2 = await client.callTool('list_repositories_with_navigation', {
      include_navigation: false,
    });
    const repos2 = JSON.parse(result2.content[0].text);

    // Should return same repositories in same order (ordered by id ASC)
    expect(repos1.map(r => r.id)).toEqual(repos2.map(r => r.id));
    expect(repos1.map(r => r.name)).toEqual(repos2.map(r => r.name));

    await client.close();
  });
});