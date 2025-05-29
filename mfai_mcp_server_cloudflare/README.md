# MFAI Repository Navigator - Cloudflare Workers Edition

This is the Cloudflare Workers version of the MFAI Repository Navigator MCP server, optimized for edge deployment with global distribution.

## Features

- **Stateless Architecture**: Each request is independent, perfect for edge computing
- **Direct JSON-RPC Handling**: Custom implementation for Cloudflare Workers compatibility
- **SSE Support**: Server-Sent Events endpoint for Cursor IDE compatibility
- **Multiple Authentication Strategies**: Bearer tokens, X-API-Key headers, and query parameters
- **Global Distribution**: Runs on Cloudflare's edge network
- **Automatic Scaling**: Handles load automatically
- **Built-in Security**: Cloudflare's security features included

## Cursor IDE Compatibility ✅

**Great news!** This server now supports multiple connection methods for Cursor IDE:

1. **SSE Endpoint (Recommended)**: Direct connection using mcp-remote with Bearer token authentication
2. **Local Proxy**: stdio bridge for environments that need it

### Option 1: Direct SSE Connection (Recommended)

Use `mcp-remote` to connect Cursor directly to the Cloudflare Worker:

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

**Status: ✅ Tested and Working** - This configuration has been validated with comprehensive testing.

### Option 2: Local Proxy (Alternative)

