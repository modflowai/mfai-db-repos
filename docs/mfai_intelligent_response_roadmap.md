# MFAI Intelligent Response Generator - Clean Architecture Roadmap

## Project Overview

Create a **NEW MCP server** (`mfai_mcp_server_response`) that processes large repository documents (35k+ tokens) and generates focused intelligent responses (8k tokens). This server works **alongside** the existing `mfai_mcp_server` by taking a repository name, search method, and query, then using Gemini 2.5 to compress and synthesize the most relevant document into actionable information.

## 🎯 Architecture Principle: No Hardcoding

**CORE PRINCIPLE**: The client decides the repository and search strategy. We focus on document processing + intelligent compression (35k+ docs → 8k focused responses).

## 🏗️ Clean Architecture Flow

```
CLIENT WORKFLOW:
1. Client calls existing server: list_repositories_with_navigation → gets repo info
2. Client decides: which repo + search method (text/semantic)  
3. Client calls NEW server: mfai_intelligent_response
   Input: {repository: "pestpp", search_type: "text", query: "What is PEST-IES?"}
                          ↓
              Document Retrieval → TOP search result (35k+ tokens)
                          ↓  
              Gemini Document Processing (35k+ → 8k synthesis)
                          ↓
Output: {response: "Focused 8k answer about PEST-IES...", sources: ["pestpp/methodology.md"]}

SCENARIOS:
A) Search finds document → Process 35k+ doc → Generate 8k focused response
B) No search results → Use navigation guide → Suggest better query/approach
```

## 📁 New Project Structure

```
mfai_mcp_server_response/
├── src/
│   ├── index.ts                     # New MCP server entry point
│   └── lib/
│       ├── ai/
│       │   └── prompts.ts           # Prompt management  
│       ├── services/
│       │   ├── document-search-service.ts    # Reuse existing search logic
│       │   └── gemini-response-service.ts    # AI response generation
│       ├── handlers/
│       │   └── intelligent-response-handler.ts # Main handler
│       └── types/
│           └── response-types.ts     # Clean interfaces
├── package.json
└── tsconfig.json
```

## 🚀 Simple 3-Phase Implementation

### Phase 1: Clean Tool Definition & Types

#### 1.1 New Tool Registration
**File:** `src/index.ts`
```typescript
{
  name: 'mfai_intelligent_response',
  description: 'Generates intelligent response for repository query. Client provides repo and search strategy.',
  inputSchema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'User question about the repository',
      },
      repository: {
        type: 'string', 
        description: 'Repository name (client already selected)',
      },
      search_type: {
        type: 'string',
        enum: ['text', 'semantic'],
        description: 'Search method (client decides - no hardcoding)',
      },
    },
    required: ['query', 'repository', 'search_type'],
  },
}
```

#### 1.2 Clean Interfaces  
**File:** `src/lib/types/response-types.ts`
```typescript
export interface IntelligentResponseInput {
  query: string;
  repository: string;
  search_type: 'text' | 'semantic';
}

export interface IntelligentResponseOutput {
  response: string;
  sources: string[];  // Simple document titles
  follow_up_suggestions: string[];
}

export interface DocumentSearchResult {
  filepath: string;
  filename: string;
  content: string;
  relevance_score?: number;
}
```

### Phase 2: Document Search Service (Reuse Existing Logic)

