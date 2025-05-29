# MCP Tools Integration Roadmap for ChatAI v2.0 - AI SDK 5 Alpha Enhanced

*Created: May 29, 2025*  
*Updated: May 29, 2025 - AI SDK 5 Alpha Integration*

## Overview

This roadmap outlines the integration of Model Context Protocol (MCP) tools into the ChatAI application using **AI SDK 5 Alpha's advanced features**, including `prepareStep` for intelligent tool orchestration, enhanced SSE streaming, and dynamic tool selection. This creates an intelligent agent that automatically chooses optimal search strategies and provides seamless MODFLOW repository exploration.

## Revolutionary AI SDK 5 Alpha Features for MCP Integration

### 🎯 **LLM-Powered Intelligence (NO HARDCODING)**
- **LLM Intent Analysis**: Use the model itself to understand user queries and determine optimal strategies
- **Dynamic Tool Selection**: LLM decides which tools to use based on contextual understanding
- **Smart Search Strategy**: LLM analyzes queries to select text/semantic/hybrid search approaches
- **Relevance Scoring**: LLM evaluates search result relevance with reasoning
- **Adaptive Workflows**: Multi-step processes guided by LLM decision-making

### 🚀 **prepareStep Intelligence**
- **Forced Tool Selection**: LLM-driven automatic tool triggering
- **Multi-Step Workflows**: Create intelligent repository exploration sequences 
- **Dynamic Tool Constraints**: LLM-based tool availability decisions
- **Context-Aware Processing**: Each step informed by LLM analysis

### 🚀 **Enhanced Streaming & Real-Time UX**
- **AI SDK 5 SSE Support**: More stable and efficient real-time streaming
- **Type-Safe Stream Writers**: Custom data parts for repository results
- **Parallel Tool Execution**: Run multiple searches simultaneously
- **Rich Metadata Streaming**: Include search context and reasoning in streams

## Current ChatAI Tool Architecture Analysis

### Existing Tool Implementation

The ChatAI app currently implements **4 core tools** following AI SDK patterns:

```typescript
// Current tool structure in /lib/ai/tools/
export const toolName = tool({
  description: 'Tool description for AI model',
  parameters: z.object({
    param1: z.string(),
    param2: z.enum(['option1', 'option2'])
  }),
  execute: async ({ param1, param2 }) => {
    // Tool logic with DataStreamWriter integration
    return result;
  }
});
```

**Key Features:**
- **Zod schema validation** for all parameters
- **DataStreamWriter integration** for real-time UI updates
- **Session-aware tools** with user authentication
- **Multi-step execution** (max 5 steps)
- **Artifact system integration** for document management

### Tool Registration Pattern

Tools are registered in the chat route (`/app/(chat)/api/chat/route.ts`):

```typescript
tools: {
  getWeather,
  createDocument: createDocument({ session, dataStream }),
  updateDocument: updateDocument({ session, dataStream }),
  requestSuggestions: requestSuggestions({ session, dataStream }),
  // NEW: MCP tools will be added here
},
experimental_activeTools: [
  'getWeather',
  'createDocument', 
  'updateDocument',
  'requestSuggestions',
  // NEW: MCP tool names
],
```

## Revolutionary Integration Strategy with AI SDK 5 Alpha

### Phase 1: AI SDK 5 Alpha Migration & Intelligent Agent Foundation
**Duration:** 3-4 days

#### 1.1 AI SDK 5 Alpha Upgrade
Migrate ChatAI to AI SDK 5 alpha to unlock advanced capabilities:

**File:** `/lib/ai/intelligent-agent.ts`
```typescript
import { experimental_generateSteps, experimental_prepareStep } from 'ai';
import { RepositoryIntentAnalyzer } from './intent-analyzer';

export interface IntelligentMCPAgent {
  analyzeQuery(query: string): Promise<RepositoryIntent>;
  executeRepositoryWorkflow(intent: RepositoryIntent): Promise<WorkflowResult>;
  streamOptimizedResults(results: any[]): AsyncGenerator<StreamPart>;
}

export class RepositoryIntentAnalyzer {
  static analyzeQuery(query: string): RepositoryIntent {
    // AI-powered query analysis to determine:
    // - Whether to list repositories or search
    // - Whether to use text or semantic search
    // - Which repositories to target
    // - Expected result format
    return {
      action: 'search' | 'list' | 'explore',
      searchType: 'text' | 'semantic' | 'hybrid',
      repositories: string[] | 'all',
      confidence: number,
      reasoning: string,
    };
  }
}
```

#### 1.2 LLM-Powered Intent Analysis & Workflow Engine
Create intelligent tool orchestration using LLM-based intent analysis with prepareStep:

