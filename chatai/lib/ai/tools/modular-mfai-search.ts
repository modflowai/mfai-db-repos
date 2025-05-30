/**
 * Modular MFAI Search Tool - Proper AI SDK tool that shows in UI
 */

import { tool } from 'ai';
import { z } from 'zod';
import { WorkflowOrchestrator } from './workflow';
import type { DataStreamWriter } from 'ai';

interface ToolProps {
  session: any;
  dataStream: DataStreamWriter;
}

export const modularMfaiSearch = ({ session, dataStream }: ToolProps) =>
  tool({
    description: 'Search MODFLOW repositories using streaming modular workflow with real-time progress updates',
    parameters: z.object({
      query: z.string().describe('Your search query for MODFLOW/PEST content'),
    }),
    execute: async ({ query }) => {
      // Initialize workflow orchestrator
      const orchestrator = new WorkflowOrchestrator(dataStream, session?.user?.id || 'user-session');

      // Execute the modular workflow
      const workflowResult = await orchestrator.execute(
        query, 
        [], // conversation history
        []  // previous results
      );

      // Return structured result for the UI
      return {
        query,
        success: workflowResult.success,
        finalAnswer: workflowResult.finalAnswer,
        workflowId: workflowResult.workflowId,
        totalTime: workflowResult.totalTime,
        toolsExecuted: workflowResult.toolsExecuted,
        degradedMode: workflowResult.degradedMode || false,
        timestamp: new Date().toISOString(),
        // Include the answer in a format the UI can display
        answer: workflowResult.finalAnswer,
        metadata: {
          executionTime: workflowResult.totalTime,
          confidence: workflowResult.degradedMode ? 0.7 : 0.9,
          searchStrategy: 'modular_workflow'
        }
      };
    },
  });