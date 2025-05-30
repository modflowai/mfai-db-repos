/**
 * Base interfaces and types for modular workflow tools
 */

import { z } from 'zod';
import type { DataStreamWriter } from 'ai';

export interface ToolContext {
  userId: string;
  sessionId: string;
  dataStream: DataStreamWriter;
  previousResults: Map<string, any>;
  streamStatus: (status: ToolStatus) => Promise<void>;
}

export interface ToolStatus {
  tool: string;
  phase: 'starting' | 'executing' | 'processing' | 'completed' | 'failed' | 'retrying';
  progress?: number;           // 0-100 percentage
  currentAction?: string;      // What the tool is currently doing
  estimatedTimeRemaining?: number;
}

export interface ToolError {
  type: 'validation' | 'execution' | 'timeout' | 'network' | 'api_limit';
  message: string;
  code?: string;
  retryable: boolean;
  context?: Record<string, any>;
}

export interface ToolResult<T> {
  success: boolean;
  data: T;
  shortSummary: string;        // One-line result for UI display
  detailedSummary?: string;    // Expandable detailed information
  confidence: number;          // 0-1 confidence score
  metadata: {
    executionTime: number;
    tokensUsed?: number;
    cacheHit?: boolean;
  };
  nextSuggestedAction?: string;
  errors?: ToolError[];
}

export interface WorkflowTool<TInput, TOutput> {
  name: string;
  description: string;
  schema: z.ZodSchema<TInput>;
  execute: (input: TInput, context: ToolContext) => Promise<ToolResult<TOutput>>;
  estimatedDuration: number;
  retryable: boolean;
}

export interface WorkflowState {
  id: string;
  userId: string;
  originalQuery: string;
  currentStep: number;
  totalSteps: number;
  tools: {
    [toolName: string]: {
      status: ToolStatus;
      result?: ToolResult<any>;
      startTime: Date;
      endTime?: Date;
      attempts: number;
    };
  };
  context: Map<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Helper function to create a workflow tool with standardized error handling
 */
export function createWorkflowTool<TInput, TOutput>(
  config: WorkflowTool<TInput, TOutput>
): WorkflowTool<TInput, TOutput> {
  return {
    ...config,
    execute: async (input: TInput, context: ToolContext): Promise<ToolResult<TOutput>> => {
      const startTime = Date.now();
      
      try {
        // Validate input
        const validatedInput = config.schema.parse(input);
        
        // Execute the tool
        const result = await config.execute(validatedInput, context);
        
        // Ensure execution time is recorded
        if (!result.metadata.executionTime) {
          result.metadata.executionTime = Date.now() - startTime;
        }
        
        return result;
      } catch (error) {
        const executionTime = Date.now() - startTime;
        
        // Stream failure status
        await context.streamStatus({
          tool: config.name,
          phase: 'failed',
          currentAction: `Failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        });
        
        return {
          success: false,
          data: null as any,
          shortSummary: `❌ ${config.name} failed`,
          confidence: 0,
          metadata: {
            executionTime
          },
          errors: [{
            type: error instanceof z.ZodError ? 'validation' : 'execution',
            message: error instanceof Error ? error.message : 'Unknown error',
            retryable: config.retryable,
            context: error instanceof z.ZodError ? { issues: error.issues } : undefined
          }]
        };
      }
    }
  };
}