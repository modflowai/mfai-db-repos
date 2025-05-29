import { z } from 'zod';

// Match schemas from /mfai_mcp_server_cloudflare/src/index-sse.ts
export const ListRepositoriesSchema = z.object({
  include_navigation: z.boolean().optional().default(true)
    .describe('Include navigation guides in response'),
});

export const SearchFilesSchema = z.object({
  query: z.string().describe('Search query'),
  search_type: z.enum(['text', 'semantic']).describe('Type of search to perform'),
  repositories: z.array(z.string()).optional().describe('Filter by repository names'),
});

// Response schemas based on actual database models
export const RepositorySchema = z.object({
  id: z.number(),
  name: z.string(),
  url: z.string(),
  file_count: z.number(),
  navigation_guide: z.string().nullable().optional(),
  repository_type: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const SearchResultSchema = z.object({
  id: z.number(),
  repo_id: z.number(),
  repo_name: z.string(),
  repo_url: z.string(),
  filepath: z.string(),
  filename: z.string(),
  extension: z.string(),
  file_type: z.string(),
  content: z.string(),
  rank: z.number().optional(),
  similarity: z.number().optional(),
  snippet: z.string(),
});

// Tool definitions matching server implementation
export const TOOL_DEFINITIONS = {
  list_repositories_with_navigation: {
    name: 'list_repositories_with_navigation',
    description: 'Get all repositories with their navigation guides that explain what each repository does and how to search it effectively.',
    inputSchema: ListRepositoriesSchema,
    outputSchema: z.array(RepositorySchema),
  },
  mfai_search: {
    name: 'mfai_search',
    description: 'Search across all MFAI indexed repositories in the database. No path needed. Use text search for exact terms/keywords or semantic search for concepts/questions.',
    inputSchema: SearchFilesSchema,
    outputSchema: z.array(SearchResultSchema),
  },
} as const;

export type ToolName = keyof typeof TOOL_DEFINITIONS;
export type ToolInput<T extends ToolName> = z.infer<typeof TOOL_DEFINITIONS[T]['inputSchema']>;
export type ToolOutput<T extends ToolName> = z.infer<typeof TOOL_DEFINITIONS[T]['outputSchema']>;