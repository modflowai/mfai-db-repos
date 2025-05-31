import { z } from 'zod';
import { GeminiService, type Repository } from '../services/gemini-service.js';
import type { RepositorySelection } from '../services/gemini-service.js';

// Input validation schema
export const RepositorySelectorSchema = z.object({
  query: z.string().describe('User\'s question or search query'),
  context: z.string().optional().describe('Optional conversation context'),
});

export type RepositorySelectorInput = z.infer<typeof RepositorySelectorSchema>;

export class RepositorySelectorHandler {
  private geminiService: GeminiService;
  private sql: any;

  constructor(geminiService: GeminiService, sqlConnection: any) {
    this.geminiService = geminiService;
    this.sql = sqlConnection;
  }

  /**
   * Handles repository selection request
   */
  async handle(input: RepositorySelectorInput): Promise<RepositorySelection> {
    // Validate input
    const { query, context } = RepositorySelectorSchema.parse(input);
    
    // Get repositories with navigation guides from database
    const repositories = await this.getRepositoriesWithNavigation();
    
    if (repositories.length === 0) {
      throw new Error('No repositories with navigation guides found in the database');
    }
    
    // Use Gemini to select the best repository
    const selection = await this.geminiService.selectRepository(query, repositories, context);
    
    // Validate that the selected repository exists
    const validatedSelection = this.geminiService.validateRepositoryExists(selection, repositories);
    
    return validatedSelection;
  }

  /**
   * Retrieves repositories with navigation guides from the database
   */
  private async getRepositoriesWithNavigation(): Promise<Repository[]> {
    try {
      const repositories = await this.sql`
        SELECT 
          id, 
          name, 
          url, 
          file_count,
          metadata->>'navigation_guide' as navigation_guide,
          metadata->>'repository_type' as repository_type,
          created_at, 
          updated_at
        FROM repositories
        WHERE metadata->>'navigation_guide' IS NOT NULL
        ORDER BY id ASC
      `;
      
      return repositories.map((repo: any) => ({
        id: repo.id,
        name: repo.name,
        url: repo.url,
        file_count: repo.file_count,
        navigation_guide: repo.navigation_guide,
        repository_type: repo.repository_type,
        created_at: repo.created_at,
        updated_at: repo.updated_at
      }));
      
    } catch (error) {
      console.error('Database error when fetching repositories:', error);
      throw new Error(`Failed to fetch repositories: ${error instanceof Error ? error.message : 'Unknown database error'}`);
    }
  }

  /**
   * Creates a tool definition for the MCP server
   */
  static getToolDefinition() {
    return {
      name: 'mfai_repository_selector',
      description: 'Analyzes user query against repository navigation guides to suggest the most relevant repository for searching',
      inputSchema: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The user\'s question or search query',
          },
          context: {
            type: 'string',
            description: 'Optional conversation context',
          },
        },
        required: ['query'],
      },
    };
  }
}