# MFAI Intelligent Response Generator - Clean Architecture Roadmap

## Project Overview

Create a **NEW MCP server** (`mfai_mcp_server_response`) that retrieves repository documents and provides them in optimal format for LLM consumption. For documents under 8k tokens, it returns the full content. For larger documents (35k+ tokens), it uses Gemini 2.5 to intelligently compress while prioritizing query-relevant content to exactly 8k tokens. This server works **alongside** the existing `mfai_mcp_server` by taking a repository name, search method, and query, then providing the best document content for LLM context.

## 🎯 Architecture Principle: No Hardcoding

**CORE PRINCIPLE**: The client decides the repository and search strategy. We focus on document retrieval + intelligent content optimization (full docs under 8k, query-focused compression to 8k for larger docs).

## 🏗️ Clean Architecture Flow

```
CLIENT WORKFLOW:
1. Client calls existing server: list_repositories_with_navigation → gets repo info
2. Client decides: which repo + search method (text/semantic)  
3. Client calls NEW server: mfai_document_retrieval
   Input: {repository: "pestpp", search_type: "text", query: "PEST-IES iterative ensemble smoother"}
                          ↓
              Document Retrieval → TOP search result
                          ↓  
              Intelligent Processing:
              - If < 8k tokens → Return full document content (no processing)
              - If ≥ 8k tokens → Query-focused compression to exactly 8k tokens
                          ↓
Output: {content: "Full doc OR query-focused compressed 8k content", sources: ["pestpp/methodology.md"], token_count: 7850, was_compressed: true}

SCENARIOS:
A) Small document (< 8k) → Return full content as-is (no processing needed)
B) Large document (≥ 8k) → Intelligent compression prioritizing query-relevant content
C) No search results → Use navigation guide → Suggest better search approach
```

## 📁 New Project Structure

```
mfai_mcp_server_response/
├── src/
│   ├── index.ts                     # New MCP server entry point
│   └── lib/
│       ├── ai/
│       │   └── prompts.ts           # Document compression prompts  
│       ├── services/
│       │   ├── document-search-service.ts    # Reuse existing search logic
│       │   ├── gemini-intelligence-service.ts # AI query-focused processing
│       │   └── token-counter-service.ts      # Token counting utility
│       ├── handlers/
│       │   └── document-retrieval-handler.ts # Main retrieval handler
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
  name: 'mfai_document_retrieval',
  description: 'Retrieves repository documents in optimal format for LLM consumption. Returns full content for small docs, intelligently compressed content for large docs.',
  inputSchema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'Search query to find relevant document',
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
export interface DocumentRetrievalInput {
  query: string;
  repository: string;
  search_type: 'text' | 'semantic';
}

export interface DocumentRetrievalOutput {
  content: string;           // Full document or compressed 8k content
  sources: string[];         // Simple document titles  
  token_count: number;       // Actual token count of returned content
  was_compressed: boolean;   // True if content was compressed by Gemini
  original_token_count?: number; // Original size if compressed
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

### Phase 3: Token Counter & Gemini Compression Services

**File:** `src/lib/services/token-counter-service.ts`
```typescript
export class TokenCounterService {
  private static readonly CHARS_PER_TOKEN = 4; // Rough estimate for English text
  
  static countTokens(text: string): number {
    // Simple token estimation: 1 token ≈ 4 characters for English
    return Math.ceil(text.length / this.CHARS_PER_TOKEN);
  }
  
  static isUnder8k(text: string): boolean {
    return this.countTokens(text) < 8000;
  }
}
```

**File:** `src/lib/services/gemini-compression-service.ts`  
```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';
import { DocumentCompressionPrompts } from '../ai/prompts.js';
import type { DocumentSearchResult } from '../types/response-types.js';

export class GeminiCompressionService {
  private genai: GoogleGenerativeAI;
  private model: any;

  constructor(apiKey: string) {
    this.genai = new GoogleGenerativeAI(apiKey);
    this.model = this.genai.getGenerativeModel({ model: 'gemini-2.0-flash-001' });
  }

  async compressDocument(
    document: DocumentSearchResult,
    repository: string,
    originalTokenCount: number
  ): Promise<string> {
    
    try {
      const prompt = DocumentCompressionPrompts.buildCompressionPrompt(
        document,
        repository,
        originalTokenCount
      );
      
      const result = await this.model.generateContent({
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.1,        // Low temperature for consistent compression
          maxOutputTokens: 8000,   // Exactly 8k tokens
        },
      });

      return result.response.text();
      
    } catch (error) {
      console.error('Gemini Document Compression Error:', error);
      throw new Error(`Failed to compress document: ${error.message}`);
    }
  }
}
```

### Phase 4: Document Retrieval Handler & Integration

**File:** `src/lib/handlers/document-retrieval-handler.ts`
```typescript
import { DocumentSearchService } from '../services/document-search-service.js';
import { GeminiCompressionService } from '../services/gemini-compression-service.js';
import { TokenCounterService } from '../services/token-counter-service.js';
import type { DocumentRetrievalInput, DocumentRetrievalOutput } from '../types/response-types.js';

export class DocumentRetrievalHandler {
  private searchService: DocumentSearchService;
  private compressionService: GeminiCompressionService;
  private sql: any;