**File:** `src/lib/services/document-search-service.ts`
```typescript
import { neon } from '@neondatabase/serverless';
import { OpenAI } from 'openai';
import type { DocumentSearchResult } from '../types/response-types.js';

export class DocumentSearchService {
  private sql: any;
  private openai: OpenAI | null;
  
  constructor(sqlConnection: any, openaiClient: OpenAI | null) {
    this.sql = sqlConnection;
    this.openai = openaiClient;
  }

  async searchDocuments(
    repository: string,
    query: string, 
    searchType: 'text' | 'semantic'
  ): Promise<DocumentSearchResult | null> {
    
    const results = searchType === 'text' 
      ? await this.textSearch(repository, query)
      : await this.semanticSearch(repository, query);
    
    // Return TOP result only (or null if no results)
    return results.length > 0 ? results[0] : null;
  }

  private async textSearch(repository: string, query: string): Promise<DocumentSearchResult[]> {
    // Reuse exact logic from existing mfai_mcp_server
    const queryWords = query.split(' ').filter(word => word.length > 0);
    const tsQuery = queryWords.map(word => `${word}:*`).join(' & ');
    
    const results = await this.sql`
      SELECT 
        rf.filepath,
        rf.filename, 
        rf.content,
        ts_rank_cd(rf.content_tsvector, to_tsquery('english', ${tsQuery})) as relevance_score
      FROM repository_files rf
      WHERE rf.content_tsvector @@ to_tsquery('english', ${tsQuery})
        AND rf.repo_name = ${repository}
      ORDER BY relevance_score DESC
      LIMIT 1
    `;
    
    return results;
  }

  private async semanticSearch(repository: string, query: string): Promise<DocumentSearchResult[]> {
    if (!this.openai) {
      throw new Error('Semantic search requires OPENAI_API_KEY environment variable');
    }
    
    // Reuse exact logic from existing mfai_mcp_server
    const embeddingResponse = await this.openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: query,
    });
    
    const embedding = embeddingResponse.data[0].embedding;
    const pgVector = `[${embedding.join(',')}]`;
    
    const results = await this.sql`
      SELECT 
        rf.filepath,
        rf.filename,
        rf.content,
        1 - (rf.embedding <=> ${pgVector}::vector) as relevance_score
      FROM repository_files rf
      WHERE rf.embedding IS NOT NULL
        AND rf.repo_name = ${repository}
      ORDER BY rf.embedding <=> ${pgVector}::vector
      LIMIT 1
    `;
    
    return results;
  }
}
```

### Phase 3: Gemini Response Service (Reuse JSON Approach)

**File:** `src/lib/services/gemini-response-service.ts`  
```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';
import { IntelligentResponsePrompts } from '../ai/prompts.js';
import type { DocumentSearchResult, IntelligentResponseOutput } from '../types/response-types.js';

export class GeminiResponseService {
  private genai: GoogleGenerativeAI;
  private model: any;

  constructor(apiKey: string) {
    this.genai = new GoogleGenerativeAI(apiKey);
    this.model = this.genai.getGenerativeModel({ model: 'gemini-2.0-flash-001' });
  }

  async generateResponse(
    query: string,
    repository: string,
    topDocument: DocumentSearchResult | null,
    navigationGuide: string
  ): Promise<IntelligentResponseOutput> {
    
    try {
      const prompt = IntelligentResponsePrompts.buildResponsePrompt(
        query, 
        repository, 
        topDocument,
        navigationGuide
      );
      
      const result = await this.model.generateContent({
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.3,
          maxOutputTokens: 8000,  // 8k focused response limit
          responseMimeType: 'application/json',
          responseSchema: IntelligentResponsePrompts.getResponseSchema()
        },
      });

      const response = result.response.text();
      return JSON.parse(response);
      
    } catch (error) {
      console.error('Gemini Response Generation Error:', error);
      throw new Error(`Failed to generate intelligent response: ${error.message}`);
    }
  }
}
```

### Phase 4: Simple Handler & Integration

