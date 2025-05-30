/**
 * Intelligent Workflow Engine with LLM-powered decision making (Stable AI SDK)
 */

import { streamText } from 'ai';
import { LLMIntentAnalyzer } from './llm-intent-analyzer';
import type { DataStreamWriter } from 'ai';

export interface WorkflowContext {
  phase: 'discovery' | 'search' | 'enhancement' | 'general';
  llmAnalysis?: any;
  stepHistory?: string[];
}

/**
 * Create intelligent repository workflow with LLM-powered decision making
 * Uses stable AI SDK with intelligent tool selection and enhanced prompting
 */
export const createRepositoryWorkflow = (dataStream: DataStreamWriter) => {
  return async ({
    model,
    system,
    messages,
    tools,
    ...options
  }: any) => {
    // Stream that we're using the intelligent workflow
    dataStream.writeData({
      type: 'text-delta',
      content: `🤖 **Intelligent Agent**: Analyzing your query...\n\n`,
    });

    // Analyze the user's intent to enhance the system prompt
    const lastMessage = messages[messages.length - 1];
    let intentAnalysis;
    try {
      intentAnalysis = await LLMIntentAnalyzer.analyzeUserIntent(lastMessage.content);
      
      // Debug logging
      console.log('🔍 Intent Analysis Results:', {
        query: lastMessage.content,
        shouldSearch: intentAnalysis.shouldSearch,
        action: intentAnalysis.action,
        optimalSearchStrategy: intentAnalysis.optimalSearchStrategy,
        requiresRepositoryContext: intentAnalysis.requiresRepositoryContext,
        confidence: intentAnalysis.confidence,
        reasoning: intentAnalysis.reasoning
      });
      
      // Stream the LLM's reasoning
      dataStream.writeData({
        type: 'text-delta',
        content: `💭 **Analysis**: ${intentAnalysis.reasoning} (${(intentAnalysis.confidence * 100).toFixed(0)}% confident)\n\n`,
      });
    } catch (error) {
      console.warn('Intent analysis failed in workflow:', error);
    }

    // Enhanced system prompt based on intent analysis
    let enhancedSystem = system;
    if (intentAnalysis) {
      if (intentAnalysis.shouldSearch) {
        enhancedSystem += `\n\nCRITICAL INSTRUCTION: The user wants to SEARCH for information. You MUST:
1. Use the intelligentMfaiSearch tool with strategy "${intentAnalysis.optimalSearchStrategy}" to find relevant content in the MODFLOW repositories
2. After the search results are returned, analyze the findings and provide a comprehensive answer to the user's question
3. Use the most relevant search results to explain what they're asking about, including examples, usage, and important details
4. DO NOT just show search results - provide the actual answer based on what you found

DO NOT use listRepositories - the user wants to search, not list. Use intelligentMfaiSearch immediately, then answer their question.`;
        
        console.log('🎯 Enhanced system prompt for SEARCH:', enhancedSystem.slice(-300));
      } else if (intentAnalysis.requiresRepositoryContext) {
        enhancedSystem += `\n\nIMPORTANT: The user needs repository information. Use the listRepositories tool to show available MODFLOW repositories.`;
      }
    }

    // Use regular streamText with enhanced system prompt and intelligent tool selection
    return streamText({
      model,
      system: enhancedSystem,
      messages,
      maxSteps: 3, // Allow multiple steps for intelligent workflows  
      tools,
      experimental_activeTools: [
        'getWeather',
        'createDocument',
        'updateDocument', 
        'requestSuggestions',
        ...(process.env.MCP_ENABLED === 'true' ? [
          'intelligentMfaiSearch',
          'listRepositories'
        ] : [])
      ],
      ...options
    });
  };
};

/**
 * Determine if workflow should continue based on LLM analysis
 */
export async function shouldContinueWorkflow(
  currentStep: number, 
  userQuery: string, 
  previousResults: any[]
): Promise<{ shouldContinue: boolean; reasoning: string }> {
  try {
    const llmAnalysis = await LLMIntentAnalyzer.analyzeUserIntent(
      `Based on this workflow so far, should we continue? User query: "${userQuery}" | Previous results: ${JSON.stringify(previousResults.slice(-2))}`
    );

    return {
      shouldContinue: llmAnalysis.confidence > 0.6 && currentStep < 5,
      reasoning: `LLM analysis: ${llmAnalysis.reasoning} (confidence: ${llmAnalysis.confidence})`
    };
  } catch (error) {
    return {
      shouldContinue: false,
      reasoning: 'LLM analysis failed, stopping workflow'
    };
  }
}