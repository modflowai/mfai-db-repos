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
    originalTokenCount: number,
    query: string,
    context?: string
  ): Promise<string> {
    
    try {
      const prompt = DocumentCompressionPrompts.buildCompressionPrompt(
        document,
        repository,
        originalTokenCount,
        query,
        context
      );
      
      const result = await this.model.generateContent({
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.0,        // Zero temperature for maximum consistency
          maxOutputTokens: 7000,   // Hard limit at 7k tokens
        },
      });

      return result.response.text();
      
    } catch (error) {
      console.error('Gemini Document Compression Error:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to compress document: ${errorMessage}`);
    }
  }
}