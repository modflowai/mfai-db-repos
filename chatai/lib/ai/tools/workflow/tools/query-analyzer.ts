/**
 * Query Analyzer Tool - Determines optimal search strategy and parameters
 */

import { generateText } from 'ai';
import { myProvider } from '../../../providers';
import { createWorkflowTool } from '../base/workflow-tool';
import { 
  QueryAnalyzerInputSchema, 
  type QueryAnalyzerOutput 
} from '../schemas/tool-schemas';

/**
 * Get available repositories from context or fetch them
 */
async function getAvailableRepositories(context: any): Promise<string[]> {
  // Check if we have recent repository data in context
  const conversationHistory = context.get?.('conversationHistory') || [];
  const previousResults = context.get?.('previousResults') || [];
  
  // Look for recent listRepositories results in context
  for (const result of [...conversationHistory, ...previousResults]) {
    if (result?.repositories && Array.isArray(result.repositories)) {
      return result.repositories.map((repo: any) => repo.name || repo);
    }
  }
  
  // Fallback to common repositories if no context available
  return ["pest", "mfusg", "pest_hp", "flopy", "pestpp"];
}

/**
 * Analyze search strategy using LLM with dynamic repository context
 */
async function analyzeSearchStrategy(query: string, relevanceData: any, context: any): Promise<QueryAnalyzerOutput & { confidence: number }> {
  // Get available repositories dynamically
  const availableRepos = await getAvailableRepositories(context);
  
  const result = await generateText({
    model: myProvider.languageModel('chat-model'),
    messages: [
      {
        role: 'system',
        content: `You are a search strategy analyzer for MODFLOW repository queries.

        Based on the query and relevance data, determine:
        1. optimalStrategy: "text" | "semantic" | "hybrid"
           - "text": exact matches, function names, code snippets
           - "semantic": conceptual questions, "how to" queries
           - "hybrid": comprehensive searches needing both approaches
        
        2. targetRepositories: Focus on specific repos or search all
           - Available repos: ${JSON.stringify(availableRepos)}
           - Use [] for all repositories
           - For repository listing queries, use [] to list all
           - Map user terms to actual repository names based on context
        
        3. searchType: Description of what we're looking for
           - "repository_listing" for queries asking for available repos
           - "search" for content searches
           - "conceptual" for understanding queries
        4. keywords: Extracted key terms for search optimization
        5. expectedResultTypes: What types of results we expect
        6. confidence: How confident you are in this strategy (0.0-1.0)

        Respond in JSON format:
        {
          "strategy": "semantic",
          "repositories": ["mfusg"],
          "searchType": "conceptual explanation",
          "keywords": ["pump", "level", "cln", "modflowusg"],
          "expectedResultTypes": ["documentation", "examples"],
          "confidence": 0.85
        }

        Examples based on available repositories:
        ${availableRepos.map(repo => `- Query mentioning "${repo}" → repositories: ["${repo}"]`).join('\n        ')}
        
        Common mappings (map user terms to actual repo names):
        - "modflowusg", "modflow-usg", "usg", "cln" → look for repository with "usg" in name
        - "pest", "parameter estimation" → look for repository with "pest" in name
        - "flopy", "python" → look for repository with "flopy" in name
        - "repo list" → searchType: "repository_listing", repositories: [], strategy: "text"
        - "what repositories are available" → searchType: "repository_listing", repositories: []
        - "search flopy for wells" → searchType: "search", repositories: ["flopy"], strategy: "semantic"`
      },
      {
        role: 'user',
        content: `Query: "${query}"
        Relevance Data: ${JSON.stringify(relevanceData)}`
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
}

/**
 * Query Analyzer Tool Implementation
 */
export const queryAnalyzer = createWorkflowTool({
  name: 'Query Analyzer',
  description: 'Analyzes query to determine optimal search strategy and parameters',
  estimatedDuration: 2500,
  retryable: true,
  schema: QueryAnalyzerInputSchema,
  
  execute: async ({ query, relevanceData }, context) => {
    const startTime = Date.now();

    // Check if query is relevant first
    if (!relevanceData.isRelevant) {
      await context.streamStatus({
        phase: 'completed',
        currentAction: 'Query not suitable for MODFLOW search'
      });

      return {
        success: false,
        data: {
          strategy: 'semantic' as const,
          repositories: [],
          searchType: 'not_applicable',
          keywords: [],
          expectedResultTypes: []
        },
        shortSummary: "⚠️ Query not suitable for MODFLOW search",
        confidence: 0,
        nextSuggestedAction: "general_response",
        metadata: {
          executionTime: Date.now() - startTime
        }
      };
    }

    await context.streamStatus({
      phase: 'executing',
      currentAction: 'Determining search strategy...'
    });

    try {
      const analysis = await analyzeSearchStrategy(query, relevanceData, context.previousResults);
      
      await context.streamStatus({
        phase: 'processing',
        currentAction: 'Optimizing search parameters...'
      });

      await context.streamStatus({
        phase: 'completed',
        currentAction: `Strategy: ${analysis.strategy}, Repos: ${analysis.repositories.length > 0 ? analysis.repositories.join(', ') : 'all'}`
      });

      const executionTime = Date.now() - startTime;

      return {
        success: true,
        data: {
          strategy: analysis.strategy,
          repositories: analysis.repositories,
          searchType: analysis.searchType,
          keywords: analysis.keywords,
          expectedResultTypes: analysis.expectedResultTypes
        },
        shortSummary: `📋 Strategy: ${analysis.strategy}, Repos: ${analysis.repositories.length > 0 ? analysis.repositories.join(', ') : 'all'}`,
        confidence: analysis.confidence,
        metadata: {
          executionTime
        }
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;
      
      await context.streamStatus({
        phase: 'failed',
        currentAction: `Strategy analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });

      // Fallback to semantic search strategy
      const fallbackResult: QueryAnalyzerOutput = {
        strategy: 'semantic',
        repositories: [], // All repositories
        searchType: 'fallback_search',
        keywords: query.split(' ').filter(word => word.length > 2),
        expectedResultTypes: ['documentation']
      };

      return {
        success: false,
        data: fallbackResult,
        shortSummary: '⚠️ Using fallback search strategy',
        confidence: 0.4,
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