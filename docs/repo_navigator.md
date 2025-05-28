# Repository Navigator Enhancement Plan

## Current State vs. Vision

### Where We Are Now

We've successfully built:
- **Database with AI Analysis**: 8 repositories indexed with comprehensive file analysis
- **README Builder Tool**: Creates detailed human-readable documentation
- **Single File Update**: Can update individual files without full reprocessing
- **Working MCP Tools**: Basic search functionality (FTS, Vector, repo search)

### Where We Need to Be

Transform READMEs from documentation into **intelligent navigation metadata** that enhances MCP tool responses.

## The Vision: READMEs as Navigation Intelligence

Instead of comprehensive documentation, we need **concise navigation guides** that help LLMs:
1. Choose the right repository for a query
2. Select the optimal search tool (FTS vs Vector)
3. Navigate to relevant sections efficiently
4. Understand repository relationships

## The Problem We're Solving

Current MCP tool ambiguity:
- "technical terms" vs "conceptual queries" is subjective
- No guidance on which repository contains what
- No query pattern recognition
- Missing tool selection logic

## Target Output Structure

### 1. Navigation-Focused README (Max 2 pages)

```markdown
# PEST - Navigation Guide

## 🎯 Primary Purpose
Parameter estimation and model calibration tool for groundwater modeling workflows.

## 🔍 Search Guidance
- **Use FTS for:** PEST keywords (PARLBND, PHIMLIM), error messages, control file parameters
- **Use Vector for:** "how to calibrate", "regularization strategies", "sensitivity analysis"
- **Skip this repo for:** model construction, visualization, time series analysis

## 📊 Query Router
| If searching for... | Pattern | Use Tool | Example |
|-------------------|---------|----------|---------|
| Control variables | ALL_CAPS | FTS | "RELPARMAX" |
| Error messages | "error:" | FTS | "error: singular matrix" |
| Concepts | "how to" | Vector | "how to regularize" |
| Theory | "explain" | Vector | "explain SVD-assist" |

## 🏷️ Repository Expertise
**Authoritative for:** parameter estimation, calibration, uncertainty analysis
**Key concepts:** Jacobian, objective function, pilot points, regularization
**Not for:** model building, post-processing, visualization

## 🔗 Integration Context
- **Reads from:** MODFLOW outputs, observation files
- **Writes to:** parameter files, uncertainty matrices
- **Works with:** FloPy (model setup), pyEMU (uncertainty workflows)
```

### 2. Database Metadata (JSON)

```json
{
  "repository_id": 21,
  "repository_type": "documentation",
  "navigation_metadata": {
    "primary_purpose": "Parameter estimation and model calibration tool",
    "expertise_score": {
      "parameter_estimation": 10,
      "model_calibration": 10,
      "uncertainty_analysis": 9,
      "visualization": 1,
      "model_construction": 2
    },
    "query_routing": {
      "fts_triggers": ["ERROR:", "WARNING:", "UPPERCASE_WORDS", "quoted strings"],
      "vector_triggers": ["how to", "what is", "explain", "why", "when to use"],
      "skip_triggers": ["plot", "visualize", "construct model", "grid generation"]
    },
    "integration_patterns": {
      "reads": ["modflow_outputs", "observation_files"],
      "writes": ["parameter_files", "jacobian_matrices"],
      "complements": ["flopy", "pyemu", "modflow"]
    }
  },
  "search_guidance": {
    "strong_match_keywords": ["pest", "calibration", "parameter", "estimation"],
    "exclude_keywords": ["visualization", "plotting", "grid"],
    "common_query_patterns": [
      {"pattern": "pest error", "tool": "fts"},
      {"pattern": "calibration workflow", "tool": "vector"},
      {"pattern": "PARUBND", "tool": "fts"}
    ]
  }
}
```

## Implementation Phases

### Phase 1: Refactor Current Builder (Week 1)

**Goal**: Transform from documentation builder to navigation metadata extractor

1. **Reduce Output Size**
   - Cap at ~100 lines regardless of repo size
   - Focus on patterns, not enumeration
   - Extract top 10-20 navigation hints

2. **Add Pattern Recognition**
   - Scan for ERROR/WARNING patterns
   - Identify parameter naming conventions
   - Extract workflow indicators

3. **Generate Router Tables**
   - Query pattern → Tool mapping
   - Common searches → Best approach
   - Integration hints from content

### Phase 2: Enhance Database Schema (Week 1-2)

```sql
-- Add navigation columns
ALTER TABLE repositories 
  ADD COLUMN repository_type VARCHAR(20), -- 'code', 'documentation', 'hybrid'
  ADD COLUMN navigation_metadata JSON,
  ADD COLUMN expertise_scores JSON,
  ADD COLUMN query_routing_rules JSON;

-- Track successful patterns
CREATE TABLE navigation_patterns (
  id SERIAL PRIMARY KEY,
  pattern TEXT,
  pattern_type VARCHAR(50),
  recommended_tool VARCHAR(20),
  success_rate FLOAT,
  usage_count INTEGER DEFAULT 1
);
```

### Phase 3: Enhance MCP Tools (Week 2)

1. **Transform `repo_list` → `repo_navigator`**
   - Return navigation metadata with each repo
   - Include expertise scores
   - Suggest best repo for query

2. **Enhance Search Results**
   - Add "why this result" explanation
   - Include next search suggestions
   - Reference navigation guide sections

## Key Decisions Needed

### 1. Navigation Guide Generation Approach

**Option A: Pure Extraction**
- Mine patterns from existing analysis
- Aggregate automatically
- Risk: May miss nuances

**Option B: Hybrid with Gemini Polish** ✓ (Recommended)
- Extract structure and patterns
- Use Gemini to write concise navigation prose
- Single API call per repo for polish

### 2. Repository Classification

We need to classify repos:
- **PEST, PEST++**: Documentation-heavy
- **FloPy, pyEMU**: Code-heavy  
- **MODFLOW**: Hybrid

This affects navigation strategy.

### 3. File Grouping Strategy

For large repos:
- Group by module/package
- Extract top patterns per group
- Maintain fixed output size

## Success Metrics

1. **Navigation guide < 100 lines** for any repo size
2. **Query routing accuracy > 80%** (correct tool selection)
3. **Integration patterns identified** for 75% of repos
4. **LLM can choose correct repo** 90% of time

## Next Steps

1. **Refactor README builder** → Navigation metadata extractor
2. **Process PEST** as proof of concept
3. **Enhance database schema** with navigation columns
4. **Test with MCP tools** to verify improvement

## Example: PEST Navigation Extraction

From 44 PEST documentation files, extract:
- **Primary purpose**: 1 sentence
- **Top 5 FTS patterns**: ERROR:, PEST keywords
- **Top 5 Vector patterns**: Conceptual questions  
- **Key expertise areas**: 3-5 domains
- **Integration hints**: From documentation references

Output: Concise navigation guide + JSON metadata for database.

## The Paradigm Shift

We're not building documentation - we're building **intelligent routing metadata** that makes every MCP tool query more effective. The README becomes a GPS system for navigating repository knowledge.