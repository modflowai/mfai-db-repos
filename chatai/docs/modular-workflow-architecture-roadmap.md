# Modular Workflow Architecture Roadmap

## Overview

This document outlines the comprehensive refactoring of the current monolithic search tool into a modular, streaming workflow system that provides real-time feedback during tool execution. The goal is to create a user experience similar to Perplexity's transparent tool calling with visual indicators and immediate feedback.

## Current Problems

### Performance Issues
- **Monolithic Tool Hanging**: Single large `intelligentMfaiSearch` tool can hang for 30+ seconds
- **No Real-time Feedback**: Users wait until completion with no progress indicators
- **Poor Error Handling**: Failures occur late in the process with minimal feedback
- **Resource Inefficiency**: Large tool calls consume unnecessary compute resources

### User Experience Issues
- **Black Box Execution**: Users don't see what's happening during tool execution
- **Unnecessary Artifacts**: Simple Q&A generates complex document artifacts
- **Long Wait Times**: No indication of progress or current operation
- **Unclear Tool Status**: No visibility into which tools are being called or why

### Technical Debt
- **Tightly Coupled Logic**: Search strategy, execution, and response generation mixed together
- **Hard to Debug**: Single large function makes troubleshooting difficult
- **Limited Reusability**: Components can't be used independently
- **Scaling Challenges**: Difficult to optimize individual workflow steps

## Proposed Architecture

### Core Principles

1. **Modular Design**: Each tool has a single, well-defined responsibility
2. **Real-time Streaming**: Immediate feedback for every operation
3. **Transparent Execution**: Users see what's happening at each step
4. **Graceful Degradation**: Failures are handled elegantly with clear messaging
5. **Progressive Enhancement**: Results stream in as they become available

### Workflow Overview

```
User Query → Relevance Check → Query Analysis → Context Validation → Repository Search → Response Generation → Final Answer
     ↓              ↓              ↓               ↓                   ↓                  ↓                ↓
   Pulsing        Status         Strategy      Check Context      Documents*         Synthesis       Complete
   Indicator      Update         Display       Sufficiency        Found             Progress        Answer
                                                   ↓
                                              Skip Search if
                                            Context Sufficient
```

*Repository Search is conditional - only executed if Context Validation determines insufficient context exists

## Phase 1: Core Architecture Refactoring

### 1.1 Modular Tool Structure

Create a new directory structure for workflow-based tools:

```
lib/ai/tools/workflow/
├── base/
│   ├── workflow-tool.ts          # Base interface for all workflow tools
│   ├── tool-result.ts            # Standardized result format
│   └── streaming-utils.ts        # Utilities for streaming updates
├── tools/
│   ├── relevance-checker.ts      # Domain relevance verification
│   ├── query-analyzer.ts         # Search strategy determination
│   ├── repository-searcher.ts    # Repository search execution
│   └── response-generator.ts     # Answer synthesis
├── orchestration/
│   ├── workflow-orchestrator.ts  # Main workflow coordinator
│   ├── error-handler.ts          # Centralized error management
│   └── retry-logic.ts            # Intelligent retry strategies
└── schemas/
    ├── tool-schemas.ts           # Zod schemas for all tools
    └── workflow-schemas.ts       # Workflow state schemas
```

### 1.2 Tool Interface Standardization

#### Base Tool Interface
```typescript
interface WorkflowTool<TInput, TOutput> {
  name: string;
  description: string;
  schema: ZodSchema<TInput>;
  execute: (input: TInput, context: ToolContext) => Promise<ToolResult<TOutput>>;
  estimatedDuration: number;
  retryable: boolean;
}

interface ToolContext {
  userId: string;
  sessionId: string;
  dataStream: DataStreamWriter;
  previousResults: Map<string, any>;
  streamStatus: (status: ToolStatus) => Promise<void>;
}

interface ToolResult<T> {
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

interface ToolStatus {
  tool: string;
  phase: 'starting' | 'executing' | 'processing' | 'completed' | 'failed' | 'retrying';
  progress?: number;           // 0-100 percentage
  currentAction?: string;      // What the tool is currently doing
  estimatedTimeRemaining?: number;
}
```

#### Error Handling Types
```typescript
interface ToolError {
  type: 'validation' | 'execution' | 'timeout' | 'network' | 'api_limit';
  message: string;
  code?: string;
  retryable: boolean;
  context?: Record<string, any>;
}
```

### 1.3 Workflow State Management

```typescript
interface WorkflowState {
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
```

## Phase 2: Individual Tool Implementation

### 2.1 Relevance Checker Tool

**Purpose**: Quickly determine if the user query is related to MODFLOW/PEST/hydrology domains.

