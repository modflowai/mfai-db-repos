/**
 * Intelligent MFAI Search Tool with LLM-guided parallel processing
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

export const intelligentMfaiSearch = ({ session, dataStream }: ToolProps) =>
  tool({
    description: 'Intelligent MFAI repository search that uses LLM analysis to automatically optimize search strategy and run parallel searches when beneficial. The LLM determines the best approach based on your query.',
    parameters: z.object({
      query: z.string().describe('Your search query - the LLM will analyze this to determine optimal strategy'),
      strategy: z.enum(['auto', 'text', 'semantic', 'hybrid']).default('auto')
        .describe('Search strategy - "auto" lets the LLM decide the optimal approach'),
      repositories: z.array(z.string()).optional()
        .describe('Specific repositories to search (leave empty to let LLM decide)'),
      parallel_search: z.boolean().optional().default(false)
        .describe('Whether to run parallel searches - LLM will decide if not specified'),
    }),
    execute: async ({ query, strategy, repositories, parallel_search }) => {
      return withMCPErrorHandling(async () => {
        // Stream initial analysis
        dataStream.writeData({
          type: 'text-delta',
          content: '🧠 Analyzing your query with LLM...\n\n',
        });

        // LLM analyzes the query to determine optimal strategy
        const llmAnalysis = await LLMIntentAnalyzer.analyzeUserIntent(query);
        
        // Stream LLM reasoning
        dataStream.writeData({
          type: 'text-delta',
          content: `💭 **LLM Analysis**: ${llmAnalysis.reasoning}\n` +
                  `🎯 **Strategy**: ${llmAnalysis.optimalSearchStrategy}\n` +
                  `⚡ **Parallel**: ${llmAnalysis.benefitsFromParallelSearch ? 'Yes' : 'No'}\n\n`,
        });

        const mcpClient = new MCPClient();
        await mcpClient.connect({
          serverUrl: process.env.MCP_SERVER_URL!,
          apiKey: process.env.MCP_API_KEY!,
        });

        let searchStrategy = strategy;
        let useParallelSearch = parallel_search;
        let targetRepositories = repositories;

        // Use LLM analysis if auto mode
        if (strategy === 'auto') {
          searchStrategy = llmAnalysis.optimalSearchStrategy;
          useParallelSearch = llmAnalysis.benefitsFromParallelSearch;
          targetRepositories = llmAnalysis.targetRepositories || repositories;
        }

        let allResults: any[] = [];

        // Execute parallel searches if beneficial (LLM-guided)
        if (useParallelSearch || searchStrategy === 'hybrid') {
          dataStream.writeData({
            type: 'text-delta',
            content: '🔄 Running parallel searches for comprehensive results...\n\n',
          });

          const [textResults, semanticResults] = await Promise.all([
            mcpClient.callTool('mfai_search', {
              query,
              search_type: 'text',
              repositories: targetRepositories,
            }),
            mcpClient.callTool('mfai_search', {
              query,
              search_type: 'semantic',
              repositories: targetRepositories,
            })
          ]);

          const textData = JSON.parse(textResults.content[0].text);
          const semanticData = JSON.parse(semanticResults.content[0].text);

          // LLM-guided result merging and ranking
          allResults = await mergeResultsWithLLM(textData, semanticData, query);
          
          dataStream.writeData({
            type: 'text-delta',
            content: `✅ Merged ${textData.length} text + ${semanticData.length} semantic results\n\n`,
          });
        } else {
          // Single search execution
          dataStream.writeData({
            type: 'text-delta',
            content: `🔍 Executing ${searchStrategy} search...\n\n`,
          });

          // Convert strategy to MCP-compatible type
          let mcpSearchType: 'text' | 'semantic';
          if (searchStrategy === 'hybrid') {
            // For hybrid, default to semantic search as it's more comprehensive
            mcpSearchType = 'semantic';
          } else {
            mcpSearchType = searchStrategy as 'text' | 'semantic';
          }

          const result = await mcpClient.callTool('mfai_search', {
            query,
            search_type: mcpSearchType,
            repositories: targetRepositories,
          });

          allResults = JSON.parse(result.content[0].text);
        }

        // Stream results with LLM-powered relevance scoring
        dataStream.writeData({
          type: 'text-delta',
          content: `📊 Found ${allResults.length} results. Analyzing relevance...\n\n`,
        });

        const scoredResults = [];
        for (const [index, searchResult] of allResults.entries()) {
          // LLM calculates relevance score with reasoning
          const relevanceAnalysis = await LLMIntentAnalyzer.calculateRelevanceScore(searchResult, query);
          
          const scoredResult = {
            ...searchResult,
            relevanceScore: relevanceAnalysis.score,
            relevanceReasoning: relevanceAnalysis.reasoning,
            rank: index + 1
          };
          
          scoredResults.push(scoredResult);

          // Stream individual result
          dataStream.writeData({
            type: 'text-delta',
            content: `**${index + 1}. ${searchResult.filename}** (${(relevanceAnalysis.score * 100).toFixed(1)}% relevant)\n` +
                    `📁 Repository: ${searchResult.repo_name}\n` +
                    `📄 Path: \`${searchResult.filepath}\`\n` +
                    `💡 Why relevant: ${relevanceAnalysis.reasoning}\n` +
                    `🔍 Snippet: ${searchResult.snippet}\n\n`,
          });
        }

        // Sort by LLM relevance score
        scoredResults.sort((a, b) => b.relevanceScore - a.relevanceScore);

        // Final step: Instruct to analyze results and provide comprehensive answer
        dataStream.writeData({
          type: 'text-delta',
          content: `\n📝 **Analysis Complete!** Now I'll review these results to answer your question: "${query}"\n\n`,
        });

        await mcpClient.close();

        // Return results with instruction for LLM to analyze and answer
        return {
          query,
          strategy: searchStrategy,
          llmAnalysis: {
            reasoning: llmAnalysis.reasoning,
            confidence: llmAnalysis.confidence,
            optimalStrategy: llmAnalysis.optimalSearchStrategy,
            parallelBenefit: llmAnalysis.benefitsFromParallelSearch
          },
          results: scoredResults,
          totalFound: allResults.length,
          repositoriesSearched: targetRepositories || 'all',
          timestamp: new Date().toISOString(),
          instruction: `Based on the search results above, please provide a comprehensive answer to the user's question: "${query}". Use the information from the most relevant results to explain what they're asking about, including examples, usage, and any important details found in the documentation.`
        };
      });
    },
  });

/**
 * LLM-guided result merging and ranking
 */
async function mergeResultsWithLLM(textResults: any[], semanticResults: any[], query: string): Promise<any[]> {
  // Simple deduplication by filepath first
  const allResults = [...textResults];
  const textPaths = new Set(textResults.map(r => r.filepath));
  
  // Add semantic results that aren't already in text results
  for (const semanticResult of semanticResults) {
    if (!textPaths.has(semanticResult.filepath)) {
      allResults.push({
        ...semanticResult,
        searchType: 'semantic'
      });
    } else {
      // Mark text results that also appeared in semantic search
      const textResult = allResults.find(r => r.filepath === semanticResult.filepath);
      if (textResult) {
        textResult.appearedInBoth = true;
        textResult.semanticSimilarity = semanticResult.similarity;
      }
    }
  }

  return allResults;
}