  constructor(
    searchService: DocumentSearchService,
    compressionService: GeminiCompressionService,
    sqlConnection: any
  ) {
    this.searchService = searchService;
    this.compressionService = compressionService;
    this.sql = sqlConnection;
  }

  async handle(input: DocumentRetrievalInput): Promise<DocumentRetrievalOutput> {
    try {
      // 1. Search for top document
      const topDocument = await this.searchService.searchDocuments(
        input.repository,
        input.query,
        input.search_type
      );
      
      if (!topDocument) {
        // No document found - return navigation guide suggestion
        const navigationGuide = await this.getNavigationGuide(input.repository);
        return {
          content: navigationGuide || `No documents found for query "${input.query}" in repository "${input.repository}". Try broader search terms.`,
          sources: ['Navigation Guide'],
          token_count: TokenCounterService.countTokens(navigationGuide || ''),
          was_compressed: false
        };
      }
      
      // 2. Check token count and decide on compression
      const originalTokenCount = TokenCounterService.countTokens(topDocument.content);
      
      if (TokenCounterService.isUnder8k(topDocument.content)) {
        // Return full document - no compression needed
        return {
          content: topDocument.content,
          sources: [topDocument.filename],
          token_count: originalTokenCount,
          was_compressed: false
        };
      } else {
        // Compress document to exactly 8k tokens
        const compressedContent = await this.compressionService.compressDocument(
          topDocument,
          input.repository,
          originalTokenCount
        );
        
        const finalTokenCount = TokenCounterService.countTokens(compressedContent);
        
        return {
          content: compressedContent,
          sources: [topDocument.filename],
          token_count: finalTokenCount,
          was_compressed: true,
          original_token_count: originalTokenCount
        };
      }
      
    } catch (error) {
      console.error('Document Retrieval Handler Error:', error);
      throw new Error(`Failed to retrieve document: ${error.message}`);
    }
  }

  private async getNavigationGuide(repository: string): Promise<string> {
    try {
      const results = await this.sql`
        SELECT metadata->>'navigation_guide' as navigation_guide
        FROM repositories
        WHERE name = ${repository}
        LIMIT 1
      `;
      
      return results.length > 0 ? results[0].navigation_guide || '' : '';
    } catch (error) {
      console.error('Error fetching navigation guide:', error);
      return '';
    }
  }

  static getToolDefinition() {
    return {
      name: 'mfai_document_retrieval',
      description: 'Retrieves repository documents in optimal format for LLM consumption. Returns full content for small docs, intelligently compressed content for large docs.',
      inputSchema: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'Search query to find relevant document',
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

### Example: Large Document (Compression Required)
```
1. Client: list_repositories_with_navigation → gets repo options
2. Client decides: "pestpp" repo, "text" search for "PEST-IES"  
3. Client: mfai_document_retrieval
   Input: {repository: "pestpp", search_type: "text", query: "PEST-IES"}
4. Server: finds 35k+ token document about PESTPP-IES methodology
5. Server: Token count = 35,000 → Compression needed
6. Server: Gemini compresses 35k doc → exactly 8k dense content
7. Output: {content: "Compressed 8k content...", sources: ["pestpp/methodology.md"], token_count: 7998, was_compressed: true, original_token_count: 35000}
```

### Example: Small Document (Full Content)
```
1. Client: mfai_document_retrieval
   Input: {repository: "flopy", search_type: "text", query: "installation guide"}
2. Server: finds 3k token installation document
3. Server: Token count = 3,000 → Return full content
4. Output: {content: "Full 3k installation guide...", sources: ["flopy/installation.md"], token_count: 3000, was_compressed: false}
```

### Example: No Document Found
```
1. Client: mfai_document_retrieval
   Input: {repository: "flopy", search_type: "text", query: "PEST-IES implementation"}
2. Server: no documents found matching query
3. Server: returns navigation guide + suggestion  
4. Output: {content: "FloPy navigation guide + search suggestions...", sources: ["Navigation Guide"], token_count: 1500, was_compressed: false}
```

## 📊 Success Criteria

### Functional Requirements ✅
- Return full content for documents under 8k tokens
- Compress large documents (35k+ tokens) to exactly 8k tokens maintaining maximum information density
- Handle both "document found" and "no results" scenarios gracefully
- Provide accurate source attribution and token count metrics
- Support both text and semantic search (client decides)

### Architecture Requirements ✅
- No hardcoded search strategy logic
- Reuse existing proven search infrastructure  
- Clean separation from existing MCP server
- Client manages repository selection and search strategy

### Quality Requirements ✅
- Response time under 10 seconds for large document compression
- Compression maintains >90% of original information density
- Proper error handling and graceful degradation
- Accurate token counting and compression metrics
- Efficient processing (instant return for small docs, intelligent compression for large docs)

## 🎯 **Core Value Proposition**

This MCP server solves the **"document size optimization problem"** by acting as an intelligent document retrieval system:

- **Small Documents (< 8k)**: Return full content immediately - no processing needed
- **Large Documents (≥ 8k)**: Intelligent compression maintaining maximum information density in exactly 8k tokens
- **Process**: AI-powered content compression preserving all critical information
- **Output**: LLM-optimized content ready for immediate consumption
- **Result**: Clients get the best possible document content regardless of original size

The architecture eliminates hardcoding, reuses proven infrastructure, and provides clean separation of concerns between repository search and intelligent document optimization.