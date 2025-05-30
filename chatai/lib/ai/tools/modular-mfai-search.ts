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
      // Stream immediate feedback
      dataStream.writeData({
        type: 'text-delta',
        content: `🚀 **Starting MODFLOW Search**: "${query}"\n\n`,
      });

      // Initialize workflow orchestrator
      const orchestrator = new WorkflowOrchestrator(dataStream, session?.user?.id || 'user-session');

      // Execute the modular workflow with streaming progress
      const workflowResult = await orchestrator.execute(
        query, 
        [], // conversation history
        []  // previous results
      );

      // Stream completion
      dataStream.writeData({
        type: 'text-delta',
        content: `✅ **Search Complete**: Found answer in ${(workflowResult.totalTime / 1000).toFixed(1)}s\n\n`,
      });

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