If you prefer a local bridge:

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "node",
      "args": ["/absolute/path/to/proxy.js"],
      "env": {
        "MCP_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Status: ✅ Tested and Working** - This is the configuration currently working for the user.

### Understanding the Difference

- **Cloudflare's @cloudflare/mcp-server-cloudflare**: Runs locally, connects to Cloudflare API
- **This server**: Runs entirely on Cloudflare Workers, accessed via HTTP

Since this is a truly remote server (not a local server connecting to an API), Cursor needs a local bridge to communicate with it.

## Prerequisites

- Node.js 18+ installed
- Cloudflare account
- Neon database with pgvector extension
- OpenAI API key (for semantic search)

## Setup Guide

### 1. Clone and Install Dependencies

```bash
# Clone or copy this folder
cd mfai_mcp_server_cloudflare

# Install dependencies
npm install
```

### 2. Configure Environment Variables

Create a `.dev.vars` file for local development:

```bash
# Copy the example file
cp .dev.vars.example .dev.vars

# Edit .dev.vars and add your actual values:
MODFLOW_AI_MCP_00_CONNECTION_STRING="postgresql://user:pass@host/db?sslmode=require"
OPENAI_API_KEY="sk-..."
```

### 3. Update Cloudflare Configuration

Edit `wrangler.toml` if needed:

```toml
name = "mfai-repository-navigator"
main = "src/index.ts"
compatibility_date = "2024-09-23"  # Important for Node.js compatibility
compatibility_flags = ["nodejs_compat"]
```

### 4. Local Development

```bash
# Start local development server
npx wrangler dev

# The server will be available at http://localhost:8787/mcp
```

### 5. Test Locally

Run the included test script:

```bash
# In another terminal
node test-local.js
```

Expected output:
- Initialize connection: Protocol version and capabilities
- List tools: Shows available MCP tools
- List repositories: Returns repository data with navigation guides
- Search: Performs text/semantic search

### 6. Deploy to Cloudflare

```bash
# Login to Cloudflare (first time only)
npx wrangler login

# Deploy to production
npx wrangler deploy

# You'll get a URL like: https://mfai-repository-navigator.little-grass-273a.workers.dev
```

### 7. Set Production Secrets

After deployment, set your secrets:

```bash
# Set database connection string
npx wrangler secret put MODFLOW_AI_MCP_00_CONNECTION_STRING
# Paste your connection string when prompted

# Set OpenAI API key
npx wrangler secret put OPENAI_API_KEY
# Paste your API key when prompted
```

### 8. Configure Rate Limiting

In Cloudflare Dashboard:

1. Go to **Security** → **WAF** → **Rate limiting rules**
2. Create a new rule:
   - **If** URI Path equals `/mcp` AND Request Method equals `POST`
   - **Then** Rate limit by IP
   - **Rate**: 10-20 requests per minute
   - **Action**: Block for 1-5 minutes

### 8.5. IMPORTANT: Add Authentication (Recommended)

**⚠️ WARNING**: Without authentication, anyone with your URL can use your MCP server and consume your resources!

#### API Key Authentication (Already Implemented)

The server includes API key authentication. When `MCP_API_KEY` is set, all requests must include the key.

#### Setting Up Authentication

**1. Generate an API Key:**
```bash
# Use the included key manager
node manage-keys.js generate

# Or generate manually
openssl rand -hex 32
```

**2. Configure Local Development:**
```bash
# Add to .dev.vars
MCP_API_KEY=your_generated_key_here

# Restart wrangler dev
npx wrangler dev
```

**3. Test Locally:**
```bash
# Test WITHOUT the API key (should fail with 401 Unauthorized)
node test-local.js

# Test WITH the API key (should work)
MCP_API_KEY=your_generated_key_here node test-local.js
```

**4. Deploy with Authentication:**
```bash
# Deploy the code
npx wrangler deploy

# Set the API key secret in production
npx wrangler secret put MCP_API_KEY
# Paste your key when prompted
```

**5. Test Production:**
```bash
# Test without key (should fail)
node test-prod.js

# Test with key (should work)
MCP_API_KEY=your_generated_key_here node test-prod.js
```

#### Managing API Keys

Use the included key manager:
```bash
# Generate a new key
node manage-keys.js generate

# List keys (shows partial key for security)
node manage-keys.js list

# Rotate keys (archives old, generates new)
node manage-keys.js rotate
```

Keys are stored in `.mcp-keys.json` (gitignored) for your reference.

#### Client Configuration with Authentication

When sharing with MCP clients, they need the API key:

**For Cursor IDE:**

Cursor requires stdio transport. Since our server is HTTP-only, you'll need to use the included proxy script:

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "node",
      "args": ["/absolute/path/to/mfai_mcp_server_cloudflare/proxy.js"],
      "env": {
        "MCP_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Important**: The proxy script runs locally but only acts as a bridge - all actual processing happens on the Cloudflare Worker.

**For Claude Desktop or other HTTP-aware clients:**

These clients may support direct HTTP connections in the future:

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "url": "https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp",
      "headers": {
        "Authorization": "Bearer your_api_key_here"
      }
    }
  }
}
```

**Note about environment variables:**
- The **server** checks for `MCP_API_KEY` (set via `wrangler secret put MCP_API_KEY`)
- The **client** uses `MCP_SERVER_AUTH` (this is what the remote service proxy expects)
- In **test scripts**, we use `MCP_API_KEY` directly: `MCP_API_KEY=your_key node test-prod.js`

**IMPORTANT**: The `MCP_SERVER_AUTH` value must include "Bearer " prefix:
- ✅ Correct: `"MCP_SERVER_AUTH": "Bearer your_api_key_here"`
- ❌ Wrong: `"MCP_SERVER_AUTH": "your_api_key_here"`

**Security Tips:**
- Never commit API keys to Git
- Use different keys for dev/staging/production
- Rotate keys regularly
- Share keys securely (password manager, encrypted messages)
- Monitor usage in Cloudflare Analytics

#### Option 2: Cloudflare Access (Advanced)

Use Cloudflare Zero Trust to protect your Worker:

1. Go to **Zero Trust** → **Access** → **Applications**
2. Add application with your Worker URL
3. Configure authentication (email, social login, etc.)
4. Users must authenticate before accessing the MCP server

#### Option 3: IP Allowlist

In Cloudflare WAF, create a rule:
- **If** IP is not in [your IP list] AND URI Path equals `/mcp`
- **Then** Block

#### Cost Protection Tips

Even with rate limiting, consider:
1. **Set spending alerts** in OpenAI dashboard
2. **Use Cloudflare Analytics** to monitor usage
3. **Implement request quotas** per API key
4. **Add CloudFlare's Super Bot Fight Mode**

### 9. Test Production Endpoints

Test both the HTTP and SSE endpoints:

```bash
# Test HTTP endpoint
node test-prod.js

# Test SSE endpoint (requires eventsource package)
npm install eventsource
node test-sse-prod.js

# Test with authentication using your API key
MCP_API_KEY=your_api_key_here node test-sse-prod.js
```

You can also test the SSE endpoint directly with curl:

```bash
# Test SSE connection - should show endpoint event
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer your_api_key_here" \
  https://mfai-repository-navigator.little-grass-273a.workers.dev/sse
```

**Expected output from curl:**
```
event: endpoint
data: https://mfai-repository-navigator.little-grass-273a.workers.dev/messages
: ping
: ping
...
```

**Expected output from test-sse-prod.js:**
```bash
✅ SSE connection opened
📡 Received endpoint URL: https://mfai-repository-navigator.little-grass-273a.workers.dev/messages
  ✅ Initialize response received
  ✅ Tools list response received
  ✅ Tool call response received
  ✅ Bearer token authentication successful