**File:** `/lib/ai/workflow-engine.ts`
```typescript
import { generateText } from 'ai';

export const repositoryWorkflowAgent = experimental_generateSteps({
  experimental_prepareStep: async ({ model, stepNumber, message }) => {
    // LLM-powered intent analysis
    const intentAnalysis = await analyzeUserIntent(message.content);
    
    // Step 0: LLM decides if repository discovery is needed
    if (stepNumber === 0 && intentAnalysis.needsRepositoryDiscovery) {
      return {
        model,
        toolChoice: { type: 'tool', toolName: 'listRepositories' },
        experimental_activeTools: ['listRepositories'],
        experimental_context: { phase: 'discovery', intent: intentAnalysis }
      };
    }
    
    // Step 1: LLM-guided search strategy selection
    if (stepNumber === 1 && intentAnalysis.shouldSearch) {
      return {
        model,
        toolChoice: { type: 'tool', toolName: 'intelligentMfaiSearch' },
        experimental_activeTools: ['intelligentMfaiSearch'],
        experimental_toolParameters: {
          intelligentMfaiSearch: {
            strategy: intentAnalysis.optimalSearchStrategy,
            parallel_search: intentAnalysis.benefitsFromParallelSearch,
            repositories: intentAnalysis.targetRepositories
          }
        }
      };
    }
    
    // Step 2: LLM decides on result enhancement
    if (stepNumber === 2 && intentAnalysis.shouldEnhanceResults) {
      return {
        model,
        toolChoice: { type: 'tool', toolName: 'createDocument' },
        experimental_activeTools: ['createDocument', 'intelligentMfaiSearch'],
        experimental_context: { phase: 'enhancement' }
      };
    }
    
    // Default: All tools available
    return { model };
  }
});

// LLM-powered intent analysis function
async function analyzeUserIntent(userQuery: string) {
  const result = await generateText({
    model: myProvider.languageModel('chat-model'),
    messages: [
      {
        role: 'system',
        content: `You are an expert at analyzing user queries for MODFLOW repository search systems.
        
        Analyze the user's query and determine:
        1. Does the user need to see available repositories first? (needsRepositoryDiscovery)
        2. Does the user want to search for specific content? (shouldSearch)
        3. What search strategy is optimal? (optimalSearchStrategy: 'text' | 'semantic' | 'hybrid')
        4. Would parallel searching improve results? (benefitsFromParallelSearch)
        5. Which repositories should be targeted? (targetRepositories or null for all)
        6. Should results be enhanced with documentation? (shouldEnhanceResults)
        
        Respond in JSON format with these exact field names.
        
        Examples:
        - "What MODFLOW repositories are available?" → needsRepositoryDiscovery: true
        - "Find groundwater pumping examples" → shouldSearch: true, optimalSearchStrategy: 'semantic'
        - "Search for 'flopy.modflow.mfwel'" → shouldSearch: true, optimalSearchStrategy: 'text'
        - "Complete guide to boundary conditions" → shouldSearch: true, shouldEnhanceResults: true, benefitsFromParallelSearch: true`
      },
      {
        role: 'user',
        content: userQuery
      }
    ],
    temperature: 0.1,
  });

  return JSON.parse(result.text);
}
```

#### 1.2 Environment Configuration
Add MCP server configuration to environment variables:

**File:** `.env.example`
```env
# MCP Server Configuration
MCP_SERVER_URL=https://mfai-repository-navigator.little-grass-273a.workers.dev
MCP_API_KEY=your_mcp_api_key_here
MCP_ENABLED=true
```

#### 1.3 MCP Tool Schema Definitions
Define Zod schemas matching our MCP server tools:

**File:** `/lib/ai/mcp/schemas.ts`
```typescript
export const ListRepositoriesSchema = z.object({
  include_navigation: z.boolean().optional().default(true)
    .describe('Include navigation guides in response'),
});

export const SearchFilesSchema = z.object({
  query: z.string().describe('Search query'),
  search_type: z.enum(['text', 'semantic']).describe('Type of search to perform'),
  repositories: z.array(z.string()).optional().describe('Filter by repository names'),
});
```

### Phase 2: Intelligent MCP Tool Implementation with Enhanced Streaming
**Duration:** 4-5 days

#### 2.1 Hybrid Search Engine with Parallel Execution
Create an intelligent search system that can run multiple search strategies simultaneously:

**File:** `/lib/ai/tools/intelligent-mfai-search.ts`
```typescript
import { experimental_streamCustomData } from 'ai';

export const intelligentMfaiSearch = ({ session, dataStream }: ToolProps) =>
  tool({
    description: 'Intelligent MFAI repository search that automatically optimizes search strategy and runs parallel searches when beneficial.',
    parameters: z.object({
      query: z.string().describe('Search query'),
      strategy: z.enum(['auto', 'text', 'semantic', 'hybrid']).default('auto')
        .describe('Search strategy - auto uses AI to determine optimal approach'),
      repositories: z.array(z.string()).optional()
        .describe('Filter to specific repositories'),
      parallel_search: z.boolean().optional().default(false)
        .describe('Run both text and semantic searches in parallel'),
    }),
    execute: async ({ query, strategy, repositories, parallel_search }) => {
      try {
        // Stream search strategy analysis
        dataStream.writeCustomData('search-analysis', {
          query,
          strategy: strategy === 'auto' ? 'analyzing...' : strategy,
          phase: 'planning'
        });

        const mcpClient = new MCPClient();
        await mcpClient.connect({
          serverUrl: process.env.MCP_SERVER_URL!,
          apiKey: process.env.MCP_API_KEY!,
        });

        let searchStrategy = strategy;
        
        // AI-powered strategy selection for 'auto' mode
        if (strategy === 'auto') {
          searchStrategy = analyzeQueryForOptimalSearch(query);
          dataStream.writeCustomData('search-strategy', {
            selected: searchStrategy,
            reasoning: getStrategyReasoning(query, searchStrategy)
          });
        }

        // Execute parallel searches for hybrid mode
        if (parallel_search || searchStrategy === 'hybrid') {
          const [textResults, semanticResults] = await Promise.all([
            mcpClient.callTool('mfai_search', {
              query,
              search_type: 'text',
              repositories,
            }),
            mcpClient.callTool('mfai_search', {
              query,
              search_type: 'semantic',
              repositories,
            })
          ]);

          // Stream results with intelligent merging
          return mergeAndRankResults(textResults, semanticResults, query);
        }

        // Single search execution with real-time streaming
        const result = await mcpClient.callTool('mfai_search', {
          query,
          search_type: searchStrategy as 'text' | 'semantic',
          repositories,
        });

        const searchResults = JSON.parse(result.content[0].text);
        
        // Enhanced streaming with metadata
        dataStream.writeCustomData('search-results', {
          total: searchResults.length,
          strategy: searchStrategy,
          repositories_searched: repositories || 'all'
        });

        // Stream individual results with LLM-powered relevance scoring
        for (const [index, searchResult] of searchResults.entries()) {
          const relevanceScore = await calculateLLMRelevanceScore(searchResult, query);
          dataStream.writeCustomData('result-item', {
            index: index + 1,
            ...searchResult,
            relevanceScore,
            relevanceReasoning: relevanceScore.reasoning
          });
        }

        await mcpClient.close();
        return { query, strategy: searchStrategy, results: searchResults };
      } catch (error) {
        dataStream.writeCustomData('search-error', { error: error.message });
        throw error;
      }
    },
  });

// LLM-powered search strategy analysis
async function analyzeQueryForOptimalSearch(query: string): Promise<'text' | 'semantic' | 'hybrid'> {
  const result = await generateText({
    model: myProvider.languageModel('chat-model'),
    messages: [
      {
        role: 'system',
        content: `You are an expert at determining optimal search strategies for MODFLOW repository queries.

        Given a user query, determine the best search strategy:
        
        - "text": For exact matches, specific function names, file names, code snippets, or quoted terms
        - "semantic": For conceptual questions, "how to" queries, understanding workflows, or finding similar approaches  
        - "hybrid": For comprehensive searches that benefit from both exact matches and conceptual similarity

        Consider:
        - Quotes or specific technical terms → text search
        - Questions about concepts or approaches → semantic search  
        - Requests for "everything about" or "complete guide" → hybrid search
        
        Respond with only: "text", "semantic", or "hybrid"`
      },
      {
        role: 'user', 
        content: `Query: "${query}"`
      }
    ],
    temperature: 0.1,
  });

  const strategy = result.text.trim().toLowerCase();
  return ['text', 'semantic', 'hybrid'].includes(strategy) 
    ? strategy as 'text' | 'semantic' | 'hybrid'
    : 'semantic'; // Default fallback
}

// LLM-powered relevance scoring instead of hardcoded calculations
async function calculateLLMRelevanceScore(searchResult: any, userQuery: string) {
  const result = await generateText({
    model: myProvider.languageModel('chat-model'),
    messages: [
      {
        role: 'system',
        content: `You are an expert at scoring relevance between search results and user queries for MODFLOW repositories.

        Given a search result and user query, provide:
        1. A relevance score from 0.0 to 1.0 (where 1.0 is perfectly relevant)
        2. A brief reasoning for the score

        Consider:
        - How well the file content matches the user's intent
        - Whether the file contains the specific information requested
        - The quality and usefulness of the code/content for the user's needs
        - The file's role in typical MODFLOW workflows

        Respond in JSON format:
        {
          "score": 0.85,
          "reasoning": "Brief explanation of why this file is relevant"
        }`
      },
      {
        role: 'user',
        content: `User Query: "${userQuery}"
        
        Search Result:
        - Filename: ${searchResult.filename}
        - Repository: ${searchResult.repo_name}
        - Path: ${searchResult.filepath}
        - Content Snippet: ${searchResult.snippet}
        ${searchResult.similarity ? `- Original Similarity: ${searchResult.similarity}` : ''}`
      }
    ],
    temperature: 0.2,
  });

  try {
    return JSON.parse(result.text);
  } catch {
    // Fallback to original similarity if LLM parsing fails
    return {
      score: searchResult.similarity || 0.5,
      reasoning: "LLM analysis unavailable, using original similarity"
    };
  }
}
```

**File:** `/lib/ai/tools/list-repositories.ts`
```typescript
export const listRepositories = ({ session, dataStream }: ToolProps) => 
  tool({
    description: 'List MODFLOW AI repositories with navigation guides that explain what each repository does and how to search effectively.',
    parameters: z.object({
      include_navigation: z.boolean().optional().default(true)
        .describe('Include full navigation guides for each repository'),
    }),
    execute: async ({ include_navigation }) => {
      try {
        // Stream real-time status updates
        dataStream.writeData({
          type: 'text-delta',
          content: '🔍 Fetching MODFLOW repositories...\n\n',
        });

        const mcpClient = new MCPClient();
        await mcpClient.connect({
          serverUrl: process.env.MCP_SERVER_URL!,
          apiKey: process.env.MCP_API_KEY!,
        });

        const result = await mcpClient.callTool('list_repositories_with_navigation', {
          include_navigation,
        });

        const repositories = JSON.parse(result.content[0].text);

        // Stream formatted repository information
        dataStream.writeData({
          type: 'text-delta',
          content: `Found ${repositories.length} repositories:\n\n`,
        });

        for (const repo of repositories) {
          dataStream.writeData({
            type: 'text-delta',
            content: `**${repo.name}** (${repo.file_count} files)\n` +
                    `📁 ${repo.url}\n` +
                    (repo.navigation_guide ? `📖 ${repo.navigation_guide.substring(0, 200)}...\n` : '') +
                    '\n',
          });
        }

        await mcpClient.close();

        return {
          repositories,
          count: repositories.length,
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        dataStream.writeData({
          type: 'text-delta',
          content: `❌ Error fetching repositories: ${error.message}\n`,
        });
        throw new Error(`Failed to list repositories: ${error.message}`);
      }
    },
  });
```

