# MCP AI SDK Test Client Implementation Roadmap v2

*Created: May 29, 2025*

## Overview

This roadmap outlines the implementation of a test client using the Vercel AI SDK to test our MCP server endpoints deployed on Cloudflare Workers, leveraging our existing codebase structure and implementations.

## Existing Codebase Integration

### Current MCP Server Implementation
- **Location**: `/home/danilopezmella/mfai_db_repos/mfai_mcp_server_cloudflare/`
- **SSE Implementation**: `src/index-sse.ts`
- **Test Scripts**: `test-sse-prod.js`, `test-prod.js`
- **Authentication**: Bearer token via `MCP_API_KEY`

### Repository Processing System
- **Location**: `/home/danilopezmella/mfai_db_repos/mfai_db_repos/`
- **Core Services**: `core/services/`
- **Database Models**: `lib/database/models.py`
- **File Processing**: `lib/file_processor/`

## Implementation Plan

### Phase 1: Project Setup & Integration

#### 1.1 Directory Structure
```
/home/danilopezmella/mfai_db_repos/tests/mcp_aisdk/
├── src/
│   ├── clients/
│   │   ├── sse-client.ts         # SSE transport implementation
│   │   ├── http-client.ts        # HTTP transport (if needed)
│   │   └── client-factory.ts     # Factory pattern for client creation
│   ├── tools/
│   │   ├── repository-tools.ts   # Repository listing tools
│   │   ├── search-tools.ts       # Search functionality
│   │   └── tool-schemas.ts       # Zod schemas matching server
│   ├── tests/
│   │   ├── connection/           # Connection tests
│   │   ├── authentication/       # Auth flow tests
│   │   ├── tools/               # Tool-specific tests
│   │   └── integration/         # End-to-end tests
│   ├── examples/
│   │   ├── basic-usage.ts       # Simple examples
│   │   ├── advanced-search.ts   # Complex search patterns
│   │   └── ai-integration.ts    # AI SDK integration
│   └── utils/
│       ├── test-data.ts         # Reference to actual DB data
│       ├── server-config.ts     # Server configuration
│       └── auth-helpers.ts      # Authentication utilities
├── docs/
│   ├── API.md                   # API documentation
│   ├── EXAMPLES.md              # Usage examples
│   └── TROUBLESHOOTING.md       # Common issues
├── scripts/
│   ├── setup.sh                 # Setup script
│   ├── test-all.sh             # Run all tests
│   └── benchmark.sh            # Performance tests
├── .env.example
├── .env
├── package.json
├── tsconfig.json
├── vitest.config.ts
├── roadmap.md                   # Original roadmap
├── roadmap-v2.md               # This file
└── README.md
```

#### 1.2 Configuration Files

