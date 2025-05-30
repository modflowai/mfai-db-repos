"""
CLI commands for processing repositories with the complete workflow.

This module provides CLI commands for processing repositories with the
complete workflow, including file extraction, content analysis, embedding
generation, and database storage.
"""
import asyncio
from typing import Optional

import click

from mfai_db_repos.core.services.processing_service import RepositoryProcessingService
from mfai_db_repos.utils.logger import setup_logging

@click.group()
def process():
    """Process repositories with comprehensive file analysis and embeddings."""

@process.command()
@click.option(
    "--repo-url",
    help="Repository URL to process (e.g., --repo-url https://github.com/modflowpy/flopy.git)",
    type=str,
    metavar="URL",
)
@click.option(
    "--repo-id",
    help="Repository ID to process (alternative to --repo-url, e.g., --repo-id 1)",
    type=int,
    metavar="ID",
)
@click.option(
    "--branch",
    help="Branch to process (defaults to main/master)",
    type=str,
    metavar="BRANCH",
)
@click.option(
    "--limit",
    help="Limit number of files to process",
    type=int,
    metavar="N",
)
@click.option(
    "--batch-size",
    help="Number of files to process in each batch",
    type=int,
    default=5,
    metavar="SIZE",
)
@click.option(
    "--verbose", "-v",
    help="Enable verbose logging",
    is_flag=True,
)
@click.option(
    "--include-tests",
    help="Include test files and directories in processing",
    is_flag=True,
)
@click.option(
    "--github-token",
    help="GitHub personal access token for private repositories",
    type=str,
    metavar="TOKEN",
    envvar="GITHUB_TOKEN",
)
@click.option(
    "--include-readme",
    help="Include repository README.md content in file analysis for better context",
    is_flag=True,
)
def repository(
    repo_url: Optional[str] = None,
    repo_id: Optional[int] = None,
    branch: Optional[str] = None,
    limit: Optional[int] = None,
    batch_size: int = 5,
    verbose: bool = False,
    include_tests: bool = False,
    github_token: Optional[str] = None,
    include_readme: bool = False,
):
    """Process a repository with the complete workflow.
    
    REQUIRED: You must specify EITHER --repo-url OR --repo-id.
    
    Examples:
      python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git
      python -m mfai_db_repos.cli.main process repository --repo-id 1 --limit 20
      python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git --include-tests
      python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/private-repo.git --github-token YOUR_TOKEN
    
    This command will:
    1. Clone/update the repository if needed
    2. Extract files from the repository
    3. Process each file with a complete workflow:
       - Extract content and metadata
       - Generate tsvector for full-text search
       - Create comprehensive Gemini analysis
       - Generate OpenAI embeddings 
       - Store all data in the database
    
    Files are processed in batches of 5 by default, with each batch
    handled in a single database transaction.
    
    By default, test files and directories are excluded. Use the --include-tests flag
    to process test files and directories as well.
    
    For private GitHub repositories, you can provide a GitHub personal access token:
    - Use the --github-token option OR
    - Set the GITHUB_TOKEN environment variable in your .env file
    """
    # Set up logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)
    
    # Validate arguments
    if not repo_url and not repo_id:
        click.echo("Error: Either --repo-url or --repo-id must be specified.")
        click.echo("\nExamples:")
        click.echo("  python -m mfai_db_repos.cli.main process repository --repo-url https://github.com/example/repo.git")
        click.echo("  python -m mfai_db_repos.cli.main process repository --repo-id 1")
        click.echo("\nRun 'python -m mfai_db_repos.cli.main process repository --help' for more information.")
        return
    
    # Set GitHub token in configuration if provided
    if github_token:
        from mfai_db_repos.utils.config import config
        config.update(**{"git.github_token": github_token})
        click.echo(f"Using provided GitHub token for authentication")
    
    # Create processing service
    service = RepositoryProcessingService(batch_size=batch_size)
    
    # Process repository
    try:
        click.echo("Starting repository processing...")
        success, failure, failed_files = asyncio.run(service.process_repository(
            repo_url=repo_url,
            repo_id=repo_id,
            branch=branch,
            limit=limit,
            include_tests=include_tests,
            include_readme=include_readme,
        ))
        
        # Print summary
        click.echo("\nProcessing complete!")
        click.echo(f"Successfully processed: {success} files")
        click.echo(f"Failed to process: {failure} files")
        
        # Print failed files if any
        if failed_files:
            click.echo("\nFailed files:")
            for failed_file in failed_files:
                click.echo(f"  - {failed_file}")
        
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
    except Exception as e:
        import traceback
        click.echo(f"\nError: {str(e)}")
        if verbose:
            click.echo(traceback.format_exc())


@process.command()
@click.option(
    "--repo-id",
    help="Repository ID where the file exists",
    type=int,
    required=True,
    metavar="ID",
)
@click.option(
    "--filepath", 
    help="Path to the file relative to repository root (e.g., README.md)",
    type=str,
    required=True,
    metavar="PATH",
)
@click.option(
    "--include-readme",
    help="Include repository README.md content in file analysis for better context",
    is_flag=True,
)
@click.option(
    "--verbose", "-v",
    help="Enable verbose logging",
    is_flag=True,
)
def file(
    repo_id: int,
    filepath: str,
    include_readme: bool = False,
    verbose: bool = False,
):
    """Update a single file in an existing repository.
    
    This command is useful for updating individual files without reprocessing
    the entire repository. Perfect for updating README.md files or other
    documentation that changes frequently.
    
    Examples:
      python -m mfai_db_repos.cli.main process file --repo-id 1 --filepath README.md
      python -m mfai_db_repos.cli.main process file --repo-id 2 --filepath docs/guide.md --include-readme
    
    This command will:
    1. Pull latest changes from the repository
    2. Extract the specified file content
    3. Regenerate analysis and embeddings
    4. Update the existing database record (or create if new)
    """
    # Set up logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)
    
    # Create processing service
    service = RepositoryProcessingService()
    
    # Process the single file
    try:
        click.echo(f"Updating file '{filepath}' in repository ID {repo_id}...")
        
        success = asyncio.run(service.update_single_file(
            repo_id=repo_id,
            filepath=filepath,
            include_readme=include_readme,
        ))
        
        if success:
            click.echo(f"\n✅ Successfully updated file: {filepath}")
        else:
            click.echo(f"\n❌ Failed to update file: {filepath}")
            click.echo("Check the logs for more details.")
            
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
    except Exception as e:
        import traceback
        click.echo(f"\nError: {str(e)}")
        if verbose:
            click.echo(traceback.format_exc())