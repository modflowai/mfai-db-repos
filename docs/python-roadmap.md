# GitContext Python Implementation Roadmap

This roadmap outlines the development plan for rebuilding GitContext as a Python-based system with UV package management.

## Changelog

### 2025-05-27
- **Added Single File Update Feature**: Implemented functionality to update individual files without reprocessing entire repositories
  - Created `update_single_file()` method in RepositoryProcessingService
  - Added new CLI command `process file` for targeted file updates
  - Particularly useful for updating README.md files with TOCs
  - Enables efficient documentation updates without full repository reprocessing
- **Discovered README Search Challenge**: Found that README files are difficult to find with standard search tools
  - FTS and vector search are optimized for content within files, not overview documents
  - Led to new insights about needing specialized tools for documentation discovery
- **Developed Hybrid README Rebuilding Strategy**: Created more efficient approach for rebuilding comprehensive READMEs
  - Combines direct file access with existing database analysis
  - Avoids search tool limitations while leveraging AI analysis already done
  - Uses extraction script to get summaries, concepts, and questions from database
  - Synthesizes perfect READMEs with navigation guides and search hints

### 2025-05-26
- **Fixed JSON Parsing Issues**: Resolved persistent JSON validation errors when processing complex code files
  - Implemented base64 encoding for content transmission to handle escape sequences
  - Switched from JSON to custom delimited format (===SECTION===) for Gemini responses
  - Created robust parsing logic for extracting structured data
- **Removed Fallback Values**: Eliminated all fallback values to enable proper error debugging
  - System now fails explicitly when critical fields cannot be extracted
  - Enables identification of problematic content patterns
- **Enhanced Domain Awareness**: Updated analysis prompts for scientific computing domains
  - Optimized for groundwater modeling (MODFLOW), parameter estimation (PEST), and technical documentation
  - Analysis now considers diverse audiences: scientists, engineers, modelers, researchers
  - Improved potential question generation for RAG applications
- **Improved Error Reporting**: Added detailed failed file tracking
  - Processing now reports specific file paths that failed
  - Helps identify patterns in processing failures
- **Configuration Updates**:
  - Increased retry attempts from 3 to 10 for API resilience
  - Increased content limits from 60k to 500k characters
  - Added .ipynb files to default processing patterns
  - Switched from Gemini 2.5 Flash Preview to Gemini 2.0 Flash for stability

