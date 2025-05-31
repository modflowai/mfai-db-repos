# MFAI MCP Server Repository Selector - Detailed Roadmap

## Project Overview

Create a new local MCP server (`mfai_mcp_server_reposel`) that provides intelligent repository selection using Google GenAI JS SDK. This server will replace the current `list_repositories_with_navigation` tool with an AI-powered `mfai_repository_selector` that analyzes user queries against navigation guides to suggest the most relevant repository.

## Project Structure

```
/home/danilopezmella/mfai_db_repos/mfai_mcp_server_reposel/
├── README.md                    # Project documentation
├── package.json                 # Dependencies and scripts
├── package-lock.json            # Dependency lock file
├── tsconfig.json                # TypeScript configuration
├── src/
│   └── index.ts                 # Main MCP server entry point
├── dist/                        # Compiled JavaScript output
└── .env                         # Environment variables
```

## Phase 1: Project Setup and Infrastructure

### 1.1 Create Project Directory and Basic Structure
- Create `/home/danilopezmella/mfai_db_repos/mfai_mcp_server_reposel/` directory
- Reference: Copy structure from `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/`

### 1.2 Package Configuration
File: `package.json`
- Copy from `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/package.json`
- Add Google GenAI JS SDK dependency: `@google/genai`
- Keep existing dependencies:
  - `@modelcontextprotocol/sdk`
  - `@neondatabase/serverless`
  - `zod`

### 1.3 TypeScript Configuration
File: `tsconfig.json`
- Copy from `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/tsconfig.json`
- No modifications needed - already compatible with Google GenAI SDK

### 1.4 Environment Configuration
File: `.env`
```env
MODFLOW_AI_MCP_00_CONNECTION_STRING=your_connection_string
GOOGLE_GENAI_API_KEY=your_google_api_key
```

## Phase 2: Database Integration

### 2.1 Database Connection Setup
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts` lines 14-23

**Connection code:**
```typescript
import { neon } from '@neondatabase/serverless';

const DATABASE_URL = process.env.MODFLOW_AI_MCP_00_CONNECTION_STRING;
const sql = neon(DATABASE_URL);
```

### 2.2 Repository Data Query
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts` lines 107-120

**Query for repositories with navigation guides:**
```sql
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
```

## Phase 3: Google GenAI Integration

### 3.1 GenAI Setup
```typescript
import { GoogleGenAI } from '@google/genai';

const GOOGLE_GENAI_API_KEY = process.env.GOOGLE_GENAI_API_KEY;
const genai = new GoogleGenAI({ apiKey: GOOGLE_GENAI_API_KEY });
```

### 3.2 Repository Selection Function
```typescript
async function selectRepository(query: string, repositories: any[]) {
  const prompt = `You are an expert assistant that helps users find the most relevant repository...
  
  REPOSITORIES:
  ${JSON.stringify(repositories, null, 2)}
  
  USER QUERY: ${query}
  
  Return JSON:
  {
    "selected_repository": "repo_name",
    "confidence": 0.95,
    "reasoning": "explanation",
    "alternatives": ["repo2"],
    "user_confirmation": "question for user"
  }`;
  
  const response = await genai.models.generateContent({
    model: 'gemini-2.0-flash-001',
    contents: prompt,
    config: {
      temperature: 0.2,
      maxOutputTokens: 1000
    }
  });
  
  return JSON.parse(response.text);
}
```

## Phase 4: Main Server Implementation

### 4.1 Main Server File
File: `src/index.ts`
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts`

**Key imports:**
```typescript
#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { neon } from '@neondatabase/serverless';
import { GoogleGenAI } from '@google/genai';
```

### 4.2 Tool Registration
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts` lines 51-94

**Tool definition:**
```typescript
{
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
}
```

### 4.3 Tool Handler Implementation
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts` lines 97-289

**Handler structure:**
```typescript
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'mfai_repository_selector': {
        const { query, context } = RepositorySelectorSchema.parse(args);
        
        // 1. Get repositories with navigation guides
        const repositories = await sql`
          SELECT 
            id, 
            name, 
            url, 
            file_count,
            metadata->>'navigation_guide' as navigation_guide,
            metadata->>'repository_type' as repository_type
          FROM repositories
          WHERE metadata->>'navigation_guide' IS NOT NULL
          ORDER BY id ASC
        `;
        
        // 2. Use GenAI to select best repository
        const selection = await selectRepository(query, repositories);
        
        // 3. Return structured response
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(selection, null, 2),
            },
          ],
        };
      }
      
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            error: error instanceof Error ? error.message : 'Unknown error',
            tool: name,
          }, null, 2),
        },
      ],
      isError: true,
    };
  }
});
```

### 4.4 Server Startup
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts` lines 292-301