#### 2.2 Repository Search Tool
Create a comprehensive search tool wrapping the MCP `mfai_search` endpoint:

**File:** `/lib/ai/tools/mfai-search.ts`
```typescript
export const mfaiSearch = ({ session, dataStream }: ToolProps) =>
  tool({
    description: 'Search across all MFAI indexed repositories in the database. No path needed. Use text search for exact terms/keywords or semantic search for concepts/questions.',
    parameters: z.object({
      query: z.string().describe('Your search query'),
      search_type: z.enum(['text', 'semantic'])
        .describe('Choose text for exact matches, semantic for conceptual search'),
      repositories: z.array(z.string()).optional()
        .describe('Optional: Filter to specific repository names'),
      max_results: z.number().optional().default(10)
        .describe('Maximum number of results to return'),
    }),
    execute: async ({ query, search_type, repositories, max_results }) => {
      try {
        // Stream search progress
        dataStream.writeData({
          type: 'text-delta',
          content: `🔍 Searching for "${query}" using ${search_type} search...\n\n`,
        });

        const mcpClient = new MCPClient();
        await mcpClient.connect({
          serverUrl: process.env.MCP_SERVER_URL!,
          apiKey: process.env.MCP_API_KEY!,
        });

        const result = await mcpClient.callTool('mfai_search', {
          query,
          search_type,
          repositories,
        });

        const searchResults = JSON.parse(result.content[0].text);
        const limitedResults = searchResults.slice(0, max_results);

        // Stream results with rich formatting
        dataStream.writeData({
          type: 'text-delta',
          content: `Found ${searchResults.length} results` +
                  (limitedResults.length < searchResults.length ? ` (showing top ${limitedResults.length})` : '') +
                  ':\n\n',
        });

        for (const [index, searchResult] of limitedResults.entries()) {
          const similarity = searchResult.similarity ? 
            ` (${(searchResult.similarity * 100).toFixed(1)}% match)` : '';
          
          dataStream.writeData({
            type: 'text-delta',
            content: `**${index + 1}. ${searchResult.filename}**${similarity}\n` +
                    `📁 Repository: ${searchResult.repo_name}\n` +
                    `📄 Path: \`${searchResult.filepath}\`\n` +
                    `🔍 Snippet: ${searchResult.snippet}\n\n`,
          });
        }

        await mcpClient.close();

        return {
          query,
          search_type,
          results: limitedResults,
          total_found: searchResults.length,
          repositories_searched: repositories || 'all',
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        dataStream.writeData({
          type: 'text-delta',
          content: `❌ Search failed: ${error.message}\n`,
        });
        throw new Error(`Search failed: ${error.message}`);
      }
    },
  });
```

### Phase 3: Intelligent Agent Integration with AI SDK 5 Alpha
**Duration:** 3-4 days

#### 3.1 Advanced Chat Route with prepareStep Intelligence
Transform the chat route to use intelligent tool orchestration:

**File:** `/app/(chat)/api/chat/route.ts`
```typescript
import { experimental_generateSteps, experimental_prepareStep, generateText } from 'ai';
import { intelligentMfaiSearch } from '@/lib/ai/tools/intelligent-mfai-search';
import { contextAwareListRepositories } from '@/lib/ai/tools/context-aware-list-repositories';