**Expected Duration**: < 2 seconds

**Implementation Details**:
```typescript
export const relevanceChecker = createWorkflowTool({
  name: 'Relevance Checker',
  description: 'Determines if query relates to MODFLOW, PEST, or hydrology concepts',
  estimatedDuration: 1500, // milliseconds
  retryable: true,
  
  schema: z.object({
    query: z.string().min(1),
  }),
  
  execute: async ({ query }, context) => {
    await context.streamStatus({
      tool: 'relevance-checker',
      phase: 'starting',
      currentAction: 'Analyzing query relevance...'
    });

    // Fast LLM call with focused prompt
    const result = await analyzeDomainRelevance(query);
    
    await context.streamStatus({
      tool: 'relevance-checker', 
      phase: 'completed',
      currentAction: `${result.isRelevant ? 'Relevant' : 'Not relevant'} to MODFLOW domain`
    });

    return {
      success: true,
      data: {
        isRelevant: result.isRelevant,
        confidence: result.confidence,
        domains: result.matchedDomains,
        reasoning: result.explanation
      },
      shortSummary: `${result.isRelevant ? '✅ MODFLOW-related' : '❌ Outside domain'} (${Math.round(result.confidence * 100)}% confident)`,
      confidence: result.confidence,
      metadata: {
        executionTime: Date.now() - startTime,
        tokensUsed: result.tokensUsed
      }
    };
  }
});
```

**Streaming Updates**:
- Start: "🔍 Checking if query relates to MODFLOW..."
- Progress: "🧠 Analyzing domain relevance..."
- Complete: "✅ MODFLOW-related (95% confident)" or "❌ Outside MODFLOW domain"

### 2.2 Query Analyzer Tool

**Purpose**: Determine optimal search strategy, target repositories, and search parameters.

**Expected Duration**: 2-3 seconds

**Implementation Details**:
```typescript
export const queryAnalyzer = createWorkflowTool({
  name: 'Query Analyzer',
  description: 'Analyzes query to determine optimal search strategy and parameters',
  estimatedDuration: 2500,
  retryable: true,
  
  schema: z.object({
    query: z.string(),
    relevanceData: z.object({
      isRelevant: z.boolean(),
      domains: z.array(z.string()),
      confidence: z.number()
    })
  }),
  
  execute: async ({ query, relevanceData }, context) => {
    if (!relevanceData.isRelevant) {
      return {
        success: false,
        data: null,
        shortSummary: "⚠️ Query not suitable for MODFLOW search",
        confidence: 0,
        nextSuggestedAction: "general_response"
      };
    }

    await context.streamStatus({
      tool: 'query-analyzer',
      phase: 'executing',
      currentAction: 'Determining search strategy...'
    });

    const analysis = await analyzeSearchStrategy(query, relevanceData);
    
    return {
      success: true,
      data: {
        strategy: analysis.optimalStrategy,
        repositories: analysis.targetRepositories, 
        searchType: analysis.searchType,
        keywords: analysis.extractedKeywords,
        expectedResultTypes: analysis.expectedTypes
      },
      shortSummary: `📋 Strategy: ${analysis.optimalStrategy}, Repos: ${analysis.targetRepositories.join(', ')}`,
      confidence: analysis.confidence
    };
  }
});
```

**Streaming Updates**:
- Start: "🧠 Analyzing your query..."
- Progress: "📊 Determining search strategy..."
- Complete: "📋 Strategy: semantic search in flopy, modflow6"

### 2.3 Context Validation Tool

**Purpose**: Determine if sufficient context exists from previous searches/conversations to answer the query without performing new searches.

**Expected Duration**: 1-2 seconds