```

## Test Scripts and Validation

This repository includes comprehensive test scripts to validate both HTTP and SSE endpoints:

### Available Test Scripts

1. **`test-prod.js`** - Tests HTTP endpoint
2. **`test-sse-prod.js`** - Tests SSE endpoint with full MCP protocol validation
3. **`test-local.js`** - Tests local development server

### Running Tests

```bash
# Basic test (no authentication - will show 401 errors)
node test-sse-prod.js

# Authenticated test with working API key
MCP_API_KEY=your_api_key_here node test-sse-prod.js
```

### Expected Test Output

**Successful SSE Test:**
```bash
🧪 Starting Production SSE MCP Server Tests
Testing SSE MCP Server at: https://mfai-repository-navigator.little-grass-273a.workers.dev
Using API key authentication
---
1. Testing health endpoint (/health):
Health check: {
  "status": "healthy",
  "version": "3.0.0",
  "endpoints": {
    "mcp": "/mcp",
    "sse": "/sse", 
    "messages": "/messages"
  },
  "authentication": "required",
  "sseSupport": true
}

✅ SSE connection opened
📡 Received endpoint URL: https://mfai-repository-navigator.little-grass-273a.workers.dev/messages
  ✅ Initialize response received
  ✅ Tools list response received
  ✅ Tool call response received
  ✅ Bearer token authentication successful
```

### Manual Testing with curl

```bash
# Test SSE stream (should show continuous output)
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer your_api_key_here" \
  https://mfai-repository-navigator.little-grass-273a.workers.dev/sse

# Expected output:
# event: endpoint
# data: https://mfai-repository-navigator.little-grass-273a.workers.dev/messages
# : ping
# : ping
# ...
```

## Using the Proxy Script for stdio Clients

Since many MCP clients (like Cursor) only support stdio transport, we include a `proxy.js` script that bridges stdio to our HTTP API.

### How it Works

The proxy script:
1. Reads JSON-RPC messages from stdin
2. Forwards them to the Cloudflare Worker via HTTP POST
3. Includes Bearer authentication if configured
4. Returns responses to stdout

### Usage

```bash
# Direct usage
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | MCP_API_KEY=your_key node proxy.js

# Or configure the server URL
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | MCP_API_KEY=your_key node proxy.js https://your-server.workers.dev/mcp
```

### Configuration in Cursor

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "node",
      "args": ["/absolute/path/to/proxy.js"],
      "env": {
        "MCP_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Testing with MCP Inspector

MCP Inspector is a tool for testing and debugging MCP servers. However, it has limitations with our implementation.

### Understanding Our Transport

We implement a **Streamable HTTP-compatible** transport:
- Accepts HTTP POST requests with JSON-RPC payloads
- Returns JSON-RPC responses
- Compatible with clients expecting Streamable HTTP transport

However, we **don't use the SDK's StreamableHTTPServerTransport** because it's incompatible with Cloudflare Workers (requires Node.js-style Request/Response objects).

### Testing with Inspector

**Current Status**: MCP Inspector doesn't yet support Streamable HTTP transport in its UI options (only "stdio" and "Server-sent Events").

**Future Compatibility**: When Inspector adds "Streamable HTTP" as a transport option, it should work with our server.

### Alternative Testing Methods

Since Inspector doesn't support Streamable HTTP yet, use these methods:

1. **Provided Test Scripts** (Recommended):
```bash
# For local testing
node test-local.js

# For production testing  
node test-prod.js
```

2. **Direct HTTP Testing**:
```bash
# Test with curl (without authentication - will fail if API key is required)
curl -X POST https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Test with curl (with authentication)
curl -X POST https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

3. **MCP Clients**: Configure real MCP clients (Claude Desktop, Cursor, etc.) which properly support Streamable HTTP transport

### Alternative Testing Methods

