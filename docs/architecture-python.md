# GitContext Python Architecture

## Overview

GitContext Python is a repository indexing system built with Python and PostgreSQL. It focuses on providing a fast, efficient CLI tool for cloning Git repositories and storing their contents in a structured database with vector embeddings.

## Core Components

### 1. Database Layer

- **PostgreSQL with pgvector** for storing repository data and vector embeddings
- **Docker Compose** for PostgreSQL deployment using port 5437
- **SQLAlchemy** for ORM and database interactions
- **Single table design** similar to the TypeScript version:
  - Repository metadata (URL, name, branch)
  - File metadata (path, type, size)
  - File content and embeddings
  - Full-text search and vector embeddings

### 2. Git Operations

- **GitPython** for repository cloning and content extraction
- Support for:
  - Repository cloning
  - Updating existing repositories
  - Extracting file content and metadata
  - Branch and commit tracking
  - Selective file inclusion based on patterns or extensions
  - Configurable file filtering for repository indexing

### 3. File Processing

- Language detection and file type analysis
- Content extraction and normalization
- Metadata extraction (size, last modified, etc.)
- Status tracking for incremental processing
- **File Type Selection**:
  - Configurable inclusion/exclusion patterns
  - Support for filtering by extension (e.g., `.py`, `.md`, `.js`)
  - Support for filtering by path patterns (e.g., `src/**/*.ts`)
  - Exclusion of binary files, build artifacts, etc. by default
  - Custom filter configuration via configuration file

### 4. Vector Embeddings

- **OpenAI Embeddings** for generating vector representations
- Embedding caching for performance optimization
- Configurable embedding models and parameters
- **Google GenAI SDK** with structured response schemas:
  - Schema-enforced responses using `types.GenerateContentConfig`
  - Structured analysis using Pydantic models
  - Type-safe handling of AI responses

#### Embedding Generation Process

The system uses a comprehensive approach to generate embeddings that capture the semantic meaning of repository files. At the core of this process is the analysis prompt used to create the structured embedding string:

```python
def create_analysis_prompt(content: str, file_type: str, filename: str) -> str:
    """
    Creates a prompt for AI analysis of file content
    """
    return f"""
    Analyze the following {file_type} file '{filename}' and create a structured document embedding in JSON format.
    
    # Content to analyze:
    ```
    {truncate_content(content, 60000)}
    ```
    
    # Analysis Instructions:
    
    ## Document Analysis:
    - Analyze the content to identify the key components, patterns, and architecture
    - For code files, identify the programming paradigms, design patterns, and architecture
    - Note dependencies and relationships between components
    
    ## Title Creation:
    - Create a concise title that clearly indicates the document's purpose
    - Format consistently with naming conventions
    - Include specific class/function names if it's code
    
    ## Semantic Summary Generation:
    - Create a comprehensive summary (250-400 words) that captures the semantic essence of the document
    - Explain how this code or content fits into a broader architecture
    - For code files, describe its purpose, when to use it, and how it differs from similar components
    - Include specific class names, method signatures, parameter names, and return types where relevant
    
    ## Key Concepts Extraction:
    - Identify 5-10 core concepts discussed in the document
    - Include both explicit concepts (mentioned by name) and implicit concepts
    
    ## Potential Questions Generation:
    - Generate 8-12 natural language questions that this document would answer
    - Include different query formulations that developers might use
    
    ## Code Snippet Analysis:
    - Extract all code examples with their context
    - For each snippet, identify:
      - The language
      - What the code demonstrates
      - Key classes, methods, and parameters used
      - Expected output or behavior
    
    ## Component Properties Extraction:
    - Identify the component type
    - Document key API elements (classes, functions, methods, parameters)
    - List required and optional elements
    - Note interactions with other components
    
    ## Keyword Extraction:
    - Extract 15-20 keywords that represent important technical terms
    - Include specific class names, parameter names, and method names
    
    # Response Format:
    
    Provide the response in a valid JSON format following this structure:
    
    {{
      "title": "A concise, descriptive title for the document",
      "summary": "A comprehensive summary (250-400 words)",
      "key_concepts": ["Concept 1", "Concept 2", "Concept 3", ...],
      "potential_questions": ["Question 1?", "Question 2?", "Question 3?", ...],
      "code_snippets": [
        {{
          "language": "Language name (e.g., python)",
          "purpose": "What this code demonstrates",
          "code": "The actual code snippet",
          "summary": "A concise 2-3 sentence summary of this specific snippet"
        }},
        ...
      ],
      "code_snippets_overview": "A consolidated 150-200 word summary of all code snippets (required only if there are more than 3 snippets)",
      "snippet_count": 0,
      "component_properties": {{
        "component_type": "Type of component",
        "api_elements": ["Class1", "Method1", "Parameter1", ...],
        "required_parameters": ["param1", "param2", ...],
        "optional_parameters": ["param1", "param2", ...],
        "related_components": ["Component1", "Component2", ...]
      }},
      "keywords": ["keyword1", "keyword2", "keyword3", ...],
      "related_topics": ["Topic1", "Topic2", "Topic3", ...],
      "document_type": "Code/Documentation/Tutorial/etc.",
      "technical_level": "Beginner/Intermediate/Advanced",
      "prerequisites": ["Prerequisite1", "Prerequisite2", ...],
      "document_hierarchy": {{
        "section": "Main section",
        "subsection": "Subsection if applicable",
        "related_pages": ["URL1", "URL2", ...]
      }}
    }}
    
    Ensure all JSON is valid and properly formatted. If certain fields cannot be determined from the content, use reasonable defaults or leave as empty arrays/objects.
    """

def truncate_content(content: str, max_length: int) -> str:
    """
    Truncates content to the specified maximum length
    """
    if len(content) <= max_length:
        return content
    
    return content[:max_length] + "\n[Content truncated due to length]"
```

