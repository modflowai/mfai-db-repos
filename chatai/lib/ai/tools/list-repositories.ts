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
      return withMCPErrorHandling(async () => {
        // Stream real-time status updates
        dataStream.writeData({
          type: 'text-delta',
          content: '🔍 Fetching MODFLOW repositories...\n\n',
        });

        const mcpClient = new MCPClient();
        await mcpClient.connect({
          serverUrl: process.env.MCP_SERVER_URL!,
          apiKey: process.env.MCP_API_KEY!,
        });

        const result = await mcpClient.callTool('list_repositories_with_navigation', {
          include_navigation,
        });

        const repositories = JSON.parse(result.content[0].text);

        // LLM analyzes how to present repositories based on user query
        if (user_query) {
          dataStream.writeData({
            type: 'text-delta',
            content: '🧠 Analyzing which repositories are most relevant for your query...\n\n',
          });

          // LLM determines relevance and ordering for user's specific needs
          const enhancedRepos = await Promise.all(
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

          // Stream results with LLM-guided presentation
          dataStream.writeData({
            type: 'text-delta',
            content: `📚 Found ${repositories.length} repositories. Here are the most relevant for your query:\n\n`,
          });

          for (const repo of enhancedRepos) {
            const relevanceIndicator = repo.relevanceScore > 0.7 ? '🔥' : 
                                     repo.relevanceScore > 0.4 ? '⭐' : '📁';
            
            dataStream.writeData({
              type: 'text-delta',
              content: `${relevanceIndicator} **${repo.name}** (${repo.file_count} files) - ${(repo.relevanceScore * 100).toFixed(0)}% relevant\n` +
                      `🔗 ${repo.url}\n` +
                      `💡 Why relevant: ${repo.relevanceReasoning}\n` +
                      (repo.navigation_guide ? `📖 ${repo.navigation_guide.substring(0, 200)}...\n` : '') +
                      '\n',
            });
          }

          await mcpClient.close();
          return {
            repositories: enhancedRepos,
            count: repositories.length,
            userQuery: user_query,
            sortedByRelevance: true,
            timestamp: new Date().toISOString(),
          };
        } else {
          // Standard presentation without specific user context
          dataStream.writeData({
            type: 'text-delta',
            content: `📚 Found ${repositories.length} MODFLOW repositories:\n\n`,
          });

          for (const repo of repositories) {
            dataStream.writeData({
              type: 'text-delta',
              content: `📁 **${repo.name}** (${repo.file_count} files)\n` +
                      `🔗 ${repo.url}\n` +
                      (repo.navigation_guide ? `📖 ${repo.navigation_guide.substring(0, 200)}...\n` : '') +
                      '\n',
            });
          }

          await mcpClient.close();
          return {
            repositories,
            count: repositories.length,
            userQuery: null,
            sortedByRelevance: false,
            timestamp: new Date().toISOString(),
          };
        }
      });
    },
  });