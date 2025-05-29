# MCP AI SDK Test Client Implementation Roadmap

*Created: May 29, 2025*

## Overview

This roadmap outlines the implementation of a test client using the Vercel AI SDK to test our MCP server endpoints (both HTTP and SSE) deployed on Cloudflare Workers.

## Objectives

1. **Validate MCP Server Integration**: Test our server with the official AI SDK MCP client
2. **Test Both Transports**: Verify both SSE and HTTP endpoints work correctly
3. **Tool Discovery**: Ensure tools are properly exposed and callable
4. **Authentication**: Test Bearer token authentication flows
5. **Create Examples**: Build reusable examples for future implementations

## Prerequisites

- Node.js 18+
- Working MCP server at `https://mfai-repository-navigator.little-grass-273a.workers.dev`
- Valid API key for authentication
- Vercel AI SDK with MCP support

## Implementation Plan

### Phase 1: Project Setup (Day 1)

#### 1.1 Initialize Test Project
```bash
cd /home/danilopezmella/mfai_db_repos/tests/mcp_aisdk
npm init -y
npm install ai @ai-sdk/openai zod dotenv
npm install -D typescript @types/node tsx
```

#### 1.2 Project Structure
```
mcp_aisdk/
├── src/
│   ├── test-sse-client.ts      # SSE transport tests
│   ├── test-http-client.ts     # HTTP transport tests (if supported)
│   ├── test-tool-discovery.ts  # Tool discovery and listing
│   ├── test-tool-calling.ts    # Tool execution tests
│   ├── test-auth.ts            # Authentication tests
│   └── utils/
│       ├── client-factory.ts   # MCP client factory
│       └── test-helpers.ts     # Test utilities
├── examples/
│   ├── basic-search.ts         # Basic search example
│   ├── repository-listing.ts   # List repositories example
│   └── combined-workflow.ts    # Complex workflow example
├── .env.example
├── .env
├── package.json
├── tsconfig.json
└── README.md
```

#### 1.3 Configuration Files

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**.env.example:**
```env
MCP_API_KEY=your_api_key_here
MCP_SERVER_URL=https://mfai-repository-navigator.little-grass-273a.workers.dev
OPENAI_API_KEY=your_openai_key_here  # If needed for AI SDK features
```

### Phase 2: Core Implementation (Day 2)

#### 2.1 Client Factory Implementation
Create a reusable factory for MCP client initialization with both SSE and HTTP support.

```typescript
// src/utils/client-factory.ts
import { experimental_createMCPClient as createMCPClient } from 'ai';

export async function createSSEClient(apiKey: string, serverUrl: string) {
  return await createMCPClient({
    transport: {
      type: 'sse',
      url: `${serverUrl}/sse`,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    },
  });
}
```

#### 2.2 SSE Transport Tests
Test the SSE endpoint with proper authentication and tool discovery.

```typescript
// src/test-sse-client.ts
import { createSSEClient } from './utils/client-factory';
import dotenv from 'dotenv';

dotenv.config();

async function testSSEConnection() {
  const client = await createSSEClient(
    process.env.MCP_API_KEY!,
    process.env.MCP_SERVER_URL!
  );
  
  // Test tool discovery
  const tools = await client.listTools();
  console.log('Available tools:', tools);
  
  // Close client after use
  await client.close();
}
```

#### 2.3 Tool Discovery Tests
Validate that our MCP tools are properly exposed.

```typescript
// src/test-tool-discovery.ts
async function testToolDiscovery() {
  const client = await createSSEClient(...);
  
  const tools = await client.listTools();
  
  // Validate expected tools
  const expectedTools = ['list_repositories_with_navigation', 'mfai_search'];
  const foundTools = tools.map(t => t.name);
  
  expectedTools.forEach(toolName => {
    if (foundTools.includes(toolName)) {
      console.log(`✅ Found tool: ${toolName}`);
    } else {
      console.error(`❌ Missing tool: ${toolName}`);
    }
  });
}
```

#### 2.4 Tool Calling Tests
Test actual tool execution with our MCP server.

```typescript
// src/test-tool-calling.ts
async function testToolCalling() {
  const client = await createSSEClient(...);
  
  // Test list_repositories_with_navigation
  const repoResult = await client.callTool('list_repositories_with_navigation', {
    include_navigation: true
  });
  
  // Test mfai_search
  const searchResult = await client.callTool('mfai_search', {
    query: 'modflow',
    search_type: 'text'
  });
  
  console.log('Repository listing:', repoResult);
  console.log('Search results:', searchResult);
}
```

### Phase 3: Advanced Examples (Day 3)

#### 3.1 AI-Powered Search Example
Integrate MCP tools with AI models for intelligent search.

