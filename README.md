# mfai_db_repos Python

A repository processing system built with Python and PostgreSQL that provides a fast, efficient CLI tool for cloning Git repositories, analyzing their contents, and storing them in a structured database with vector embeddings. Designed for building RAG (Retrieval-Augmented Generation) systems for scientific and technical documentation.

```bash
# Process a Git repository with a single command:
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/username/repository.git
```

✨ **Recent Updates**: 
- **Robust JSON Processing**: Resolved complex escape sequence handling in code analysis with base64 encoding and custom parsing
- **Domain-Aware Analysis**: Optimized for scientific computing, groundwater modeling, and parameter estimation domains
- **Enhanced Error Reporting**: Removed fallbacks to enable proper debugging of analysis failures
- **Failed File Tracking**: Detailed reporting of which files failed processing and why

✨ **New Feature**: mfai_db_repos now supports [Neon DB](https://neon.tech/) for serverless PostgreSQL deployments, enabling scalable cloud-based operation without managing your own database server.

## Features

- **Repository Processing**: Clone and index Git repositories with comprehensive file analysis
- **Scientific Domain Support**: Optimized for groundwater modeling (MODFLOW 6, MODFLOW-USG), parameter estimation (PEST++, PEST), and scientific computing
- **Robust Analysis Pipeline**: 
  - Base64 encoding for complex code with escape sequences
  - Custom parsing format to avoid JSON validation issues
  - Domain-aware content analysis considering diverse technical audiences
  - No fallback values - proper error tracking for debugging
- **AI-Powered Analysis**: Google Gemini for structured content analysis with scientific domain awareness
- **Vector Embeddings**: OpenAI embeddings for semantic search and RAG applications
- **Database Support**: PostgreSQL with pgvector extension, including serverless Neon DB support
- **Private Repository Support**: Automatic GitHub token handling for private repositories
- **Configurable Processing**: File type filtering, batch processing, and parallel execution
- **Comprehensive CLI**: Full command-line interface for all operations
- **Failed File Tracking**: Detailed reporting of processing failures with specific file paths

## Installation

### Prerequisites

On Ubuntu/Debian systems, you may need to install the Python venv package first:

```bash
# Generic Python venv package
sudo apt install python3-venv

# Or for a specific Python version (e.g., Python 3.10)
sudo apt install python3.10-venv
```

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/mfai_db_repos-py.git
cd mfai_db_repos-py

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Option 1: Install all dependencies directly (recommended for new installations)
pip install -r requirements.txt

# Option 2: Install using pyproject.toml
pip install -e .

# Option 3: Install using uv (faster alternative)
pip install uv
uv pip install -e .

# If you encounter "No module named X" errors, install the specific dependency:
pip install chardet python-magic pgvector
```

> **Note**: This project uses both pyproject.toml and requirements.txt. The pyproject.toml is the primary dependency definition, while requirements.txt contains pinned versions and additional development dependencies. If you encounter dependency issues, try installing directly from requirements.txt.

## Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Check type hints
mypy .

# Run linting
ruff check .
```

## Database Setup

### Local PostgreSQL with Docker

```bash
# Start PostgreSQL with pgvector using Docker
docker-compose up -d
```

Note: This project uses the pgvector extension for PostgreSQL. If you encounter an error like "vector object has no attribute _set_parent_with_dispatch", make sure to install the pgvector Python package:

```bash
pip install pgvector
```

### Using Neon DB (Serverless PostgreSQL)

mfai_db_repos also supports [Neon DB](https://neon.tech/), a serverless PostgreSQL service:

1. Create a Neon account and database:
   - Sign up at [neon.tech](https://neon.tech/)
   - Create a new project
   - Create a database named `mfai_db_repos`
   - Create a role with a password
   - Enable the pgvector extension in your database settings

2. Configure mfai_db_repos for Neon DB:
   ```bash
   # Add to your .env file
   DB_HOST=your-project-id.neon.tech
   DB_PORT=5432
   DB_USER=your-username
   DB_PASSWORD=your-password
   DB_NAME=mfai_db_repos
   DB_SSLMODE=require
   DB_SERVERLESS=true
   DB_USE_POOLER=true  # Recommended for better connection management
   ```

3. Initialize the database extensions before first use:
   ```bash
   python -m mfai_db_repos.cli.main database init
   ```

4. Use mfai_db_repos as normal:
   ```bash
   python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git
   ```

Serverless PostgreSQL considerations:
- Connection pooling is recommended for Neon DB
- Cold starts may occasionally cause initial slowness
- Vector search uses HNSW indexes for better performance on Neon DB

## Configuration

Create a `.env` file in the project root directory to configure API keys and other settings:

```bash
# OpenAI API key for embeddings
OPENAI_API_KEY=your-openai-api-key

# Google GenAI API key for structured analysis
GOOGLE_GENAI_API_KEY=your-google-api-key

# GitHub personal access token for private repositories
GITHUB_TOKEN=your-github-token

# Optional configuration
BATCH_SIZE=5               # Number of files to process in each batch
PARALLEL_WORKERS=5         # Number of parallel workers for API calls
MAX_FILE_SIZE_MB=10        # Maximum file size to process in MB
```

## Command Line Interface

mfai_db_repos provides a comprehensive CLI for managing repositories, files, and database operations.

### Repository Processing

The main way to use mfai_db_repos is to process a repository with a single command:

```bash
# Process a repository by URL (main command)
python3 -m mfai_db_repos.cli.main process repository --repo-url https://github.com/username/repository.git

# Example with different Python command format
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git

# Process a private repository (uses GITHUB_TOKEN from .env file)
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/yourusername/private-repo.git

# Override GitHub token for a specific command
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/yourusername/private-repo.git --github-token YOUR_TOKEN

# Process an existing repository by ID
python -m mfai_db_repos.cli.main process repository --repo-id 1

# Process with a limit on number of files
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git --limit 50

# Process with a specific batch size (default: 5)
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git --batch-size 10

# Process with a specific branch
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git --branch develop

# Process with verbose logging
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git -v

# Include test files and directories (excluded by default)
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git --include-tests

# Include README context for better file analysis
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git --include-readme
```

#### Update Single File

Update individual files without reprocessing the entire repository:

```bash
# Update README.md in repository with ID 1
python -m mfai_db_repos.cli.main process file --repo-id 1 --filepath README.md

# Update a documentation file with README context
python -m mfai_db_repos.cli.main process file --repo-id 2 --filepath docs/guide.md --include-readme

# Update with verbose logging
python -m mfai_db_repos.cli.main process file --repo-id 1 --filepath README.md -v
```

This is perfect for:
- Updating README.md files after adding table of contents
- Refreshing frequently changing documentation
- Updating configuration files
- Processing newly added files

The single file update:
1. Pulls latest changes from the repository
2. Verifies the file exists
3. Regenerates analysis and embeddings
4. Updates the existing database record (or creates if new)

See [Single File Update Documentation](docs/single-file-update.md) for more details.

The processing utilizes parallel execution to maximize efficiency:

- Multiple files are processed concurrently within each batch
- Multiple batches are processed in parallel
- Concurrency is carefully managed with semaphores to prevent API rate limiting
- All file changes are committed in atomic transactions per batch
- Retry logic with exponential backoff for API failures

#### Complete Processing Workflow

The repository processing command performs a complete workflow:

1. Loads the repository (either from the database if it exists or clones it if needed)
2. Extracts all files from the repository
3. Processes each file in parallel batches with:
   - Content extraction and base64 encoding for safe transmission
   - Git metadata extraction
   - AI analysis with Gemini model using custom parsing format
   - Domain-aware analysis considering scientific/technical audiences
   - Retry logic with exponential backoff (up to 10 attempts)
   - OpenAI embedding generation for semantic search
   - Atomic database storage per batch

#### Processing Robustness

The system includes several robustness improvements:

- **Base64 Content Encoding**: All file content is base64-encoded before analysis to handle complex escape sequences and special characters safely
- **Custom Response Format**: Uses delimited format (===SECTION===) instead of JSON to avoid parsing issues with code content
- **No Fallback Values**: System fails explicitly when critical fields (potential_questions, keywords, etc.) cannot be extracted, enabling proper debugging
- **Failed File Tracking**: Detailed logging and reporting of which specific files failed processing
- **Domain-Aware Analysis**: Prompts optimized for scientific computing, groundwater modeling, and parameter estimation domains
- **Increased Retry Logic**: Up to 10 retry attempts with exponential backoff for transient API failures

#### README Context Integration

The system includes an advanced README context integration feature that significantly improves file analysis accuracy by providing the AI with project context when analyzing individual files.

**Usage:**
```bash
# Enable README context integration
python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git --include-readme
```

**How it works:**
- README content is extracted once at the beginning of repository processing
- The README (up to 15,000 characters) is included as context for every file analysis
- File content is limited to 45,000 characters when README is included (vs 60,000 without)
- The AI uses this context to better understand the project's purpose and architecture

**Benefits:**
- **Better Understanding**: AI knows what the overall project does before analyzing files
- **Architecture Awareness**: Understands how individual files fit into the project structure
- **Improved Analysis**: More accurate titles, summaries, and keyword extraction
- **Relationship Context**: Better identification of how components relate to each other

### Repository Management

Commands for managing repositories in the database.

```bash
# List all repositories
python -m mfai_db_repos.cli.main repositories list

# Get details for a specific repository by ID
python -m mfai_db_repos.cli.main repositories get 1

# Add a repository without processing
python -m mfai_db_repos.cli.main repositories add https://github.com/example/repo.git

# Add a repository with a specific branch
python -m mfai_db_repos.cli.main repositories add https://github.com/example/repo.git --branch main

# Update an existing repository to latest commit
python -m mfai_db_repos.cli.main repositories update 1

# Delete a repository
python -m mfai_db_repos.cli.main repositories delete 1
```

### File Management

Commands for managing repository files.

```bash
# Process files in a repository (without full reprocessing)
python -m mfai_db_repos.cli.main files process -r 1

# Process files with options
python -m mfai_db_repos.cli.main files process -r 1 --limit 20 --workers 3 --max-size 5.0

# List files in a repository
python -m mfai_db_repos.cli.main files list -r 1

# List files with filtering and pagination
python -m mfai_db_repos.cli.main files list -r 1 --pattern "*.py" --limit 50 --offset 20

# Show file status and statistics
python -m mfai_db_repos.cli.main files status -r 1
```

### Embedding Management

Commands for managing and generating embeddings.

```bash
# Generate embeddings for a repository
python -m mfai_db_repos.cli.main embeddings generate -r 1

# Generate embeddings for all repositories
python -m mfai_db_repos.cli.main embeddings generate --all

# Show embedding information for a repository
python -m mfai_db_repos.cli.main embeddings info -r 1
```

### Database Management

Commands for managing the database.

```bash
# Reset the database (drops and recreates all tables)
python -m mfai_db_repos.cli.main database reset

# Reset without confirmation prompt
python -m mfai_db_repos.cli.main database reset --force

# Reset with verbose output
python -m mfai_db_repos.cli.main database reset --verbose

# Initialize database extensions (required for Neon DB)
python -m mfai_db_repos.cli.main database init

# Remove a repository and all its files from the database
python -m mfai_db_repos.cli.main database remove-repo 1

# Remove by repository URL
python -m mfai_db_repos.cli.main database remove-repo https://github.com/example/repo.git
```

> **Note**: The `database reset` command only works with local Docker PostgreSQL setups. For Neon DB, you should manage the database through the Neon web interface and use the `database init` command to set up extensions.

### Configuration

Commands for viewing and modifying configuration.

```bash
# List all configuration settings
python -m mfai_db_repos.cli.main config --list

# Get a specific configuration value
python -m mfai_db_repos.cli.main config --get openai.api_key

# Set a configuration value
python -m mfai_db_repos.cli.main config --set openai.api_key --value "your-api-key"
```

### Status and Help

Commands for getting system status and help.

```bash
# Show system status
python -m mfai_db_repos.cli.main status

# Show general help
python -m mfai_db_repos.cli.main help

# Show help for a specific topic
python -m mfai_db_repos.cli.main help repositories
python -m mfai_db_repos.cli.main help process
python -m mfai_db_repos.cli.main help database
```


## License

MIT