**package.json:**
```json
{
  "name": "mfai-mcp-aisdk-test",
  "version": "1.0.0",
  "description": "Test client for MFAI MCP server using Vercel AI SDK",
  "scripts": {
    "test": "vitest",
    "test:sse": "tsx src/tests/connection/test-sse.ts",
    "test:tools": "tsx src/tests/tools/test-discovery.ts",
    "test:integration": "tsx src/tests/integration/full-workflow.ts",
    "example:basic": "tsx src/examples/basic-usage.ts",
    "example:search": "tsx src/examples/advanced-search.ts",
    "benchmark": "tsx scripts/benchmark.ts",
    "typecheck": "tsc --noEmit",
    "lint": "eslint src/**/*.ts"
  },
  "dependencies": {
    "ai": "^3.0.0",
    "@ai-sdk/openai": "^0.0.1",
    "zod": "^3.22.0",
    "dotenv": "^16.4.0",
    "eventsource": "^2.0.2"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/eventsource": "^1.1.0",
    "typescript": "^5.3.0",
    "tsx": "^4.0.0",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0",
    "eslint": "^8.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0"
  }
}
```

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "paths": {
      "@/*": ["./src/*"],
      "@server/*": ["../../mfai_mcp_server_cloudflare/src/*"],
      "@core/*": ["../../mfai_db_repos/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**.env.example:**
```env
# Server Configuration
MCP_SERVER_URL=https://mfai-repository-navigator.little-grass-273a.workers.dev
MCP_API_KEY=your_api_key_here

# Test Configuration
TEST_REPOSITORY_NAME=modflowapi
TEST_SEARCH_QUERY=groundwater model
TEST_TIMEOUT_MS=30000

# AI SDK Configuration (optional)
OPENAI_API_KEY=your_openai_key_here
AI_MODEL=gpt-3.5-turbo
```

### Phase 2: Core Implementation

#### 2.1 Tool Schemas (Matching Server Implementation)

**src/tools/tool-schemas.ts:**
```typescript
import { z } from 'zod';

// Match schemas from /mfai_mcp_server_cloudflare/src/index-sse.ts
export const ListRepositoriesSchema = z.object({
  include_navigation: z.boolean().optional().default(true)
    .describe('Include navigation guides in response'),
});

export const SearchFilesSchema = z.object({
  query: z.string().describe('Search query'),
  search_type: z.enum(['text', 'semantic']).describe('Type of search to perform'),
  repositories: z.array(z.string()).optional().describe('Filter by repository names'),
});

// Response schemas based on actual database models
export const RepositorySchema = z.object({
  id: z.number(),
  name: z.string(),
  url: z.string(),
  file_count: z.number(),
  navigation_guide: z.string().optional(),
  repository_type: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const SearchResultSchema = z.object({
  id: z.number(),
  repo_id: z.number(),
  repo_name: z.string(),
  repo_url: z.string(),
  filepath: z.string(),
  filename: z.string(),
  extension: z.string(),
  file_type: z.string(),
  content: z.string(),
  rank: z.number().optional(),
  similarity: z.number().optional(),
  snippet: z.string(),
});
```

#### 2.2 Client Factory (Referencing Existing Test Scripts)

**src/clients/client-factory.ts:**
```typescript
import { experimental_createMCPClient as createMCPClient } from 'ai';
import { Experimental_StdioMCPTransport as StdioMCPTransport } from 'ai/mcp-stdio';
import type { MCPClient } from 'ai';

// Based on test-sse-prod.js authentication patterns
export interface ClientConfig {
  apiKey: string;
  serverUrl: string;
  timeout?: number;
}

export async function createSSEClient(config: ClientConfig): Promise<MCPClient> {
  // Using authentication pattern from test-sse-prod.js
  return await createMCPClient({
    transport: {
      type: 'sse',
      url: `${config.serverUrl}/sse`,
      headers: {
        'Authorization': `Bearer ${config.apiKey}`,
        // Additional headers from authenticateRequest function in index-sse.ts
        'X-API-Key': config.apiKey, // Alternative auth strategy
      },
    },
  });
}

// For testing local proxy.js if needed
export async function createStdioClient(proxyPath: string): Promise<MCPClient> {
  return await createMCPClient({
    transport: new StdioMCPTransport({
      command: 'node',
      args: [proxyPath],
      env: {
        MCP_API_KEY: process.env.MCP_API_KEY,
      },
    }),
  });
}
```

#### 2.3 Test Implementation (Based on Existing Test Scripts)

**src/tests/connection/test-sse.ts:**
```typescript
import { createSSEClient } from '@/clients/client-factory';
import { config } from 'dotenv';
import { expect, test, describe } from 'vitest';

config();

// Inspired by test-sse-prod.js
describe('SSE Connection Tests', () => {
  test('should establish SSE connection', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    expect(client).toBeDefined();
    
    // Test endpoints from health check in test-sse-prod.js
    const expectedEndpoints = {
      mcp: '/mcp',
      sse: '/sse',
      messages: '/messages',
    };

    await client.close();
  });

  test('should handle authentication correctly', async () => {
    // Test auth strategies from authenticateRequest in index-sse.ts
    const authStrategies = [
      { header: 'Authorization', value: `Bearer ${process.env.MCP_API_KEY}` },
      { header: 'X-API-Key', value: process.env.MCP_API_KEY },
      { query: 'auth', value: process.env.MCP_API_KEY },
    ];

    for (const strategy of authStrategies) {
      // Test each authentication method
    }
  });
});
```

#### 2.4 Tool Discovery Tests

**src/tests/tools/test-discovery.ts:**
```typescript
import { createSSEClient } from '@/clients/client-factory';
import { expect, test, describe } from 'vitest';

describe('Tool Discovery', () => {
  test('should discover expected MCP tools', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const tools = await client.listTools();
    
    // Expected tools from listToolsHandler in index-sse.ts
    const expectedTools = [
      'list_repositories_with_navigation',
      'mfai_search',
    ];

    expect(tools.map(t => t.name)).toEqual(expect.arrayContaining(expectedTools));

    // Validate tool schemas match our definitions
    const listRepoTool = tools.find(t => t.name === 'list_repositories_with_navigation');
    expect(listRepoTool?.inputSchema).toMatchObject({
      type: 'object',
      properties: {
        include_navigation: {
          type: 'boolean',
          description: expect.any(String),
          default: true,
        },
      },
    });

    await client.close();
  });
});
```

### Phase 3: Integration with Existing Data

#### 3.1 Repository Integration Tests

**src/tests/integration/repository-tests.ts:**
```typescript
import { createSSEClient } from '@/clients/client-factory';
import { RepositorySchema } from '@/tools/tool-schemas';
import { expect, test, describe } from 'vitest';

describe('Repository Integration', () => {
  test('should list repositories with navigation guides', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('list_repositories_with_navigation', {
      include_navigation: true,
    });

    // Parse and validate response
    const repositories = JSON.parse(result.content[0].text);
    
    // Validate against schema
    const validatedRepos = repositories.map(repo => 
      RepositorySchema.parse(repo)
    );

    // Check for expected repositories from our database
    const expectedRepos = ['modflowapi', 'flopy', 'modflow6'];
    const foundRepoNames = validatedRepos.map(r => r.name);
    
    expect(foundRepoNames).toEqual(
      expect.arrayContaining(expectedRepos.filter(name => 
        foundRepoNames.includes(name)
      ))
    );

    await client.close();
  });
});
```

#### 3.2 Search Integration Tests

**src/tests/integration/search-tests.ts:**
```typescript
import { createSSEClient } from '@/clients/client-factory';
import { SearchResultSchema } from '@/tools/tool-schemas';

describe('Search Integration', () => {
  test('should perform text search', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    // Test query based on actual repository content
    const result = await client.callTool('mfai_search', {
      query: 'groundwater model',
      search_type: 'text',
    });

    const searchResults = JSON.parse(result.content[0].text);
    
    // Validate response format
    if (Array.isArray(searchResults) && searchResults.length > 0) {
      const validatedResults = searchResults.map(r => 
        SearchResultSchema.parse(r)
      );
      
      // Check for expected file types from file_processor patterns
      const expectedExtensions = ['.py', '.f90', '.nam', '.dis'];
      const foundExtensions = validatedResults.map(r => r.extension);
      
      expect(foundExtensions).toEqual(
        expect.arrayContaining(
          expectedExtensions.filter(ext => foundExtensions.includes(ext))
        )
      );
    }

    await client.close();
  });

  test('should perform semantic search with embeddings', async () => {
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });

    const result = await client.callTool('mfai_search', {
      query: 'How to create a MODFLOW model?',
      search_type: 'semantic',
    });

    // Semantic search should return similarity scores
    const searchResults = JSON.parse(result.content[0].text);
    
    if (searchResults.length > 0) {
      expect(searchResults[0]).toHaveProperty('similarity');
      expect(searchResults[0].similarity).toBeGreaterThan(0);
      expect(searchResults[0].similarity).toBeLessThanOrEqual(1);
    }

    await client.close();
  });
});
```

### Phase 4: Advanced Examples

#### 4.1 AI-Integrated Repository Analysis

**src/examples/ai-repository-analysis.ts:**
```typescript
import { createSSEClient } from '@/clients/client-factory';
import { openai } from '@ai-sdk/openai';
import { generateText } from 'ai';

async function analyzeRepositoryWithAI() {
  const client = await createSSEClient({
    apiKey: process.env.MCP_API_KEY!,
    serverUrl: process.env.MCP_SERVER_URL!,
  });

  // 1. Get repositories with navigation guides
  const repoResult = await client.callTool('list_repositories_with_navigation', {
    include_navigation: true,
  });
  
  const repositories = JSON.parse(repoResult.content[0].text);
  
  // 2. Use AI to analyze navigation guides
  for (const repo of repositories) {
    if (repo.navigation_guide) {
      const analysis = await generateText({
        model: openai('gpt-3.5-turbo'),
        prompt: `Based on this repository navigation guide, what are the key MODFLOW features implemented?
        
        Navigation Guide:
        ${repo.navigation_guide}
        
        List the top 3 MODFLOW-specific features:`,
      });

      console.log(`Repository: ${repo.name}`);
      console.log(`Analysis: ${analysis.text}`);
      
      // 3. Search for specific features identified by AI
      const features = analysis.text.split('\n').slice(0, 3);
      
      for (const feature of features) {
        const searchResult = await client.callTool('mfai_search', {
          query: feature,
          search_type: 'semantic',
          repositories: [repo.name],
        });
        
        console.log(`  Feature: ${feature}`);
        console.log(`  Found in: ${JSON.parse(searchResult.content[0].text).length} files`);
      }
    }
  }

  await client.close();
}
```

#### 4.2 Code Pattern Detection

**src/examples/pattern-detection.ts:**
```typescript
import { createSSEClient } from '@/clients/client-factory';

// Based on file patterns from lib/file_processor/patterns.py
const MODFLOW_PATTERNS = {
  modelInput: ['*.nam', '*.dis', '*.bas', '*.lpf'],
  solvers: ['*.pcg', '*.sms', '*.ims'],
  packages: ['*.wel', '*.riv', '*.ghb', '*.rch', '*.evt'],
};

async function detectModflowPatterns() {
  const client = await createSSEClient({
    apiKey: process.env.MCP_API_KEY!,
    serverUrl: process.env.MCP_SERVER_URL!,
  });

  // Search for specific MODFLOW file patterns
  for (const [category, patterns] of Object.entries(MODFLOW_PATTERNS)) {
    console.log(`\nSearching for ${category} files:`);
    
    for (const pattern of patterns) {
      const searchResult = await client.callTool('mfai_search', {
        query: pattern.replace('*', ''),
        search_type: 'text',
      });
      
      const results = JSON.parse(searchResult.content[0].text);
      console.log(`  ${pattern}: ${results.length} files found`);
      
      if (results.length > 0) {
        console.log(`    Example: ${results[0].filepath}`);
      }
    }
  }

  await client.close();
}
```

### Phase 5: Performance Benchmarks

#### 5.1 Benchmark Script

**scripts/benchmark.ts:**
```typescript
import { createSSEClient } from '../src/clients/client-factory';
import { performance } from 'perf_hooks';

interface BenchmarkResult {
  operation: string;
  duration: number;
  success: boolean;
  error?: string;
}

async function runBenchmarks() {
  const results: BenchmarkResult[] = [];
  
  // Connection benchmark
  const connectionStart = performance.now();
  const client = await createSSEClient({
    apiKey: process.env.MCP_API_KEY!,
    serverUrl: process.env.MCP_SERVER_URL!,
  });
  results.push({
    operation: 'SSE Connection',
    duration: performance.now() - connectionStart,
    success: true,
  });

  // Tool discovery benchmark
  const discoveryStart = performance.now();
  await client.listTools();
  results.push({
    operation: 'Tool Discovery',
    duration: performance.now() - discoveryStart,
    success: true,
  });

  // Repository listing benchmark
  const repoStart = performance.now();
  await client.callTool('list_repositories_with_navigation', {
    include_navigation: false, // Faster without guides
  });
  results.push({
    operation: 'List Repositories',
    duration: performance.now() - repoStart,
    success: true,
  });

  // Text search benchmark
  const textSearchStart = performance.now();
  await client.callTool('mfai_search', {
    query: 'modflow',
    search_type: 'text',
  });
  results.push({
    operation: 'Text Search',
    duration: performance.now() - textSearchStart,
    success: true,
  });

  // Semantic search benchmark
  const semanticSearchStart = performance.now();
  await client.callTool('mfai_search', {
    query: 'groundwater flow simulation',
    search_type: 'semantic',
  });
  results.push({
    operation: 'Semantic Search',
    duration: performance.now() - semanticSearchStart,
    success: true,
  });

  await client.close();

  // Print results
  console.log('\n=== Performance Benchmark Results ===\n');
  console.table(results.map(r => ({
    Operation: r.operation,
    'Duration (ms)': r.duration.toFixed(2),
    Status: r.success ? '✅' : '❌',
  })));

  // Compare with expected thresholds
  const thresholds = {
    'SSE Connection': 1000,
    'Tool Discovery': 500,
    'List Repositories': 3000,
    'Text Search': 3000,
    'Semantic Search': 3000,
  };

  console.log('\n=== Performance vs Thresholds ===\n');
  results.forEach(r => {
    const threshold = thresholds[r.operation];
    const status = r.duration <= threshold ? '✅ PASS' : '❌ FAIL';
    console.log(`${r.operation}: ${r.duration.toFixed(2)}ms / ${threshold}ms ${status}`);
  });
}

runBenchmarks().catch(console.error);
```

### Phase 6: CI/CD Integration

#### 6.1 GitHub Actions Workflow

**.github/workflows/test-mcp-client.yml:**
```yaml
name: Test MCP AI SDK Client

on:
  push:
    paths:
      - 'tests/mcp_aisdk/**'
      - 'mfai_mcp_server_cloudflare/**'
  pull_request:
    paths:
      - 'tests/mcp_aisdk/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: Install dependencies
        working-directory: ./tests/mcp_aisdk
        run: npm install
        
      - name: Run type checking
        working-directory: ./tests/mcp_aisdk
        run: npm run typecheck
        
      - name: Run tests
        working-directory: ./tests/mcp_aisdk
        env:
          MCP_API_KEY: ${{ secrets.MCP_TEST_API_KEY }}
          MCP_SERVER_URL: ${{ secrets.MCP_SERVER_URL }}
        run: npm test
        
      - name: Run benchmarks
        working-directory: ./tests/mcp_aisdk
        env:
          MCP_API_KEY: ${{ secrets.MCP_TEST_API_KEY }}
          MCP_SERVER_URL: ${{ secrets.MCP_SERVER_URL }}
        run: npm run benchmark
```

## Success Criteria

1. **Integration Success**
   - ✅ AI SDK client connects to our SSE endpoint
   - ✅ All authentication strategies work
   - ✅ Tools match server implementation exactly
   - ✅ Response schemas validated against database models

2. **Test Coverage**
   - 100% of MCP tools tested
   - All authentication methods validated
   - Error scenarios covered
   - Performance benchmarks established

3. **Documentation**
   - Examples for each tool
   - Integration patterns documented
   - Troubleshooting guide complete
   - API reference generated from schemas

## Timeline

- **Day 1**: Setup and basic connectivity
- **Day 2**: Tool implementation and validation
- **Day 3**: Integration tests with real data
- **Day 4**: Advanced examples and AI integration
- **Day 5**: Documentation and CI/CD setup

## References

### Internal Codebase
- Server Implementation: `/mfai_mcp_server_cloudflare/src/index-sse.ts`
- Test Scripts: `/mfai_mcp_server_cloudflare/test-*.js`
- Database Models: `/mfai_db_repos/lib/database/models.py`
- File Patterns: `/mfai_db_repos/lib/file_processor/patterns.py`

### External Documentation
- [Vercel AI SDK MCP Docs](https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling#mcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Our SSE Implementation](/docs/mcp_sse_roadmap.md)