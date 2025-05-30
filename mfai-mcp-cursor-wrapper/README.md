# @modflowai/mcp-server

A wrapper that enables Cursor IDE to connect to the MFAI Repository Navigator MCP server using HTTP transport. This package works around known compatibility issues between Cursor and mcp-remote.

## Installation

You don't need to install this package separately. It can be run directly using `npx`.

## Usage

## IDE-Specific Configurations

### Cursor IDE & Claude Desktop (Use This Wrapper)

**Config Location:**
- **Cursor**: `~/.cursor/mcp.json` or Cursor Settings > MCP
- **Claude Desktop**: 
  - macOS: `~/Library/Application Support/Claude/claude-desktop-config.json`
  - Windows: `%APPDATA%\Claude\claude-desktop-config.json`
  - Linux: `~/.config/Claude/claude-desktop-config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "mfai": {
      "command": "npx",
      "args": ["-y", "@modflowai/mcp-server"],
      "env": {
        "MFAI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### VS Code & Windsurf (Direct HTTP - No Wrapper Needed)

**Config Location:** `.vscode/settings.json` or VS Code Settings > MCP

**Configuration:**
```json
{
  "mcpServers": {
    "mfai": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp",
        "--header",
        "Authorization:Bearer your_api_key_here",
        "--transport",
        "http-only"
      ]
    }
  }
}
```

## Compatibility Matrix

| IDE | Method | Status | Notes |
|-----|--------|--------|-------|
| **Cursor** | Wrapper | ✅ Working | Requires wrapper for Windows npx compatibility |
| **Claude Desktop** | Wrapper | ✅ Working | Requires wrapper for Windows npx compatibility |
| **VS Code** | Direct HTTP | ✅ Working | Native mcp-remote support |
| **Windsurf** | Direct HTTP | ✅ Working | Native mcp-remote support |

## Configuration

### Required Environment Variables

- `MFAI_API_KEY`: Your API key for authentication (required)

### Optional Environment Variables

- `MFAI_SERVER_URL`: Override the default server URL (default: `https://mfai-repository-navigator.little-grass-273a.workers.dev/mcp`)
- `MFAI_DEBUG`: Set to `"true"` for debug logging

## Example with Custom Server

```json
{
  "mcpServers": {
    "mfai": {
      "command": "npx",
      "args": ["-y", "@modflowai/mcp-server"],
      "env": {
        "MFAI_API_KEY": "your_api_key_here",
        "MFAI_SERVER_URL": "https://your-custom-server.workers.dev/mcp"
      }
    }
  }
}
```

## How It Works

This wrapper:
1. Reads the API key from the `MFAI_API_KEY` environment variable
2. Spawns `mcp-remote` with the correct HTTP transport settings
3. Handles process lifecycle and error management
4. Passes through all stdio communication between Cursor and the MCP server
5. **Cross-platform compatibility**: Automatically detects Windows and handles `npx` path resolution
6. **Proper authentication**: Sends Bearer token in Authorization header to Cloudflare Workers

## Architecture

```
Cursor IDE (stdio) ←→ Wrapper ←→ mcp-remote (HTTP + Bearer Auth) ←→ Cloudflare Workers Server
```

- **Cursor IDE**: Uses stdio transport (the only transport Cursor supports reliably)
- **Wrapper**: Bridges stdio ↔ HTTP, handles Windows compatibility
- **mcp-remote**: Official HTTP transport client with authentication
- **Cloudflare Workers**: Your MCP server running on the edge

## Features

- ✅ **Windows Support**: Automatically finds and uses correct `npx` path
- ✅ **Cross-platform**: Works on Windows, macOS, and Linux
- ✅ **HTTP Transport**: Full compatibility with HTTP-based MCP servers
- ✅ **Bearer Authentication**: Secure API key authentication
- ✅ **Debug Mode**: Detailed logging for troubleshooting
- ✅ **No Installation**: Run directly with `npx`

## Monitoring & Analytics

Since this wrapper uses HTTP transport to communicate with your server, you retain full monitoring capabilities:

- **Cloudflare Analytics**: Request counts, response times, geographic distribution
- **Custom Logging**: Add logging to your Cloudflare Workers server
- **Rate Limiting**: Track usage per API key
- **Error Monitoring**: Monitor 401, 500, and other error responses
- **External Services**: Integrate with Datadog, New Relic, Sentry, etc.

Every Cursor request becomes a traceable HTTP request to your server!

## Troubleshooting

If the wrapper doesn't work:

1. **Check Node.js is installed**: Run `node --version` (requires Node.js 18+)
2. **Check npm is available**: Run `npm --version`
3. **Enable debug mode**: Set `MFAI_DEBUG=true` in the env section
4. **Check the API key**: Ensure it's correctly set and valid
5. **Test manually**: Run `npx @modflowai/mcp-server` with your API key in terminal
6. **Windows users**: The wrapper automatically handles `npx` path resolution
7. **Check server status**: Verify your Cloudflare Workers server is deployed and accessible

### Common Issues

**Windows Path Issues**: Fixed in v1.0.3+ - the wrapper automatically finds and quotes `npx` paths with spaces.

**Authentication Errors**: Ensure your API key is correctly set and matches the key configured in your Cloudflare Workers environment.

**Network Issues**: Check if corporate firewalls or proxies are blocking requests to `*.workers.dev` domains.

## License

MIT