import { GoogleGenerativeAI } from '@google/generative-ai';
export interface RepositorySelection {
  selected_repository: string;
  confidence: number;
  reasoning: string;
  alternatives: string[];
  user_confirmation: string;
}

export interface Repository {
  id: number;
  name: string;
  url: string;
  file_count: number;
  navigation_guide: string;
  repository_type: string;
  created_at: string;
  updated_at: string;
}

export class GeminiService {
  private genai: GoogleGenerativeAI;
  private model: any;

  constructor(apiKey: string) {
    if (!apiKey) {
      throw new Error('Google GenAI API key is required');
    }
    
    this.genai = new GoogleGenerativeAI(apiKey);
    this.model = this.genai.getGenerativeModel({ model: 'gemini-2.0-flash-exp' });
  }

  /**
   * Analyzes user query against repositories and selects the most relevant one
   */
  async selectRepository(
    query: string, 
    repositories: Repository[], 
    context?: string
  ): Promise<RepositorySelection> {
    try {
      const prompt = this.buildPrompt(query, repositories, context);
      const result = await this.model.generateContent({
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.2,
          maxOutputTokens: 1000,
          responseMimeType: 'application/json',
          responseSchema: {
            type: 'object',
            properties: {
              selected_repository: { type: 'string' },
              confidence: { type: 'number' },
              reasoning: { type: 'string' },
              alternatives: { 
                type: 'array', 
                items: { type: 'string' } 
              },
              user_confirmation: { type: 'string' }
            },
            required: ['selected_repository', 'confidence', 'reasoning', 'alternatives', 'user_confirmation']
          }
        },
      });

      const response = result.response.text();
      return JSON.parse(response);
      
    } catch (error) {
      console.error('Gemini API error:', error);
      throw error;
    }
  }

  /**
   * Builds the prompt for repository selection
   */
  private buildPrompt(query: string, repositories: Repository[], context?: string): string {
    const repositoryData = repositories.map(repo => ({
      name: repo.name,
      url: repo.url,
      file_count: repo.file_count,
      repository_type: repo.repository_type,
      navigation_guide: repo.navigation_guide
    }));

    return `You are an expert assistant that helps users find the most relevant repository from a collection of groundwater modeling and analysis repositories.

REPOSITORIES:
${JSON.stringify(repositoryData, null, 2)}

USER QUERY: ${query}

${context ? `CONVERSATION CONTEXT: ${context}` : ''}

Analyze the user's query against the repository navigation guides and select the most relevant repository.

Return ONLY a JSON object with this exact structure (no markdown formatting, no code blocks):
{
  "selected_repository": "repository_name",
  "confidence": 0.95,
  "reasoning": "Clear explanation of why this repository was selected based on the query and navigation guides",
  "alternatives": ["alternative_repo1", "alternative_repo2"],
  "user_confirmation": "A question to confirm with the user that this is the correct repository to search"
}

IMPORTANT RULES:
1. Return ONLY the JSON object, no additional text, no markdown code blocks
2. Choose the repository whose navigation guide best matches the user's query
3. Confidence should be between 0.0 and 1.0
4. Include 1-3 alternative repositories if relevant
5. Generate a helpful confirmation question for the user
6. Be precise and specific in your reasoning
7. Consider repository types and file counts when relevant
8. selected_repository must be exactly one of the repository names from the list above`;
  }

  /**
   * Validates that the selected repository exists in the provided list
   */
  validateRepositoryExists(selection: RepositorySelection, repositories: Repository[]): RepositorySelection {
    const selectedRepo = repositories.find(repo => repo.name === selection.selected_repository);
    
    if (!selectedRepo) {
      throw new Error(`Selected repository "${selection.selected_repository}" not found in repository list`);
    }
    
    return selection;
  }
}