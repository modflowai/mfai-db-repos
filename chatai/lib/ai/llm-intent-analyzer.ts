/**
 * LLM-Powered Intent Analyzer - Uses the model itself for intelligent query analysis
 * NO HARDCODING - All decisions made by the LLM
 */

import { generateText } from 'ai';
import { myProvider } from './providers';

export interface LLMIntentAnalysis {
  requiresRepositoryContext: boolean;
  action: 'search' | 'list' | 'explore' | 'general';
  shouldSearch: boolean;
  optimalSearchStrategy: 'text' | 'semantic' | 'hybrid';
  benefitsFromParallelSearch: boolean;
  targetRepositories: string[] | null;
  shouldEnhanceResults: boolean;
  confidence: number;
  reasoning: string;
}

export interface LLMRelevanceScore {
  score: number;
  reasoning: string;
}

export class LLMIntentAnalyzer {
  /**
   * Analyze user query using LLM to determine optimal strategy
   */
  static async analyzeUserIntent(userQuery: string): Promise<LLMIntentAnalysis> {
    try {
      const result = await generateText({
        model: myProvider.languageModel('chat-model'),
        messages: [
          {
            role: 'system',
            content: `You are a MODFLOW and PEST documentation assistant. Your job is to determine if a user's query is related to MODFLOW/PEST topics and what action is needed.

            First, determine RELEVANCE to these topics:
            - MODFLOW (groundwater modeling software)
            - PEST (parameter estimation software) 
            - Hydrology concepts
            - Groundwater modeling
            - Calibration techniques for groundwater models
            - Python libraries like flopy, pestpy
            - Related repositories: flopy, modflow6, pest, mt3d, seawat, mfusg

            Then analyze the user's intent:

            1. requiresRepositoryContext: boolean - Only true if they specifically ask about "what repositories", "available repos", "list repositories"
            2. action: 'search' | 'list' | 'explore' | 'general' - What is their primary intent?
            3. shouldSearch: boolean - Only true if they want to search for specific MODFLOW/PEST content
            4. optimalSearchStrategy: 'text' | 'semantic' | 'hybrid' - What search approach would work best?
               - 'text': For exact matches, specific function names, file names, code snippets
               - 'semantic': For conceptual questions, "how to" queries, understanding workflows
               - 'hybrid': For comprehensive searches that benefit from both approaches
            5. benefitsFromParallelSearch: boolean - Would running multiple search strategies simultaneously help?
            6. targetRepositories: string[] | null - Should we focus on specific repositories or search all?
            7. shouldEnhanceResults: boolean - Should we create enhanced documentation from results?
            8. confidence: number - How confident are you in this analysis? (0.0-1.0)
            9. reasoning: string - Brief explanation of your analysis

            Respond in JSON format with these exact field names.

            Examples:
            - "hello" → requiresRepositoryContext: false, action: "general", shouldSearch: false, reasoning: "General greeting, not MODFLOW related"
            - "What MODFLOW repositories are available?" → requiresRepositoryContext: true, action: "list", shouldSearch: false
            - "Find groundwater pumping examples" → shouldSearch: true, optimalSearchStrategy: "semantic", action: "search"
            - "Search for 'flopy.modflow.mfwel'" → shouldSearch: true, optimalSearchStrategy: "text", action: "search"
            - "use mfsearch to search what is flopy" → shouldSearch: true, optimalSearchStrategy: "semantic", action: "search"
            - "mfaiSearch what is modflow" → shouldSearch: true, optimalSearchStrategy: "semantic", action: "search"
            - "How do I install Python?" → requiresRepositoryContext: false, action: "general", shouldSearch: false, reasoning: "General Python question, not MODFLOW specific"
            
            CRITICAL: Only set shouldSearch: true if the query is asking about MODFLOW/PEST specific content. Only set requiresRepositoryContext: true if they specifically want to see available repositories.`
          },
          {
            role: 'user',
            content: userQuery
          }
        ],
        temperature: 0.1,
      });

      // Clean the response text - remove markdown code blocks if present
      let cleanText = result.text.trim();
      if (cleanText.startsWith('```json')) {
        cleanText = cleanText.replace(/^```json\s*/, '').replace(/\s*```$/, '');
      } else if (cleanText.startsWith('```')) {
        cleanText = cleanText.replace(/^```\s*/, '').replace(/\s*```$/, '');
      }

      const analysis = JSON.parse(cleanText);
      return {
        requiresRepositoryContext: false,
        action: 'general',
        shouldSearch: false,
        optimalSearchStrategy: 'semantic',
        benefitsFromParallelSearch: false,
        targetRepositories: null,
        shouldEnhanceResults: false,
        confidence: 0.5,
        reasoning: 'Default analysis',
        ...analysis // Override with LLM analysis
      };
    } catch (error) {
      console.warn('LLM intent analysis failed, using fallback:', error);
      return {
        requiresRepositoryContext: false,
        action: 'general',
        shouldSearch: false,
        optimalSearchStrategy: 'semantic',
        benefitsFromParallelSearch: false,
        targetRepositories: null,
        shouldEnhanceResults: false,
        confidence: 0.3,
        reasoning: 'Fallback analysis due to LLM error'
      };
    }
  }