**Implementation Details**:
```typescript
export const contextValidator = createWorkflowTool({
  name: 'Context Validator',
  description: 'Validates if existing context is sufficient to answer the query',
  estimatedDuration: 1500,
  retryable: true,
  
  schema: z.object({
    query: z.string(),
    analysisContext: z.object({
      strategy: z.string(),
      repositories: z.array(z.string()),
      keywords: z.array(z.string())
    }),
    previousResults: z.array(z.any()).optional(),
    conversationHistory: z.array(z.any()).optional()
  }),
  
  execute: async ({ query, analysisContext, previousResults, conversationHistory }, context) => {
    await context.streamStatus({
      tool: 'context-validator',
      phase: 'starting',
      currentAction: 'Checking existing context...'
    });

    // LLM analyzes if previous context can answer the query
    const contextAnalysis = await analyzeContextSufficiency({
      query,
      previousResults,
      conversationHistory,
      analysisContext
    });
    
    await context.streamStatus({
      tool: 'context-validator',
      phase: 'completed',
      currentAction: contextAnalysis.needsNewSearch 
        ? 'New search required' 
        : 'Sufficient context found'
    });

    return {
      success: true,
      data: {
        needsNewSearch: contextAnalysis.needsNewSearch,
        contextSufficiency: contextAnalysis.sufficiency,
        availableContext: contextAnalysis.availableContext,
        reasoning: contextAnalysis.reasoning,
        suggestedResponse: contextAnalysis.needsNewSearch ? null : contextAnalysis.suggestedResponse
      },
      shortSummary: contextAnalysis.needsNewSearch 
        ? '🔍 New search needed - insufficient context'
        : '✅ Sufficient context available',
      confidence: contextAnalysis.confidence,
      nextSuggestedAction: contextAnalysis.needsNewSearch ? 'repository_search' : 'response_generation',
      metadata: {
        executionTime: Date.now() - startTime,
        contextItemsAnalyzed: (previousResults?.length || 0) + (conversationHistory?.length || 0)
      }
    };
  }
});
```

**Context Analysis Logic**:
- **Previous Search Results**: Check if recent searches contain relevant information for the current query
- **Conversation History**: Analyze if the conversation thread has built up sufficient context
- **Topic Continuity**: Determine if this is a follow-up question that can be answered from existing context
- **Content Freshness**: Ensure context is recent and relevant
- **Query Complexity**: Assess if the query requires new information or can be answered from available context

**Decision Criteria**:
- **Skip Search If**: Previous results directly answer the query, follow-up question with sufficient context, clarification request
- **Perform Search If**: New topic, insufficient previous results, complex query requiring fresh information

**Streaming Updates**:
- Start: "🔍 Checking existing context..."
- Progress: "📚 Analyzing previous results and conversation..."
- Complete: "✅ Sufficient context available" or "🔍 New search required"

### 2.4 Repository Searcher Tool

**Purpose**: Execute the actual search operations against MODFLOW repositories.

**Expected Duration**: 5-10 seconds

**Implementation Details**:
```typescript
export const repositorySearcher = createWorkflowTool({
  name: 'Repository Searcher',
  description: 'Searches MODFLOW repositories using optimized strategy',
  estimatedDuration: 7500,
  retryable: true,
  
  schema: z.object({
    query: z.string(),
    strategy: z.enum(['text', 'semantic', 'hybrid']),
    repositories: z.array(z.string()),
    searchParameters: z.object({
      maxResults: z.number().default(10),
      minSimilarity: z.number().default(0.7)
    }).optional()
  }),
  
  execute: async ({ query, strategy, repositories, searchParameters }, context) => {
    const results = [];
    const totalRepos = repositories.length;
    
    for (let i = 0; i < repositories.length; i++) {
      const repo = repositories[i];
      
      await context.streamStatus({
        tool: 'repository-searcher',
        phase: 'executing',
        progress: Math.round((i / totalRepos) * 100),
        currentAction: `Searching ${repo}...`
      });
      
      try {
        const repoResults = await searchRepository(repo, query, strategy, searchParameters);
        results.push(...repoResults);
        
        // Stream intermediate results
        await context.streamStatus({
          tool: 'repository-searcher',
          phase: 'processing',
          currentAction: `Found ${repoResults.length} results in ${repo}`
        });
        
      } catch (error) {
        console.warn(`Search failed for ${repo}:`, error);
        // Continue with other repositories
      }
    }
    
    const rankedResults = await rankResultsByRelevance(results, query);
    
    return {
      success: true,
      data: {
        results: rankedResults,
        totalFound: results.length,
        repositoriesSearched: repositories,
        searchStrategy: strategy
      },
      shortSummary: `📄 Found ${rankedResults.length} relevant documents across ${repositories.length} repositories`,
      confidence: calculateSearchConfidence(rankedResults),
      metadata: {
        executionTime: Date.now() - startTime,
        cacheHit: checkCacheHit(query, strategy)
      }
    };
  }
});
```

**Streaming Updates**:
- Start: "🔍 Searching MODFLOW repositories..."
- Progress: "📚 Searching flopy repository... (33%)"
- Progress: "📚 Searching modflow6 repository... (66%)" 
- Complete: "📄 Found 8 relevant documents"

### 2.5 Response Generator Tool

**Purpose**: Synthesize search results into a comprehensive, coherent answer.

**Expected Duration**: 3-5 seconds

