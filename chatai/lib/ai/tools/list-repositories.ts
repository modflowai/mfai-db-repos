/**
 * List Repositories Tool with LLM-guided presentation
 */

import { tool } from 'ai';
import { z } from 'zod';
import { MCPClient, withMCPErrorHandling } from '../mcp/client';
import { LLMIntentAnalyzer } from '../llm-intent-analyzer';
import type { DataStreamWriter } from 'ai';

interface ToolProps {
  session: any;
  dataStream: DataStreamWriter;
}

export const listRepositories = ({ session, dataStream }: ToolProps) => 
  tool({
    description: 'List MODFLOW AI repositories with navigation guides. The LLM will analyze what information would be most helpful for your specific query.',
    parameters: z.object({
      include_navigation: z.boolean().optional().default(true)
        .describe('Include detailed navigation guides for each repository'),
      user_query: z.string().optional()
        .describe('The original user query to help LLM customize the presentation'),
    }),
    execute: async ({ include_navigation, user_query }) => {
      console.log('📚 listRepositories tool EXECUTED with params:', { include_navigation, user_query });
      console.log('📚 listRepositories - dataStream available:', !!dataStream);
      
      return withMCPErrorHandling(async () => {
        console.log('📚 listRepositories - inside withMCPErrorHandling');
        
        // No streaming - just fetch data and return like weather tool
        const mcpClient = new MCPClient();
        await mcpClient.connect({
          serverUrl: process.env.MCP_SERVER_URL!,
          apiKey: process.env.MCP_API_KEY!,
        });

        const result = await mcpClient.callTool('list_repositories_with_navigation', {
          include_navigation,
        });

        const repositories = JSON.parse(result.content[0].text);

        // Process data but don't stream - return structured result like weather tool
        let enhancedRepos = repositories;
        
        if (user_query) {
          // LLM determines relevance and ordering for user's specific needs
          enhancedRepos = await Promise.all(
            repositories.map(async (repo: any) => {
              const relevanceAnalysis = await LLMIntentAnalyzer.calculateRelevanceScore(
                {
                  filename: repo.name,
                  repo_name: repo.name,
                  filepath: repo.url,
                  snippet: repo.navigation_guide || repo.description || '',
                },
                user_query
              );

              return {
                ...repo,
                relevanceScore: relevanceAnalysis.score,
                relevanceReasoning: relevanceAnalysis.reasoning,
              };
            })
          );

          // Sort by LLM relevance score
          enhancedRepos.sort((a, b) => b.relevanceScore - a.relevanceScore);
        }

        await mcpClient.close();
        
        // Return structured data like weather tool - no streaming
        return {
          repositories: enhancedRepos,
          count: repositories.length,
          userQuery: user_query || null,
          sortedByRelevance: !!user_query,
          timestamp: new Date().toISOString(),
        };
      });
    },
  });