  /**
   * Determine optimal search strategy using LLM analysis
   */
  static async analyzeSearchStrategy(query: string): Promise<'text' | 'semantic' | 'hybrid'> {
    try {
      const result = await generateText({
        model: myProvider.languageModel('chat-model'),
        messages: [
          {
            role: 'system',
            content: `You are an expert at determining optimal search strategies for MODFLOW repository queries.

            Given a user query, determine the best search strategy:
            
            - "text": For exact matches, specific function names, file names, code snippets, or quoted terms
            - "semantic": For conceptual questions, "how to" queries, understanding workflows, or finding similar approaches  
            - "hybrid": For comprehensive searches that benefit from both exact matches and conceptual similarity

            Consider:
            - Quotes or specific technical terms → text search
            - Questions about concepts or approaches → semantic search  
            - Requests for "everything about" or "complete guide" → hybrid search
            
            Respond with only: "text", "semantic", or "hybrid"`
          },
          {
            role: 'user', 
            content: `Query: "${query}"`
          }
        ],
        temperature: 0.1,
      });

      let strategy = result.text.trim().toLowerCase();
      
      // Clean markdown code blocks if present
      if (strategy.startsWith('```')) {
        strategy = strategy.replace(/^```\w*\s*/, '').replace(/\s*```$/, '');
      }
      
      // Extract just the strategy word
      strategy = strategy.replace(/[^a-z]/g, '');
      
      return ['text', 'semantic', 'hybrid'].includes(strategy) 
        ? strategy as 'text' | 'semantic' | 'hybrid'
        : 'semantic'; // Default fallback
    } catch (error) {
      console.warn('LLM search strategy analysis failed, using semantic fallback:', error);
      return 'semantic';
    }
  }

  /**
   * Calculate relevance score using LLM analysis instead of hardcoded rules
   */
  static async calculateRelevanceScore(searchResult: any, userQuery: string): Promise<LLMRelevanceScore> {
    try {
      const result = await generateText({
        model: myProvider.languageModel('chat-model'),
        messages: [
          {
            role: 'system',
            content: `You are an expert at scoring relevance between search results and user queries for MODFLOW repositories.

            Given a search result and user query, provide:
            1. A relevance score from 0.0 to 1.0 (where 1.0 is perfectly relevant)
            2. A brief reasoning for the score

            Consider:
            - How well the file content matches the user's intent
            - Whether the file contains the specific information requested
            - The quality and usefulness of the code/content for the user's needs
            - The file's role in typical MODFLOW workflows
            - Whether this would help the user accomplish their goal

            Respond in JSON format:
            {
              "score": 0.85,
              "reasoning": "Brief explanation of why this file is relevant"
            }`
          },
          {
            role: 'user',
            content: `User Query: "${userQuery}"
            
            Search Result:
            - Filename: ${searchResult.filename}
            - Repository: ${searchResult.repo_name}
            - Path: ${searchResult.filepath}
            - Content Snippet: ${searchResult.snippet}
            ${searchResult.similarity ? `- Original Similarity: ${searchResult.similarity}` : ''}`
          }
        ],
        temperature: 0.2,
      });

      // Clean the response text - remove markdown code blocks if present
      let cleanText = result.text.trim();
      if (cleanText.startsWith('```json')) {
        cleanText = cleanText.replace(/^```json\s*/, '').replace(/\s*```$/, '');
      } else if (cleanText.startsWith('```')) {
        cleanText = cleanText.replace(/^```\s*/, '').replace(/\s*```$/, '');
      }

      return JSON.parse(cleanText);
    } catch (error) {
      console.warn('LLM relevance scoring failed, using fallback:', error);
      // Fallback to original similarity if LLM parsing fails
      return {
        score: searchResult.similarity || 0.5,
        reasoning: "LLM analysis unavailable, using original similarity"
      };
    }
  }

  /**
   * Determine if tool should be called based on LLM analysis
   */
  static async shouldCallTool(toolName: string, userQuery: string, context?: any): Promise<{ shouldCall: boolean; confidence: number; reasoning: string }> {
    try {
      const result = await generateText({
        model: myProvider.languageModel('chat-model'),
        messages: [
          {
            role: 'system',
            content: `You are an expert at determining when to call specific tools for MODFLOW repository queries.

            Available tools:
            - "listRepositories": Shows available MODFLOW repositories with descriptions
            - "mfaiSearch": Searches through repository content (text or semantic search)
            - "createDocument": Creates enhanced documentation from search results

            Given a user query and tool name, determine:
            1. shouldCall: boolean - Should this tool be called for this query?
            2. confidence: number - How confident are you? (0.0-1.0)  
            3. reasoning: string - Brief explanation of your decision

            Consider:
            - User's actual intent and needs
            - Whether the tool would provide valuable information
            - If the user is asking for something the tool can provide
            - Context from previous interactions

            Respond in JSON format with these exact field names.`
          },
          {
            role: 'user',
            content: `Tool: "${toolName}"
            User Query: "${userQuery}"
            ${context ? `Context: ${JSON.stringify(context)}` : ''}`
          }
        ],
        temperature: 0.1,
      });

      // Clean the response text - remove markdown code blocks if present
      let cleanText = result.text.trim();
      if (cleanText.startsWith('```json')) {
        cleanText = cleanText.replace(/^```json\s*/, '').replace(/\s*```$/, '');
      } else if (cleanText.startsWith('```')) {
        cleanText = cleanText.replace(/^```\s*/, '').replace(/\s*```$/, '');
      }

      return JSON.parse(cleanText);
    } catch (error) {
      console.warn('LLM tool calling analysis failed, using conservative fallback:', error);
      return {
        shouldCall: false,
        confidence: 0.3,
        reasoning: 'LLM analysis failed, defaulting to not calling tool'
      };
    }
  }
}