**Implementation Details**:
```typescript
export const responseGenerator = createWorkflowTool({
  name: 'Response Generator',
  description: 'Generates comprehensive answer from search results',
  estimatedDuration: 4000,
  retryable: true,
  
  schema: z.object({
    query: z.string(),
    searchResults: z.array(SearchResultSchema),
    analysisContext: z.object({
      strategy: z.string(),
      repositories: z.array(z.string()),
      confidence: z.number()
    })
  }),
  
  execute: async ({ query, searchResults, analysisContext }, context) => {
    await context.streamStatus({
      tool: 'response-generator',
      phase: 'executing',
      currentAction: 'Analyzing search results...'
    });
    
    // Filter and rank results by relevance
    const topResults = searchResults
      .filter(r => r.relevanceScore > 0.6)
      .slice(0, 5);
    
    await context.streamStatus({
      tool: 'response-generator',
      phase: 'processing',
      currentAction: 'Synthesizing comprehensive answer...'
    });
    
    const answer = await synthesizeAnswer({
      query,
      results: topResults,
      context: analysisContext
    });
    
    return {
      success: true,
      data: {
        answer: answer.text,
        sourceDocuments: topResults,
        confidence: answer.confidence,
        additionalResources: answer.relatedLinks
      },
      shortSummary: `✅ Generated comprehensive answer with ${topResults.length} sources`,
      confidence: answer.confidence,
      metadata: {
        executionTime: Date.now() - startTime,
        tokensUsed: answer.tokensUsed,
        sourcesUsed: topResults.length
      }
    };
  }
});
```

**Streaming Updates**:
- Start: "📝 Generating comprehensive answer..."
- Progress: "🔗 Analyzing 5 source documents..."
- Progress: "✍️ Synthesizing final response..."
- Complete: "✅ Complete answer ready with 5 sources"

## Phase 3: Workflow Orchestration

### 3.1 Orchestrator Architecture

The workflow orchestrator manages the sequential execution of tools, handles data flow between steps, and coordinates streaming updates.

```typescript
export class WorkflowOrchestrator {
  private workflow: WorkflowTool[];
  private state: WorkflowState;
  private errorHandler: ErrorHandler;
  private retryLogic: RetryLogic;
  
  constructor(
    private dataStream: DataStreamWriter,
    private userId: string
  ) {
    this.workflow = [
      relevanceChecker,
      queryAnalyzer,
      contextValidator,
      repositorySearcher,
      responseGenerator
    ];
    this.errorHandler = new ErrorHandler(dataStream);
    this.retryLogic = new RetryLogic();
  }
  
  async execute(userQuery: string): Promise<WorkflowResult> {
    this.state = this.initializeWorkflowState(userQuery);
    
    try {
      // Stream workflow start
      await this.streamWorkflowStart();
      
      let context = new Map<string, any>();
      context.set('originalQuery', userQuery);
      
      for (let i = 0; i < this.workflow.length; i++) {
        const tool = this.workflow[i];
        const stepResult = await this.executeToolWithRetry(tool, context, i);
        
        if (!stepResult.success) {
          return await this.handleWorkflowFailure(tool, stepResult, i);
        }
        
        // Add result to context for next tools
        context.set(tool.name, stepResult.data);
        
        // Check if workflow should continue
        if (stepResult.nextSuggestedAction === 'general_response') {
          return await this.handleGeneralResponse(userQuery);
        }
      }
      
      return await this.completeWorkflow(context);
      
    } catch (error) {
      return await this.handleCriticalFailure(error);
    }
  }
  
  private async executeToolWithRetry(
    tool: WorkflowTool, 
    context: Map<string, any>, 
    stepIndex: number
  ): Promise<ToolResult> {
    const maxRetries = tool.retryable ? 2 : 0;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // Prepare tool input from context
        const input = this.prepareToolInput(tool, context);
        
        // Update workflow state
        this.updateToolStatus(tool.name, {
          tool: tool.name,
          phase: 'starting',
          currentAction: `Starting ${tool.name}...`
        });
        
        // Execute tool
        const result = await tool.execute(input, {
          userId: this.userId,
          sessionId: this.state.id,
          dataStream: this.dataStream,
          previousResults: context,
          streamStatus: (status) => this.streamToolStatus(status)
        });
        
        // Update success state
        this.updateToolStatus(tool.name, {
          tool: tool.name,
          phase: 'completed',
          currentAction: result.shortSummary
        });
        
        return result;
        
      } catch (error) {
        const isLastAttempt = attempt === maxRetries;
        
        if (isLastAttempt) {
          // Final failure
          this.updateToolStatus(tool.name, {
            tool: tool.name,
            phase: 'failed',
            currentAction: `Failed: ${error.message}`
          });
          throw error;
        } else {
          // Retry attempt
          this.updateToolStatus(tool.name, {
            tool: tool.name,
            phase: 'retrying',
            currentAction: `Retrying... (attempt ${attempt + 2})`
          });
          
          await this.retryLogic.wait(attempt);
        }
      }
    }
  }
}
```

