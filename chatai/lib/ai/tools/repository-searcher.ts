/**
 * Repository Searcher Tool - Standalone AI SDK tool
 */

import { tool } from 'ai';
import { z } from 'zod';
import { repositorySearcher as workflowRepositorySearcher } from './workflow/tools/repository-searcher';
import type { DataStreamWriter } from 'ai';

interface ToolProps {
  session: any;
  dataStream: DataStreamWriter;
}

export const repositorySearcher = ({ session, dataStream }: ToolProps) =>
  tool({
    description: 'Search MODFLOW repositories for relevant content based on query analysis',
    parameters: z.object({
      query: z.string().describe('Search query'),
      strategy: z.enum(['text', 'semantic', 'hybrid']).describe('Search strategy to use'),
      repositories: z.array(z.string()).describe('Target repositories to search'),
      searchParameters: z.object({
        maxResults: z.number().default(10),
        minSimilarity: z.number().default(0.7)
      }).optional()
    }),
    execute: async ({ query, strategy, repositories, searchParameters }) => {
      console.log('🔍 Repository Searcher tool EXECUTED:', { query, strategy, repositories });
      
      // Create minimal tool context
      const toolContext = {
        userId: session?.user?.id || 'user-session',
        sessionId: 'standalone-session',
        dataStream,
        previousResults: new Map(),
        streamStatus: async (status: any) => {
          dataStream.writeData({
            type: 'text-delta',
            content: `🔍 **Repository Searcher**: ${status.currentAction || 'Searching...'}\n\n`,
          });
        }
      };

      // Execute the workflow tool
      const result = await workflowRepositorySearcher.execute({ 
        query, 
        strategy,
        repositories,
        searchParameters: searchParameters || { maxResults: 10, minSimilarity: 0.7 }
      }, toolContext);

      // Return structured result for UI component
      return {
        query,
        strategy,
        repositories,
        results: result.data?.results || [],
        totalFound: result.data?.totalFound || 0,
        repositoriesSearched: result.data?.repositoriesSearched || [],
        searchStrategy: result.data?.searchStrategy || strategy,
        success: result.success,
        timestamp: new Date().toISOString(),
      };
    },
  });