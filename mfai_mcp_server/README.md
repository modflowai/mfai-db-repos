# MFAI Repository Navigator MCP Server

A simple Model Context Protocol (MCP) server that provides repository information and search capabilities for groundwater modeling repositories.

## Philosophy

This MCP server is designed as a **simple data provider**. It doesn't make decisions about which repositories are relevant or which search type to use - it just provides the data and lets the LLM make intelligent decisions based on the navigation guides.

## Features

- **Repository listing with navigation guides**: Get all repositories with their navigation metadata
- **Flexible file search**: Text search for exact matches or semantic search for concepts
- **No hardcoded logic**: The server just queries the database and returns results

## Installation

```bash
npm install mfai-repository-navigator
```

## Configuration

Set these environment variables:

```bash
# Required: PostgreSQL connection string
export MODFLOW_AI_MCP_00_CONNECTION_STRING="postgresql://..."

# Optional: OpenAI API key for semantic search
export OPENAI_API_KEY="sk-..."
```

## Claude Desktop Setup

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "node",
      "args": ["/absolute/path/to/mfai_mcp_server/build/index.js"],
      "env": {
        "MODFLOW_AI_MCP_00_CONNECTION_STRING": "postgresql://user:password@host:port/database",
        "OPENAI_API_KEY": "sk-your-openai-api-key"
      }
    }
  }
}
```

Or if you've published to npm:

```json
{
  "mcpServers": {
    "mfai-navigator": {
      "command": "npx",
      "args": ["mfai-repository-navigator"],
      "env": {
        "MODFLOW_AI_MCP_00_CONNECTION_STRING": "postgresql://user:password@host:port/database",
        "OPENAI_API_KEY": "sk-your-openai-api-key"
      }
    }
  }
}
```

## Available Tools

### 1. `list_repositories_with_navigation`

Returns the most recently updated repository with its navigation guide.

**Parameters:**
- `include_navigation` (boolean, default: true): Include navigation guides

**Returns:**
```json
[{
  "id": 1,
  "name": "pest",
  "url": "https://github.com/...",
  "file_count": 150,
  "navigation_guide": "# 🧭 PEST Navigation Guide\n\n## 🎯 Primary Purpose\n...",
  "repository_type": "calibration_tool"
}]
```

The navigation guide is a markdown document that explains:
- What the repository does
- When to use text vs semantic search
- What it integrates with
- Expert domains

### 2. `search_files`

Search for the most relevant file using text or semantic search.

**Parameters:**
- `query` (string, required): Your search query
- `search_type` (string, required): Either "text" or "semantic"
- `repositories` (array of strings, optional): Filter to specific repositories

**Returns:**
```json
[{
  "id": 123,
  "repo_name": "pest",
  "filepath": "src/pest_control.f90",
  "content": "...",
  "rank": 0.95,
  "snippet": "...<<<matched text>>>..."
}]
```

## How the LLM Should Use These Tools

1. **Finding repositories**: Call `list_repositories_with_navigation` and read the navigation guides to understand what each repository does

2. **Deciding on search type**: The navigation guides explain when to use text vs semantic search:
   - Text search: For specific keywords, function names, error messages
   - Semantic search: For concepts, workflows, "how to" questions

3. **Filtering repositories**: Based on the user's query and the navigation guides, decide which repositories to search

## Database Schema

The server expects:
- `repositories` table with:
  - `metadata` JSONB column containing `navigation_guide` and `repository_type`
- `repository_files` table with:
  - Full-text search index (`content_tsvector`)
  - Optional vector embeddings (`embedding`)

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Development
npm run dev
```

## Key Design Principles

1. **Simple data provider**: No query analysis, no relevance scoring, no routing logic
2. **Let the LLM decide**: The LLM reads navigation guides and makes decisions
3. **Transparent**: What you query is what you get
4. **Efficient**: Direct database queries with proper indexes

## License

MIT