### 3.2 Error Handling Strategy

#### Error Classification
```typescript
enum ErrorSeverity {
  RECOVERABLE = 'recoverable',    // Retry with same parameters
  DEGRADED = 'degraded',          // Continue with reduced functionality  
  CRITICAL = 'critical'           // Stop workflow, return error
}

class ErrorHandler {
  classifyError(error: Error, tool: WorkflowTool): ErrorClassification {
    // Network timeouts, rate limits -> RECOVERABLE
    // API key issues, service down -> CRITICAL
    // Partial results, low confidence -> DEGRADED
  }
  
  async handleError(
    error: Error, 
    tool: WorkflowTool, 
    context: Map<string, any>
  ): Promise<ErrorHandlingStrategy> {
    const classification = this.classifyError(error, tool);
    
    switch (classification.severity) {
      case ErrorSeverity.RECOVERABLE:
        return { action: 'retry', delay: 1000 };
        
      case ErrorSeverity.DEGRADED:
        return { action: 'continue', fallback: this.createFallback(tool, context) };
        
      case ErrorSeverity.CRITICAL:
        return { action: 'abort', userMessage: this.createUserFriendlyMessage(error) };
    }
  }
}
```

#### Graceful Degradation
- **Search Tool Failure**: Fall back to simpler search or cached results
- **Response Generator Failure**: Return raw search results with basic formatting
- **Relevance Checker Failure**: Assume query is relevant and continue
- **Analysis Tool Failure**: Use default search strategy

### 3.3 Retry Logic

```typescript
class RetryLogic {
  private readonly baseDelay = 1000;
  private readonly maxDelay = 8000;
  private readonly backoffMultiplier = 2;
  
  async wait(attemptNumber: number): Promise<void> {
    const delay = Math.min(
      this.baseDelay * Math.pow(this.backoffMultiplier, attemptNumber),
      this.maxDelay
    );
    
    // Add jitter to prevent thundering herd
    const jitteredDelay = delay + (Math.random() * 1000);
    
    await new Promise(resolve => setTimeout(resolve, jitteredDelay));
  }
  
  shouldRetry(error: Error, attemptNumber: number, maxRetries: number): boolean {
    if (attemptNumber >= maxRetries) return false;
    
    // Retry on network errors, timeouts, rate limits
    return this.isRetryableError(error);
  }
  
  private isRetryableError(error: Error): boolean {
    return error.message.includes('timeout') ||
           error.message.includes('rate limit') ||
           error.message.includes('network') ||
           error.message.includes('ECONNRESET');
  }
}
```

## Phase 4: Streaming UI Components

### 4.1 Component Architecture

```
components/workflow/
├── workflow-container.tsx        # Main container for workflow display
├── tool-status-card.tsx         # Individual tool status display
├── workflow-progress.tsx        # Overall progress tracker
├── tool-result-stream.tsx       # Real-time result streaming
├── pulsing-indicator.tsx        # Perplexity-style visual feedback
├── error-display.tsx           # Error handling UI
└── workflow-summary.tsx         # Final results summary
```

### 4.2 Tool Status Card Component

