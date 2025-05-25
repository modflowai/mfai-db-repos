# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

CRITICAL RULE:
- WE DONT USE MOCKS, WE MAKE IT WORK OR MAKE THE USER KNOW AND STOP. MOCKS COVER ERRORS
- ALWAYS .venv 
- KEEP A CLEAN CODEBASE. IF YOU MAKE A TEST PUT IT IN TEST FOLDER. IF YOU MAKE A SCRIPT YOU HAVE TO MAINTAIN IT WITHING THE FILE STRUCTURED - PROPOSED OR MAKE A SPECIFIC FOLDER IF ITS STRICTLY NECCESARY AND YOU HAVE A GOOD REASON (FOR EXAMPLE WE DIDNT KNOW WHEN WE START THE PROJECT THAT WE WOULD NEED IT).
- WE USE google-genai. NO GOOGLE GENERATIVE AI
- STICK TO THE ROADMAP AND UPDATE THE ROADMAP CONTINOUSLY ACCOUNTING THE ACHIEVED TASKS.

### Problem Solving Strategies

- If you are stuck use perplexity sonar pro mcp and ask him giving examples of your issue and why you are stuck or with a new technology you dont might not know like google-genai.

### Search and Research Tools Priority

When encountering questions or tasks requiring additional information, consider using these tools based on the nature of the query:

1. **Perplexity Sonar Pro** (Primary Research Tool)
   - Useful for complex technical questions and specialized knowledge
   - Ideal for detailed explanations and up-to-date technical information
   - Great for understanding new technologies, libraries, and frameworks
   - Effective for synthesizing diverse viewpoints and technical comparisons

2. **Context7** (Library Documentation Specialist)
   - Provides up-to-date, version-specific documentation directly from the source
   - Offers real, working code examples instead of potentially hallucinated ones
   - Delivers concise, relevant information with no filler
   - Particularly valuable when working with npm packages and libraries
   - Helps avoid outdated documentation from training data
   - Especially useful for the GitContext project's key dependencies

3. **Brave Search** (Supporting Research Tool)
   - Good for general web searches and finding relevant websites
   - Useful for locating documentation, articles, and tutorials
   - Beneficial for discovering community discussions and forum posts
   - Helpful for finding code examples and implementation patterns

### Usage Guidelines

```bash
# Perplexity Sonar Pro for deep technical understanding
/mcp perplexity-search "detailed technical query requiring expert explanation"

# Context7 for library-specific documentation and APIs
/mcp context7 resolve-library-id "library-name"
/mcp context7 get-library-docs "context7-compatible-library-id"

# Brave Search for locating resources and examples
/mcp brave-search "query to find documentation, tutorials, or code examples"
```


## Project Overview

GitContext Python is a repository indexing system built with Python and PostgreSQL. It focuses on providing a fast, efficient CLI tool for cloning Git repositories and storing their contents in a structured database with vector embeddings.

### Core Architecture

- **Database Layer**: PostgreSQL with pgvector extension for storing repository data and vector embeddings
- **Git Operations**: GitPython for repository cloning and content extraction
- **File Processing**: Language detection, content extraction, and metadata handling
- **Vector Embeddings**: OpenAI Embeddings with Google GenAI SDK for structured responses
- **CLI Interface**: Command-line tools for repository management

## Development Environment Setup

```bash
# Set up uv Python environment (recommended)
pip install uv
uv venv

# Database setup
docker-compose up -d  # Starts PostgreSQL with pgvector on port 5437

# Install dependencies (when requirements.txt is created)
uv pip install -r requirements.txt
```

## Expected Directory Structure

```
gitcontext/
├── cli/               # Command-line interface
│   ├── commands/      # Individual command implementations
│   └── main.py        # CLI entry point
├── core/              # Core functionality
│   ├── models/        # Data models
│   └── services/      # Business logic services
├── lib/               # Library code
│   ├── database/      # Database connection and repositories
│   ├── embeddings/    # Vector embedding generation
│   ├── file_processor/# File content and metadata extraction
│   └── git/           # Git operations
├── utils/             # Utility functions
│   ├── config.py      # Configuration management
│   └── logger.py      # Logging setup
├── tests/             # Test suite
```

