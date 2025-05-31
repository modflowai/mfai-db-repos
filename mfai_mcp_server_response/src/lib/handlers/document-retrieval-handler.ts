import { DocumentSearchService } from '../services/document-search-service.js';
import { GeminiCompressionService } from '../services/gemini-response-service.js';
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
        const fallbackContent = navigationGuide || `No documents found for query "${input.query}" in repository "${input.repository}". Try broader search terms.`;
        return {
          content: fallbackContent,
          sources: ['Navigation Guide'],
          token_count: TokenCounterService.countTokens(fallbackContent),
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
        // Compress document to exactly 8k tokens with query and context focus
        const compressedContent = await this.compressionService.compressDocument(
          topDocument,
          input.repository,
          originalTokenCount,
          input.query,
          input.context
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
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to retrieve document: ${errorMessage}`);
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
          context: {
            type: 'string',
            description: 'Optional context to guide document compression and focus',
          },
        },
        required: ['query', 'repository', 'search_type'],
      },
    };
  }
}