/**
 * Response Generator Tool - Synthesizes search results into comprehensive answers
 */

import { generateText } from 'ai';
import { myProvider } from '../../../providers';
import { createWorkflowTool } from '../base/workflow-tool';
import { 
  ResponseGeneratorInputSchema, 
  type SearchResult
} from '../schemas/tool-schemas';

/**
 * Synthesize search results into a comprehensive answer
 */
async function synthesizeAnswer({
  query,
  results,
  context: analysisContext
}: {
  query: string;
  results: SearchResult[];
  context: any;
}): Promise<{ text: string; confidence: number; tokensUsed: number; relatedLinks: string[] }> {
  try {
    const result = await generateText({
      model: myProvider.languageModel('chat-model'),
      messages: [
        {
          role: 'system',
          content: `You are a MODFLOW/PEST documentation expert. Your job is to synthesize search results into a comprehensive, helpful answer.

          Guidelines:
          1. **Direct Answer**: Start with a clear, direct answer to the user's question
          2. **Use Examples**: Include code examples, usage patterns, or practical implementations from the search results
          3. **Cite Sources**: Reference specific files, functions, or documentation sections
          4. **Be Comprehensive**: Cover multiple aspects of the topic when relevant
          5. **Stay Accurate**: Only use information directly from the search results
          6. **Be Practical**: Focus on how the user can apply this information
          7. **Formatting**: Write naturally flowing text. When mentioning technical terms, keywords, or program names, incorporate them naturally into sentences rather than using code blocks or special formatting for individual words.

          Format your response as a helpful explanation that teaches the user about the topic.
          Include relevant code snippets, examples, and references to specific files when available.
          
          IMPORTANT: Write in natural prose. Don't use code blocks for individual keywords or program names unless showing actual code. For example, write "PWHISP_HP is a program" not backtick-wrapped individual terms.

          If the search results don't contain sufficient information to answer the query, 
          be honest about the limitations and suggest what type of additional information might be needed.`
        },
        {
          role: 'user',
          content: `User Question: "${query}"

          Search Context:
          - Strategy Used: ${analysisContext.strategy}
          - Repositories Searched: ${analysisContext.repositories.join(', ')}
          - Search Confidence: ${analysisContext.confidence}

          Search Results (${results.length} items):
          ${results.map((result, index) => `
          ${index + 1}. **${result.filename}** (${result.repo_name})
             Path: ${result.filepath}
             Relevance: ${Math.round((result.relevanceScore || 0) * 100)}%
             Content: ${result.snippet}
             ${result.relevanceReasoning ? `Why relevant: ${result.relevanceReasoning}` : ''}
          `).join('\n')}

          Please provide a comprehensive answer based on these search results.`
        }
      ],
      temperature: 0.3, // Slightly higher for more natural explanation
    });

    // Estimate confidence based on result quality and quantity
    const avgRelevance = results.reduce((sum, r) => sum + (r.relevanceScore || 0), 0) / Math.max(results.length, 1);
    const hasHighQualityResults = results.some(r => (r.relevanceScore || 0) > 0.8);
    const hasSufficientResults = results.length >= 3;
    
    let confidence = 0.5;
    if (hasHighQualityResults && avgRelevance > 0.7 && hasSufficientResults) {
      confidence = 0.9;
    } else if (avgRelevance > 0.6 && hasSufficientResults) {
      confidence = 0.8;
    } else if (avgRelevance > 0.5) {
      confidence = 0.7;
    } else if (results.length > 0) {
      confidence = 0.6;
    }

    // Extract potential related links from results
    const relatedLinks = results
      .filter(r => (r.relevanceScore || 0) > 0.5)
      .map(r => `${r.repo_name}/${r.filepath}`)
      .slice(0, 5);

    return {
      text: result.text,
      confidence,
      tokensUsed: result.usage?.totalTokens || 0,
      relatedLinks
    };
  } catch (error) {
    console.warn('Answer synthesis failed:', error);
    throw error;
  }
}

/**
 * Response Generator Tool Implementation
 */
