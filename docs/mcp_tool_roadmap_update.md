# MCP Tool Roadmap Update: Navigation Metadata Integration

## Executive Summary

This roadmap outlines the transformation of our MCP server tools from basic search interfaces into an intelligent navigation system that leverages the repository navigation metadata stored in our PostgreSQL database.

## Current State

### Existing MCP Tools (TypeScript)
- `modflow_ai_mcp_00_list_repos` - Lists repositories with minimal metadata
- `modflow_ai_mcp_00_fts` - Full-text search across all files
- `modflow_ai_mcp_00_vec` - Vector/semantic search (with OpenAI fallback to FTS)
- `modflow_ai_mcp_00_repo_search` - Repository-specific FTS search

### New Database Capabilities
- Navigation metadata stored in `repositories.metadata` JSON field
- Repository type classification in metadata
- Clone path properly populated
- Navigation guides (85-line structured documents) per repository

## Proposed Architecture

### Option 1: Enhanced Tools with Embedded Navigation (Recommended)

Transform existing tools to return navigation-aware results:

```typescript
// Enhanced repo_list → repo_navigator
{
  name: 'modflow_ai_mcp_00_repo_navigator',
  description: 'Get intelligent repository recommendations with navigation metadata',
  inputSchema: {
    properties: {
      query: { type: 'string', description: 'Optional query to get targeted recommendations' },
      limit: { type: 'number', default: 10 }
    }
  }
}

// Response includes navigation intelligence
{
  repositories: [{
    name: "pest",
    url: "...",
    navigation_summary: {
      primary_purpose: "Parameter estimation and model calibration",
      expertise_domains: ["calibration", "uncertainty", "regularization"],
      search_guidance: {
        use_fts_for: ["PEST keywords", "error messages"],
        use_vector_for: ["calibration strategies", "conceptual questions"]
      },
      integrates_with: ["modflow", "flopy", "pyemu"]
    }
  }]
}
```

### Option 2: MCP Resources for Navigation Metadata

Expose navigation guides as readable resources:

```typescript
// List navigation resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  const repos = await sql`
    SELECT name, metadata->>'navigation_guide' as nav_guide 
    FROM repositories 
    WHERE metadata->>'navigation_guide' IS NOT NULL
  `;
  
  return {
    resources: repos.map(repo => ({
      uri: `navigation://${repo.name}`,
      name: `${repo.name} Navigation Guide`,
      mimeType: "text/markdown"
    }))
  };
});

// Read specific navigation guide
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const repoName = request.params.uri.replace('navigation://', '');
  const result = await sql`
    SELECT metadata->>'navigation_guide' as nav_guide 
    FROM repositories 
    WHERE name = ${repoName}
  `;
  
  return {
    contents: [{
      uri: request.params.uri,
      mimeType: "text/markdown",
      text: result[0].nav_guide
    }]
  };
});
```

## Implementation Plan

### Phase 1: Database Query Enhancement (Week 1)

#### 1.1 Update SQL Queries

```sql
-- Enhanced repository listing with navigation metadata
SELECT 
  r.id, r.name, r.url, r.file_count,
  r.metadata->>'repository_type' as repo_type,
  r.metadata->>'navigation_guide' as navigation_guide,
  r.metadata->'file_statistics' as file_stats
FROM repositories r
WHERE r.metadata->>'navigation_guide' IS NOT NULL
ORDER BY r.updated_at DESC;

-- Search with repository context
SELECT 
  rf.*, 
  r.metadata->>'navigation_guide' as repo_navigation
FROM repository_files rf
JOIN repositories r ON rf.repo_id = r.id
WHERE rf.content_tsvector @@ to_tsquery('english', ${query})
  AND r.metadata->>'navigation_guide' IS NOT NULL;