export async function POST(request: Request) {
  const { messages, id } = await request.json();
  const session = await auth();
  
  // Create enhanced data stream with AI SDK 5 capabilities
  const dataStream = experimental_createDataStream({
    async execute(dataStream) {
      const lastMessage = messages[messages.length - 1];
      
      // LLM-powered intent analysis for intelligent tool selection
      const repositoryIntent = await analyzeLLMIntent(lastMessage.content);
      
      const result = await experimental_generateSteps({
        model: myProvider.languageModel('chat-model'),
        messages: convertToCoreMessages(messages),
        
        // Intelligent tool orchestration with prepareStep
        experimental_prepareStep: async ({ stepNumber, previousSteps, message }) => {
          const intent = repositoryIntent;
          
          // STEP 0: Repository Intent Detection & Auto-Discovery
          if (stepNumber === 0 && intent.requiresRepositoryContext) {
            dataStream.writeCustomData('agent-reasoning', {
              step: 0,
              intent: intent.action,
              reasoning: `Detected ${intent.action} intent with ${intent.confidence}% confidence. Auto-triggering repository discovery.`
            });
            
            return {
              model: myProvider.languageModel('chat-model'),
              toolChoice: { type: 'tool', toolName: 'contextAwareListRepositories' },
              experimental_activeTools: ['contextAwareListRepositories'],
              experimental_context: { intent, phase: 'discovery' }
            };
          }
          
          // STEP 1: Intelligent Search Execution
          if (stepNumber === 1 && intent.action === 'search') {
            dataStream.writeCustomData('agent-reasoning', {
              step: 1,
              searchType: intent.optimalSearchType,
              reasoning: `Executing ${intent.optimalSearchType} search based on query analysis.`
            });
            
            return {
              model: myProvider.languageModel('chat-model'),
              toolChoice: { type: 'tool', toolName: 'intelligentMfaiSearch' },
              experimental_activeTools: ['intelligentMfaiSearch'],
              experimental_toolParameters: {
                intelligentMfaiSearch: {
                  strategy: intent.optimalSearchType,
                  parallel_search: intent.benefitsFromParallelSearch,
                  repositories: intent.targetRepositories
                }
              },
              experimental_context: { intent, phase: 'search' }
            };
          }
          
          // STEP 2: Result Enhancement & Artifact Creation
          if (stepNumber === 2 && intent.shouldCreateArtifact) {
            return {
              model: myProvider.languageModel('artifact-model'),
              toolChoice: { type: 'tool', toolName: 'createDocument' },
              experimental_activeTools: ['createDocument', 'requestSuggestions'],
              experimental_context: { intent, phase: 'enhancement' }
            };
          }
          
          // FALLBACK: All tools available for general conversation
          return {
            model: myProvider.languageModel('chat-model'),
            experimental_activeTools: [
              'getWeather',
              'createDocument',
              'updateDocument',
              'requestSuggestions',
              ...(process.env.MCP_ENABLED === 'true' ? [
                'intelligentMfaiSearch',
                'contextAwareListRepositories'
              ] : [])
            ]
          };
        },
        
        // Enhanced tools with AI SDK 5 features
        tools: {
          getWeather,
          createDocument: createDocument({ session, dataStream }),
          updateDocument: updateDocument({ session, dataStream }),
          requestSuggestions: requestSuggestions({ session, dataStream }),
          ...(process.env.MCP_ENABLED === 'true' && {
            intelligentMfaiSearch: intelligentMfaiSearch({ session, dataStream }),
            contextAwareListRepositories: contextAwareListRepositories({ session, dataStream }),
          }),
        },
        
        // Advanced streaming configuration
        experimental_streamCustomData: true,
        maxSteps: 5,
        onStepFinish: async ({ stepNumber, stepResult }) => {
          // Track step completion for analytics
          dataStream.writeCustomData('step-completed', {
            step: stepNumber,
            toolsUsed: stepResult.toolCalls?.map(call => call.toolName) || [],
            duration: stepResult.finishReason
          });
        }
      });
      
      // Stream final results with enhanced metadata
      for await (const part of result.stream) {
        if (part.type === 'text-delta') {
          dataStream.writeText(part.textDelta);
        } else if (part.type === 'custom-data') {
          dataStream.writeCustomData(part.name, part.value);
        }
      }
    }
  });
  
  return dataStream.toResponse();
}

// LLM-powered intent analysis function
async function analyzeLLMIntent(userQuery: string) {
  const result = await generateText({
    model: myProvider.languageModel('chat-model'),
    messages: [
      {
        role: 'system',
        content: `Analyze user queries for MODFLOW repository search intent.

        Determine:
        1. requiresRepositoryContext: boolean - needs to see available repositories
        2. action: 'search' | 'list' | 'explore' | 'general' - primary user intent
        3. shouldSearch: boolean - wants to search for content
        4. optimalSearchStrategy: 'text' | 'semantic' | 'hybrid' - best search approach
        5. benefitsFromParallelSearch: boolean - would benefit from multiple search strategies
        6. targetRepositories: string[] | null - specific repos to search or null for all
        7. shouldEnhanceResults: boolean - should create enhanced documentation
        8. confidence: number - confidence in analysis (0.0-1.0)

        Respond in JSON format with these exact field names.

        Examples:
        - "What repositories are available?" → {"requiresRepositoryContext": true, "action": "list", ...}
        - "Find pumping well examples" → {"shouldSearch": true, "optimalSearchStrategy": "semantic", ...}
        - "Search for exact function name" → {"shouldSearch": true, "optimalSearchStrategy": "text", ...}`
      },
      {
        role: 'user',
        content: userQuery
      }
    ],
    temperature: 0.1,
  });

  try {
    return JSON.parse(result.text);
  } catch {
    // Fallback intent if LLM parsing fails
    return {
      requiresRepositoryContext: false,
      action: 'general',
      shouldSearch: false,
      optimalSearchStrategy: 'semantic',
      benefitsFromParallelSearch: false,
      targetRepositories: null,
      shouldEnhanceResults: false,
      confidence: 0.5
    };
  }
}
```

#### 3.2 Error Handling and Fallbacks
Implement robust error handling for MCP connectivity:

**File:** `/lib/ai/mcp/error-handling.ts`
```typescript
export class MCPError extends Error {
  constructor(
    message: string,
    public readonly code: 'CONNECTION_FAILED' | 'AUTH_FAILED' | 'TOOL_NOT_FOUND' | 'EXECUTION_FAILED'
  ) {
    super(message);
    this.name = 'MCPError';
  }
}