```typescript
// examples/ai-powered-search.ts
import { openai } from '@ai-sdk/openai';
import { generateText } from 'ai';

async function aiPoweredSearch(userQuery: string) {
  const client = await createSSEClient(...);
  
  // Use AI to determine search type
  const searchStrategy = await generateText({
    model: openai('gpt-3.5-turbo'),
    prompt: `Determine if this query needs 'text' or 'semantic' search: "${userQuery}"`,
  });
  
  // Execute search with MCP tool
  const results = await client.callTool('mfai_search', {
    query: userQuery,
    search_type: searchStrategy.text.includes('semantic') ? 'semantic' : 'text'
  });
  
  return results;
}
```

#### 3.2 Repository Analysis Workflow
Complex workflow combining multiple tools.

```typescript
// examples/repository-analysis.ts
async function analyzeRepositories() {
  const client = await createSSEClient(...);
  
  // 1. List all repositories
  const repos = await client.callTool('list_repositories_with_navigation', {
    include_navigation: true
  });
  
  // 2. Search for specific patterns in each repo
  const analysisResults = [];
  for (const repo of repos) {
    const searchResult = await client.callTool('mfai_search', {
      query: 'groundwater model',
      search_type: 'semantic',
      repositories: [repo.name]
    });
    
    analysisResults.push({
      repository: repo.name,
      findings: searchResult
    });
  }
  
  return analysisResults;
}
```

### Phase 4: Testing & Validation (Day 4)

#### 4.1 Test Suite Structure
```
tests/
├── integration/
│   ├── sse-connection.test.ts
│   ├── tool-discovery.test.ts
│   ├── tool-calling.test.ts
│   └── auth.test.ts
├── performance/
│   ├── latency.test.ts
│   └── throughput.test.ts
└── edge-cases/
    ├── error-handling.test.ts
    └── timeout.test.ts
```

#### 4.2 Key Test Scenarios

1. **Connection Tests**
   - SSE connection establishment
   - Authentication validation
   - Connection persistence
   - Reconnection handling

2. **Tool Tests**
   - Tool discovery accuracy
   - Parameter validation
   - Response format validation
   - Error handling

3. **Performance Tests**
   - Response time measurements
   - Concurrent request handling
   - Memory usage tracking

4. **Edge Cases**
   - Invalid authentication
   - Malformed requests
   - Network interruptions
   - Large response handling

### Phase 5: Documentation (Day 5)

#### 5.1 README Structure
- Installation guide
- Configuration instructions
- Example usage
- API reference
- Troubleshooting guide

#### 5.2 Example Documentation
- Basic usage examples
- Advanced workflows
- Integration patterns
- Best practices

#### 5.3 API Documentation
- Tool schemas
- Response formats
- Error codes
- Rate limits

## Success Metrics

1. **Functional Success**
   - ✅ All MCP tools discoverable via AI SDK
   - ✅ Successful tool execution with correct parameters
   - ✅ Proper authentication flow
   - ✅ SSE connection stability

2. **Performance Metrics**
   - Response time < 3 seconds for searches
   - Connection establishment < 1 second
   - 99% uptime during tests

3. **Documentation Coverage**
   - All functions documented
   - 5+ working examples
   - Complete troubleshooting guide

## Risk Mitigation

1. **AI SDK Compatibility**
   - Risk: Version incompatibilities
   - Mitigation: Pin specific versions, test multiple versions

2. **SSE Connection Issues**
   - Risk: Connection drops or timeouts
   - Mitigation: Implement retry logic, connection monitoring

3. **Authentication Challenges**
   - Risk: Token format mismatches
   - Mitigation: Test multiple auth strategies

4. **Rate Limiting**
   - Risk: Test suite hits rate limits
   - Mitigation: Implement throttling, use test-specific limits

## Timeline

- **Day 1**: Project setup and configuration
- **Day 2**: Core implementation (client factory, basic tests)
- **Day 3**: Advanced examples and workflows
- **Day 4**: Comprehensive testing and validation
- **Day 5**: Documentation and finalization

## Dependencies

```json
{
  "dependencies": {
    "ai": "^3.x",
    "@ai-sdk/openai": "^0.x",
    "zod": "^3.x",
    "dotenv": "^16.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "@types/node": "^20.x",
    "tsx": "^4.x",
    "vitest": "^1.x"
  }
}
```

## Next Steps

1. [ ] Create project directory structure
2. [ ] Install dependencies
3. [ ] Implement client factory
4. [ ] Create basic SSE test
5. [ ] Test tool discovery
6. [ ] Implement tool calling tests
7. [ ] Build example workflows
8. [ ] Write comprehensive tests
9. [ ] Document everything
10. [ ] Create demo video/screenshots

## Notes

- The AI SDK's MCP support is experimental, so API changes are possible
- Focus on SSE transport as it's most compatible with our Cloudflare Worker
- Ensure all tests can run in CI/CD environments
- Consider creating a separate test API key with limited permissions

## References

- [Vercel AI SDK MCP Documentation](https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling#mcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Our MCP Server Documentation](/mfai_mcp_server_cloudflare/README.md)