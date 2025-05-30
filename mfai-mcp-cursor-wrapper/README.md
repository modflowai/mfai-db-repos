# @modflowai/mcp-cursor-wrapper

A wrapper that enables Cursor IDE to connect to the MFAI Repository Navigator MCP server using HTTP transport. This package works around known compatibility issues between Cursor and mcp-remote.

## Installation

You don't need to install this package separately. It can be run directly using `npx`.

## Usage

Add this configuration to your Cursor MCP settings (usually in `~/.cursor/mcp.json` or through Cursor's settings):

```json
{
  "mcpServers": {
    "mfai": {
      "command": "npx",
      "args": ["-y", "@modflowai/mcp-cursor-wrapper"],
      "env": {
        "MFAI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

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
      "args": ["-y", "@modflowai/mcp-cursor-wrapper"],
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

## Troubleshooting

If the wrapper doesn't work:

1. **Check Node.js is installed**: Run `node --version` (requires Node.js 18+)
2. **Check npm is available**: Run `npm --version`
3. **Enable debug mode**: Set `MFAI_DEBUG=true` in the env section
4. **Check the API key**: Ensure it's correctly set and valid

## License

MIT