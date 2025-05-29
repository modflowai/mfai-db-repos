# MCP AI SDK Test Client

This test client validates the integration between our MCP server (deployed on Cloudflare Workers) and the Vercel AI SDK's MCP client capabilities.

## Purpose

- Test SSE transport connectivity with our MCP server
- Validate tool discovery and execution
- Demonstrate authentication flows
- Provide working examples for developers

## Quick Start

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API key
   ```

3. **Run tests:**
   ```bash
   # Test SSE connection
   npm run test:sse

   # Test tool discovery
   npm run test:tools

   # Run all tests
   npm test
   ```

## Project Structure

```
mcp_aisdk/
├── src/              # Test implementations
├── examples/         # Usage examples
├── tests/           # Formal test suites
├── roadmap.md       # Implementation roadmap
└── README.md        # This file
```

## Available Tests

- **SSE Connection**: Validates Server-Sent Events transport
- **Tool Discovery**: Lists available MCP tools
- **Tool Calling**: Executes tools with parameters
- **Authentication**: Tests Bearer token flows
- **Examples**: Real-world usage patterns

## MCP Server Endpoints

- **Production**: `https://mfai-repository-navigator.little-grass-273a.workers.dev`
- **SSE Endpoint**: `/sse`
- **HTTP Endpoint**: `/mcp`

## Tools Available

1. **list_repositories_with_navigation**
   - Lists all indexed repositories
   - Includes AI-generated navigation guides

2. **mfai_search**
   - Text or semantic search
   - Repository filtering
   - Returns relevant code snippets

## Authentication

The server requires Bearer token authentication:

```typescript
const client = await createMCPClient({
  transport: {
    type: 'sse',
    url: 'https://mfai-repository-navigator.little-grass-273a.workers.dev/sse',
    headers: {
      'Authorization': 'Bearer your_api_key_here'
    }
  }
});
```

## Development

See [roadmap.md](./roadmap.md) for the complete implementation plan.

## License

Part of the MFAI DB Repos project.