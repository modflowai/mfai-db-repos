/**
 * Error Handler - Centralized error management for workflow tools
 */

import type { DataStreamWriter } from 'ai';
import type { WorkflowTool, ToolResult } from '../base/workflow-tool';

export enum ErrorSeverity {
  RECOVERABLE = 'recoverable',    // Retry with same parameters
  DEGRADED = 'degraded',          // Continue with reduced functionality  
  CRITICAL = 'critical'           // Stop workflow, return error
}

export interface ErrorClassification {
  severity: ErrorSeverity;
  retryable: boolean;
  fallbackAvailable: boolean;
  userMessage: string;
}

export interface ErrorHandlingStrategy {
  action: 'retry' | 'continue' | 'abort';
  delay?: number;
  fallback?: any;
  userMessage?: string;
}

export class ErrorHandler {
  constructor(private dataStream: DataStreamWriter) {}

  /**
   * Classify error based on type and context
   */
  classifyError(error: Error, tool: WorkflowTool<any, any>): ErrorClassification {
    const errorMessage = error.message.toLowerCase();
    
    // Network/API errors - usually recoverable
    if (errorMessage.includes('timeout') || 
        errorMessage.includes('network') || 
        errorMessage.includes('econnreset') ||
        errorMessage.includes('rate limit')) {
      return {
        severity: ErrorSeverity.RECOVERABLE,
        retryable: true,
        fallbackAvailable: false,
        userMessage: 'Temporary network issue, retrying...'
      };
    }
    
    // API key or authentication issues - critical
    if (errorMessage.includes('unauthorized') || 
        errorMessage.includes('api key') ||
        errorMessage.includes('forbidden')) {
      return {
        severity: ErrorSeverity.CRITICAL,
        retryable: false,
        fallbackAvailable: false,
        userMessage: 'Authentication error - please check API configuration'
      };
    }
    
    // Service unavailable - degraded operation possible
    if (errorMessage.includes('service unavailable') ||
        errorMessage.includes('server error') ||
        errorMessage.includes('internal error')) {
      return {
        severity: ErrorSeverity.DEGRADED,
        retryable: true,
        fallbackAvailable: this.hasFallback(tool),
        userMessage: 'Service temporarily unavailable, using fallback approach'
      };
    }
    
    // Validation errors - usually critical
    if (errorMessage.includes('validation') ||
        errorMessage.includes('invalid input')) {
      return {
        severity: ErrorSeverity.CRITICAL,
        retryable: false,
        fallbackAvailable: false,
        userMessage: 'Invalid input provided'
      };
    }
    
    // Default to degraded for unknown errors
    return {
      severity: ErrorSeverity.DEGRADED,
      retryable: tool.retryable,
      fallbackAvailable: this.hasFallback(tool),
      userMessage: 'Unexpected error occurred, attempting fallback'
    };
  }
  
  /**
   * Handle error based on classification
   */
  async handleError(
    error: Error, 
    tool: WorkflowTool<any, any>, 
    context: Map<string, any>
  ): Promise<ErrorHandlingStrategy> {
    const classification = this.classifyError(error, tool);
    
    switch (classification.severity) {
      case ErrorSeverity.RECOVERABLE:
        return { 
          action: 'retry', 
          delay: 1000,
          userMessage: classification.userMessage
        };
        
      case ErrorSeverity.DEGRADED:
        if (classification.fallbackAvailable) {
          return { 
            action: 'continue', 
            fallback: this.createFallback(tool, context, error),
            userMessage: classification.userMessage
          };
        }
        return { 
          action: 'abort', 
          userMessage: 'Unable to continue workflow due to service issues'
        };
        
      case ErrorSeverity.CRITICAL:
        return { 
          action: 'abort', 
          userMessage: classification.userMessage
        };
        
      default:
        return { 
          action: 'abort', 
          userMessage: 'Unknown error occurred'
        };
    }
  }
  
