# MCP SSE Implementation Roadmap

*Created: May 29, 2025*
*Completed: May 29, 2025*

## ✅ IMPLEMENTATION COMPLETED

**Status: Successfully implemented and deployed!**

This document outlined the plan to add SSE (Server-Sent Events) support to our MCP server on Cloudflare Workers. **The implementation has been completed and is fully operational.**

## ✅ Final Implementation

- **HTTP Endpoint**: `https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp`
- **SSE Endpoint**: `https://mfai-repository-navigator.little-grass-273a.workers.dev/sse` ✅
- **Messages Endpoint**: `https://mfai-repository-navigator.little-grass-273a.workers.dev/messages` ✅
- **Authentication**: Multiple strategies (Bearer tokens, X-API-Key, query params) ✅
- **Solution**: Direct connection from Cursor via mcp-remote with `--header` option ✅
- **Status**: **FULLY OPERATIONAL** 🚀

## How Cloudflare's MCP Servers Work

Based on analysis of Cloudflare's MCP server examples:

1. They use the `agents` npm package (v0.0.67) which provides `McpAgent` class with built-in SSE support
2. SSE endpoints are created using `McpAgent.serveSSE('/sse')`
3. OAuth authentication is handled by `@cloudflare/workers-oauth-provider`
4. Clients connect using `mcp-remote` which bridges stdio to SSE

## Proposed Solutions ✅ **COMPLETED**

### Option 1: Use the `agents` Package (Full Migration) ❌ Not Chosen

**Advantages:**
- Battle-tested SSE implementation
- Handles all MCP protocol details
- Native support for Durable Objects and state management

**Implementation:**
```typescript
import { McpAgent } from 'agents/mcp';

export class MFAIRepositoryMCP extends McpAgent<Env, State, Props> {
  // Migrate existing MCP implementation
}

export default {
  fetch: async (req: Request, env: Env) => {
    // Bearer token auth
    if (env.MCP_API_KEY) {
      const authHeader = request.headers.get('Authorization');
      if (!authHeader || authHeader !== `Bearer ${env.MCP_API_KEY}`) {
        return new Response('Unauthorized', { status: 401 });
      }
    }
    
    // Route to SSE or HTTP endpoints
    if (url.pathname === '/sse') {
      return MFAIRepositoryMCP.serveSSE('/sse').fetch(req, env);
    }
  }
}
```

**Effort:** High - Requires rewriting server to use `agents` framework

### Option 2: Manual SSE Implementation ❌ Not Chosen

**Advantages:**
- Full control over implementation
- No new dependencies
- Can keep existing architecture

**Implementation:**
```typescript
// Add to existing index.ts
if (request.method === 'GET' && url.pathname === '/sse') {
  // Bearer auth check
  
  // Create SSE stream
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  
  // Send endpoint event per MCP spec
  const messagesUrl = `${url.origin}/sse/messages`;
  await writer.write(encoder.encode(`event: endpoint\ndata: ${messagesUrl}\n\n`));
  
  // Handle messages at /sse/messages endpoint
  
  return new Response(readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  });
}
```

**Effort:** Medium - Need to implement SSE protocol correctly

### Option 3: Hybrid SSE Proxy ✅ **IMPLEMENTED**

**Advantages:**
- Minimal changes to existing server
- Quick to implement and deploy
- Can be deployed as separate worker
- Easy to test and rollback

**Implementation:**

