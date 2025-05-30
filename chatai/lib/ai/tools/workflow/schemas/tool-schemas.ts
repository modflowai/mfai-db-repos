/**
 * Zod schemas for all workflow tools
 */

import { z } from 'zod';

// Relevance Checker Schemas
export const RelevanceCheckerInputSchema = z.object({
  query: z.string().min(1, "Query cannot be empty"),
});

export const RelevanceCheckerOutputSchema = z.object({
  isRelevant: z.boolean(),
  confidence: z.number().min(0).max(1),
  domains: z.array(z.string()),
  reasoning: z.string(),
});

// Query Analyzer Schemas
export const QueryAnalyzerInputSchema = z.object({
  query: z.string(),
  relevanceData: z.object({
    isRelevant: z.boolean(),
    domains: z.array(z.string()),
    confidence: z.number()
  })
});

export const QueryAnalyzerOutputSchema = z.object({
  strategy: z.enum(['text', 'semantic', 'hybrid']),
  repositories: z.array(z.string()),
  searchType: z.string(),
  keywords: z.array(z.string()),
  expectedResultTypes: z.array(z.string()),
});

// Repository Searcher Schemas
export const RepositorySearcherInputSchema = z.object({
  query: z.string(),
  strategy: z.enum(['text', 'semantic', 'hybrid']),
  repositories: z.array(z.string()),
  searchParameters: z.object({
    maxResults: z.number().default(10),
    minSimilarity: z.number().default(0.7)
  }).optional()
});

export const SearchResultSchema = z.object({
  filename: z.string(),
  filepath: z.string(),
  repo_name: z.string(),
  snippet: z.string(),
  similarity: z.number().optional(),
  relevanceScore: z.number().optional(),
  relevanceReasoning: z.string().optional(),
});

export const RepositorySearcherOutputSchema = z.object({
  results: z.array(SearchResultSchema),
  totalFound: z.number(),
  repositoriesSearched: z.array(z.string()),
  searchStrategy: z.string(),
});

// Context Validator Schemas
export const ContextValidatorInputSchema = z.object({
  query: z.string(),
  analysisContext: z.object({
    strategy: z.string(),
    repositories: z.array(z.string()),
    keywords: z.array(z.string())
  }),
  previousResults: z.array(z.any()).optional(),
  conversationHistory: z.array(z.any()).optional()
});

export const ContextValidatorOutputSchema = z.object({
  needsNewSearch: z.boolean(),
  contextSufficiency: z.number(),
  availableContext: z.array(z.string()),
  reasoning: z.string(),
  suggestedResponse: z.string().optional(),
});

// Response Generator Schemas
export const ResponseGeneratorInputSchema = z.object({
  query: z.string(),
  searchResults: z.array(SearchResultSchema),
  analysisContext: z.object({
    strategy: z.string(),
    repositories: z.array(z.string()),
    confidence: z.number()
  })
});

export const ResponseGeneratorOutputSchema = z.object({
  answer: z.string(),
  sourceDocuments: z.array(SearchResultSchema),
  confidence: z.number(),
  additionalResources: z.array(z.string()).optional(),
});

// Workflow State Schema
export const WorkflowStateSchema = z.object({
  id: z.string(),
  userId: z.string(),
  originalQuery: z.string(),
  currentStep: z.number(),
  totalSteps: z.number(),
  context: z.record(z.any()),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// Type exports
export type RelevanceCheckerInput = z.infer<typeof RelevanceCheckerInputSchema>;
export type RelevanceCheckerOutput = z.infer<typeof RelevanceCheckerOutputSchema>;
export type QueryAnalyzerInput = z.infer<typeof QueryAnalyzerInputSchema>;
export type QueryAnalyzerOutput = z.infer<typeof QueryAnalyzerOutputSchema>;
export type ContextValidatorInput = z.infer<typeof ContextValidatorInputSchema>;
export type ContextValidatorOutput = z.infer<typeof ContextValidatorOutputSchema>;
export type RepositorySearcherInput = z.infer<typeof RepositorySearcherInputSchema>;
export type RepositorySearcherOutput = z.infer<typeof RepositorySearcherOutputSchema>;
export type ResponseGeneratorInput = z.infer<typeof ResponseGeneratorInputSchema>;
export type ResponseGeneratorOutput = z.infer<typeof ResponseGeneratorOutputSchema>;
export type SearchResult = z.infer<typeof SearchResultSchema>;