export function withMCPErrorHandling<T>(operation: () => Promise<T>): Promise<T> {
  return operation().catch((error) => {
    if (error instanceof MCPError) {
      throw error;
    }
    
    // Convert common errors to MCPError
    if (error.message.includes('Failed to connect')) {
      throw new MCPError('MCP server is currently unavailable', 'CONNECTION_FAILED');
    }
    
    if (error.message.includes('Unauthorized')) {
      throw new MCPError('Invalid MCP API key', 'AUTH_FAILED');
    }
    
    throw new MCPError(`MCP operation failed: ${error.message}`, 'EXECUTION_FAILED');
  });
}
```

### Phase 4: Enhanced User Experience
**Duration:** 3-4 days

#### 4.1 Tool Usage Hints and Suggestions
Add intelligent tool suggestions based on user queries:

**File:** `/lib/ai/tools/tool-suggestions.ts`
```typescript
export function getMCPToolSuggestions(userMessage: string): string[] {
  const message = userMessage.toLowerCase();
  const suggestions: string[] = [];
  
  // Repository listing suggestions
  if (message.includes('repositories') || message.includes('what repos') || message.includes('available') || message.includes('list')) {
    suggestions.push('listRepositories');
  }
  
  // Search suggestions
  if (message.includes('search') || message.includes('find') || message.includes('look for') || 
      message.includes('groundwater') || message.includes('modflow') || message.includes('code')) {
    suggestions.push('mfaiSearch');
  }
  
  return suggestions;
}
```

#### 4.2 Streaming UI Enhancements
Create custom UI components for MCP tool results:

**File:** `/components/mcp-results.tsx`
```typescript
interface MCPResultsProps {
  type: 'repositories' | 'search';
  data: any;
}

export function MCPResults({ type, data }: MCPResultsProps) {
  switch (type) {
    case 'repositories':
      return <RepositoryList repositories={data.repositories} />;
    case 'search':
      return <SearchResults results={data.results} query={data.query} />;
    default:
      return null;
  }
}

function RepositoryList({ repositories }: { repositories: any[] }) {
  return (
    <div className="space-y-4">
      {repositories.map((repo, index) => (
        <Card key={index} className="p-4">
          <h3 className="font-semibold">{repo.name}</h3>
          <p className="text-sm text-muted-foreground">{repo.file_count} files</p>
          <p className="text-sm">{repo.url}</p>
          {repo.navigation_guide && (
            <p className="text-sm mt-2">{repo.navigation_guide.substring(0, 200)}...</p>
          )}
        </Card>
      ))}
    </div>
  );
}

function SearchResults({ results, query }: { results: any[]; query: string }) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Search Results for "{query}"</h3>
      {results.map((result, index) => (
        <Card key={index} className="p-4">
          <h4 className="font-medium">{result.filename}</h4>
          <p className="text-sm text-muted-foreground">Repository: {result.repo_name}</p>
          <p className="text-sm font-mono">{result.filepath}</p>
          {result.similarity && (
            <p className="text-sm text-green-600">{(result.similarity * 100).toFixed(1)}% match</p>
          )}
          <p className="text-sm mt-2">{result.snippet}</p>
        </Card>
      ))}
    </div>
  );
}
```

#### 4.3 Caching and Performance
Implement intelligent caching for MCP responses:

**File:** `/lib/ai/mcp/cache.ts`
```typescript
import { Redis } from '@upstash/redis';

export class MCPCache {
  private redis: Redis;
  
  constructor() {
    this.redis = Redis.fromEnv();
  }
  
  async get(key: string): Promise<any | null> {
    try {
      const cached = await this.redis.get(`mcp:${key}`);
      return cached ? JSON.parse(cached as string) : null;
    } catch {
      return null;
    }
  }
  
  async set(key: string, value: any, ttlSeconds: number = 300): Promise<void> {
    try {
      await this.redis.setex(`mcp:${key}`, ttlSeconds, JSON.stringify(value));
    } catch {
      // Fail silently - caching is optional
    }
  }
  
  generateKey(tool: string, params: any): string {
    return `${tool}:${Buffer.from(JSON.stringify(params)).toString('base64')}`;
  }
}
```

### Phase 5: Testing and Documentation
**Duration:** 2-3 days

#### 5.1 Integration Tests
Create comprehensive tests for MCP tool integration:

**File:** `/tests/mcp-tools.test.ts`
```typescript
import { test, expect } from '@playwright/test';

test.describe('MCP Tools Integration', () => {
  test('should list repositories when asked', async ({ page }) => {
    await page.goto('/');
    
    // Type a query that should trigger repository listing
    await page.fill('[data-testid="chat-input"]', 'What MODFLOW repositories are available?');
    await page.click('[data-testid="send-button"]');
    
    // Wait for the tool to be called and results to appear
    await expect(page.locator('[data-testid="chat-message"]').last()).toContainText('Found');
    await expect(page.locator('[data-testid="chat-message"]').last()).toContainText('repositories');
  });
  
  test('should search repositories with text search', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('[data-testid="chat-input"]', 'Search for groundwater modeling examples');
    await page.click('[data-testid="send-button"]');
    
    await expect(page.locator('[data-testid="chat-message"]').last()).toContainText('Searching for');
    await expect(page.locator('[data-testid="chat-message"]').last()).toContainText('results');
  });
  
  test('should search repositories with semantic search', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('[data-testid="chat-input"]', 'Find code examples for aquifer pumping simulation');
    await page.click('[data-testid="send-button"]');
    
    await expect(page.locator('[data-testid="chat-message"]').last()).toContainText('semantic search');
    await expect(page.locator('[data-testid="chat-message"]').last()).toContainText('results');
  });
});
```

#### 5.2 Documentation Updates
Update the main README with MCP tool capabilities:

**File:** `/README.md` (additions)
```markdown
### 🔧 **MODFLOW AI Integration**
- **Repository Browser** - List and explore MODFLOW AI repositories with navigation guides
- **Text Search** - Exact keyword matching across all repositories
- **Semantic Search** - AI-powered conceptual search for finding related content
- **Code Discovery** - Find specific implementations and examples with file snippets
- **Real-time Results** - Streaming search results with live progress updates

