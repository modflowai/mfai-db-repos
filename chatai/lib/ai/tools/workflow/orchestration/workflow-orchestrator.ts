/**
 * Workflow Orchestrator - Manages sequential execution of modular tools
 */

import type { DataStreamWriter } from 'ai';
import { StreamingUtils } from '../base/streaming-utils';
import { ErrorHandler } from './error-handler';
import { RetryLogic } from './retry-logic';
import type { WorkflowTool, WorkflowState, ToolResult, ToolContext } from '../base/workflow-tool';
import { relevanceChecker } from '../tools/relevance-checker';
import { queryAnalyzer } from '../tools/query-analyzer';
import { contextValidator } from '../tools/context-validator';
import { repositorySearcher } from '../tools/repository-searcher';
import { responseGenerator } from '../tools/response-generator';
import { generateUUID } from '../../../../utils';

export interface WorkflowResult {
  success: boolean;
  finalAnswer?: string;
  workflowId: string;
  totalTime: number;
  toolsExecuted: string[];
  degradedMode?: boolean;
  errors?: any[];
}

export class WorkflowOrchestrator {
  private workflow: WorkflowTool<any, any>[];
  private state: WorkflowState;
  private streamingUtils: StreamingUtils;
  private errorHandler: ErrorHandler;
  private retryLogic: RetryLogic;
  
  constructor(
    private dataStream: DataStreamWriter,
    private userId: string
  ) {
    this.workflow = [
      relevanceChecker,
      queryAnalyzer,
      contextValidator,
      repositorySearcher,
      responseGenerator
    ];
    this.streamingUtils = new StreamingUtils(dataStream);
    this.errorHandler = new ErrorHandler(dataStream);
    this.retryLogic = new RetryLogic();
  }
  
  async execute(userQuery: string, conversationHistory?: any[], previousResults?: any[]): Promise<WorkflowResult> {
    const workflowStartTime = Date.now();
    const workflowId = generateUUID();
    
    this.state = this.initializeWorkflowState(workflowId, userQuery);
    
    try {
      // Stream workflow start
      await this.streamingUtils.streamWorkflowStart(this.workflow.length);
      
      const context = new Map<string, any>();
      context.set('originalQuery', userQuery);
      context.set('conversationHistory', conversationHistory || []);
      context.set('previousResults', previousResults || []);
      
      const toolsExecuted: string[] = [];
      let skipToResponseGeneration = false;
      
      for (let i = 0; i < this.workflow.length; i++) {
        const tool = this.workflow[i];
        
        // Skip repository search if context validation says we have sufficient context
        if (tool.name === 'Repository Searcher' && skipToResponseGeneration) {
          console.log('🚀 Skipping repository search - sufficient context available');
          continue;
        }
        
        // For repository listing queries, skip to response generation after query analysis
        const queryAnalysisResult = context.get('Query Analyzer');
        if (tool.name === 'Context Validator' && queryAnalysisResult?.searchType === 'repository_listing') {
          console.log('🚀 Skipping context validation and repository search for repository listing');
          // Set up context for repository listing response
          context.set('Context Validator', {
            needsNewSearch: false,
            contextSufficiency: 1.0,
            availableContext: ['repository_listing_request'],
            reasoning: 'Repository listing request - using listRepositories tool'
          });
          skipToResponseGeneration = true;
          continue;
        }
        
        if (tool.name === 'Repository Searcher' && queryAnalysisResult?.searchType === 'repository_listing') {
          console.log('🚀 Skipping repository search for repository listing - will use listRepositories tool');
          continue;
        }
        
        console.log(`🔧 Executing tool: ${tool.name} (step ${i + 1}/${this.workflow.length})`);
        const stepResult = await this.executeToolWithRetry(tool, context, i);
        toolsExecuted.push(tool.name);
        
        console.log(`🔧 Tool ${tool.name} completed:`, {
          success: stepResult.success,
          shortSummary: stepResult.shortSummary,
          confidence: stepResult.confidence,
          nextSuggestedAction: stepResult.nextSuggestedAction
        });
        
        if (!stepResult.success) {
          console.log(`❌ Tool ${tool.name} failed, handling workflow failure`);
          return await this.handleWorkflowFailure(tool, stepResult, i, workflowStartTime, workflowId, toolsExecuted);
        }
        
        // Add result to context for next tools
        context.set(tool.name, stepResult.data);
        console.log(`🔧 Added ${tool.name} result to context`);
        
        // Stream tool result
        console.log(`🔧 Streaming tool result for ${tool.name}`);
        await this.streamingUtils.streamToolResult(tool.name, stepResult);
        
        // Check for workflow control flow
        if (stepResult.nextSuggestedAction === 'general_response') {
          return await this.handleGeneralResponse(userQuery, workflowStartTime, workflowId, toolsExecuted);
        }
        
        if (stepResult.nextSuggestedAction === 'response_generation') {
          skipToResponseGeneration = true;
        }
      }
      
      return await this.completeWorkflow(context, workflowStartTime, workflowId, toolsExecuted);
      
    } catch (error) {
      return await this.handleCriticalFailure(error, workflowStartTime, workflowId, []);
    }
  }
  
