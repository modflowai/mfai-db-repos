/**
 * Query Analyzer Tool - Standalone AI SDK tool
 */

import { tool } from 'ai';
import { z } from 'zod';
import { queryAnalyzer as workflowQueryAnalyzer } from './workflow/tools/query-analyzer';
import type { DataStreamWriter } from 'ai';

interface ToolProps {
  session: any;
  dataStream: DataStreamWriter;
}

export const queryAnalyzer = ({ session, dataStream }: ToolProps) =>
  tool({
    description: 'Analyze query to determine optimal search strategy and target repositories',
    parameters: z.object({
      query: z.string().describe('User query to analyze'),
      relevanceData: z.object({
        isRelevant: z.boolean(),
        domains: z.array(z.string()),
        confidence: z.number()
      }).optional().describe('Previous relevance check results'),
    }),
    execute: async ({ query, relevanceData }) => {
      console.log('📋 Query Analyzer tool EXECUTED with query:', query);
      
      // Create minimal tool context
      const toolContext = {
        userId: session?.user?.id || 'user-session',
        sessionId: 'standalone-session',
        dataStream,
        previousResults: new Map(),
        streamStatus: async (status: any) => {
          dataStream.writeData({
            type: 'text-delta',
            content: `⚡ **Query Analyzer**: ${status.currentAction || 'Analyzing...'}\n\n`,
          });
        }
      };

      // Execute the workflow tool
      const result = await workflowQueryAnalyzer.execute({ 
        query, 
        relevanceData: relevanceData || { isRelevant: true, domains: [], confidence: 0.5 }
      }, toolContext);

      // Return structured result for UI component
      return {
        query,
        strategy: result.data?.strategy || 'semantic',
        repositories: result.data?.repositories || [],
        searchType: result.data?.searchType || 'general',
        keywords: result.data?.keywords || [],
        expectedResultTypes: result.data?.expectedResultTypes || [],
        success: result.success,
        timestamp: new Date().toISOString(),
      };
    },
  });