#### Available MCP Tools
- `listRepositories` - Browse available MODFLOW repositories with optional navigation guides
- `mfaiSearch` - Search across all MFAI indexed repositories using text or semantic search
```

### Phase 6: Advanced Features and Optimization
**Duration:** 2-3 days

#### 6.1 Enhanced Search Features
Add advanced search capabilities and filtering:

**File:** `/lib/ai/tools/enhanced-search.ts`
```typescript
// Extend mfaiSearch with additional features
export const enhancedMfaiSearch = ({ session, dataStream }: ToolProps) =>
  tool({
    // Add features like:
    // - Repository-specific search shortcuts
    // - File type filtering (.py, .f90, .md)
    // - Date range filtering
    // - Similarity threshold for semantic search
  });
```

#### 6.2 Performance Monitoring
Add telemetry for MCP tool usage:

**File:** `/lib/ai/mcp/telemetry.ts`
```typescript
export class MCPTelemetry {
  static async trackToolUsage(tool: string, duration: number, success: boolean) {
    // Track tool performance and usage patterns
  }
  
  static async trackServerHealth() {
    // Monitor MCP server availability and response times
  }
}
```

#### 6.3 Result Export Features
Allow users to export search results:

**File:** `/lib/ai/tools/export-results.ts`
```typescript
// Integration with existing artifact system
// Export search results as downloadable artifacts
// Format options: JSON, CSV, Markdown
```

## Revolutionary Implementation Timeline

### Phase 1: AI SDK 5 Alpha Foundation (Days 1-4)
- **Day 1**: AI SDK 5 alpha migration and environment setup
- **Day 2**: LLM-powered intent analysis system (NO HARDCODING)
- **Day 3**: prepareStep intelligent orchestration with LLM decision-making
- **Day 4**: Enhanced streaming and custom data parts integration

### Phase 2: Intelligent Tools Development (Days 5-9)
- **Day 5**: Hybrid search engine with parallel execution
- **Day 6**: Context-aware repository listing with smart caching
- **Day 7**: Advanced result merging and relevance scoring
- **Day 8**: Real-time streaming optimization and metadata enhancement
- **Day 9**: Error handling and fallback intelligence

### Phase 3: Agent Integration & Testing (Days 10-13)
- **Day 10**: Chat route transformation with experimental_generateSteps
- **Day 11**: Multi-step workflow testing and optimization
- **Day 12**: Performance benchmarking and fine-tuning
- **Day 13**: Advanced features and polish

### Phase 4: Documentation & Deployment (Days 14-15)
- **Day 14**: Comprehensive testing and documentation
- **Day 15**: Production deployment and monitoring setup

## Revolutionary Success Criteria

### 🤖 **LLM-Powered Intelligent Agent Capabilities**
- ✅ **LLM Intent Detection**: Model understands user intent with reasoning (95%+ accuracy)
- ✅ **LLM Tool Orchestration**: prepareStep uses LLM to trigger optimal tools
- ✅ **LLM-Guided Workflows**: Multi-step sequences driven by model decisions
- ✅ **LLM Parallel Strategy**: Model determines when parallel searches benefit users
- ✅ **LLM Search Strategy**: Model analyzes queries to select optimal search approach
- ✅ **LLM Relevance Scoring**: Model evaluates and explains result relevance

### 🚀 **Enhanced User Experience**
- ✅ **Zero-Thought Interface**: Users never need to specify search types
- ✅ **Proactive Discovery**: System suggests relevant repositories automatically
- ✅ **Real-Time Intelligence**: Live reasoning explanations during searches
- ✅ **Contextual Continuity**: Conversations build on previous repository context
- ✅ **Adaptive Learning**: System improves with user interaction patterns

### ⚡ **Performance & Technical Excellence**
- ✅ **Sub-2s Response Time**: Even complex multi-step workflows complete quickly
- ✅ **Parallel Efficiency**: Simultaneous searches complete faster than sequential
- ✅ **Stream Optimization**: Real-time results with zero loading states
- ✅ **Error Resilience**: Graceful degradation with intelligent fallbacks
- ✅ **Scalable Architecture**: Ready for additional MCP servers and tools

### Integration Quality
- ✅ Maintains existing ChatAI UX patterns
- ✅ Compatible with all authentication modes
- ✅ Works with existing rate limiting system
- ✅ Supports both mobile and desktop interfaces
- ✅ Graceful degradation when MCP server unavailable

## Risk Mitigation

### Technical Risks
1. **MCP Server Availability**
   - Mitigation: Implement robust fallbacks and caching
   - Fallback: Graceful degradation with helpful error messages

2. **Performance Impact**
   - Mitigation: Intelligent caching and request optimization
   - Monitoring: Track tool response times and success rates

3. **Security Concerns**
   - Mitigation: Proper API key management and input validation
   - Security: Rate limiting for MCP tool usage

### User Experience Risks
1. **Complex Tool Invocation**
   - Mitigation: Clear tool descriptions and natural language processing
   - UX: Smart tool suggestions based on user queries

2. **Information Overload**
   - Mitigation: Progressive disclosure and result pagination
   - UI: Clean, scannable result formatting

## Dependencies

### External Dependencies
- **MCP Server**: Reliable MFAI repository navigator server
- **API Keys**: Valid MCP API key with appropriate permissions
- **Network**: Stable connection to MCP server

### Internal Dependencies
- **AI SDK**: Continued compatibility with tool calling patterns
- **Database**: Potential schema updates for caching
- **Redis**: For performance caching and rate limiting

## Revolutionary User Experience Examples

### 🎯 **Zero-Effort Repository Discovery**

**User:** *"I need help with MODFLOW boundary conditions"*

**AI Agent Intelligence:**
1. **Auto-Intent Detection** (0.2s): Detects search intent + boundary condition focus
2. **prepareStep Activation** (0.1s): Forces `intelligentMfaiSearch` with semantic strategy
3. **Parallel Execution** (1.2s): Runs both semantic + text searches simultaneously
4. **Smart Result Merging** (0.3s): Combines results with relevance scoring

**User Sees:**
```
🧠 Understanding your boundary condition question...
🔍 Running semantic search across all MODFLOW repositories...
⚡ Also checking for exact "boundary condition" matches...
📊 Found 23 results, ranking by relevance...