The overall embedding generation process consists of the following steps:

1. **Content Analysis**: Each file undergoes deep semantic content analysis using the prompt above, including:
   - Extraction of key concepts and terminology
   - Identification of code structures and patterns
   - Detection of programming language features
   - Documentation and comment processing

2. **Structured Embedding String Generation**: The embedding string is generated in a structured JSON format with these fields:
   - `title`: A concise, descriptive title for the document
   - `summary`: A comprehensive summary (250-400 words)
   - `key_concepts`: 5-10 core concepts discussed in the document
   - `potential_questions`: 8-12 natural language questions the document would answer
   - `code_snippets`: Details of code examples with language, purpose, and summary
   - `code_snippets_overview`: Consolidated summary of all code snippets
   - `component_properties`: Technical details about the code component
   - `keywords`: 15-20 important technical terms
   - `related_topics`: Related technical topics
   - `document_type`: Classification of the document type
   - `technical_level`: Beginner/Intermediate/Advanced classification
   - `prerequisites`: Required knowledge or dependencies
   - `document_hierarchy`: Document structure and related pages

3. **Embedding Generation Pipeline**:
   - File content is prepared and truncated if necessary (60,000 character limit)
   - The prompt is generated with file-specific information
   - **Parallel processing**:
     - Files are batched for efficient processing
     - **5 parallel workers by default** for API calls (configurable)
     - Multiple AI model requests run concurrently
     - Asynchronous processing of embeddings with asyncio
     - Worker pools for CPU-bound operations
     - Task queues with prioritization for efficient processing
     - **Real-time progress tracking** with completion percentage
   - **Google GenAI SDK implementation**:
     ```python
     from google import genai
     from google.genai import types
     from pydantic import BaseModel
     
     # Define structured response schema with Pydantic
     class FileAnalysis(BaseModel):
         title: str
         summary: str
         key_concepts: list[str]
         potential_questions: list[str]
         code_snippets: list[dict]
         keywords: list[str]
         # Additional fields as defined in the schema
     
     # Initialize Gemini client
     genai.configure(api_key="YOUR_API_KEY")
     client = genai.GenerativeModel('gemini-2.0-flash-001')
     
     # Generate structured analysis with enforced schema
     response = client.generate_content(
         contents=f"Analyze the following {file_type} file '{filename}'...",
         generation_config=types.GenerationConfig(
             temperature=0.2,
             max_output_tokens=8192,
             top_p=0.95,
         ),
         response_mime_type='application/json',
         response_schema={
             "type": "OBJECT",
             "required": ["title", "summary", "key_concepts", "potential_questions", "keywords"],
             "properties": {
                 "title": {"type": "STRING"},
                 "summary": {"type": "STRING"},
                 "key_concepts": {"type": "ARRAY", "items": {"type": "STRING"}},
                 "potential_questions": {"type": "ARRAY", "items": {"type": "STRING"}},
                 "code_snippets": {
                     "type": "ARRAY",
                     "items": {
                         "type": "OBJECT",
                         "properties": {
                             "language": {"type": "STRING"},
                             "purpose": {"type": "STRING"},
                             "code": {"type": "STRING"},
                             "summary": {"type": "STRING"}
                         }
                     }
                 },
                 "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
                 # Additional schema properties...
             }
         }
     )
     
     # Extract structured result
     analysis_result = FileAnalysis.model_validate_json(response.text)
     ```
   - The resulting structured response is validated and normalized
   - Conversion to vector representation using OpenAI's embedding model
   - Results are aggregated and processed in parallel