## Development Commands

These commands will be implemented as the project progresses:

```bash
# Running the application (when implemented)
python -m gitcontext.cli.main

# Running tests (when implemented)
pytest tests/
pytest tests/unit/  # Unit tests only
pytest tests/integration/  # Integration tests only

# Running type checking (when implemented)
mypy .

# Running linters (when implemented)
ruff check .
black . --check

# Formatting code (when implemented)
black .
```

## Key Technologies

- **Python 3.10+**: Core programming language
- **SQLAlchemy**: ORM for database interactions
- **PostgreSQL 14+ with pgvector**: For vector embeddings storage
- **GitPython**: For Git repository operations
- **OpenAI SDK**: For embedding generation
- **Google GenAI SDK**: For structured AI responses
- **Pydantic**: For data validation and type safety

## API Implementations

For embedding generation, the project will use:

### OpenAI API
```python
from openai import OpenAI

client = OpenAI()

response = client.embeddings.create(
    model="text-embedding-ada-002",
    input=["Sample text to embed"],
)
```

### Google GenAI API with Structured Responses
```python
from google import genai
from google.genai import types
from pydantic import BaseModel

# Define structured response schema
class FileAnalysis(BaseModel):
    title: str
    summary: str
    key_concepts: list[str]
    potential_questions: list[str]
    keywords: list[str]

# Generate structured analysis
client = genai.GenerativeModel('gemini-2.0-flash-001')
response = client.generate_content(
    contents=f"Analyze the following file...",
    generation_config=types.GenerationConfig(
        temperature=0.2,
        max_output_tokens=8192,
    ),
    response_mime_type='application/json',
    response_schema=FileAnalysis,
)

# Extract structured result
analysis_result = FileAnalysis.model_validate_json(response.text)
```

## README Context Integration

The system includes an advanced README context integration feature that significantly improves file analysis accuracy:

### 🔄 **README Integration Flow:**

1. **Extraction (Once per Repository)**
   - README.md is extracted once when processing starts using `--include-readme` flag
   - Content is validated and stored for the entire session
   - Supports multiple README formats (README.md, readme.md, etc.) and handles symlinks properly

2. **Content Management & Limits**
   - README content is truncated to **15,000 characters** if longer
   - File content is truncated to **45,000 characters** (vs 60K without README)
   - Total prompt stays under ~60K characters to respect token limits

3. **Prompt Structure Integration**
   When README content exists, the analysis prompt is structured as:
   ```
   # Analysis Task
   # Repository Context (from README):
   [FULL README CONTENT HERE]

   Analyze the following file content and provide comprehensive structured information...

   [FILE CONTENT HERE]

   # Analysis Instructions:
   - Use the repository context (if provided) to better understand the project's purpose and architecture
   - Use the repository context to explain how this code or content fits into the broader project architecture
   ```

4. **Explicit AI Instructions**
   The analysis instructions explicitly tell Gemini to:
   - Use the repository context to understand the project's purpose and architecture
   - Explain how individual files fit into the broader project ecosystem
   - Generate more contextually aware titles, summaries, and relationship mappings

### 🎯 **Benefits of README Context:**

- **Project Understanding**: AI knows what the overall project does before analyzing individual files
- **Architecture Awareness**: Understands project structure and purpose for better component analysis
- **Relationship Context**: Can explain how specific files fit into the broader project ecosystem
- **Purpose Clarity**: Better titles and summaries that reference the project's actual purpose
- **Component Relationships**: Identifies how individual components relate to the project's main functionality

### 💡 **Usage:**
```bash
# Enable README context integration
python -m gitcontext.cli.main process repository --include-readme --repo-url https://github.com/username/repository.git
```

This feature transforms isolated file analysis into contextually aware analysis that understands how each piece contributes to the overall project architecture.

## Important Notes

- The database runs on port 5437 (not the default 5432) to avoid conflicts
- Content truncation is applied to very large files (60,000 character limit)
- Parallel processing is used for embedding generation (5 workers by default)
- Support for configurable file filtering based on patterns and extensions