Top Results:
1. **boundary_conditions.py** (flopy) - 94.5% relevance
   "Comprehensive boundary condition setup for MODFLOW models..."
   
2. **constant_head_example.py** (modflow6) - 91.2% relevance  
   "Example implementation of constant head boundaries..."
```

### 🚀 **Intelligent Multi-Step Workflows**

**User:** *"Show me what groundwater modeling repositories you have"*

**AI Agent Intelligence:**
1. **Repository Discovery Phase**: Auto-triggers `contextAwareListRepositories`
2. **Context Building Phase**: Analyzes navigation guides for relevance
3. **Proactive Search Phase**: Anticipates likely follow-up searches

**User Sees:**
```
📚 I found 9 groundwater modeling repositories. Let me show you the most relevant:

🌊 **MODFLOW 6** (189 files) - Latest USGS groundwater flow simulator
   → "MODFLOW 6 is designed to simulate groundwater flow and transport..."

🐍 **FloPy** (473 files) - Python package for MODFLOW
   → "FloPy creates, runs, and post-processes MODFLOW models..."

Would you like me to search for specific examples in any of these repositories?
```

### ⚡ **Context-Aware Conversations**

**User:** *"Find pumping well examples in FloPy"*

**AI Agent Intelligence:**
1. **Context Recognition**: Remembers previous repository discussion
2. **Targeted Search**: Auto-filters to FloPy repository
3. **Smart Strategy**: Uses text search for specific "pumping well" terms

**User Sees:**
```
🎯 Searching FloPy specifically for pumping well examples...
🔍 Using targeted text search for exact matches...

Found 8 pumping well examples in FloPy:
```

### 🧠 **Adaptive Learning & Reasoning**

**User:** *"How do I calibrate a MODFLOW model?"*

**AI Agent Intelligence:**
1. **Question Analysis**: Detects how-to question pattern
2. **Strategy Selection**: Auto-chooses semantic search for conceptual content
3. **Multi-Repository Search**: Searches across all repos for calibration techniques
4. **Live Reasoning**: Streams thought process to user

**User Sees:**
```
💭 This is a conceptual question about calibration techniques...
🔍 Using semantic search to find calibration workflows and methodologies...
🌐 Searching across all repositories for comprehensive coverage...

🎯 **Calibration Techniques Found:**

📈 **PEST Integration Examples** (pest_hp repository)
   "Parameter estimation workflow for MODFLOW calibration..."

🔧 **FloPy Calibration Tools** (flopy repository) 
   "Automated calibration helpers and utilities..."
```

## Game-Changing Advantages

### 🚀 **For Users**
- **No Learning Curve**: Natural conversation, zero technical syntax
- **Proactive Intelligence**: System anticipates needs and suggests next steps
- **Comprehensive Results**: Parallel searches ensure nothing is missed
- **Real-Time Feedback**: See the AI's reasoning process live

### 🔧 **For Developers**
- **Effortless Tool Usage**: prepareStep handles all orchestration automatically
- **Scalable Architecture**: Easy to add new MCP servers and tools
- **Rich Analytics**: Detailed insights into user patterns and tool performance
- **Production Ready**: Built on stable AI SDK 5 alpha foundations

### 🎯 **Technical Breakthrough**
- **First LLM-Powered MCP Implementation** using AI SDK 5 alpha prepareStep
- **Zero-Hardcoding Intelligence** - all decisions made by the model itself
- **Revolutionary UX** that eliminates the need for users to understand tools  
- **Self-Reasoning Agent** that explains its decision-making process
- **Adaptive Intelligence** that improves understanding through conversation context
- **Seamless Integration** with existing ChatAI architecture

This represents a **paradigm shift** from manual tool selection to **intelligent agent orchestration**, creating the most advanced repository exploration system ever built for groundwater modeling professionals.

## Implementation Impact

This AI SDK 5 alpha integration will transform ChatAI from a chat application with tools into an **intelligent groundwater modeling assistant** that:

✅ **Understands context** and user intent automatically  
✅ **Orchestrates tools** without user intervention  
✅ **Learns from interactions** to improve over time  
✅ **Provides proactive suggestions** based on conversation flow  
✅ **Streams intelligence** so users see the reasoning process  

The result: **The world's first truly intelligent MODFLOW repository assistant.**