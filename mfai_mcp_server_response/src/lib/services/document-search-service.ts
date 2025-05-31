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
      console.warn('OPENAI_API_KEY not provided, falling back to text search');
      return this.textSearch(repository, query);
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