```tsx
interface ToolStatusCardProps {
  tool: {
    name: string;
    description: string;
    estimatedDuration: number;
  };
  status: ToolStatus;
  result?: ToolResult;
  expanded?: boolean;
  onToggleExpanded?: () => void;
}

export const ToolStatusCard = ({ 
  tool, 
  status, 
  result, 
  expanded = false,
  onToggleExpanded 
}: ToolStatusCardProps) => {
  const getStatusIcon = () => {
    switch (status.phase) {
      case 'starting':
      case 'executing': 
        return <PulsingDot color="blue" />;
      case 'processing':
        return <Spinner className="w-4 h-4" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'retrying':
        return <RotateCcw className="w-4 h-4 text-orange-500" />;
      default:
        return <Circle className="w-4 h-4 text-gray-300" />;
    }
  };
  
  const getStatusColor = () => {
    switch (status.phase) {
      case 'completed': return 'border-green-200 bg-green-50';
      case 'failed': return 'border-red-200 bg-red-50'; 
      case 'executing': return 'border-blue-200 bg-blue-50';
      case 'retrying': return 'border-orange-200 bg-orange-50';
      default: return 'border-gray-200 bg-gray-50';
    }
  };
  
  return (
    <div className={`border rounded-lg p-4 mb-3 transition-all duration-300 ${getStatusColor()}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <h3 className="font-medium text-sm">{tool.name}</h3>
            {status.currentAction && (
              <p className="text-xs text-muted-foreground mt-1">
                {status.currentAction}
              </p>
            )}
          </div>
        </div>
        
        {/* Progress indicator */}
        {status.progress !== undefined && (
          <div className="flex items-center gap-2">
            <div className="w-16 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${status.progress}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {status.progress}%
            </span>
          </div>
        )}
        
        {/* Expand/collapse button */}
        {result && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleExpanded}
            className="p-1"
          >
            <ChevronDown 
              className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} 
            />
          </Button>
        )}
      </div>
      
      {/* Result summary */}
      {result && (
        <div className="mt-3 p-3 bg-white rounded border">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">Result:</span>
            <span className="text-xs bg-gray-100 px-2 py-1 rounded">
              {Math.round(result.confidence * 100)}% confident
            </span>
          </div>
          <p className="text-sm text-gray-700">{result.shortSummary}</p>
          
          {/* Expanded details */}
          {expanded && result.detailedSummary && (
            <div className="mt-3 pt-3 border-t">
              <p className="text-sm text-gray-600">{result.detailedSummary}</p>
              
              {/* Metadata */}
              <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
                <span>⏱️ {result.metadata.executionTime}ms</span>
                {result.metadata.tokensUsed && (
                  <span>🎯 {result.metadata.tokensUsed} tokens</span>
                )}
                {result.metadata.cacheHit && (
                  <span>💾 Cached</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Error display */}
      {status.phase === 'failed' && result?.errors && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-sm text-red-700">
            {result.errors[0].message}
          </p>
          {result.errors[0].retryable && (
            <p className="text-xs text-red-600 mt-1">
              This error is retryable. The system will try again.
            </p>
          )}
        </div>
      )}
    </div>
  );
};
```

### 4.3 Pulsing Indicator Component

```tsx
interface PulsingDotProps {
  color?: 'blue' | 'green' | 'red' | 'orange' | 'gray';
  size?: 'sm' | 'md' | 'lg';
}

export const PulsingDot = ({ color = 'blue', size = 'md' }: PulsingDotProps) => {
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3', 
    lg: 'w-4 h-4'
  };
  
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
    orange: 'bg-orange-500',
    gray: 'bg-gray-400'
  };
  
  return (
    <div className="relative">
      <div className={`${sizeClasses[size]} ${colorClasses[color]} rounded-full`} />
      <div className={`absolute inset-0 ${sizeClasses[size]} ${colorClasses[color]} rounded-full animate-ping opacity-75`} />
    </div>
  );
};
```

### 4.4 Workflow Progress Component

```tsx
interface WorkflowProgressProps {
  currentStep: number;
  totalSteps: number;
  tools: Array<{
    name: string;
    status: ToolStatus;
  }>;
}