export const responseGenerator = createWorkflowTool({
  name: 'Response Generator',
  description: 'Generates comprehensive answer from search results or existing context',
  estimatedDuration: 4000,
  retryable: true,
  schema: ResponseGeneratorInputSchema,
  
  execute: async ({ query, searchResults, analysisContext }, context) => {
    const startTime = Date.now();

    await context.streamStatus({
      phase: 'starting',
      currentAction: 'Preparing to generate response...'
    });

    try {
      // Check if this is a repository listing request
      const contextValidation = context.previousResults.get('Context Validator');
      if (contextValidation?.availableContext?.includes('repository_listing_request')) {
        await context.streamStatus({
          phase: 'executing',
          currentAction: 'Fetching repository list using listRepositories tool...'
        });

        // Use the actual listRepositories tool from the existing MCP system
        const { listRepositories } = require('../../list-repositories');
        const repoTool = listRepositories({ session: { user: { id: 'workflow-user' } }, dataStream: context.dataStream });
        
        try {
          const repoResult = await repoTool.execute({});
          
          await context.streamStatus({
            phase: 'completed',
            currentAction: 'Generated repository list'
          });

          const executionTime = Date.now() - startTime;

          return {
            success: true,
            data: {
              answer: `Here are the available MODFLOW repositories:\n\n${JSON.stringify(repoResult, null, 2)}`,
              sourceDocuments: [],
              confidence: 0.95,
              additionalResources: []
            },
            shortSummary: '✅ Generated repository list',
            confidence: 0.95,
            metadata: {
              executionTime,
              sourcesUsed: 0,
              repositoryListing: true
            }
          };
        } catch (repoError) {
          console.warn('listRepositories tool failed:', repoError);
          // Fall back to simple list
          const fallbackAnswer = `Here are the main MODFLOW-related repositories I can help you with:

• **flopy** - Python interface for MODFLOW
• **modflow6** - Latest MODFLOW version with advanced features  
• **pest** - Parameter estimation and uncertainty analysis
• **mt3d** - Solute transport modeling
• **seawat** - Variable-density groundwater flow

You can ask me to search any of these repositories for specific information!`;

          await context.streamStatus({
            phase: 'completed',
            currentAction: 'Generated fallback repository list'
          });

          return {
            success: true,
            data: {
              answer: fallbackAnswer,
              sourceDocuments: [],
              confidence: 0.8,
              additionalResources: []
            },
            shortSummary: '✅ Generated fallback repository list',
            confidence: 0.8,
            metadata: {
              executionTime: Date.now() - startTime,
              sourcesUsed: 0,
              fallback: true
            }
          };
        }
      }
      // Filter and rank results by relevance
      const topResults = searchResults
        .filter(r => (r.relevanceScore || 0) > 0.4) // Lower threshold to include more results
        .slice(0, 8); // Increase limit for more comprehensive answers

      if (topResults.length === 0) {
        await context.streamStatus({
          phase: 'completed',
          currentAction: 'No sufficient results found for synthesis'
        });

        return {
          success: false,
          data: {
            answer: "I couldn't find sufficient relevant information in the MODFLOW repositories to answer your question. You might want to try rephrasing your query or asking about a different aspect of the topic.",
            sourceDocuments: [],
            confidence: 0.1,
            additionalResources: []
          },
          shortSummary: '❌ Insufficient results for answer generation',
          confidence: 0.1,
          metadata: {
            executionTime: Date.now() - startTime,
            sourcesUsed: 0
          }
        };
      }

      await context.streamStatus({
        phase: 'executing',
        currentAction: 'Analyzing search results...'
      });
      
      await context.streamStatus({
        phase: 'processing',
        currentAction: 'Synthesizing comprehensive answer...'
      });
      
      const answer = await synthesizeAnswer({
        query,
        results: topResults,
        context: analysisContext
      });
      
      await context.streamStatus({
        phase: 'completed',
        currentAction: `Generated answer with ${topResults.length} sources`
      });

      const executionTime = Date.now() - startTime;

      return {
        success: true,
        data: {
          answer: answer.text,
          sourceDocuments: topResults,
          confidence: answer.confidence,
          additionalResources: answer.relatedLinks
        },
        shortSummary: `✅ Generated comprehensive answer with ${topResults.length} sources`,
        confidence: answer.confidence,
        metadata: {
          executionTime,
          tokensUsed: answer.tokensUsed,
          sourcesUsed: topResults.length
        }
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;
      
      await context.streamStatus({
        phase: 'failed',
        currentAction: `Answer generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });

      // Fallback to basic result summary
      const fallbackAnswer = searchResults.length > 0 
        ? `Based on the search results, I found ${searchResults.length} potentially relevant documents:\n\n${searchResults.slice(0, 3).map((r, i) => `${i + 1}. ${r.filename} (${r.repo_name}): ${r.snippet.slice(0, 100)}...`).join('\n\n')}\n\nHowever, I encountered an error while generating a comprehensive answer. Please review these results directly.`
        : "I apologize, but I encountered an error while generating an answer and don't have any search results to fall back on.";

      return {
        success: false,
        data: {
          answer: fallbackAnswer,
          sourceDocuments: searchResults.slice(0, 3),
          confidence: 0.3,
          additionalResources: []
        },
        shortSummary: '⚠️ Generated fallback response due to synthesis error',
        confidence: 0.3,
        metadata: {
          executionTime
        },
        errors: [{
          type: 'execution',
          message: error instanceof Error ? error.message : 'Unknown error',
          retryable: true
        }]
      };
    }
  }
});