```

#### 1.2 Create Navigation Parser

```typescript
interface NavigationMetadata {
  primary_purpose: string;
  expertise_domains: string[];
  search_guidance: {
    use_fts_for: string[];
    use_vector_for: string[];
  };
  integrates_with: string[];
  power_user_tips: string[];
}

function parseNavigationGuide(navGuide: string): NavigationMetadata {
  // Extract structured data from markdown navigation guide
  // Parse sections like "🎯 Primary Purpose", "🔍 When to Search", etc.
}
```

### Phase 2: Tool Evolution (Week 2)

#### 2.1 Transform `list_repos` → `repo_navigator`

```typescript
case 'modflow_ai_mcp_00_repo_navigator': {
  const { query, limit } = args;
  
  // Get repos with navigation metadata
  const results = await sql`
    SELECT 
      name, url, file_count,
      metadata->>'navigation_guide' as nav_guide,
      metadata->>'repository_type' as repo_type
    FROM repositories
    WHERE metadata->>'navigation_guide' IS NOT NULL
    ORDER BY updated_at DESC
    LIMIT ${limit}
  `;
  
  // If query provided, rank repositories by relevance
  const enrichedResults = query 
    ? rankRepositoriesByQuery(results, query)
    : results.map(r => ({
        ...r,
        navigation: parseNavigationGuide(r.nav_guide),
        relevance_score: 1.0
      }));
  
  return {
    content: [{
      type: 'text',
      text: JSON.stringify({
        query_analysis: query ? analyzeQueryPattern(query) : null,
        recommended_tool: query ? suggestBestTool(query) : null,
        repositories: enrichedResults
      }, null, 2)
    }]
  };
}
```

#### 2.2 Enhance Search Results with Navigation Context

```typescript
// Add to all search results
function enrichSearchResult(result: SearchResult, repoNavigation: string) {
  const nav = parseNavigationGuide(repoNavigation);
  
  return {
    ...result,
    navigation_context: {
      repository_expertise: nav.expertise_domains,
      related_searches: suggestRelatedSearches(result, nav),
      integration_hints: nav.integrates_with,
      next_steps: generateNextSteps(result, nav)
    }
  };
}
```

### Phase 3: Query Intelligence (Week 3)

#### 3.1 Query Pattern Analyzer

```typescript
interface QueryAnalysis {
  query_type: 'parameter' | 'error' | 'conceptual' | 'workflow';
  recommended_tool: 'fts' | 'vector';
  target_repositories: string[];
  confidence: number;
}

function analyzeQueryPattern(query: string): QueryAnalysis {
  // Detect patterns:
  // - UPPERCASE_WORDS → parameter → FTS
  // - "error" or quoted strings → error message → FTS
  // - "how to" or "?" → conceptual → Vector
  // - Repository names → repo_search
}
```

#### 3.2 Repository Ranking System

```typescript
function rankRepositoriesByQuery(repos: Repository[], query: string): RankedRepository[] {
  return repos.map(repo => {
    const nav = parseNavigationGuide(repo.nav_guide);
    let score = 0;
    
    // Check if query matches expertise domains
    score += calculateDomainMatch(query, nav.expertise_domains) * 0.4;
    
    // Check if query matches recommended search patterns
    score += calculatePatternMatch(query, nav.search_guidance) * 0.3;
    
    // Check for tool name mentions
    score += calculateToolMention(query, repo.name) * 0.3;
    
    return { ...repo, relevance_score: score };
  }).sort((a, b) => b.relevance_score - a.relevance_score);
}
```

### Phase 4: Optional Resource Implementation (Week 4)

If we decide to also implement resources:

```typescript
// Add resource capability
server = new Server(
  { name: 'modflow-ai-mcp-00-server', version: '2.0.0' },
  {
    capabilities: {
      tools: {},
      resources: {
        subscribe: false,
        listChanged: false
      }
    }
  }
);

