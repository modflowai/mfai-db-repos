"""
Main entry point for the GitContext CLI.
"""

import click
import logging
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from dotenv import load_dotenv

from mfai_db_repos.cli.commands import (
    embeddings_group, repositories_group, files_group, process_group, database_group
)
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import setup_logging

# Create console for rich output
console = Console()

# Load .env file first
dotenv_path = Path(os.getcwd()) / '.env'
if dotenv_path.exists():
    console.print(f"[dim]Loading environment from {dotenv_path}[/dim]")
    load_dotenv(dotenv_path=dotenv_path)
else:
    console.print(f"[yellow]Warning: No .env file found at {dotenv_path}[/yellow]")

# Load application configuration
config = Config()
config.load_from_env()  # Explicitly load from environment


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "--verbose", "-v", 
    is_flag=True, 
    default=False, 
    help="Enable verbose output"
)
def cli(verbose):
    """MFAI DB Repos - Repository indexing and retrieval system."""
    # Configure logging based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)


# Register command groups
cli.add_command(repositories_group)
cli.add_command(embeddings_group)
cli.add_command(files_group)
cli.add_command(process_group)
cli.add_command(database_group)


@cli.command("config")
@click.option("--list", "list_all", is_flag=True, help="List all configuration settings")
@click.option("--get", help="Get a specific configuration value")
@click.option("--set", "set_key", help="Configuration key to set")
@click.option("--value", help="Value to set for the configuration key")
def config_command(list_all, get, set_key, value):
    """View and manage configuration settings."""
    if list_all:
        console.print("[bold]Configuration settings:[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Key")
        table.add_column("Value")
        
        for key, val in config.get_all().items():
            # Skip sensitive values
            if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
                val = "********"
            table.add_row(key, str(val))
        
        console.print(table)
    
    elif get:
        value = config.get(get)
        if value is None:
            console.print(f"[yellow]Warning:[/yellow] Configuration key '{get}' not found")
        else:
            # Skip sensitive values
            if "key" in get.lower() or "token" in get.lower() or "secret" in get.lower():
                value = "********"
            console.print(f"{get}: {value}")
    
    elif set_key and value is not None:
        config.set(set_key, value)
        console.print(f"[green]Success:[/green] Set '{set_key}' to '{value}'")
    
    else:
        console.print(Panel(
            "Usage Examples:\n"
            "--list              View all configuration settings\n"
            "--get KEY           View a specific configuration value\n"
            "--set KEY --value VALUE  Set a configuration value",
            title="Configuration Options",
            expand=False
        ))


@cli.command("status")
def status_command():
    """Show system status and statistics."""
    try:
        async def run_status():
            from mfai_db_repos.lib.database.connection import get_session
            from mfai_db_repos.lib.database.repository import RepositoryRepository
            from mfai_db_repos.lib.database.repository_file import RepositoryFileRepository
            
            status_table = Table(title="MFAI DB Repos Status", show_header=True, header_style="bold")
            status_table.add_column("Component")
            status_table.add_column("Status")
            status_table.add_column("Details")
            
            # Database connection
            try:
                async with get_session() as session:
                    status_table.add_row("Database", "[green]Connected[/green]", "PostgreSQL database is available")
                    
                    # Repository statistics
                    repo_repo = RepositoryRepository(session)
                    file_repo = RepositoryFileRepository(session)
                    
                    repos = await repo_repo.get_all()
                    repo_count = len(repos)
                    
                    total_files = 0
                    embedded_files = 0
                    
                    for repo in repos:
                        repo_files = await file_repo.count_by_repository_id(repo.id)
                        repo_embedded = repo_files - await file_repo.count_files_without_embeddings(repo.id)
                        
                        total_files += repo_files
                        embedded_files += repo_embedded
                    
                    status_table.add_row(
                        "Repositories", 
                        f"[blue]{repo_count}[/blue]", 
                        f"{total_files} files indexed"
                    )
                    
                    embedding_coverage = 0
                    if total_files > 0:
                        embedding_coverage = embedded_files / total_files * 100
                    
                    status_table.add_row(
                        "Embeddings",
                        f"[blue]{embedded_files}/{total_files}[/blue]",
                        f"{embedding_coverage:.1f}% coverage"
                    )
            except Exception as e:
                status_table.add_row("Database", "[red]Error[/red]", str(e))
            
            console.print(status_table)
        
        import asyncio
        asyncio.run(run_status())
    except Exception as e:
        console.print(f"[red]Error retrieving status:[/red] {str(e)}")