4. **Considerations by File Type**:
   - **Code Files**: Focus on function signatures, class definitions, import statements, and meaningful comments
   - **Documentation**: Extract headings, key points, examples, and conceptual information
   - **Configuration**: Identify configuration parameters, their purpose, and possible values
   - **Data Files**: Analyze structure, schema, and data relationships

5. **Optimization Techniques**:
   - Truncation of very large files to focus on the most representative content
   - Strategic sampling of content sections for consistent representation
   - Special handling of binary files through metadata analysis
   - Language-specific preprocessing for improved semantic understanding

### 5. CLI Interface

- Repository management commands
- Configuration management
- Support for direct repository name resolution
- **File Selection Options**:
  - Commands to add repositories with specific file type filters
  - Support for including only particular languages or file types
  - Command-line arguments for file pattern inclusion/exclusion
  - Options to update file type selection for existing repositories
- **User Experience**:
  - Rich progress bars for repository processing
  - Real-time status indicators for long-running operations
  - Visual feedback on embedding generation progress
  - File count and processing statistics
  - Estimated time remaining for operations

## Technical Design Decisions

### Asynchronous Processing

- Async database operations for improved throughput
- Concurrent file processing and embedding generation
- Batch operations for efficiency
- **Parallel API Processing**:
  - Parallel API calls to Gemini for file analysis
  - Parallel calls to OpenAI for embedding generation
  - Asynchronous request pooling with throttling
  - Rate limiting to respect API quotas
  - Automatic retry with backoff for failed requests
  - Connection pooling for efficient HTTP requests

### Type Safety

- Extensive use of Python type hints
- Input validation and error handling
- Mypy integration for static type checking

### Performance Considerations

- Embedding caching to minimize API calls
- Incremental repository updates
- Optimized PostgreSQL queries with proper indexes

### Extensibility

- Modular design allowing for future extensions
- Support for alternative embedding models

## Directory Structure

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
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── pyproject.toml     # Project configuration
└── README.md          # Documentation
```

## Key Interfaces

### Database Schema

```sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE repository_files (
    id SERIAL PRIMARY KEY,
    -- Repository information
    repo_url TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    repo_branch TEXT,
    repo_commit_hash TEXT,
    repo_metadata JSONB,
    -- File information
    filepath TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT,
    file_size INTEGER,
    last_modified TIMESTAMP,
    git_status TEXT,
    -- Content and embedding columns
    content TEXT,
    content_tsvector TSVECTOR,
    embedding_string TEXT,
    embedding VECTOR(1536),
    -- Metadata
    analysis JSONB,
    tags TEXT[],
    file_type TEXT,
    technical_level TEXT,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Constraints
    CONSTRAINT unique_file UNIQUE (repo_url, filepath)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_repository_files_repo_url ON repository_files(repo_url);
CREATE INDEX IF NOT EXISTS idx_repository_files_extension ON repository_files(extension);
CREATE INDEX IF NOT EXISTS idx_repository_files_tags ON repository_files USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_repository_files_content_tsvector ON repository_files USING GIN(content_tsvector);
CREATE INDEX IF NOT EXISTS idx_repository_files_embedding ON repository_files USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_repository_files_filepath ON repository_files(filepath);

```

**Docker Compose Configuration:**

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg14-v0.5.1
    container_name: gitcontext-postgres
    ports:
      - "5437:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: gitcontext
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command: ["postgres", "-c", "max_connections=100", "-c", "shared_buffers=256MB"]
    restart: always

volumes:
  postgres_data:
```

### Core Service Interfaces

The Python implementation will maintain clean interfaces between components, with key services including:

- **RepositoryService**: Managing git repositories
- **FileProcessorService**: Processing file content and metadata
- **EmbeddingService**: Generating and managing vector embeddings
- **DatabaseService**: Handling database operations

Each service will be designed with clear responsibilities and interfaces to ensure maintainability and testability.