**Startup code:**
```typescript
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MFAI Repository Selector MCP Server started');
}

main().catch((error) => {
  console.error('Fatal error starting server:', error);
  process.exit(1);
});
```

## Phase 5: Input Schema and Validation

### 5.1 Input Schema Definition
```typescript
const RepositorySelectorSchema = z.object({
  query: z.string().describe('User\'s question or search query'),
  context: z.string().optional().describe('Optional conversation context'),
});
```

### 5.2 Error Handling
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts` error handling pattern

**Error scenarios:**
- Missing environment variables
- Database connection failures
- GenAI API errors
- Invalid navigation guide data
- JSON parsing errors

## Phase 6: Testing and Validation

### 6.1 Test Environment Setup
```bash
# Environment variables needed
export MODFLOW_AI_MCP_00_CONNECTION_STRING="your_connection_string"
export GOOGLE_GENAI_API_KEY="your_google_api_key"
```

### 6.2 Build and Run Commands
Reference: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/` build process

```bash
# Build the project
npm run build

# Run the server
npm start

# Test with input
echo '{"method": "tools/call", "params": {"name": "mfai_repository_selector", "arguments": {"query": "What is PEST-IES?"}}}' | npm start
```

### 6.3 Test Cases
**Expected query → repository mappings:**
- "What is PEST-IES?" → `pestpp`
- "MODFLOW 6 well package" → `mf6`
- "FloPy grid generation" → `flopy`
- "parameter estimation uncertainty" → `pest` or `pyemu`

### 6.4 Response Format Validation
**Expected response structure:**
```json
{
  "selected_repository": "pestpp",
  "confidence": 0.95,
  "reasoning": "Query mentions PEST-IES, which refers to PESTPP-IES documented in pestpp repository",
  "alternatives": ["pest", "pyemu"],
  "user_confirmation": "Should I search the 'pestpp' repository for information about PEST-IES?"
}
```

## Phase 7: Documentation

### 7.1 README Documentation
File: `README.md`

**Content sections:**
- Project purpose and functionality
- Installation and setup instructions
- Environment variable configuration
- Usage examples with test queries
- Tool schema documentation
- Troubleshooting common issues

### 7.2 Usage Examples
**MCP tool call example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "mfai_repository_selector",
    "arguments": {
      "query": "How to set up PEST parameter estimation?",
      "context": "User working on groundwater model calibration"
    }
  }
}
```

## Reference Files

### Core Implementation Reference
- `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts`: Complete working MCP server with database connection
- `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/package.json`: Required dependencies
- `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/tsconfig.json`: TypeScript configuration

### Database Reference
- Lines 14-23: Environment and database setup
- Lines 107-120: Repository query with navigation guides
- Lines 97-289: Tool handler pattern and error handling

### Current Navigation System
- `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts`: Working stdio MCP server with navigation guide retrieval (lines 107-120)

## Success Criteria

### Functional Requirements
- Tool connects to existing database using `MODFLOW_AI_MCP_00_CONNECTION_STRING`
- Retrieves repositories with navigation guides successfully
- Integrates Google GenAI JS SDK for repository selection
- Returns structured JSON responses with confidence scores
- Handles errors gracefully with appropriate error messages

### Technical Requirements
- Follows MCP protocol using stdio transport
- Uses existing database connection pattern from reference server
- Maintains TypeScript type safety
- Implements proper async/await error handling
- Provides meaningful user confirmation questions

### Quality Requirements
- Code follows patterns from `/home/danilopezmella/mfai_db_repos/mfai_mcp_server/src/index.ts`
- Includes clear documentation and usage examples
- Response times under 3 seconds for repository selection
- Consistent JSON response format
- Proper environment variable validation

This roadmap leverages the existing working MCP server structure and database connection patterns, focusing on adding Google GenAI intelligence for repository selection while maintaining compatibility with the established architecture.