Create `sse-proxy-worker.ts`:
```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // SSE endpoint
    if (url.pathname === '/sse') {
      // Check Bearer auth
      if (env.MCP_API_KEY) {
        const authHeader = request.headers.get('Authorization');
        if (!authHeader || authHeader !== `Bearer ${env.MCP_API_KEY}`) {
          return new Response('Unauthorized', { status: 401 });
        }
      }
      
      const { readable, writable } = new TransformStream();
      const writer = writable.getWriter();
      
      // Send endpoint URL
      const messagesUrl = `${url.origin}/messages`;
      await writer.write(new TextEncoder().encode(
        `event: endpoint\ndata: ${messagesUrl}\n\n`
      ));
      
      // Keep alive
      const pingInterval = setInterval(async () => {
        try {
          await writer.write(new TextEncoder().encode(':ping\n\n'));
        } catch {
          clearInterval(pingInterval);
        }
      }, 30000);
      
      return new Response(readable, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
      });
    }
    
    // Messages endpoint - forward to existing server
    if (url.pathname === '/messages') {
      const body = await request.text();
      
      return fetch('https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': request.headers.get('Authorization') || '',
        },
        body: body,
      });
    }
    
    return new Response('Not Found', { status: 404 });
  }
}
```

**Effort:** Low - Can be implemented in hours

## ✅ Implementation Plan - COMPLETED

### ✅ Phase 1: SSE Proxy **COMPLETED**
1. ✅ Create new Cloudflare Worker for SSE proxy
2. ✅ Implement basic SSE endpoint with Bearer auth
3. ✅ Forward messages to existing MCP server
4. ✅ Deploy to main worker (integrated approach)

### ✅ Phase 2: Testing **COMPLETED**
1. ✅ Test with curl and Node.js test scripts
2. ✅ Test with `mcp-remote` using `--header` option
3. ✅ Validate Cursor IDE configuration

### ✅ Phase 3: Documentation **COMPLETED**
1. ✅ Update README with SSE endpoint
2. ✅ Add Cursor configuration examples
3. ✅ Document authentication flow

### 🔮 Phase 4: Future Enhancements (Optional)
1. Migrate to `agents` package for full feature support
2. Add WebSocket support
3. Implement stateful sessions with Durable Objects

## Authentication Flow

### How MCP Clients Pass Authentication

MCP clients can pass authentication in different ways:

1. **Via Environment Variables** (What Cursor supports):
```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mfai-sse-proxy.workers.dev/sse"],
      "env": {
        "AUTHORIZATION": "Bearer your_api_key_here"
      }
    }
  }
}
```

2. **Via OAuth Flow** (What `mcp-remote` expects by default):
- `mcp-remote` initiates OAuth authentication
- Redirects to authorization endpoint
- Handles token exchange

### Authentication in Each Approach

#### Option 1: Using `agents` Package
- The `agents` package expects OAuth by default
- Would need customization to accept Bearer tokens from env vars
- Complex to override the OAuth flow

#### Option 2: Manual SSE Implementation
- Full control over auth checking
- Can read from any header or query parameter
- Need to handle how `mcp-remote` passes the auth

#### Option 3: Hybrid SSE Proxy (Recommended)
```typescript
// The key challenge: mcp-remote doesn't pass env vars as headers
// Solution: Multiple auth strategies

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // Strategy 1: Check Authorization header (if mcp-remote passes it)
    let authToken = request.headers.get('Authorization');
    
    // Strategy 2: Check query parameter (custom mcp-remote fork)
    if (!authToken && url.searchParams.has('auth')) {
      authToken = `Bearer ${url.searchParams.get('auth')}`;
    }
    
    // Strategy 3: Check custom header
    if (!authToken && request.headers.get('X-API-Key')) {
      authToken = `Bearer ${request.headers.get('X-API-Key')}`;
    }
    
    // Validate token
    if (env.MCP_API_KEY && authToken !== `Bearer ${env.MCP_API_KEY}`) {
      return new Response('Unauthorized', { status: 401 });
    }
    
    // ... rest of SSE implementation
  }
}
```

### The Authentication Problem

**Issue**: `mcp-remote` is designed for OAuth, not Bearer tokens. The `env` variables in the MCP client config are passed to the `npx` command, not to the remote server.

**Solutions**:

1. **Fork/Modify mcp-remote** to pass environment variables as headers
2. **Use a different proxy** that supports Bearer auth
3. **Implement OAuth** in your server (like Cloudflare does)
4. **Create a custom stdio-to-HTTP proxy** that handles auth properly

