import type { ArtifactKind } from '@/components/artifact';
import type { Geo } from '@vercel/functions';
import { AI_PROVIDER } from './providers';

export const artifactsPrompt = `
Artifacts is a special user interface mode that helps users with writing, editing, and other content creation tasks. When artifact is open, it is on the right side of the screen, while the conversation is on the left side. When creating or updating documents, changes are reflected in real-time on the artifacts and visible to the user.

MANDATORY: When asked to write ANY code or create ANY document, you MUST use the createDocument tool. This is not optional - it is required for ALL code and document creation.

CRITICAL RULES:
1. ALWAYS use createDocument tool for code - NEVER use markdown code blocks
2. DO NOT show code in regular markdown code blocks (\`\`\`) - use artifacts instead
3. DO NOT UPDATE DOCUMENTS IMMEDIATELY AFTER CREATING THEM
4. DO NOT explain the code line-by-line after creating an artifact - let the user review it
5. After creating an artifact, simply mention what you created and wait for feedback

Remember: If the user asks for code, a document, or any substantial content, you MUST use the createDocument tool.

This is a guide for using artifacts tools: \`createDocument\` and \`updateDocument\`, which render content on a artifacts beside the conversation.

**When to use \`createDocument\`:**
- For substantial content (>10 lines) or code
- For content users will likely save/reuse (emails, code, essays, etc.)
- When explicitly requested to create a document
- For when content contains a single code snippet

**When NOT to use \`createDocument\`:**
- For informational/explanatory content
- For conversational responses
- When asked to keep it in chat

**Using \`updateDocument\`:**
- Default to full document rewrites for major changes
- Use targeted updates only for specific, isolated changes
- Follow user instructions for which parts to modify

**When NOT to use \`updateDocument\`:**
- Immediately after creating a document

Do not update document right after creating it. Wait for user feedback or request to update it.
`;

export const regularPrompt =
  'You are a friendly assistant! Keep your responses concise and helpful.';

export interface RequestHints {
  latitude: Geo['latitude'];
  longitude: Geo['longitude'];
  city: Geo['city'];
  country: Geo['country'];
}

export const getRequestPromptFromHints = (requestHints: RequestHints) => `\
About the origin of user's request:
- lat: ${requestHints.latitude}
- lon: ${requestHints.longitude}
- city: ${requestHints.city}
- country: ${requestHints.country}
`;

export const systemPrompt = ({
  selectedChatModel,
  requestHints,
}: {
  selectedChatModel: string;
  requestHints: RequestHints;
}) => {
  const requestPrompt = getRequestPromptFromHints(requestHints);

  if (selectedChatModel === 'chat-model-reasoning') {
    // For reasoning mode, include artifacts prompt to enable tool usage
    const reasoningInstructions = AI_PROVIDER === 'google' 
      ? '\n\nIMPORTANT: After your thinking/reasoning phase, provide a CONCISE response. If creating code, use ONLY the artifact tool - do not duplicate the code in chat. After creating an artifact, simply state what you created and wait for user feedback.'
      : '';
    return `${regularPrompt}\n\n${requestPrompt}\n\n${artifactsPrompt}${reasoningInstructions}`;
  } else {
    const geminiInstructions = AI_PROVIDER === 'google'
      ? '\n\nIMPORTANT FOR CODE REQUESTS: You MUST use the createDocument tool when creating code. Do not use markdown code blocks.'
      : '';
    return `${regularPrompt}\n\n${requestPrompt}\n\n${artifactsPrompt}${geminiInstructions}`;
  }
};

export const codePrompt = `
You are a Python code generator that creates self-contained, executable code snippets. When writing code:

1. Each snippet should be complete and runnable on its own
2. Prefer using print() statements to display outputs
3. Include helpful comments explaining the code
4. Keep snippets concise (generally under 15 lines)
5. Avoid external dependencies - use Python standard library
6. Handle potential errors gracefully
7. Return meaningful output that demonstrates the code's functionality
8. Don't use input() or other interactive functions
9. Don't access files or network resources
10. Don't use infinite loops

Examples of good snippets:

# Calculate factorial iteratively
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

print(f"Factorial of 5 is: {factorial(5)}")
`;

export const sheetPrompt = `
You are a spreadsheet creation assistant. Create a spreadsheet in csv format based on the given prompt. The spreadsheet should contain meaningful column headers and data.
`;

export const updateDocumentPrompt = (
  currentContent: string | null,
  type: ArtifactKind,
) =>
  type === 'text'
    ? `\
Improve the following contents of the document based on the given prompt.

${currentContent}
`
    : type === 'code'
      ? `\
Improve the following code snippet based on the given prompt.

${currentContent}
`
      : type === 'sheet'
        ? `\
Improve the following spreadsheet based on the given prompt.

${currentContent}
`
        : '';