1. **Command Line with curl**:
```bash
# Test tools list (with authentication if API key is configured)
curl -X POST https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

2. **Provided Test Scripts**:
- `test-local.js` - For local development
- `test-prod.js` - For production testing

3. **Postman or Similar Tools**:
- Import as POST request
- Set Content-Type: application/json
- Send JSON-RPC formatted requests

4. **Integration with Real MCP Clients**:
- Claude Desktop
- Cursor
- Other MCP-compatible applications

## Architecture Notes

### Why Not StreamableHTTPServerTransport?

The MCP SDK's `StreamableHTTPServerTransport` expects Node.js-style Request/Response objects with methods like `writeHead()`, which aren't available in Cloudflare Workers. This implementation:

1. **Handles JSON-RPC directly**: Bypasses the transport layer
2. **Uses Web Standards**: Works with Fetch API Request/Response
3. **Stateless design**: No session management needed
4. **Manual handler mapping**: Stores handlers in a Map for direct access

### Key Implementation Details

```typescript
// Instead of using StreamableHTTPServerTransport:
const transport = new StreamableHTTPServerTransport(...);

// We handle JSON-RPC directly:
const response = await handleJsonRpcRequest(server, body);
```

## Client Configuration

Configure MCP clients to connect to your Worker:

### For Local Development
```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "curl",
      "args": ["-X", "POST", "http://localhost:8787/mcp"]
    }
  }
}
```

### For Production

**Note**: Since our server uses environment variables (database connection, API keys), but these are configured on Cloudflare's side, not in the client config. The client just needs the URL and API key.

#### For Cursor IDE

Cursor currently only supports stdio transport, not direct HTTP connections. You have two options:

**Option 1: Use Local Proxy Script (If you must use our HTTP endpoint)**
```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "node",
      "args": ["/path/to/mfai_mcp_server_cloudflare/proxy.js"],
      "env": {
        "MCP_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Option 2: Use mcp-remote with SSE (Recommended)**
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

**Note**: This uses the new SSE endpoint which supports Bearer token authentication. **✅ Fully tested and working.**

#### For Future HTTP-Compatible Clients

When MCP clients support direct HTTP connections:

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "url": "https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp",
      "headers": {
        "Authorization": "Bearer your_api_key_here"
      }
    }
  }
}
```

**Important**: Unlike local MCP servers where you'd set environment variables in the client config:
```json
{
  "mcpServers": {
    "local-server": {
      "command": "node",
      "args": ["server.js"],
      "env": {
        "DATABASE_URL": "...",
        "API_KEY": "..."
      }
    }
  }
}
```

With Cloudflare Workers, the environment variables are:
- Set via `wrangler secret put` for production
- Configured in `.dev.vars` for local development
- Managed entirely on the server side

This is actually more secure because:
1. Clients don't need to know your database credentials
2. API keys are stored encrypted in Cloudflare
3. No sensitive data in client configurations

## Troubleshooting

### "res.writeHead is not a function" Error
This means the code is trying to use StreamableHTTPServerTransport. Make sure you're using the custom JSON-RPC handler implementation.

### "Cannot read properties of undefined (reading 'get')" Error
The handlers Map wasn't initialized properly. Ensure handlers are stored when setting up the server.

### Connection Refused
Make sure `npx wrangler dev` is running in another terminal.

### Node.js Compatibility Issues
Ensure `compatibility_date = "2024-09-23"` and `compatibility_flags = ["nodejs_compat"]` are set in `wrangler.toml`.

## Monitoring

View logs and analytics:

```bash
# Stream live logs
npx wrangler tail

# Or view in Cloudflare Dashboard:
# Workers & Pages > Your Worker > Logs
```

## Limitations

- **No Push Notifications**: Can't push updates to clients (except via SSE endpoint)
- **Request Limits**: 
  - 10ms CPU time (free plan)
  - 50ms CPU time (paid plan)
  - 100MB maximum request size
- **Limited Persistent Connections**: SSE connections are supported but stateless

## Cost Considerations

- **Free Tier**: 100,000 requests/day
- **Paid Plans**: Start at $5/month for 10 million requests
- **Additional Costs**:
  - Neon database usage
  - OpenAI API calls for semantic search

## Development Workflow

1. Make changes to `src/index.ts`
2. `wrangler dev` auto-reloads
3. Test with `node test-local.js`
4. Deploy with `npx wrangler deploy`
5. Monitor with `npx wrangler tail`

## Security Best Practices

1. **Never commit `.dev.vars`** - it contains secrets
2. **Use wrangler secrets** for production
3. **Enable rate limiting** to prevent abuse
4. **Monitor usage** in Cloudflare Analytics
5. **Rotate API keys** regularly

## Next Steps

- Add caching with Cloudflare KV for frequent queries
- Implement request validation and sanitization
- Add comprehensive error handling
- Set up GitHub Actions for CI/CD
- Add health check endpoint
- Implement usage analytics