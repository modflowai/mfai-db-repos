/**
 * Context Validator Tool - Determines if sufficient context exists to answer query without new searches
 */

import { generateText } from 'ai';
import { myProvider } from '../../../providers';
import { createWorkflowTool } from '../base/workflow-tool';
import { z } from 'zod';

// Input schema for context validation
const ContextValidatorInputSchema = z.object({
  query: z.string(),
  analysisContext: z.object({
    strategy: z.string(),
    repositories: z.array(z.string()),
    keywords: z.array(z.string())
  }),
  previousResults: z.array(z.any()).optional(),
  conversationHistory: z.array(z.any()).optional()
});

// Output schema for context validation
export interface ContextValidatorOutput {
  needsNewSearch: boolean;
  contextSufficiency: number; // 0-1 score
  availableContext: string[];
  reasoning: string;
  suggestedResponse?: string;
}

/**
 * Analyze if existing context is sufficient to answer the query
 */
async function analyzeContextSufficiency({
  query,
  previousResults,
  conversationHistory,
  analysisContext
}: any): Promise<ContextValidatorOutput & { confidence: number }> {
  try {
    const result = await generateText({
      model: myProvider.languageModel('chat-model'),
      messages: [
        {
          role: 'system',
          content: `You are a context sufficiency analyzer for MODFLOW/PEST queries.

          Your job is to determine if existing context (previous search results and conversation history) 
          is sufficient to answer the user's current query WITHOUT performing a new search.

          Consider:
          1. **Content Relevance**: Do previous results directly address the current query?
          2. **Topic Continuity**: Is this a follow-up question building on previous context?
          3. **Information Completeness**: Is there enough detail to provide a comprehensive answer?
          4. **Context Freshness**: Is the available context recent and still relevant?
          5. **Query Complexity**: Does the query require information not available in context?

          Respond in JSON format:
          {
            "needsNewSearch": boolean,
            "contextSufficiency": number (0.0-1.0),
            "availableContext": string[] (types of context available),
            "reasoning": string (explanation of decision),
            "suggestedResponse": string (if needsNewSearch is false, provide the answer),
            "confidence": number (0.0-1.0)
          }

          Examples:
          - Follow-up: "Can you explain more about that function?" → needsNewSearch: false (if previous context has the function)
          - New topic: "How to install MODFLOW?" → needsNewSearch: true (likely new information needed)
          - Clarification: "What did you mean by boundary conditions?" → needsNewSearch: false (if BC info in context)`
        },
        {
          role: 'user',
          content: `Current Query: "${query}"

          Analysis Context:
          - Strategy: ${analysisContext.strategy}
          - Target Repositories: ${analysisContext.repositories.join(', ')}
          - Keywords: ${analysisContext.keywords.join(', ')}

          Previous Results Available: ${previousResults?.length || 0} items
          ${previousResults?.length ? `Sample Previous Results:\n${JSON.stringify(previousResults.slice(0, 3), null, 2)}` : 'No previous results'}

          Conversation History: ${conversationHistory?.length || 0} messages
          ${conversationHistory?.length ? `Recent Conversation:\n${JSON.stringify(conversationHistory.slice(-3), null, 2)}` : 'No conversation history'}`
        }
      ],
      temperature: 0.2,
    });

    // Clean and parse response
    let cleanText = result.text.trim();
    if (cleanText.startsWith('```json')) {
      cleanText = cleanText.replace(/^```json\s*/, '').replace(/\s*```$/, '');
    } else if (cleanText.startsWith('```')) {
      cleanText = cleanText.replace(/^```\s*/, '').replace(/\s*```$/, '');
    }

    return JSON.parse(cleanText);
  } catch (error) {
    console.warn('Context validation analysis failed:', error);
    // Conservative fallback - assume new search is needed
    return {
      needsNewSearch: true,
      contextSufficiency: 0.2,
      availableContext: [],
      reasoning: 'Analysis failed, defaulting to new search for safety',
      confidence: 0.3
    };
  }
}

/**
 * Context Validator Tool Implementation
 */
export const contextValidator = createWorkflowTool({
  name: 'Context Validator',
  description: 'Validates if existing context is sufficient to answer the query',
  estimatedDuration: 1500,
  retryable: true,
  schema: ContextValidatorInputSchema,
  
  execute: async ({ query, analysisContext, previousResults, conversationHistory }, context) => {
    const startTime = Date.now();

    await context.streamStatus({
      phase: 'starting',
      currentAction: 'Checking existing context...'
    });

    try {
      await context.streamStatus({
        phase: 'executing',
        currentAction: 'Analyzing previous results and conversation...'
      });

      // LLM analyzes if previous context can answer the query
      const contextAnalysis = await analyzeContextSufficiency({
        query,
        previousResults,
        conversationHistory,
        analysisContext
      });
      
      await context.streamStatus({
        phase: 'completed',
        currentAction: contextAnalysis.needsNewSearch 
          ? 'New search required' 
          : 'Sufficient context found'
      });

      const executionTime = Date.now() - startTime;

      return {
        success: true,
        data: {
          needsNewSearch: contextAnalysis.needsNewSearch,
          contextSufficiency: contextAnalysis.contextSufficiency,
          availableContext: contextAnalysis.availableContext,
          reasoning: contextAnalysis.reasoning,
          suggestedResponse: contextAnalysis.needsNewSearch ? undefined : contextAnalysis.suggestedResponse
        },
        shortSummary: contextAnalysis.needsNewSearch 
          ? '🔍 New search needed - insufficient context'
          : '✅ Sufficient context available',
        confidence: contextAnalysis.confidence,
        nextSuggestedAction: contextAnalysis.needsNewSearch ? 'repository_search' : 'response_generation',
        metadata: {
          executionTime,
          contextItemsAnalyzed: (previousResults?.length || 0) + (conversationHistory?.length || 0)
        }
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;
      
      await context.streamStatus({
        phase: 'failed',
        currentAction: `Context validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });

      // Conservative fallback - assume new search is needed
      const fallbackResult: ContextValidatorOutput = {
        needsNewSearch: true,
        contextSufficiency: 0.2,
        availableContext: [],
        reasoning: 'Context validation failed, defaulting to new search'
      };

      return {
        success: false,
        data: fallbackResult,
        shortSummary: '⚠️ Context validation failed, will perform new search',
        confidence: 0.3,
        nextSuggestedAction: 'repository_search',
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

export type ContextValidatorInput = z.infer<typeof ContextValidatorInputSchema>;