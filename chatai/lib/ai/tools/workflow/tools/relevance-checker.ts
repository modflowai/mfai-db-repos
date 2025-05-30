/**
 * Relevance Checker Tool - Determines if query is MODFLOW/PEST related
 */

import { generateText } from 'ai';
import { myProvider } from '../../../providers';
import { createWorkflowTool } from '../base/workflow-tool';
import { 
  RelevanceCheckerInputSchema, 
  type RelevanceCheckerOutput 
} from '../schemas/tool-schemas';

/**
 * Analyze domain relevance using LLM
 */
async function analyzeDomainRelevance(query: string): Promise<RelevanceCheckerOutput> {
  const result = await generateText({
    model: myProvider.languageModel('chat-model'),
    messages: [
      {
        role: 'system',
        content: `You are a domain relevance analyzer for MODFLOW/PEST/hydrology queries.

        Determine if the user query is related to these domains:
        - MODFLOW (groundwater modeling software)
        - PEST (parameter estimation software)
        - Hydrology and hydrogeology concepts
        - Groundwater modeling and simulation
        - Python libraries: flopy, pestpy, pymake
        - Related software: MT3D, SEAWAT, MFUSG, MODPATH
        - Repository listings and availability queries for MODFLOW-related repositories

        IMPORTANT: Queries asking for repository lists, available repos, or what repositories are available
        should be considered RELEVANT since they relate to MODFLOW repository exploration.

        Respond in JSON format:
        {
          "isRelevant": boolean,
          "confidence": number (0.0-1.0),
          "domains": string[] (matched domains),
          "reasoning": string (brief explanation)
        }

        Examples:
        - "what is flopy" → isRelevant: true, domains: ["modflow", "python"], confidence: 0.95
        - "repo list" → isRelevant: true, domains: ["repositories"], confidence: 0.90
        - "list repositories" → isRelevant: true, domains: ["repositories"], confidence: 0.95
        - "what repos are available" → isRelevant: true, domains: ["repositories"], confidence: 0.90
        - "how to cook pasta" → isRelevant: false, domains: [], confidence: 0.98
        - "groundwater flow modeling" → isRelevant: true, domains: ["hydrology", "modeling"], confidence: 0.90`
      },
      {
        role: 'user',
        content: query
      }
    ],
    temperature: 0.1,
  });

  // Clean and parse response
  let cleanText = result.text.trim();
  if (cleanText.startsWith('```json')) {
    cleanText = cleanText.replace(/^```json\s*/, '').replace(/\s*```$/, '');
  } else if (cleanText.startsWith('```')) {
    cleanText = cleanText.replace(/^```\s*/, '').replace(/\s*```$/, '');
  }

  return JSON.parse(cleanText);
}

/**
 * Relevance Checker Tool Implementation
 */
export const relevanceChecker = createWorkflowTool({
  name: 'Relevance Checker',
  description: 'Determines if query relates to MODFLOW, PEST, or hydrology concepts',
  estimatedDuration: 1500, // milliseconds
  retryable: true,
  schema: RelevanceCheckerInputSchema,
  
  execute: async ({ query }, context) => {
    const startTime = Date.now();

    await context.streamStatus({
      phase: 'starting',
      currentAction: 'Analyzing query relevance...'
    });

    try {
      // Fast LLM call with focused prompt
      const result = await analyzeDomainRelevance(query);
      
      await context.streamStatus({
        phase: 'completed',
        currentAction: `${result.isRelevant ? 'Relevant' : 'Not relevant'} to MODFLOW domain`
      });

      const confidence = result.confidence;
      const executionTime = Date.now() - startTime;

      return {
        success: true,
        data: result,
        shortSummary: `${result.isRelevant ? '✅ MODFLOW-related' : '❌ Outside domain'} (${Math.round(confidence * 100)}% confident)`,
        confidence,
        metadata: {
          executionTime,
          cacheHit: false // Could implement caching later
        }
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;
      
      await context.streamStatus({
        phase: 'failed',
        currentAction: `Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });

      // Fallback analysis
      const fallbackResult: RelevanceCheckerOutput = {
        isRelevant: false,
        confidence: 0.3,
        domains: [],
        reasoning: 'Fallback analysis due to LLM error'
      };

      return {
        success: false,
        data: fallbackResult,
        shortSummary: '⚠️ Relevance analysis failed, using fallback',
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