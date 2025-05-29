# MCP AI SDK Test Client

A comprehensive test client for the MFAI MCP server using the Vercel AI SDK. This client provides tools for testing, benchmarking, and integrating with the MODFLOW AI repository navigator.

## Features

- 🚀 **SSE (Server-Sent Events) Support** - Real-time communication with Cursor IDE compatibility
- 🔍 **Full MCP Tool Support** - Repository listing and semantic/text search capabilities
- 🧪 **Comprehensive Test Suite** - Connection, tool discovery, and integration tests
- 🤖 **AI Integration** - Examples using Google's Gemini 2.0 Flash model
- 📊 **Performance Benchmarks** - Track and measure API response times
- 🔐 **Multiple Auth Strategies** - Bearer token, X-API-Key, and query parameter auth

## Prerequisites

- Node.js 18+
- npm or pnpm
- Access to the MFAI MCP server
- API keys for:
  - MCP Server (`MCP_API_KEY`)
  - Google Generative AI (`GOOGLE_GENERATIVE_AI_API_KEY`)

## Installation

1. Clone the repository:
```bash
cd /home/danilopezmella/mfai_db_repos/tests/mcp_aisdk
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Edit `.env` file with your credentials:

```env
# Server Configuration
MCP_SERVER_URL=https://mfai-repository-navigator.little-grass-273a.workers.dev
MCP_API_KEY=your_mcp_api_key_here

# Test Configuration
TEST_REPOSITORY_NAME=modflowapi
TEST_SEARCH_QUERY=groundwater model
TEST_TIMEOUT_MS=30000

# AI SDK Configuration
GOOGLE_GENERATIVE_AI_API_KEY=your_google_api_key_here
CHAT_MODEL=gemini-2.0-flash-001
```

## Usage

### Running Tests

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:sse          # Connection tests
npm run test:tools        # Tool discovery tests
npm run test:integration  # Full integration tests
```

### Running Examples

```bash
# Basic usage example
npm run example:basic

# AI-powered repository analysis
npm run example:search
```

### Performance Benchmarks

```bash
npm run benchmark
```

### Type Checking and Linting

```bash
npm run typecheck
npm run lint
```

## Project Structure

```
src/
├── clients/
│   ├── client-factory.ts    # SSE client creation
│   └── ...
├── tools/
│   └── tool-schemas.ts      # Zod schemas for MCP tools
├── tests/
│   ├── connection/          # SSE connection tests
│   ├── tools/              # Tool discovery tests
│   └── integration/        # End-to-end tests
├── examples/
│   ├── basic-usage.ts      # Simple usage example
│   └── ai-repository-analysis.ts  # AI integration example
└── utils/
    └── ...
```

## Available MCP Tools

### 1. `list_repositories_with_navigation`
Lists all repositories with optional navigation guides.

**Parameters:**
- `include_navigation` (boolean, default: true) - Include navigation guides

**Example:**
```typescript
const result = await client.callTool('list_repositories_with_navigation', {
  include_navigation: true
});
```

### 2. `mfai_search`
Search across all indexed repositories using text or semantic search.

**Parameters:**
- `query` (string) - Search query
- `search_type` ('text' | 'semantic') - Type of search
- `repositories` (string[], optional) - Filter by repository names

**Example:**
```typescript
const result = await client.callTool('mfai_search', {
  query: 'groundwater flow simulation',
  search_type: 'semantic',
  repositories: ['modflowapi', 'flopy']
});
```

## Test Coverage

- ✅ SSE connection establishment
- ✅ Authentication strategies
- ✅ Tool discovery and validation
- ✅ Repository listing (with/without navigation)
- ✅ Text search functionality
- ✅ Semantic search with embeddings
- ✅ Repository-filtered searches
- ✅ Error handling and edge cases
- ✅ Performance benchmarks

## Performance Thresholds

| Operation | Threshold |
|-----------|-----------|
| SSE Connection | 1000ms |
| Tool Discovery | 500ms |
| List Repositories | 3000ms |
| Text Search | 3000ms |
| Semantic Search | 5000ms |

## AI Integration

The test client includes examples of integrating with Google's Gemini 2.0 Flash model for:

- Analyzing repository navigation guides
- Identifying MODFLOW features
- Cross-repository pattern detection
- Semantic understanding of code structures

## Troubleshooting

### Connection Issues
- Verify `MCP_API_KEY` is set correctly
- Check server URL is accessible
- Ensure API key has proper permissions

### Test Failures
- Check `.env` configuration
- Verify server is running
- Review error messages for specific issues

### Performance Issues
- Check network connectivity
- Verify server response times
- Consider implementing caching for repeated queries

## Development

### Adding New Tests

1. Create test file in appropriate directory
2. Import necessary utilities:
```typescript
import { createSSEClient } from '@/clients/client-factory';
import { expect, test, describe } from 'vitest';
```

3. Write tests following existing patterns

### Extending Tool Support

1. Update `tool-schemas.ts` with new schemas
2. Add tests for new tools
3. Update documentation

## Contributing

1. Follow existing code patterns
2. Add tests for new features
3. Update documentation
4. Run type checking and tests before submitting

## Related Documentation

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Vercel AI SDK Documentation](https://ai-sdk.dev/)
- [MFAI MCP Server Documentation](../../mfai_mcp_server_cloudflare/README.md)
- [Original Roadmap](./roadmap.md)
- [Implementation Roadmap v2](./roadmap-v2.md)

## License

Part of the MFAI DB Repos project.