**File:** `src/lib/handlers/intelligent-response-handler.ts`
```typescript
import { DocumentSearchService } from '../services/document-search-service.js';
import { GeminiResponseService } from '../services/gemini-response-service.js';
import type { IntelligentResponseInput, IntelligentResponseOutput } from '../types/response-types.js';

export class IntelligentResponseHandler {
  private searchService: DocumentSearchService;
  private responseService: GeminiResponseService;

  constructor(
    searchService: DocumentSearchService,
    responseService: GeminiResponseService
  ) {
    this.searchService = searchService;
    this.responseService = responseService;
  }

  async handle(input: IntelligentResponseInput): Promise<IntelligentResponseOutput> {
    try {
      // 1. Get repository navigation guide
      const navigationGuide = await this.getNavigationGuide(input.repository);
      
      // 2. Search for top document (35k+ tokens or null)
      const topDocument = await this.searchService.searchDocuments(
        input.repository,
        input.query,
        input.search_type
      );
      
      // 3. Generate intelligent response (compress 35k+ → 8k response)
      const response = await this.responseService.generateResponse(
        input.query,
        input.repository,
        topDocument,
        navigationGuide
      );
      
      return response;
      
    } catch (error) {
      console.error('Intelligent Response Handler Error:', error);
      throw new Error(`Failed to generate intelligent response: ${error.message}`);
    }
  }

  private async getNavigationGuide(repository: string): Promise<string> {
    // Get navigation guide from database for repository context
    // Implementation details...
    return "";
  }

  static getToolDefinition() {
    return {
      name: 'mfai_intelligent_response',
      description: 'Generates intelligent response for repository query. Client provides repo and search strategy.',
      inputSchema: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'User question about the repository',
          },
          repository: {
            type: 'string',
            description: 'Repository name (client already selected)',
          },
          search_type: {
            type: 'string',
            enum: ['text', 'semantic'],
            description: 'Search method (client decides - no hardcoding)',
          },
        },
        required: ['query', 'repository', 'search_type'],
      },
    };
  }
}
```

## 🎯 Key Architecture Benefits

### No Hardcoding ✅
- Client provides repository (no AI selection needed)
- Client provides search strategy (no regex heuristics)
- We focus on: search + intelligent response

### Reuse Existing Infrastructure ✅  
- Document search logic from existing `mfai_mcp_server`
- Gemini JSON response from `mfai_mcp_server_reposel`
- Database connections and queries already proven

### Clean Separation of Concerns ✅
- Existing server: repository info + raw search
- NEW server: intelligent AI responses
- Client: orchestration and strategy decisions

## 🚀 Expected Client Workflow

### Example: Technical Query (Document Found)
```
1. Client: list_repositories_with_navigation → gets repo options
2. Client decides: "pestpp" repo, "text" search for "PEST-IES"  
3. Client: mfai_intelligent_response
   Input: {repository: "pestpp", search_type: "text", query: "What is PEST-IES?"}
4. Server: finds 35k+ token document about PESTPP-IES methodology
5. Server: Gemini processes 35k+ doc → generates focused 8k response
6. Output: {response: "PEST-IES (Iterative Ensemble Smoother) is...", sources: ["pestpp/methodology.md"]}
```

### Example: No Document Found
```
1. Client: mfai_intelligent_response
   Input: {repository: "flopy", search_type: "text", query: "PEST-IES implementation"}
2. Server: no documents found matching query
3. Server: uses navigation guide + repository knowledge  
4. Output: {response: "PEST-IES is not available in FloPy. FloPy focuses on MODFLOW...", sources: ["Repository Navigation Guide"]}
```

## 📊 Success Criteria

### Functional Requirements ✅
- Process large documents (35k+ tokens) into focused responses (8k tokens)
- Generate comprehensive, contextual answers from document analysis
- Handle both "document found" and "no results" scenarios gracefully
- Provide accurate source attribution as simple document titles
- Support both text and semantic search (client decides)

### Architecture Requirements ✅
- No hardcoded search strategy logic
- Reuse existing proven search infrastructure  
- Clean separation from existing MCP server
- Client manages repository selection and search strategy

### Quality Requirements ✅
- Response time under 10 seconds for large document processing
- Response accuracy >90% based on document content analysis
- Proper error handling and graceful degradation
- Source references are accurate document titles
- Efficient token usage (35k+ input → 8k focused output)

## 🎯 **Core Value Proposition**

This MCP server solves the **"large document problem"** by acting as an intelligent document processor:

- **Input**: 35k+ token repository documents (too large for normal consumption)
- **Process**: AI-powered analysis, extraction, and synthesis 
- **Output**: 8k token focused responses with actionable information
- **Result**: Users get comprehensive answers without reading massive documents

The architecture eliminates hardcoding, reuses proven infrastructure, and provides clean separation of concerns between repository navigation and intelligent document processing.