## Cursor Configuration with Authentication

### Current Limitation
```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mfai-sse-proxy.workers.dev/sse"],
      "env": {
        "MCP_API_KEY": "your_key_here"  // ❌ This doesn't get sent to the server!
      }
    }
  }
}
```

The `env` variables are available to the `mcp-remote` process, but `mcp-remote` doesn't forward them to the server.

### SOLUTION: mcp-remote Supports Custom Headers! ✅

`mcp-remote` DOES support passing custom headers including Bearer tokens via the `--header` option!

#### Working Configuration for Cursor with Bearer Auth:

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest", 
        "https://mfai-sse-proxy.workers.dev/sse",
        "--header",
        "Authorization: Bearer ${MCP_API_KEY}"
      ],
      "env": {
        "MCP_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### Important: Cursor/Claude Desktop Bug Workaround

There's a known bug where spaces in args aren't properly escaped. Use this format instead:

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest", 
        "https://mfai-sse-proxy.workers.dev/sse",
        "--header",
        "Authorization:${AUTH_HEADER}"  // No space after colon!
      ],
      "env": {
        "AUTH_HEADER": "Bearer your_api_key_here"  // Space goes here
      }
    }
  }
}
```

This means we can implement SSE support and authentication will work properly!

## ✅ Success Criteria - ALL ACHIEVED

1. ✅ **Cursor can connect without local proxy script** - Users can connect directly via mcp-remote
2. ✅ **Authentication works with Bearer tokens** - Multiple auth strategies implemented
3. ✅ **All existing MCP tools remain functional** - Backward compatibility maintained
4. ✅ **No changes required to existing database or core logic** - Minimal impact approach

## Risks and Mitigations

1. **Risk**: SSE connection limits on Cloudflare Workers
   - **Mitigation**: Implement connection pooling and timeouts

2. **Risk**: `mcp-remote` OAuth expectations vs Bearer auth
   - **Mitigation**: Test thoroughly, may need custom auth flow

3. **Risk**: Breaking existing HTTP clients
   - **Mitigation**: Keep existing `/mcp` endpoint unchanged

## Decision

**Recommended approach: Option 3 (Hybrid SSE Proxy)**

Reasons:
- Fastest to implement
- Lowest risk to existing system
- Easy to test and rollback
- Can evolve to full `agents` implementation later

## Updated Implementation Plan

Now that we know `mcp-remote` supports custom headers, the implementation becomes simpler:

1. **Create SSE Proxy Worker** that accepts Bearer tokens in Authorization header
2. **Test with mcp-remote** using `--header` option
3. **Document Cursor configuration** with proper auth setup

## ✅ Implementation Results

### 🎉 What Was Accomplished

1. ✅ **SSE Endpoint Implemented** - Working at `/sse` with proper event streaming
2. ✅ **Multiple Authentication Strategies** - Bearer tokens, X-API-Key, and query params
3. ✅ **Cursor IDE Compatibility** - Direct connection via mcp-remote with `--header` option
4. ✅ **Comprehensive Testing** - Validated with curl, Node.js scripts, and production testing
5. ✅ **Complete Documentation** - Updated README with working configurations
6. ✅ **Security Hardened** - API keys removed from public documentation

### 🚀 Live Endpoints

- **HTTP**: `https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp`
- **SSE**: `https://mfai-repository-navigator.little-grass-273a.workers.dev/sse`
- **Messages**: `https://mfai-repository-navigator.little-grass-273a.workers.dev/messages`
- **Health**: `https://mfai-repository-navigator.little-grass-273a.workers.dev/health`

### 📋 Working Cursor Configuration

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest", 
        "https://mfai-repository-navigator.little-grass-273a.workers.dev/sse",
        "--header",
        "Authorization:Bearer ${MCP_API_KEY}"
      ],
      "env": {
        "MCP_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### 🏁 Project Status: **COMPLETE AND OPERATIONAL** ✅