  private async executeToolWithRetry(
    tool: WorkflowTool<any, any>, 
    context: Map<string, any>, 
    stepIndex: number
  ): Promise<ToolResult<any>> {
    const maxRetries = tool.retryable ? 2 : 0;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // Prepare tool input from context
        const input = this.prepareToolInput(tool, context);
        
        // Update workflow state
        this.updateToolStatus(tool.name, {
          tool: tool.name,
          phase: 'starting',
          currentAction: `Starting ${tool.name}...`
        });
        
        // Create tool context
        const toolContext: ToolContext = {
          userId: this.userId,
          sessionId: this.state.id,
          dataStream: this.dataStream,
          previousResults: context,
          streamStatus: (status) => this.streamToolStatus(status)
        };
        
        // Execute tool
        const result = await tool.execute(input, toolContext);
        
        // Update success state
        this.updateToolStatus(tool.name, {
          tool: tool.name,
          phase: 'completed',
          currentAction: result.shortSummary
        });
        
        return result;
        
      } catch (error) {
        const isLastAttempt = attempt === maxRetries;
        
        if (isLastAttempt) {
          // Final failure
          this.updateToolStatus(tool.name, {
            tool: tool.name,
            phase: 'failed',
            currentAction: `Failed: ${error instanceof Error ? error.message : 'Unknown error'}`
          });
          
          // Stream error
          await this.streamingUtils.streamError(tool.name, error, false);
          
          throw error;
        } else {
          // Retry attempt
          this.updateToolStatus(tool.name, {
            tool: tool.name,
            phase: 'retrying',
            currentAction: `Retrying... (attempt ${attempt + 2})`
          });
          
          await this.streamingUtils.streamError(tool.name, error, true, attempt + 2);
          await this.retryLogic.wait(attempt);
        }
      }
    }
    
    // This should never be reached due to throw in catch block
    throw new Error('Unexpected end of retry loop');
  }
  
  private prepareToolInput(tool: WorkflowTool<any, any>, context: Map<string, any>): any {
    const query = context.get('originalQuery');
    
    switch (tool.name) {
      case 'Relevance Checker':
        return { query };
        
      case 'Query Analyzer':
        return {
          query,
          relevanceData: context.get('Relevance Checker') || { isRelevant: true, domains: [], confidence: 0.5 }
        };
        
      case 'Context Validator':
        return {
          query,
          analysisContext: context.get('Query Analyzer') || { strategy: 'semantic', repositories: [], keywords: [] },
          previousResults: context.get('previousResults'),
          conversationHistory: context.get('conversationHistory')
        };
        
      case 'Repository Searcher': {
        const analysisData = context.get('Query Analyzer');
        return {
          query,
          strategy: analysisData?.strategy || 'semantic',
          repositories: analysisData?.repositories || [],
          searchParameters: {
            maxResults: 10,
            minSimilarity: 0.7
          }
        };
      }
        
      case 'Response Generator': {
        const searchData = context.get('Repository Searcher');
        const contextData = context.get('Context Validator');
        const queryAnalysisData = context.get('Query Analyzer');
        
        return {
          query,
          searchResults: searchData?.results || [],
          analysisContext: {
            strategy: queryAnalysisData?.strategy || 'semantic',
            repositories: queryAnalysisData?.repositories || [],
            confidence: 0.9 // Add the required confidence field
          }
        };
      }
        
      default:
        return { query };
    }
  }
  
  private initializeWorkflowState(workflowId: string, userQuery: string): WorkflowState {
    return {
      id: workflowId,
      userId: this.userId,
      originalQuery: userQuery,
      currentStep: 0,
      totalSteps: this.workflow.length,
      tools: {},
      context: new Map<string, any>(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }
  
  private updateToolStatus(toolName: string, status: any): void {
    if (!this.state.tools[toolName]) {
      this.state.tools[toolName] = {
        status,
        startTime: new Date(),
        attempts: 1
      };
    } else {
      this.state.tools[toolName].status = status;
      if (status.phase === 'completed' || status.phase === 'failed') {
        this.state.tools[toolName].endTime = new Date();
      }
    }
    this.state.updatedAt = new Date();
  }
  
  private async streamToolStatus(status: any): Promise<void> {
    await this.streamingUtils.streamToolStatus(status);
  }
  
  private async completeWorkflow(
    context: Map<string, any>, 
    startTime: number, 
    workflowId: string, 
    toolsExecuted: string[]
  ): Promise<WorkflowResult> {
    const totalTime = Date.now() - startTime;
    const responseData = context.get('Response Generator');
    
    await this.streamingUtils.streamWorkflowComplete(totalTime);
    
    // The response data is nested in the data property from the tool result
    const finalAnswer = responseData?.answer || responseData?.data?.answer;
    
    if (finalAnswer) {
      await this.streamingUtils.streamFinalAnswer(finalAnswer);
    }
    
    return {
      success: true,
      finalAnswer: finalAnswer || 'Workflow completed but no final answer generated.',
      workflowId,
      totalTime,
      toolsExecuted
    };
  }
  
  private async handleWorkflowFailure(
    tool: WorkflowTool<any, any>, 
    result: ToolResult<any>, 
    stepIndex: number, 
    startTime: number, 
    workflowId: string, 
    toolsExecuted: string[]
  ): Promise<WorkflowResult> {
    const totalTime = Date.now() - startTime;
    
    // Try graceful degradation
    const degradedResponse = await this.errorHandler.handleGracefulDegradation(tool, result, stepIndex);
    
    if (degradedResponse) {
      await this.streamingUtils.streamFinalAnswer(degradedResponse);
      
      return {
        success: true,
        finalAnswer: degradedResponse,
        workflowId,
        totalTime,
        toolsExecuted,
        degradedMode: true
      };
    }
    
    return {
      success: false,
      workflowId,
      totalTime,
      toolsExecuted,
      errors: result.errors
    };
  }
  
  private async handleGeneralResponse(
    userQuery: string, 
    startTime: number, 
    workflowId: string, 
    toolsExecuted: string[]
  ): Promise<WorkflowResult> {
    const totalTime = Date.now() - startTime;
    const generalAnswer = `I understand you're asking about "${userQuery}", but this doesn't appear to be related to MODFLOW, PEST, or hydrology topics that I can search for in the repositories. Could you rephrase your question to focus on groundwater modeling, MODFLOW usage, or related technical topics?`;
    
    await this.streamingUtils.streamFinalAnswer(generalAnswer);
    
    return {
      success: true,
      finalAnswer: generalAnswer,
      workflowId,
      totalTime,
      toolsExecuted
    };
  }
  
  private async handleCriticalFailure(
    error: any, 
    startTime: number, 
    workflowId: string, 
    toolsExecuted: string[]
  ): Promise<WorkflowResult> {
    const totalTime = Date.now() - startTime;
    
    await this.streamingUtils.streamFinalAnswer(
      'I apologize, but I encountered a critical error while processing your request. Please try again or rephrase your question.'
    );
    
    return {
      success: false,
      workflowId,
      totalTime,
      toolsExecuted,
      errors: [{ message: error instanceof Error ? error.message : 'Unknown critical error' }]
    };
  }
}