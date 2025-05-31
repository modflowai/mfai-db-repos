import type { RepositoryListInput, RepositoryListOutput } from '../types/response-types.js';

export class RepositoryListHandler {
  private sql: any;

  constructor(sqlConnection: any) {
    this.sql = sqlConnection;
  }

  async handle(input: RepositoryListInput): Promise<RepositoryListOutput> {
    try {
      const results = input.include_navigation 
        ? await this.sql`
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
            ORDER BY id ASC
            LIMIT 50
          `
        : await this.sql`
            SELECT 
              id, 
              name, 
              url, 
              file_count,
              created_at, 
              updated_at
            FROM repositories
            ORDER BY id ASC
            LIMIT 50
          `;

      return {
        repositories: results
      };
      
    } catch (error) {
      console.error('Repository List Handler Error:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to list repositories: ${errorMessage}`);
    }
  }

  static getToolDefinition() {
    return {
      name: 'list_repositories_with_navigation',
      description: 'Lists all available repositories with optional navigation guides for repository selection and understanding.',
      inputSchema: {
        type: 'object',
        properties: {
          include_navigation: {
            type: 'boolean',
            description: 'Include navigation guides in response (default: true)',
            default: true
          }
        },
        required: []
      }
    };
  }
}