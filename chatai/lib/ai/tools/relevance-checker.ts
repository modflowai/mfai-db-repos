/**
 * Relevance Checker Tool - Standalone AI SDK tool
 */

import { tool } from 'ai';
import { z } from 'zod';
import { relevanceChecker as workflowRelevanceChecker } from './workflow/tools/relevance-checker';
import type { DataStreamWriter } from 'ai';

interface ToolProps {
  session: any;
  dataStream: DataStreamWriter;
}

export const relevanceChecker = ({ session, dataStream }: ToolProps) =>
  tool({
    description: 'Check if a query is relevant to MODFLOW/PEST domain',
    parameters: z.object({
      query: z.string().describe('User query to check for relevance'),
    }),
    execute: async ({ query }) => {
      console.log('🔍 Relevance Checker tool EXECUTED with query:', query);
      
      // Create minimal tool context
      const toolContext = {
        userId: session?.user?.id || 'user-session',
        sessionId: 'standalone-session',
        dataStream,
        previousResults: new Map(),
        streamStatus: async (status: any) => {
          dataStream.writeData({
            type: 'text-delta',
            content: `🔄 **Relevance Checker**: ${status.currentAction || 'Analyzing...'}\n\n`,
          });
        }
      };

      // Execute the workflow tool
      const result = await workflowRelevanceChecker.execute({ query }, toolContext);

      // Return structured result for UI component
      return {
        query,
        isRelevant: result.data?.isRelevant || false,
        confidence: result.data?.confidence || 0,
        domains: result.data?.domains || [],
        reasoning: result.data?.reasoning || '',
        success: result.success,
        timestamp: new Date().toISOString(),
      };
    },
  });