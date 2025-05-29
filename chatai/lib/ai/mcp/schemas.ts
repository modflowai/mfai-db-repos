/**
 * MCP Tool Schema Definitions for MFAI Repository Navigator
 */

import { z } from 'zod';

export const ListRepositoriesSchema = z.object({
  include_navigation: z.boolean().optional().default(true)
    .describe('Include navigation guides in response'),
});

export const SearchFilesSchema = z.object({
  query: z.string().describe('Search query'),
  search_type: z.enum(['text', 'semantic']).describe('Type of search to perform'),
  repositories: z.array(z.string()).optional().describe('Filter by repository names'),
});

export const MCPToolResultSchema = z.object({
  content: z.array(z.object({
    type: z.literal('text'),
    text: z.string(),
  })),
});

export type ListRepositoriesParams = z.infer<typeof ListRepositoriesSchema>;
export type SearchFilesParams = z.infer<typeof SearchFilesSchema>;
export type MCPToolResult = z.infer<typeof MCPToolResultSchema>;