export const WorkflowProgress = ({ currentStep, totalSteps, tools }: WorkflowProgressProps) => {
  return (
    <div className="mb-6">
      {/* Progress bar */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm font-medium">Workflow Progress</span>
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-blue-500 transition-all duration-500"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>
        <span className="text-sm text-muted-foreground">
          {currentStep}/{totalSteps}
        </span>
      </div>
      
      {/* Step indicators */}
      <div className="flex items-center justify-between">
        {tools.map((tool, index) => (
          <div key={tool.name} className="flex flex-col items-center gap-1">
            <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-medium transition-all ${
              index < currentStep 
                ? 'border-green-500 bg-green-500 text-white'
                : index === currentStep && tool.status.phase !== 'failed'
                ? 'border-blue-500 bg-blue-500 text-white'
                : tool.status.phase === 'failed'
                ? 'border-red-500 bg-red-500 text-white'
                : 'border-gray-300 bg-white text-gray-500'
            }`}>
              {index < currentStep ? (
                <Check className="w-4 h-4" />
              ) : tool.status.phase === 'failed' ? (
                <X className="w-4 h-4" />
              ) : (
                index + 1
              )}
            </div>
            <span className="text-xs text-center max-w-16 truncate">
              {tool.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 4.5 Stream Object Integration

```typescript
// Using AI SDK's streamObject for real-time UI updates
export const streamWorkflowUpdates = (
  workflow: WorkflowOrchestrator,
  query: string
) => {
  return streamObject({
    model: myProvider.languageModel('chat-model'),
    schema: z.object({
      workflowId: z.string(),
      currentStep: z.number(),
      totalSteps: z.number(),
      tools: z.array(z.object({
        name: z.string(),
        status: z.enum(['pending', 'running', 'completed', 'failed']),
        progress: z.number().optional(),
        result: z.string().optional(),
        error: z.string().optional()
      })),
      finalAnswer: z.string().optional()
    }),
    
    onPartial: (partial) => {
      // Update UI components in real-time
      updateWorkflowDisplay(partial);
    },
    
    execute: async (dataStream) => {
      return await workflow.execute(query);
    }
  });
};
```

## Phase 5: Integration & Migration

### 5.1 Replace Current Implementation

#### Current Workflow Engine Update
```typescript
// lib/ai/workflow-engine.ts

// OLD APPROACH - Remove
// if (intentAnalysis.shouldSearch) {
//   enhancedSystem += `...use intelligentMfaiSearch tool...`;
// }

// NEW APPROACH - Add
if (intentAnalysis.shouldSearch) {
  // Use modular workflow instead of monolithic tool
  const orchestrator = new WorkflowOrchestrator(dataStream, session.user.id);
  const workflowResult = await orchestrator.execute(lastMessage.content);
  
  // Stream final answer
  dataStream.writeData({
    type: 'text-delta',
    content: workflowResult.finalAnswer
  });
  
  return; // Skip regular streamText
}
```

#### Remove Artifact Generation
```typescript
// Remove from tools configuration
tools: {
  getWeather,
  // Remove: createDocument, updateDocument for simple Q&A
  requestSuggestions,
  // Keep MCP tools but use new modular approach
}
```

### 5.2 Backward Compatibility

During migration, maintain both systems:

```typescript
const USE_MODULAR_WORKFLOW = process.env.EXPERIMENTAL_MODULAR_WORKFLOW === 'true';

if (intentAnalysis.shouldSearch) {
  if (USE_MODULAR_WORKFLOW) {
    // New modular approach
    const orchestrator = new WorkflowOrchestrator(dataStream, session.user.id);
    return await orchestrator.execute(lastMessage.content);
  } else {
    // Fallback to current approach
    return await intelligentMfaiSearch.execute({...});
  }
}
```

### 5.3 Performance Optimization

#### Caching Strategy
```typescript
interface CacheKey {
  query: string;
  strategy: string;
  repositories: string[];
  userId: string;
}

class WorkflowCache {
  private cache = new Map<string, CachedResult>();
  private readonly TTL = 1000 * 60 * 15; // 15 minutes
  
  async get(key: CacheKey): Promise<CachedResult | null> {
    const cacheKey = this.createKey(key);
    const cached = this.cache.get(cacheKey);
    
    if (cached && !this.isExpired(cached)) {
      return cached;
    }
    
    return null;
  }
  
  async set(key: CacheKey, result: any): Promise<void> {
    const cacheKey = this.createKey(key);
    this.cache.set(cacheKey, {
      data: result,
      timestamp: Date.now(),
      hits: 0
    });
  }
}
```

#### Parallel Execution
```typescript
// Where possible, run tools in parallel
async executeSearchPhase(query: string, repositories: string[]): Promise<SearchResults> {
  // Run searches in parallel for different repositories
  const searchPromises = repositories.map(repo => 
    this.searchRepository(repo, query)
  );
  
  const results = await Promise.allSettled(searchPromises);
  
  // Handle partial failures gracefully
  return this.mergeResults(results.filter(r => r.status === 'fulfilled'));
}
```

### 5.4 Monitoring & Analytics

```typescript
interface WorkflowMetrics {
  workflowId: string;
  userId: string;
  query: string;
  totalDuration: number;
  toolMetrics: {
    [toolName: string]: {
      duration: number;
      attempts: number;
      success: boolean;
      cacheHit: boolean;
    };
  };
  finalConfidence: number;
  userSatisfaction?: number;
}

class WorkflowAnalytics {
  async recordWorkflow(metrics: WorkflowMetrics): Promise<void> {
    // Send to analytics service
    await this.analyticsService.track('workflow_executed', metrics);
  }
  
  async getPerformanceInsights(): Promise<PerformanceReport> {
    // Analyze common failure points, slow tools, etc.
    return await this.analyticsService.getInsights();
  }
}
```

## Phase 6: Testing & Quality Assurance

### 6.1 Unit Testing Strategy

```typescript
// Test individual tools
describe('RelevanceChecker', () => {
  it('should identify MODFLOW queries correctly', async () => {
    const result = await relevanceChecker.execute(
      { query: 'what is flopy modflow' },
      mockContext
    );
    
    expect(result.success).toBe(true);
    expect(result.data.isRelevant).toBe(true);
    expect(result.confidence).toBeGreaterThan(0.8);
  });
  
  it('should reject non-MODFLOW queries', async () => {
    const result = await relevanceChecker.execute(
      { query: 'how to cook pasta' },
      mockContext
    );
    
    expect(result.data.isRelevant).toBe(false);
  });
});

// Test workflow orchestration
describe('WorkflowOrchestrator', () => {
  it('should execute complete workflow successfully', async () => {
    const orchestrator = new WorkflowOrchestrator(mockDataStream, 'user123');
    const result = await orchestrator.execute('what is maxcompdim in modflow');
    
    expect(result.success).toBe(true);
    expect(result.finalAnswer).toContain('maxcompdim');
    expect(result.toolsExecuted).toHaveLength(4);
  });
  
  it('should handle tool failures gracefully', async () => {
    // Mock repository searcher to fail
    const orchestrator = new WorkflowOrchestrator(mockDataStream, 'user123');
    const result = await orchestrator.execute('test query');
    
    // Should still provide fallback response
    expect(result.success).toBe(true);
    expect(result.degradedMode).toBe(true);
  });
});
```

### 6.2 Integration Testing

```typescript
// Test complete user flows
describe('User Workflows', () => {
  it('should handle MODFLOW query end-to-end', async () => {
    const query = 'how to set up well boundary in flopy';
    
    // Simulate user input through API
    const response = await request(app)
      .post('/api/chat')
      .send({ 
        message: { content: query },
        selectedChatModel: 'chat-model'
      });
    
    expect(response.status).toBe(200);
    
    // Verify workflow was triggered
    expect(mockOrchestrator.execute).toHaveBeenCalledWith(query);
    
    // Verify streaming updates
    expect(mockDataStream.writeData).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'workflow-status'
      })
    );
  });
});
```

### 6.3 Performance Testing

```typescript
// Load testing for concurrent workflows
describe('Performance Tests', () => {
  it('should handle multiple concurrent workflows', async () => {
    const queries = [
      'what is modflow',
      'flopy well package example',  
      'pest calibration tutorial',
      'groundwater flow equations'
    ];
    
    const startTime = Date.now();
    
    const results = await Promise.all(
      queries.map(query => orchestrator.execute(query))
    );
    
    const totalTime = Date.now() - startTime;
    
    expect(results.every(r => r.success)).toBe(true);
    expect(totalTime).toBeLessThan(15000); // Should complete within 15s
  });
});
```

## Success Metrics

### User Experience Metrics
- **Perceived Speed**: Time to first meaningful feedback (< 2 seconds)
- **Transparency**: User understanding of what's happening (measured via surveys)
- **Task Completion**: Percentage of queries that get satisfactory answers (> 85%)
- **Error Recovery**: How often users retry after failures (< 20%)

### Technical Performance Metrics
- **Tool Success Rate**: Individual tool completion rate (> 95%)
- **Workflow Completion Time**: End-to-end query resolution (< 15 seconds avg)
- **Cache Hit Rate**: Percentage of cached responses (> 30%)
- **Resource Utilization**: Token usage efficiency (< current system)

### Quality Metrics
- **Answer Relevance**: LLM-scored answer quality (> 0.8 average)
- **Source Accuracy**: Percentage of answers with valid sources (> 90%)
- **Confidence Calibration**: Alignment between confidence and actual quality

## Migration Strategy

### Gradual Rollout Plan

1. **Alpha Testing**: Internal testing with feature flag
2. **Beta Users**: Limited user group with opt-in toggle
3. **A/B Testing**: 50/50 split between old and new systems
4. **Full Migration**: Complete replacement after validation

### Rollback Plan

- Maintain old system as fallback
- Circuit breaker to detect new system failures
- Automatic fallback triggers
- Manual override controls

### Data Migration

- Export existing workflow logs for comparison
- Preserve user query history and preferences
- Migrate any cached results to new cache format

## Future Enhancements

### Advanced Workflow Features
- **Conditional Branching**: Different workflows based on query type
- **Parallel Tool Execution**: Run compatible tools simultaneously  
- **User Customization**: Allow users to modify workflow steps
- **Learning Workflows**: Adapt based on user feedback and success rates

### Enhanced UI/UX
- **Voice Narration**: Audio feedback for accessibility
- **Mobile Optimization**: Touch-friendly workflow display
- **Workflow History**: Show previous workflow executions
- **Performance Dashboard**: Real-time system health display

### Intelligence Improvements
- **Adaptive Confidence**: Learn from user feedback to improve confidence scoring
- **Query Expansion**: Automatically suggest related queries
- **Result Clustering**: Group similar results for better presentation
- **Context Awareness**: Use conversation history to improve relevance

This roadmap provides a comprehensive path to transform the current monolithic search tool into a modern, streaming, modular workflow system that provides transparency, reliability, and an excellent user experience similar to Perplexity's approach.