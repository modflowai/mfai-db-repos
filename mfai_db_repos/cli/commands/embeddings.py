"""
CLI commands for managing embeddings.
"""
import asyncio
import logging
import sys
import time
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from mfai_db_repos.core.services.embedding_service import EmbeddingService
from mfai_db_repos.lib.database.connection import get_session
from mfai_db_repos.lib.database.repository import RepositoryRepository
from mfai_db_repos.lib.database.repository_file import RepositoryFileRepository
from mfai_db_repos.lib.embeddings.manager import EmbeddingManager
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)
console = Console()


@click.group(name="embeddings", help="Manage and generate embeddings")
def embeddings_group():
    """Command group for embedding operations."""


@embeddings_group.command(name="generate", help="Generate embeddings for repository files")
@click.option(
    "--repository", "-r",
    help="Repository ID to generate embeddings for",
    type=int,
    required=False,
)
@click.option(
    "--all", "-a",
    help="Process all repositories",
    is_flag=True,
    default=False,
)
@click.option(
    "--limit", "-l",
    help="Limit number of files to process",
    type=int,
    default=None,
)
@click.option(
    "--only-new", "-n",
    help="Only process files without embeddings",
    is_flag=True,
    default=True,
)
@click.option(
    "--provider", "-p",
    help="Embedding provider to use (openai, google_genai)",
    type=click.Choice(["openai", "google_genai"]),
    default="openai",
)
@click.option(
    "--batch-size", "-b",
    help="Number of files to process in a batch",
    type=int,
    default=20,
)
@click.option(
    "--concurrency", "-c",
    help="Maximum number of concurrent API requests",
    type=int,
    default=5,
)
@click.option(
    "--verbose", "-v",
    help="Enable verbose logging",
    is_flag=True,
    default=False,
)
def generate_embeddings(
    repository: Optional[int],
    all: bool,
    limit: Optional[int],
    only_new: bool,
    provider: str,
    batch_size: int,
    concurrency: int,
    verbose: bool,
):
    """Generate embeddings for repository files."""
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    if not repository and not all:
        console.print("[red]Error:[/] Must specify either --repository or --all")
        sys.exit(1)
    
    # Load configuration
    config = Config()
    
    # Setup embedding manager
    embedding_manager = EmbeddingManager(
        primary_provider=provider,
        max_parallel_requests=concurrency,
        batch_size=batch_size,
    )
    
    # Create service
    async def run():
        async with get_session() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            embedding_service = EmbeddingService(
                config=config,
                repository_file_repo=file_repo,
                embedding_manager=embedding_manager,
            )
            
            if repository:
                # Get repository by ID
                repo = await repo_repo.get_by_id(repository)
                if not repo:
                    console.print(f"[red]Error:[/] Repository with ID {repository} not found")
                    return
                
                console.print(f"Generating embeddings for repository: [bold]{repo.name}[/bold]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    console=console,
                ) as progress:
                    # First, get count of files to be processed
                    if only_new:
                        file_count = await file_repo.count_files_without_embeddings(repository)
                    else:
                        file_count = await file_repo.count_by_repository_id(repository)
                    
                    # Adjust limit if needed
                    if limit is not None and limit < file_count:
                        file_count = limit
                    
                    task = progress.add_task(
                        f"Generating embeddings ({file_count} files)",
                        total=file_count,
                    )
                    
                    # Create progress tracking callback
                    async def progress_callback(current, total):
                        progress.update(task, completed=current)
                    
                    # Process repository with progress tracking
                    start_time = time.time()
                    success, failure = await embedding_service.process_repository(
                        repository_id=repository,
                        limit=limit,
                        only_new=only_new,
                        show_progress=False,
                    )
                    elapsed = time.time() - start_time
                    
                    progress.update(task, completed=file_count)
                
                console.print(
                    f"Completed in {elapsed:.2f}s: [green]{success}[/green] succeeded, "
                    f"[red]{failure}[/red] failed, [bold]{success + failure}[/bold] total"
                )
            
            elif all:
                # Get all repositories
                repos = await repo_repo.get_all()
                if not repos:
                    console.print("[yellow]Warning:[/] No repositories found")
                    return
                
                console.print(f"Generating embeddings for [bold]{len(repos)}[/bold] repositories")
                
                total_success = 0
                total_failure = 0
                start_time = time.time()
                
                for repo in repos:
                    console.print(f"Processing repository: [bold]{repo.name}[/bold]")
                    
                    success, failure = await embedding_service.process_repository(
                        repository_id=repo.id,
                        limit=limit,
                        only_new=only_new,
                        show_progress=True,
                    )
                    
                    total_success += success
                    total_failure += failure
                    
                    console.print(
                        f"Repository completed: [green]{success}[/green] succeeded, "
                        f"[red]{failure}[/red] failed"
                    )
                
                elapsed = time.time() - start_time
                console.print(
                    f"All repositories completed in {elapsed:.2f}s: "
                    f"[green]{total_success}[/green] succeeded, "
                    f"[red]{total_failure}[/red] failed, "
                    f"[bold]{total_success + total_failure}[/bold] total"
                )
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error:[/] {str(e)}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@embeddings_group.command(name="info", help="Show information about embeddings")
@click.option(
    "--repository", "-r",
    help="Repository ID to show info for",
    type=int,
    required=False,
)
@click.option(
    "--all", "-a",
    help="Show info for all repositories",
    is_flag=True,
    default=False,
)
def embeddings_info(repository: Optional[int], all: bool):
    """Show information about embeddings."""
    if not repository and not all:
        console.print("[red]Error:[/] Must specify either --repository or --all")
        sys.exit(1)
    
    async def run():
        async with get_session() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            if repository:
                # Get repository by ID
                repo = await repo_repo.get_by_id(repository)
                if not repo:
                    console.print(f"[red]Error:[/] Repository with ID {repository} not found")
                    return
                
                total_files = await file_repo.count_by_repository_id(repository)
                files_with_embeddings = total_files - await file_repo.count_files_without_embeddings(repository)
                
                console.print(f"Repository: [bold]{repo.name}[/bold]")
                console.print(f"Total files: {total_files}")
                console.print(f"Files with embeddings: {files_with_embeddings}")
                console.print(f"Files without embeddings: {total_files - files_with_embeddings}")
                
                if files_with_embeddings > 0:
                    # Get statistics on embedding models
                    models = await file_repo.get_embedding_model_counts(repository)
                    
                    console.print("\nEmbedding models:")
                    for model, count in models.items():
                        console.print(f"  {model}: {count}")
            
            elif all:
                # Get all repositories
                repos = await repo_repo.get_all()
                if not repos:
                    console.print("[yellow]Warning:[/] No repositories found")
                    return
                
                total_repos = len(repos)
                total_files = 0
                total_with_embeddings = 0
                
                console.print(f"[bold]Embeddings Info for {total_repos} Repositories[/bold]\n")
                
                for repo in repos:
                    repo_total = await file_repo.count_by_repository_id(repo.id)
                    repo_without = await file_repo.count_files_without_embeddings(repo.id)
                    repo_with = repo_total - repo_without
                    
                    total_files += repo_total
                    total_with_embeddings += repo_with
                    
                    console.print(f"Repository: [bold]{repo.name}[/bold]")
                    console.print(f"  Files: {repo_total} total, {repo_with} with embeddings")
                    console.print(f"  Coverage: {repo_with / repo_total * 100:.1f}% of files\n")
                
                console.print("[bold]Summary:[/bold]")
                console.print(f"Total repositories: {total_repos}")
                console.print(f"Total files: {total_files}")
                console.print(f"Files with embeddings: {total_with_embeddings}")
                console.print(f"Overall coverage: {total_with_embeddings / total_files * 100:.1f}% of files")
                
                # Get overall statistics on embedding models
                models = await file_repo.get_all_embedding_model_counts()
                
                if models:
                    console.print("\n[bold]Embedding models:[/bold]")
                    for model, count in models.items():
                        console.print(f"  {model}: {count}")
    
    try:
        asyncio.run(run())
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")
        sys.exit(1)