/**
 * Modular Workflow Engine - Replaces monolithic intelligentMfaiSearch with streaming modular tools
 */

import { streamText } from 'ai';
import { LLMIntentAnalyzer } from './llm-intent-analyzer';
import { WorkflowOrchestrator } from './tools/workflow';
import type { DataStreamWriter } from 'ai';

export interface ModularWorkflowContext {
  phase: 'analysis' | 'workflow' | 'response' | 'complete';
  llmAnalysis?: any;
  workflowResult?: any;
  stepHistory?: string[];
}

/**
 * Create modular workflow with intelligent tool orchestration
 * Replaces the monolithic approach with streaming, transparent tool execution
 */
export const createModularWorkflow = (dataStream: DataStreamWriter) => {
  return async ({
    model,
    system,
    messages,
    tools,
    ...options
  }: any) => {
    // Get the last user message
    const lastMessage = messages[messages.length - 1];
    const userQuery = lastMessage.content;

    // Stream that we're using the modular workflow
    dataStream.writeData({
      type: 'text-delta',
      content: `🚀 **Modular Workflow Engine**: Analyzing your query with streaming tools...\n\n`,
    });

    // Analyze user intent first
    let intentAnalysis: any;
    try {
      intentAnalysis = await LLMIntentAnalyzer.analyzeUserIntent(userQuery);
      
      // Debug logging
      console.log('🔍 Modular Workflow Intent Analysis:', {
        query: userQuery,
        shouldSearch: intentAnalysis.shouldSearch,
        action: intentAnalysis.action,
        optimalSearchStrategy: intentAnalysis.optimalSearchStrategy,
        requiresRepositoryContext: intentAnalysis.requiresRepositoryContext,
        confidence: intentAnalysis.confidence,
        reasoning: intentAnalysis.reasoning
      });
      
      // Stream the intent analysis
      dataStream.writeData({
        type: 'text-delta',
        content: `💭 **Intent Analysis**: ${intentAnalysis.reasoning} (${(intentAnalysis.confidence * 100).toFixed(0)}% confident)\n\n`,
      });
    } catch (error) {
      console.warn('Intent analysis failed in modular workflow:', error);
      // Fallback to assuming search is needed
      intentAnalysis = {
        shouldSearch: true,
        requiresRepositoryContext: false,
        action: 'search',
        optimalSearchStrategy: 'semantic',
        confidence: 0.5,
        reasoning: 'Fallback analysis due to error'
      };
    }

    // Determine if we should use the modular workflow
    const useModularWorkflow = intentAnalysis.shouldSearch || intentAnalysis.requiresRepositoryContext;

    if (useModularWorkflow) {
      // Determine which tool to use based on intent
      if (intentAnalysis.shouldSearch) {
        // Use individual workflow tools for step-by-step execution
        try {
          console.log('🔍 Search request - using individual workflow tools');
          console.log('🔍 Available tools for search:', Object.keys(tools));
          console.log('🔍 Active tools specified:', ['relevanceChecker', 'queryAnalyzer', 'repositorySearcher']);
          
          return streamText({
            model,
            system: system + `\n\nIMPORTANT: The user is asking to search MODFLOW repositories. Execute this step-by-step workflow:

1. FIRST: Use the relevanceChecker tool to verify the query is MODFLOW-related
2. THEN: Use the queryAnalyzer tool to determine search strategy 
3. FINALLY: Use the repositorySearcher tool to find relevant content

Execute these tools in sequence. Each tool will show progress independently.`,
            messages,
            maxSteps: 5,
            tools,
            experimental_activeTools: ['relevanceChecker', 'queryAnalyzer', 'repositorySearcher'],
            ...options
          });
        } catch (error) {
          console.error('Modular search failed:', error);
          
          dataStream.writeData({
            type: 'text-delta',
            content: `❌ **Modular Search Failed**: ${error instanceof Error ? error.message : 'Unknown error'}\n\nFalling back to general response...\n\n`,
          });

          return streamText({
            model,
            system: `${system}\n\nNote: There was an issue with the repository search workflow. Please provide a helpful general response to the user's query.`,
            messages,
            maxSteps: 2,
            tools: {}, // No tools for error fallback
            ...options
          });
        }
      } else if (intentAnalysis.requiresRepositoryContext) {
        // Use listRepositories tool for repository listing
        try {
          console.log('📚 Repository listing - using listRepositories tool');
          console.log('📚 Available tools for repository listing:', Object.keys(tools));
          console.log('📚 Active tools specified:', ['listRepositories']);
          
          return streamText({
            model,
            system: system + `\n\nIMPORTANT: The user is asking for a list of MODFLOW repositories. You MUST use the listRepositories tool to fetch and display the available repositories. This is a tool call request - call the listRepositories tool now.`,
            messages,
            maxSteps: 2,
            tools,
            experimental_activeTools: ['listRepositories'],
            ...options
          });
        } catch (error) {
          console.error('Repository listing failed:', error);
          
          dataStream.writeData({
            type: 'text-delta',
            content: `❌ **Repository Listing Failed**: ${error instanceof Error ? error.message : 'Unknown error'}\n\nFalling back to general response...\n\n`,
          });

          return streamText({
            model,
            system: `${system}\n\nNote: There was an issue with the repository listing. Please provide a helpful general response to the user's query.`,
            messages,
            maxSteps: 2,
            tools: {}, // No tools for error fallback
            ...options
          });
        }
      }
    } else {
      // Query doesn't require repository search, use standard streamText
      if (intentAnalysis.requiresRepositoryContext) {
        // User wants to see available repositories - use the existing listRepositories tool
        return streamText({
          model,
          system: `${system}\n\nThe user is asking for available MODFLOW repositories. Use the listRepositories tool to show them what's available. Provide a clear, simple text response listing the repositories without creating any artifacts or documents.`,
          messages,
          maxSteps: 2,
          tools,
          experimental_activeTools: ['listRepositories'],
          ...options
        });
      } else {
        // General conversation
        dataStream.writeData({
          type: 'text-delta',
          content: `💬 **General Response**: This doesn't appear to be a MODFLOW-specific query\n\n`,
        });

        return streamText({
          model,
          system,
          messages,
          maxSteps: 2,
          tools: {}, // No repository tools for general conversation
          ...options
        });
      }
    }
  };
};

/**
 * Backward compatibility helper - can be used to gradually migrate from old workflow
 */
export const createHybridWorkflow = (dataStream: DataStreamWriter, useModular = true) => {
  if (useModular) {
    return createModularWorkflow(dataStream);
  } else {
    // Fall back to existing workflow-engine implementation
    const { createRepositoryWorkflow } = require('./workflow-engine');
    return createRepositoryWorkflow(dataStream);
  }
};