  /**
   * Attempt graceful degradation for workflow failures
   */
  async handleGracefulDegradation(
    tool: WorkflowTool<any, any>, 
    result: ToolResult<any>, 
    stepIndex: number
  ): Promise<string | null> {
    
    switch (tool.name) {
      case 'Relevance Checker':
        // If relevance check fails, assume query is relevant and continue
        return null; // Continue workflow with assumption of relevance
        
      case 'Query Analyzer':
        // If analysis fails, use default semantic search strategy
        return null; // Continue with fallback strategy
        
      case 'Context Validator':
        // If context validation fails, assume new search is needed
        return null; // Continue to repository search
        
      case 'Repository Searcher':
        // If search fails, provide a helpful message about the failure
        return `I apologize, but I'm currently unable to search the MODFLOW repositories due to a technical issue. This might be temporary. You could try:

1. Rephrasing your question
2. Trying again in a few minutes
3. Asking a more specific question about MODFLOW concepts

If the issue persists, the search service might be temporarily unavailable.`;
        
      case 'Response Generator': {
        // If response generation fails, return raw search results if available
        const searchData = result.data;
        if (searchData?.results?.length > 0) {
          return `I found some relevant information but had trouble generating a comprehensive answer. Here are the key results:

${searchData.results.slice(0, 3).map((r: any, i: number) => 
  `${i + 1}. **${r.filename}** (${r.repo_name})
     ${r.snippet.slice(0, 200)}...`
).join('\n\n')}

Please review these results for information about your query.`;
        }
        return 'I apologize, but I encountered an error while generating a response and don\'t have search results to show you.';
      }
        
      default:
        return null;
    }
  }
  
  /**
   * Check if tool has fallback capabilities
   */
  private hasFallback(tool: WorkflowTool<any, any>): boolean {
    // Define which tools have fallback mechanisms
    const toolsWithFallbacks = new Set([
      'Relevance Checker',
      'Query Analyzer', 
      'Context Validator',
      'Response Generator'
    ]);
    
    return toolsWithFallbacks.has(tool.name);
  }
  
  /**
   * Create fallback result for a failed tool
   */
  private createFallback(tool: WorkflowTool<any, any>, context: Map<string, any>, error: Error): any {
    switch (tool.name) {
      case 'Relevance Checker':
        return {
          isRelevant: true, // Assume relevance to continue workflow
          confidence: 0.3,
          domains: ['modflow'],
          reasoning: 'Fallback analysis due to error'
        };
        
      case 'Query Analyzer':
        return {
          strategy: 'semantic',
          repositories: [], // Search all repositories
          searchType: 'fallback_search',
          keywords: context.get('originalQuery')?.split(' ').filter((w: string) => w.length > 2) || [],
          expectedResultTypes: ['documentation']
        };
        
      case 'Context Validator':
        return {
          needsNewSearch: true, // Conservative approach - always search when validation fails
          contextSufficiency: 0.2,
          availableContext: [],
          reasoning: 'Context validation failed, defaulting to new search'
        };
        
      case 'Response Generator':
        return {
          answer: 'I encountered an error while generating a comprehensive response. Please refer to the search results above.',
          sourceDocuments: [],
          confidence: 0.2,
          additionalResources: []
        };
        
      default:
        return null;
    }
  }
  
  /**
   * Create user-friendly error message
   */
  createUserFriendlyMessage(error: Error): string {
    const errorMessage = error.message.toLowerCase();
    
    if (errorMessage.includes('timeout')) {
      return 'The request timed out. Please try again.';
    }
    
    if (errorMessage.includes('network')) {
      return 'Network connection issue. Please check your connection and try again.';
    }
    
    if (errorMessage.includes('rate limit')) {
      return 'Too many requests. Please wait a moment and try again.';
    }
    
    if (errorMessage.includes('unauthorized')) {
      return 'Authentication error. Please check your credentials.';
    }
    
    return 'An unexpected error occurred. Please try again or contact support if the issue persists.';
  }
}