// Expose navigation guides as resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  const navResources = await sql`
    SELECT name FROM repositories 
    WHERE metadata->>'navigation_guide' IS NOT NULL
  `;
  
  return {
    resources: navResources.map(r => ({
      uri: `mfai://navigation/${r.name}`,
      name: `${r.name} Navigation Guide`,
      mimeType: 'text/markdown',
      description: `Search guidance and expertise map for ${r.name}`
    }))
  };
});
```

## Migration Strategy

### Step 1: Backward Compatibility
- Keep existing tool names as aliases
- Add deprecation notices in descriptions
- Return both old and new response formats

### Step 2: Gradual Enhancement
- Start with `repo_navigator` as most impactful change
- Add navigation context to search results incrementally
- Monitor usage patterns to refine query analysis

### Step 3: Full Migration
- Remove deprecated tools after transition period
- Consolidate to navigation-aware tools only
- Document new query patterns for users

## Success Metrics

1. **Query Routing Accuracy**: >90% of queries routed to optimal tool
2. **Repository Selection**: >85% first repository suggestion is correct
3. **Search Refinement**: 50% reduction in follow-up searches needed
4. **User Satisfaction**: Positive feedback on navigation hints

## Technical Considerations

### Performance
- Cache parsed navigation metadata in memory
- Use database indexes on metadata JSON fields
- Implement connection pooling for concurrent requests

### Error Handling
- Graceful fallback when navigation metadata missing
- Clear error messages for malformed navigation guides
- Logging for query pattern analysis improvements

### Extensibility
- Plugin system for custom query analyzers
- Webhook support for navigation updates
- API versioning for smooth upgrades

## Recommended Approach

**Go with Option 1 (Enhanced Tools)** because:

1. **Simpler Integration**: AI assistants already know how to use tools
2. **Contextual Results**: Navigation data arrives with search results
3. **Backward Compatible**: Existing integrations continue working
4. **Single Request**: No need for separate resource fetches
5. **Natural Evolution**: Tools become smarter, not more complex

Resources would be better suited for:
- Exposing full documentation content
- Providing static reference materials
- Implementing subscription-based updates

## Next Steps

1. Review and approve this roadmap
2. Create TypeScript interfaces for navigation metadata
3. Implement query pattern analyzer
4. Update SQL queries with navigation joins
5. Test with real repository navigation guides
6. Deploy enhanced tools incrementally
7. Monitor usage and refine algorithms

## Code Location Updates

Update `/home/danilopezmella/mfai_db_repos/docs/modflow_ai_mcp_server_tools.md`:

### Line 29-31: Enhance ListReposSchema
```typescript
const ListReposSchema = z.object({
  query: z.string().optional().describe('Optional query for targeted recommendations'),
  limit: z.number().optional().default(10),
});
```

### Line 62-79: Update tool definition
```typescript
{
  name: 'modflow_ai_mcp_00_repo_navigator',
  description: 'Get intelligent repository recommendations with navigation metadata for your query.',
  inputSchema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'Optional query to get targeted repository recommendations'
      },
      limit: {
        type: 'number',
        description: 'Maximum number of repositories to return',
        default: 10,
      },
    },
  },
},
```

### Line 151-170: Replace implementation
```typescript
case 'modflow_ai_mcp_00_repo_navigator': {
  const { query, limit } = ListReposSchema.parse(args);
  
  // Implementation as shown in Phase 2.1 above
  // Returns enriched repository data with navigation intelligence
}
```

### Add navigation parsing utilities after line 27
```typescript
// Navigation metadata interfaces and parsers
interface NavigationMetadata { /* ... */ }
function parseNavigationGuide(navGuide: string): NavigationMetadata { /* ... */ }
function analyzeQueryPattern(query: string): QueryAnalysis { /* ... */ }
function rankRepositoriesByQuery(repos: any[], query: string): any[] { /* ... */ }
```

This roadmap provides a clear path to transform our MCP tools from simple search interfaces into an intelligent navigation system that helps LLMs make optimal decisions about where and how to search for groundwater modeling information.