### 2025-05-17
- Created Python virtual environment (.venv)
- Set up uv Python environment with pip
- Created project structure with gitcontext package
- Created core configuration files (pyproject.toml, setup.cfg)
- Set up linting and typing tools (pytest, mypy, black, isort, ruff)
- Implemented logging and configuration management system
- Set up Docker Compose with PostgreSQL + pgvector on port 5437
- Added database schema initialization script
- Implemented database models and repositories for storing repository data
- Created Git operations module for repository cloning and file extraction
- Implemented embedding generation modules for OpenAI and Google GenAI
- Added batch processing and parallel API calls for efficient embedding generation
- Created CLI commands for managing embeddings
- Implemented comprehensive command-line interface (CLI) for all operations
- Added rich terminal UI with progress bars and interactive displays
- Implemented core models and services layer
- Updated database connection handling to use asyncio and SQLAlchemy async
- Fixed dependency issues and implemented proper async database operations
- Tested with flopy repository (https://github.com/modflowpy/flopy.git)
- Fixed file filtering to correctly handle .py and .md files with improved glob pattern matching
- Fixed repository database field mappings and parameter handling
- Processed 484 files from the flopy repository (466 Python files, 18 Markdown files)
- Implemented database initialization script with clean reset functionality
- Implemented embedded string generation from structured Gemini analysis output
- Created scripts for generating and testing embeddings with parallel processing
- Generated embeddings for flopy repository using OpenAI's text-embedding-3-small model
- Generated structured content analysis using Google's Gemini 2.0 Flash model
- Implemented configuration from gitcontext-config.json for API keys and model parameters
- Enhanced structured analysis to include comprehensive document analysis
- Implemented detailed code snippet analysis and extraction in structured responses
- Enhanced embedding string generation with potential questions, technical level, and other metadata
- Created database cleanup script with options for selective cleaning
- Added component properties extraction in the structured analysis
- Improved analysis prompt with detailed instructions for Gemini
- Added filtering to skip empty files during processing and embedding generation
- Enhanced database cleanup script with option to clean only empty files
- Added content validation to ensure meaningful embeddings from non-empty files

## Phase 1: Project Setup and Core Infrastructure

### 1.1 Environment and Project Setup (Week 1)
- [x] Create Python virtual environment (.venv)
- [x] Set up uv Python environment
- [x] Create project structure and package configuration
- [x] Configure linting, typing, and testing tools
- [x] Establish logging and configuration management
- [x] Set up Docker Compose for PostgreSQL with pgvector on port 5437

### 1.2 Database Implementation (Week 1-2)
- [x] Implement database schema
- [x] Create SQLAlchemy models for repository files
- [x] Implement database connection and session management

### 1.3 Git Operations (Week 2)
- [x] Implement repository cloning functionality
- [x] Add repository update and status checking
- [x] Create file extraction and content parsing
- [x] Implement incremental file processing
- [x] Add metadata extraction for repositories and files
- [x] Implement file type selection and filtering
- [x] Add configurable inclusion/exclusion patterns

## Phase 2: Core Functionality

### 2.1 Repository Indexing (Week 3) ✅
- [x] Implement Git repository cloning and update operations
- [x] Create PostgreSQL database models for repositories and files
- [x] Implement blob content extraction from Git repositories
- [x] Add file metadata extraction (size, type, modification date)
- [x] Create database storage operations for repository data
- [x] Implement efficient file filtering with glob patterns
- [x] Add pattern-based inclusion/exclusion of files
- [x] Create update detection for incremental repository processing
- [x] Implement proper error handling for Git operations
- [x] Create status tracking for repository operations

### 2.2 File Processing (Week 3-4) ✅
- [x] Implement file type detection and language identification
- [x] Create content normalization and preprocessing
- [x] Add support for different file encodings
- [x] Implement file status tracking for incremental updates
- [x] Add support for ignoring certain files/directories
- [x] Create content extraction pipeline
- [x] Filter out empty files from database
- [x] Implement efficient pattern matching for file selection
- [x] Add transaction support for file batch processing

### 2.3 Embedding Generation (Week 4) ✅
- [x] Integrate with OpenAI API for embeddings
- [x] Implement Google GenAI SDK with structured schema responses
- [x] Set up Pydantic models for type-safe AI responses
- [x] Implement JSON schema validation for Gemini responses
- [x] Implement embedding generation for file content
- [x] Add batch processing for efficient API usage
- [x] Implement parallel API calls for Gemini and OpenAI
- [x] Configure default of 5 parallel workers for API calls
- [x] Set up embedding configuration management
- [x] Create asynchronous worker pool for concurrent processing
- [x] Implement rate limiting and backoff strategies
- [x] Add monitoring for API call efficiency
- [x] Implement real-time progress tracking
- [x] Generate rich structured analysis of content using Gemini
- [x] Create comprehensive embedding strings from structured analysis
- [x] Support code snippet extraction and analysis
- [x] Implement component properties analysis

### 2.4 Complete Processing Pipeline (Week 5) ✅

- [x] Enhance file processor to populate all database fields in one complete workflow:
  - Store file content and basic metadata
  - Capture and store git metadata including commit hash
  - Generate and store tsvector from content
  - Generate complete Gemini analysis and store full JSON
  - Extract and store file_type, technical_level, and tags
  - Create embedding string from analysis
  - Generate and store embedding vector
  - Process files in consistent batches of 5 with proper transactions

- [x] Test the complete pipeline with flopy repository:
  - Use clean_db.py to reset the database
  - Start by processing the first 5 files to verify field population
  - Continue processing in 5-file batches until completion
  - Log detailed information for each batch
  - Verify all database fields are properly populated
  - Create validation queries to confirm data integrity

## Phase 3: CLI and User Experience

### 3.1 Command Line Interface (Week 4-5) ✅
- [x] Design CLI structure and command hierarchy
- [x] Implement repository management commands
  - [x] Add/remove repositories
  - [x] List repositories
  - [x] Update repositories
  - [x] File type selection options
  - [x] Pattern-based inclusion/exclusion
- [x] Implement output formatting and display options
- [x] Add configuration management commands
- [x] Add commands to modify file selection for existing repositories
- [x] Implement rich progress bars for repository processing
- [x] Add real-time status indicators for long operations
- [x] Create visual feedback for embedding generation
- [x] Display file count and processing statistics
- [x] Create database management commands
- [x] Add embedding generation commands

### 3.2 Database Management Tools (Week 5) ✅
- [x] Implement database reset and cleanup script
- [x] Create empty file cleaning functionality
- [x] Add selective embedding clearing option
- [x] Implement repository-specific operations
- [x] Add confirmation prompts for destructive operations
- [x] Create database initialization scripts
- [x] Add status reporting for database operations

### Dependencies
- **Core**:
  - Python 3.10+
  - uv (for package management)
  - SQLAlchemy
  - psycopg2-binary
  - GitPython
  - Click (for CLI)
  - pydantic (for data validation)
  - openai (for embeddings)
  - google-genai (for Gemini API integration)
  - rich (for progress bars and terminal UI)
  - asyncio (for async operations)
  - aiohttp (for async HTTP requests)

- **Database**:
  - PostgreSQL 14+ (via Docker Compose)
  - pgvector extension
  - Port 5437 for PostgreSQL connection


## Project Status and Milestones

### Completed Milestones
- ✅ **Repository Indexing System**: Successfully implemented a robust system for cloning and indexing Git repositories
- ✅ **File Processing Pipeline**: Efficiently processes repository files, filters by patterns, and stores in PostgreSQL
- ✅ **Advanced Content Analysis**: Implemented comprehensive analysis of file contents using Google Gemini
- ✅ **Embedding Generation**: Successfully generates high-quality vector embeddings from structured file analysis
- ✅ **Database Storage**: Implemented efficient storage of repositories, files, content, and vector embeddings


### Next Steps
- ✅ Refine file filtering to correctly handle .py and .md files
- ✅ Setup correct embedding generation approach for Google GenAI
- ✅ Add concurrent processing for file batches
- ✅ Improve repository processing with better progress tracking
- ✅ Implement enhanced structured analysis with comprehensive metadata
- ✅ Filter out empty files from database
- ✅ Complete the processing pipeline to populate all database fields in one workflow:
  - ✅ Store git metadata and generate tsvector
  - ✅ Keep full analysis JSON and extract metadata
  - ✅ Process files in consistent batches of 5
  - ✅ Add proper error handling and transaction management
  - ✅ Use environment variables (.env) for configuration
- ✅ Implement single file update functionality for efficient documentation updates

### Phase 4: Navigation Metadata System for MCP Enhancement

**Important Pivot**: We're shifting from building comprehensive documentation to creating concise navigation metadata that enhances MCP tool intelligence. The goal is navigation guides (max 2 pages) that help LLMs choose the right tools and repositories, not detailed documentation.

#### 4.1 Navigation Metadata Builder ✅ (Refined Single-Step Approach)

**Initial Attempt: 2-Step Mechanical + LLM** (Abandoned)
- ❌ Built mechanical pattern extractor that counted frequencies
- ❌ Generated poor examples (JCOORDER vs NOPTMAX)
- ❌ Required hardcoded "known" parameters
- ❌ Not robust across different repositories

**✅ Final Solution: Direct Gemini Analysis**
- **✅ Comprehensive README as Input**: Use existing detailed README (500+ lines)
- **✅ Single Gemini 2.5 Pro Call**: Feed entire README to model for intelligent analysis
- **✅ Data-Driven Extraction**: Let AI determine importance from actual content
- **✅ MCP-Optimized Output**: Generate navigation guide specifically for LLM tool selection

**Accomplished:**
```bash
# Complete workflow achieved:
1. python -m mfai_db_repos.cli.main process repository --repo-url URL --include-readme
2. python -m mfai_db_repos.tools.readme_builder analyzed_repos/pest --repo-name pest
3. python -m mfai_db_repos.tools.navigation_gemini analyzed_repos/pest/README.md pest
4. python -m mfai_db_repos.tools.update_repo_metadata pest --navigation-file analyzed_repos/pest/NAVIGATION_FINAL.md
```

**Key Innovation**: Instead of mechanical pattern extraction, we use the comprehensive README as rich context for Gemini to intelligently extract:
- Real parameters users search for (NOPTMAX, PHIMLIM, PESTMODE)
- Actual query patterns from domain expertise
- Specific tool selection logic (FTS vs Vector)
- Repository authority rankings with explanations
- Integration context and workflow tips

**Output**: 85-line navigation guide with actionable intelligence for MCP tools

**✅ Database Integration Completed:**
- **Clone path properly set**: `analyzed_repos/pest` stored in repositories.clone_path
- **Navigation in metadata**: 86-line guide stored in repositories.metadata JSON field
- **Single source of truth**: MCP tools access navigation directly from database
- **Clean file system**: Only README.md needed per repository

**Final Optimized Workflow** (1 file + database):
1. Generate `README.md` via readme_builder (comprehensive analysis)
2. Generate navigation guide via navigation_gemini (temporary file)
3. Store in database metadata via update_repo_metadata (permanent storage)

**Benefits:**
- Navigation accessible to MCP tools via database queries
- No separate navigation files to maintain
- Proper repository metadata population (clone_path, navigation_guide)
- Clean separation: README for humans, metadata for AI tools

#### 4.2 Database Schema Enhancements ✅ (Realistic Implementation)

**Fields We Can Actually Populate Now:**
- **✅ `repository_type`**: 'code' | 'documentation' | 'hybrid' (calculated from file extensions)
- **✅ Enhanced `metadata` JSON**: Store navigation_guide, repository_type, file_statistics
- **✅ `readme_content`**: TEXT field for quick README access (future enhancement)
- **✅ Proper `clone_path`**: Ensure it's populated during processing

**Schema Update for Immediate Implementation:**
```sql
-- These fields already exist, just need proper population:
-- clone_path TEXT (populate with 'analyzed_repos/{name}')
-- metadata JSON (expand to include navigation guide + stats)

-- Future consideration (not implemented now):
-- ALTER TABLE repositories ADD COLUMN readme_content TEXT;
```

**Repository Classification Logic:**
- Documentation repo: >70% markdown files
- Code repo: >70% code files (.py, .js, .ts, etc.)
- Hybrid: Mixed content

**Deferred to Future Phases:**
- ❌ expertise_scores (needs usage data)
- ❌ navigation_patterns table (needs tracking over time)
- ❌ tool_interoperability (needs multi-repo analysis)

#### 4.3 MCP Tool Evolution (TypeScript Codebase)
- **Transform `repo_list` → `repo_navigator`**:
  - Return navigation metadata with repository lists
  - Include expertise scores for intelligent repository selection
  - Suggest best repository based on query analysis
  
- **Enhance Search Result Context**:
  - Add navigation hints to all search results
  - Include "why this result" explanations
  - Suggest next search patterns
  - Reference relevant navigation guide sections

### Phase 5: Incremental Repository Updates

#### 5.1 Implement Git-Based Change Detection
- **Track Last Processed Commit**:
  - Store last processed commit hash in repository metadata
  - Compare with current HEAD to detect changes
  - Build list of modified files since last processing
  
- **Implement Selective File Processing**:
  - Process only files that have changed since last update
  - Handle file additions, modifications, and deletions
  - Update embeddings only for changed content
  - Maintain database consistency during incremental updates
  
- **Add Incremental Update Command**:
  - Create `update repository --incremental` CLI command
  - Show statistics of files added/modified/deleted
  - Provide option to force full reprocessing if needed
  - Log incremental update history for debugging

#### 5.2 Optimize for Large Repository Updates
- **Batch Processing Improvements**:
  - Detect and group related file changes
  - Process files in optimal order (dependencies first)
  - Implement smart batching based on file size and type
  
- **Performance Monitoring**:
  - Track time saved using incremental vs full updates
  - Monitor API usage reduction from incremental processing
  - Generate reports on update efficiency
  
- **Conflict Resolution**:
  - Handle cases where database and repository are out of sync
  - Implement recovery mechanisms for failed partial updates
  - Add validation checks to ensure data integrity