@cli.command("help")
@click.argument("topic", required=False)
def help_command(topic):
    """Show detailed help and usage examples."""
    # Main help topics
    help_topics = {
        "database": """
# Database Management

Manage the PostgreSQL database for MFAI DB Repos.

## Commands

* `mfai_db_repos database reset` - Reset the database (WARNING: Deletes all data)
* `mfai_db_repos database remove-repo <repository>` - Remove a specific repository and all its files

## Reset Database Examples

```bash
# Reset the database with confirmation prompt
python -m mfai_db_repos.cli.main database reset

# Reset the database without confirmation
python -m mfai_db_repos.cli.main database reset --force

# Reset with verbose output
python -m mfai_db_repos.cli.main database reset --verbose
```

The reset command stops Docker containers, removes database volumes, and restarts the containers with a fresh database.

## Remove Repository Examples

```bash
# Remove repository by ID
python -m mfai_db_repos.cli.main database remove-repo 1

# Remove repository by name
python -m mfai_db_repos.cli.main database remove-repo my-repo-name

# Remove repository by URL
python -m mfai_db_repos.cli.main database remove-repo https://github.com/user/repo.git

# Remove repository without confirmation
python -m mfai_db_repos.cli.main database remove-repo 1 --force
```

The remove-repo command removes a specific repository and all its files from the database without affecting other repositories.
""",
        "repositories": """
# Repository Management

Manage Git repositories in MFAI DB Repos.

## Commands

* `mfai_db_repos repositories add <url>` - Add a new repository
* `mfai_db_repos repositories list` - List all repositories
* `mfai_db_repos repositories get <id>` - Get details about a repository
* `mfai_db_repos repositories update <id>` - Update a repository
* `mfai_db_repos repositories delete <id>` - Delete a repository

## Examples

```
# Add a new repository
mfai_db_repos repositories add https://github.com/example/repo.git

# List all repositories
mfai_db_repos repositories list

# Update a repository to the latest commit
mfai_db_repos repositories update 1
```
""",
        "embeddings": """
# Embedding Management

Generate and manage vector embeddings for repository files.

## Commands

* `mfai_db_repos embeddings generate -r <repo_id>` - Generate embeddings for a repository
* `mfai_db_repos embeddings generate --all` - Generate embeddings for all repositories
* `mfai_db_repos embeddings info -r <repo_id>` - Show embedding info for a repository

## Examples

```
# Generate embeddings for repository with ID 1
mfai_db_repos embeddings generate -r 1

# Generate embeddings for all repositories
mfai_db_repos embeddings generate --all

# Show embedding info for repository with ID 1
mfai_db_repos embeddings info -r 1
```
""",
        "files": """
# File Processing

Process and manage repository files.

## Commands

* `mfai_db_repos files process -r <repo_id>` - Process files in a repository
* `mfai_db_repos files status -r <repo_id>` - Show file processing status
* `mfai_db_repos files list -r <repo_id>` - List files in a repository
* `mfai_db_repos files search -r <repo_id> -q <query>` - Search files using vector similarity

## Examples

```
# Process files in repository with ID 1
mfai_db_repos files process -r 1

# Show file status for repository with ID 1
mfai_db_repos files status -r 1

# List files in repository with ID 1
mfai_db_repos files list -r 1 --limit 20

# Search files in repository with ID 1
mfai_db_repos files search -r 1 -q "How do I install this library?"
```
""",
        "process": """
# Complete Repository Processing

Process repositories with a comprehensive workflow that performs all steps in a single pass.

## Commands

* `mfai_db_repos process repository --repo-url <url>` - Process a repository by URL
* `mfai_db_repos process repository --repo-id <id>` - Process a repository by ID
* `mfai_db_repos process repository --batch-size <n>` - Set batch size (default: 5)

## Examples

```
# Process a repository by URL with default batch size (5)
mfai_db_repos process repository --repo-url https://github.com/modflowpy/flopy.git

# Process a repository by ID with a custom batch size
mfai_db_repos process repository --repo-id 1 --batch-size 5

# Process only the first 10 files of a repository
mfai_db_repos process repository --repo-id 1 --limit 10
```

This command performs the complete processing workflow for each file:
1. Extract file content and metadata
2. Capture git metadata including commit hash
3. Generate comprehensive Gemini analysis
4. Extract metadata from analysis (file_type, technical_level, tags)
5. Create embedding string from analysis
6. Generate embedding vector
7. Process files in batches with proper transactions
""",
        "config": """
# Configuration Management

View and manage MFAI DB Repos configuration.

## Commands

* `mfai_db_repos config --list` - List all configuration settings
* `mfai_db_repos config --get <key>` - Get a specific configuration value
* `mfai_db_repos config --set <key> --value <value>` - Set a configuration value

## Examples

```
# List all configuration settings
mfai_db_repos config --list

# Get OpenAI API key (masked)
mfai_db_repos config --get openai.api_key

# Set OpenAI API key
mfai_db_repos config --set openai.api_key --value "your-api-key"
```
"""
    }
    
    if topic and topic in help_topics:
        # Show help for specific topic
        console.print(Markdown(help_topics[topic]))
    elif topic:
        # Unknown topic
        console.print(f"[yellow]Unknown help topic:[/yellow] {topic}")
        console.print("Available topics: repositories, embeddings, files, process, config")
    else:
        # Show general help
        console.print(Panel(
            "MFAI DB Repos is a tool for indexing and embedding Git repositories.\n\n"
            "Available help topics:\n"
            "  * repositories - Repository management commands\n"
            "  * embeddings - Embedding generation and management\n"
            "  * files - File processing and management\n"
            "  * process - Complete repository processing workflow\n"
            "  * config - Configuration settings\n\n"
            "Use 'mfai_db_repos help <topic>' for detailed information.",
            title="MFAI DB Repos Help",
            expand=False
        ))


def main():
    """Main entry point for the application."""
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()