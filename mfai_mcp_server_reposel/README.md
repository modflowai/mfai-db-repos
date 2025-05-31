# MFAI Repository Selector MCP Server

An intelligent MCP server that uses Google GenAI to analyze user queries against repository navigation guides and suggest the most relevant repository for searching.

## Overview

This server provides an AI-powered `mfai_repository_selector` tool that replaces the traditional `list_repositories_with_navigation` approach with intelligent repository selection based on user queries and conversation context.

## Features

- **AI-Powered Selection**: Uses Google GenAI (Gemini 2.0 Flash) to analyze queries against navigation guides
- **Structured Output**: Uses Gemini's responseSchema for guaranteed clean JSON responses
- **Modular Architecture**: Clean separation of services, handlers, and utilities for easy testing
- **Confidence Scoring**: Provides confidence levels for repository selections
- **Alternative Suggestions**: Offers alternative repositories when relevant
- **User Confirmation**: Generates contextual confirmation questions
- **Database Integration**: Connects to existing MFAI repository database
- **Error Handling**: Proper error propagation without fallbacks for testing

## Installation

```bash
cd /home/danilopezmella/mfai_db_repos/mfai_mcp_server_reposel
npm install
npm run build
```

## MCP Client Configuration

Add this server to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "mfai-repository-selector": {
      "command": "node",
      "args": [
        "/home/danilopezmella/mfai_db_repos/mfai_mcp_server_reposel/build/index.js"
      ],
      "cwd": "/home/danilopezmella/mfai_db_repos/mfai_mcp_server_reposel",
      "env": {
        "MODFLOW_AI_MCP_00_CONNECTION_STRING": "your_postgres_connection_string",
        "GOOGLE_GENAI_API_KEY": "your_google_genai_api_key"
      }
    }
  }
}
```

## Environment Variables

The required environment variables are provided through the MCP client configuration:

- `MODFLOW_AI_MCP_00_CONNECTION_STRING`: PostgreSQL connection string
- `GOOGLE_GENAI_API_KEY`: Google GenAI API key

## Usage

### Running the Server

```bash
npm start
```

### Tool Usage

The server provides one tool: `mfai_repository_selector`

#### Input Schema

```json
{
  "query": "string (required) - The user's question or search query",
  "context": "string (optional) - Additional conversation context"
}
```

#### Example Call

```json
{
  "method": "tools/call",
  "params": {
    "name": "mfai_repository_selector",
    "arguments": {
      "query": "What is PEST-IES?",
      "context": "User is asking about parameter estimation methods"
    }
  }
}
```

#### Example Response

```json
{
  "selected_repository": "pestpp",
  "confidence": 0.95,
  "reasoning": "Query mentions PEST-IES, which refers to PESTPP-IES documented in pestpp repository",
  "alternatives": ["pest", "pyemu"],
  "user_confirmation": "Should I search the 'pestpp' repository for information about PEST-IES?"
}
```

## Test Cases

You can test the server with these example queries (environment variables must be set in the MCP client):

```bash
# Test PEST-IES query
echo '{"method": "tools/call", "params": {"name": "mfai_repository_selector", "arguments": {"query": "What is PEST-IES?"}}}' | npm start

# Test MODFLOW 6 query
echo '{"method": "tools/call", "params": {"name": "mfai_repository_selector", "arguments": {"query": "MODFLOW 6 well package"}}}' | npm start

# Test FloPy query
echo '{"method": "tools/call", "params": {"name": "mfai_repository_selector", "arguments": {"query": "FloPy grid generation"}}}' | npm start

# Test parameter estimation query
echo '{"method": "tools/call", "params": {"name": "mfai_repository_selector", "arguments": {"query": "parameter estimation uncertainty"}}}' | npm start
```

## Expected Query → Repository Mappings

- "What is PEST-IES?" → `pestpp`
- "MODFLOW 6 well package" → `mf6`
- "FloPy grid generation" → `flopy`
- "parameter estimation uncertainty" → `pest` or `pyemu`

## API Integration

This server is designed to work with existing MCP clients and can be integrated into chat applications that need intelligent repository selection capabilities.

### Response Structure

All responses follow this structure:

```typescript
interface RepositorySelection {
  selected_repository: string;    // Name of the selected repository
  confidence: number;             // Confidence score (0.0 - 1.0)
  reasoning: string;              // Explanation for the selection
  alternatives: string[];         // Alternative repository names
  user_confirmation: string;      // Question for user confirmation
}
```

## Error Handling

The server handles various error scenarios:

- Missing environment variables
- Database connection failures
- GenAI API errors
- Invalid navigation guide data
- JSON parsing errors

All errors return structured error responses with appropriate error messages.

## Development

### Build and Watch

```bash
npm run build    # Build once
npm run watch    # Build and watch for changes
npm run dev      # Build and run
```

### Dependencies

- `@modelcontextprotocol/sdk`: MCP protocol implementation
- `@neondatabase/serverless`: Database connection
- `@google/generative-ai`: Google GenAI SDK
- `zod`: Input validation and type safety

## Architecture

The server follows the established MCP server pattern used in the existing MFAI infrastructure:

1. **Database Layer**: Connects to PostgreSQL with repository metadata
2. **AI Layer**: Uses Google GenAI for intelligent selection
3. **MCP Layer**: Implements standard MCP protocol for tool communication
4. **Validation Layer**: Uses Zod for input validation and type safety

## Integration Notes

This server is designed to replace the `list_repositories_with_navigation` tool in existing workflows while maintaining compatibility with the established database schema and MCP protocol patterns.

## Project Structure

```
src/
├── index.ts                           # Main MCP server entry point
└── lib/
    ├── handlers/
    │   └── repository-selector.ts     # Main request handler and validation
    └── services/
        └── gemini-service.ts          # Google GenAI integration service
```

### Key Components

- **GeminiService**: Handles Google GenAI API calls with structured output using responseSchema
- **RepositorySelectorHandler**: Coordinates database queries and AI service calls
- **Structured Output**: Uses Gemini's built-in JSON schema validation for reliable responses