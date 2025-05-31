import type { DocumentSearchResult } from '../types/response-types.js';

export class DocumentCompressionPrompts {
  static buildCompressionPrompt(
    document: DocumentSearchResult,
    repository: string,
    originalTokenCount: number,
    query: string,
    context?: string
  ): string {
    const contextSection = context ? `
**USER CONTEXT:** "${context}"
**SEARCH QUERY:** "${query}"

Focus compression on content relevant to the user's context, using the search query as a guide.` : `
**SEARCH QUERY:** "${query}"

Focus compression on content directly related to this query.`;

    return `# EXTREME COMPRESSION REQUIRED

You must compress this ${originalTokenCount}-token document to EXACTLY 7000 tokens (28,000 characters).
${contextSection}

**CRITICAL RULES:**
1. **MAXIMUM 7000 tokens output** - This is MANDATORY
2. **Focus 80% on relevant content** - Everything else is secondary  
3. **Cut ruthlessly** - Remove entire sections unrelated to the user's needs
4. **No fluff** - Every sentence must add value to understanding the topic

**COMPRESSION STRATEGY:**
- **Keep 100%**: Direct explanations, examples, parameters, procedures for the topic
- **Keep 50%**: Related technical context needed to understand the topic
- **Keep 10%**: General background only if absolutely critical
- **Remove 100%**: Unrelated sections, verbose explanations, redundant examples

**DOCUMENT TO COMPRESS:**
${document.content}

**OUTPUT FORMAT:**
Return ONLY the compressed content. Start immediately with the document content. No explanations, metadata, or introductions.`;
  }
}