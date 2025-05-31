// Repository List Tool Types
export interface RepositoryListInput {
  include_navigation?: boolean;
}

export interface RepositoryListOutput {
  repositories: Array<{
    id: number;
    name: string;
    url: string;
    file_count: number;
    navigation_guide?: string;
    repository_type?: string;
    created_at: string;
    updated_at: string;
  }>;
}

// Document Retrieval Tool Types
export interface DocumentRetrievalInput {
  query: string;
  repository: string;
  search_type: 'text' | 'semantic';
  context?: string; // Optional context to guide compression
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