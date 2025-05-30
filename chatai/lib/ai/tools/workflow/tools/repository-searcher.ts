/**
 * Repository Searcher Tool - Executes search operations against MODFLOW repositories
 */

import { MCPClient, withMCPErrorHandling } from '../../../mcp/client';
import { LLMIntentAnalyzer } from '../../../llm-intent-analyzer';
import { createWorkflowTool } from '../base/workflow-tool';
import { 
  RepositorySearcherInputSchema, 
  type SearchResult
} from '../schemas/tool-schemas';

/**
 * Search a single repository
 */
async function searchRepository(
  mcpClient: MCPClient,
  repo: string, 
  query: string, 
  strategy: string, 
  searchParameters?: any
): Promise<SearchResult[]> {
  const result = await mcpClient.callTool('mfai_search', {
    query,
    search_type: strategy as 'text' | 'semantic',
    repositories: [repo],
    max_results: searchParameters?.maxResults || 10,
  });

  return JSON.parse(result.content[0].text);
}

/**
 * Rank results by relevance using LLM
 */
async function rankResultsByRelevance(results: SearchResult[], query: string): Promise<SearchResult[]> {
  const scoredResults = [];
  
  for (const result of results) {
    try {
      const relevanceAnalysis = await LLMIntentAnalyzer.calculateRelevanceScore(result, query);
      scoredResults.push({
        ...result,
        relevanceScore: relevanceAnalysis.score,
        relevanceReasoning: relevanceAnalysis.reasoning
      });
    } catch (error) {
      // Fallback to original similarity or default score
      scoredResults.push({
        ...result,
        relevanceScore: result.similarity || 0.5,
        relevanceReasoning: "LLM analysis unavailable"
      });
    }
  }

  // Sort by relevance score (highest first)
  return scoredResults.sort((a, b) => (b.relevanceScore || 0) - (a.relevanceScore || 0));
}

/**
 * Calculate search confidence based on results
 */
function calculateSearchConfidence(results: SearchResult[]): number {
  if (results.length === 0) return 0;
  
  const avgRelevance = results.reduce((sum, r) => sum + (r.relevanceScore || 0), 0) / results.length;
  const hasHighQualityResults = results.some(r => (r.relevanceScore || 0) > 0.8);
  
  if (hasHighQualityResults && avgRelevance > 0.6) return 0.9;
  if (avgRelevance > 0.5) return 0.7;
  if (results.length > 3) return 0.6;
  return 0.4;
}

/**
 * Repository Searcher Tool Implementation
 */
export const repositorySearcher = createWorkflowTool({
  name: 'Repository Searcher',
  description: 'Searches MODFLOW repositories using optimized strategy',
  estimatedDuration: 7500,
  retryable: true,
  schema: RepositorySearcherInputSchema,
  
  execute: async ({ query, strategy, repositories, searchParameters }, context) => {
    const startTime = Date.now();

    return withMCPErrorHandling(async () => {
      await context.streamStatus({
        phase: 'starting',
        currentAction: 'Connecting to MODFLOW repositories...'
      });

      const mcpClient = new MCPClient();
      
      const serverUrl = process.env.MCP_SERVER_URL;
      const apiKey = process.env.MCP_API_KEY;
      
      if (!serverUrl || !apiKey) {
        throw new Error('MCP server configuration missing: MCP_SERVER_URL and MCP_API_KEY must be set');
      }
      
      await mcpClient.connect({
        serverUrl,
        apiKey,
      });

      try {
        const targetRepositories = repositories.length > 0 ? repositories : ['flopy', 'modflow6', 'pest', 'mt3d'];
        const results: SearchResult[] = [];
        const totalRepos = targetRepositories.length;
        
        await context.streamStatus({
          phase: 'executing',
          currentAction: `Searching ${totalRepos} repositories...`
        });

        // Execute searches across repositories
        for (let i = 0; i < targetRepositories.length; i++) {
          const repo = targetRepositories[i];
          
          await context.streamStatus({
            phase: 'executing',
            progress: Math.round((i / totalRepos) * 100),
            currentAction: `Searching ${repo}...`
          });
          
          try {
            const repoResults = await searchRepository(mcpClient, repo, query, strategy, searchParameters);
            results.push(...repoResults);
            
            // Stream intermediate results
            await context.streamStatus({
              phase: 'processing',
              currentAction: `Found ${repoResults.length} results in ${repo}`
            });
            
          } catch (error) {
            console.warn(`Search failed for ${repo}:`, error);
            // Continue with other repositories
            await context.streamStatus({
              phase: 'processing',
              currentAction: `Search failed for ${repo}, continuing...`
            });
          }
        }
        
        await context.streamStatus({
          phase: 'processing',
          currentAction: `Ranking ${results.length} results by relevance...`
        });

        // Rank results by LLM-determined relevance
        const rankedResults = await rankResultsByRelevance(results, query);
        
        await context.streamStatus({
          phase: 'completed',
          currentAction: `Found ${rankedResults.length} ranked results`
        });

        const executionTime = Date.now() - startTime;
        const confidence = calculateSearchConfidence(rankedResults);

        return {
          success: true,
          data: {
            results: rankedResults,
            totalFound: results.length,
            repositoriesSearched: targetRepositories,
            searchStrategy: strategy
          },
          shortSummary: `📄 Found ${rankedResults.length} relevant documents across ${targetRepositories.length} repositories`,
          confidence,
          metadata: {
            executionTime,
            cacheHit: false // Could implement caching later
          }
        };
      } finally {
        await mcpClient.close();
      }
    });
  }
});