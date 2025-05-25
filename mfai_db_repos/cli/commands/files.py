"""
CLI commands for managing repository files.
"""
import asyncio
import logging
import sys
from typing import Optional, List

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

from mfai_db_repos.lib.database.connection import get_session
from mfai_db_repos.lib.database.repository import RepositoryRepository
from mfai_db_repos.lib.database.repository_file import RepositoryFileRepository
from mfai_db_repos.lib.file_processor.pipeline import ExtractionPipeline, ProcessingOptions
from mfai_db_repos.lib.git.repository import GitRepository
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)
console = Console()


@click.group(name="files", help="Manage repository files")
def files_group():
    """Command group for file operations."""


@files_group.command(name="process", help="Process files in a repository")
@click.option(
    "--repository", "-r",
    help="Repository ID to process",
    type=int,
    required=True,
)
@click.option(
    "--incremental", "-i",
    help="Process only changed files",
    is_flag=True,
    default=True,
)
@click.option(
    "--max-size", "-m",
    help="Maximum file size in MB",
    type=float,
    default=10.0,
)
@click.option(
    "--include",
    help="File patterns to include (can be used multiple times)",
    multiple=True,
)
@click.option(
    "--exclude",
    help="File patterns to exclude (can be used multiple times)",
    multiple=True,
)
@click.option(
    "--include-ext",
    help="File extensions to include (can be used multiple times)",
    multiple=True,
)
@click.option(
    "--exclude-ext",
    help="File extensions to exclude (can be used multiple times)",
    multiple=True,
)
@click.option(
    "--ignore-binary",
    help="Ignore binary files",
    is_flag=True,
    default=True,
)
@click.option(
    "--limit",
    help="Maximum number of files to process",
    type=int,
)
@click.option(
    "--workers", "-w",
    help="Number of worker processes",
    type=int,
    default=5,
)
@click.option(
    "--verbose", "-v",
    help="Enable verbose logging",
    is_flag=True,
    default=False,
)
def process_files(
    repository: int,
    incremental: bool,
    max_size: float,
    include: List[str],
    exclude: List[str],
    include_ext: List[str],
    exclude_ext: List[str],
    ignore_binary: bool,
    limit: Optional[int],
    workers: int,
    verbose: bool,
):
    """Process files in a repository."""
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    async def run():
        async with get_session() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            # Get repository
            repo = await repo_repo.get_by_id(repository)
            if not repo:
                console.print(f"[red]Error:[/red] Repository with ID {repository} not found")
                return
            
            # Create Git repository object
            git_repo = GitRepository(
                url=repo.url,
                clone_path=repo.clone_path,
                branch=repo.default_branch,
            )
            
            # Check if repository is cloned
            if not git_repo.is_cloned():
                console.print(f"[red]Error:[/red] Repository {repo.name} is not cloned")
                return
            
            # Update repository status
            await repo_repo.update_status(repository, "processing")
            
            # Create processing options
            options = ProcessingOptions(
                max_file_size_mb=max_size,
                ignore_binary_files=ignore_binary,
                include_patterns=list(include) if include else None,
                exclude_patterns=list(exclude) if exclude else None,
                include_extensions=list(include_ext) if include_ext else None,
                exclude_extensions=list(exclude_ext) if exclude_ext else None,
            )
            
            # Create extraction pipeline
            pipeline = ExtractionPipeline(
                config=Config(),
                options=options,
            )
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                # Add task for processing
                process_task = progress.add_task(
                    f"Processing {repo.name} ({'incremental' if incremental else 'full'})", 
                    total=None,
                )
                
                try:
                    # Process repository
                    results = pipeline.process_repository(
                        git_repo=git_repo,
                        incremental=incremental,
                        max_files=limit,
                        max_workers=workers,
                    )
                    
                    # Update progress
                    progress.update(
                        process_task, 
                        completed=1.0, 
                        description=f"Processed {len(results)} files"
                    )
                    
                    # Count successful and failed files
                    success_count = sum(1 for r in results if r.success)
                    failed_count = sum(1 for r in results if not r.success and not r.skipped)
                    skipped_count = sum(1 for r in results if r.skipped)
                    
                    # Update repository file count if needed
                    if repo.file_count is None or repo.file_count == 0:
                        await repo_repo.increment_file_count(repository, success_count)
                    
                    # Update repository status
                    await repo_repo.update_status(repository, "ready")
                    
                    # Display results
                    console.print(f"\n[green]Processing completed:[/green]")
                    console.print(f"  Total files: {len(results)}")
                    console.print(f"  Successful: {success_count}")
                    console.print(f"  Failed: {failed_count}")
                    console.print(f"  Skipped: {skipped_count}")
                    
                    # Show skipped files if verbose
                    if verbose and skipped_count > 0:
                        console.print("\n[yellow]Skipped files:[/yellow]")
                        for result in results:
                            if result.skipped:
                                console.print(f"  {result.path}: {result.skip_reason}")
                    
                    # Show failed files if any
                    if failed_count > 0:
                        console.print("\n[red]Failed files:[/red]")
                        for result in results:
                            if not result.success and not result.skipped:
                                console.print(f"  {result.path}: {result.error}")
                    
                except Exception as e:
                    progress.update(
                        process_task, 
                        description=f"[red]Error: {str(e)}[/red]"
                    )
                    logger.error(f"Failed to process repository: {e}")
                    
                    # Update repository status
                    await repo_repo.update_status(repository, "error")
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@files_group.command(name="list", help="List files in a repository")
@click.option(
    "--repository", "-r",
    help="Repository ID",
    type=int,
    required=True,
)
@click.option(
    "--pattern",
    help="File path pattern (SQL LIKE format)",
    type=str,
)
@click.option(
    "--extension",
    help="Filter by file extension",
    type=str,
)
@click.option(
    "--limit",
    help="Maximum number of files to list",
    type=int,
    default=100,
)
@click.option(
    "--offset",
    help="Offset for pagination",
    type=int,
    default=0,
)
@click.option(
    "--sort",
    help="Sort field (path, size, language, created_at, updated_at)",
    type=click.Choice(["path", "size", "language", "created_at", "updated_at"]),
    default="path",
)
@click.option(
    "--order",
    help="Sort order (asc, desc)",
    type=click.Choice(["asc", "desc"]),
    default="asc",
)
def list_files(
    repository: int,
    pattern: Optional[str],
    extension: Optional[str],
    limit: int,
    offset: int,
    sort: str,
    order: str,
):
    """List files in a repository."""
    async def run():
        async with get_session() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            # Get repository
            repo = await repo_repo.get_by_id(repository)
            if not repo:
                console.print(f"[red]Error:[/red] Repository with ID {repository} not found")
                return
            
            # Create file query parameters
            params = {
                "repository_id": repository,
                "limit": limit,
                "offset": offset,
                "sort_by": sort,
                "sort_order": order,
            }
            
            if pattern:
                params["path_pattern"] = pattern
            
            if extension:
                params["extension"] = extension.lstrip(".")
            
            # Get files
            files = await file_repo.search(**params)
            
            # Count total files matching criteria
            total_count = await file_repo.count_search_results(**params)
            
            if not files:
                console.print(f"[yellow]No files found for repository {repo.name}[/yellow]")
                return
            
            # Create table
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID")
            table.add_column("Path")
            table.add_column("Size")
            table.add_column("Language")
            table.add_column("Has Embedding")
            
            # Add rows for each file
            for file in files:
                # Format file size
                size_str = f"{file.size / 1024:.1f} KB" if file.size else "N/A"
                
                # Check if file has embedding
                has_embedding = "Yes" if file.embedding_id else "No"
                
                table.add_row(
                    str(file.id),
                    file.path,
                    size_str,
                    file.language or "Unknown",
                    has_embedding,
                )
            
            # Print table
            console.print(f"Files for repository: [bold]{repo.name}[/bold]")
            console.print(f"Showing {len(files)} of {total_count} files (offset: {offset}, limit: {limit})")
            console.print(table)
            
            # Show pagination info if needed
            if total_count > limit:
                pages = (total_count + limit - 1) // limit
                current_page = offset // limit + 1
                console.print(f"Page {current_page} of {pages}")
    
    try:
        asyncio.run(run())
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@files_group.command(name="status", help="Show file processing status")
@click.option(
    "--repository", "-r",
    help="Repository ID",
    type=int,
    required=True,
)
def file_status(repository: int):
    """Show file processing status for a repository."""
    async def run():
        async with get_session() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            # Get repository
            repo = await repo_repo.get_by_id(repository)
            if not repo:
                console.print(f"[red]Error:[/red] Repository with ID {repository} not found")
                return
            
            # Get file counts
            total_count = await file_repo.count_by_repository_id(repository)
            
            if total_count == 0:
                console.print(f"[yellow]No files found for repository {repo.name}[/yellow]")
                return
            
            # Get language counts
            language_counts = await file_repo.get_language_counts(repository)
            
            # Get extension counts
            extension_counts = await file_repo.get_extension_counts(repository)
            
            # Get embedded counts
            without_embeddings = await file_repo.count_files_without_embeddings(repository)
            with_embeddings = total_count - without_embeddings
            
            # Display results
            console.print(f"[bold]File status for repository:[/bold] {repo.name}")
            console.print(f"[bold]Total files:[/bold] {total_count}")
            console.print(f"[bold]Files with embeddings:[/bold] {with_embeddings} ({with_embeddings / total_count * 100:.1f}%)")
            console.print(f"[bold]Files without embeddings:[/bold] {without_embeddings}")
            
            # Display language breakdown
            if language_counts:
                console.print("\n[bold]Languages:[/bold]")
                language_table = Table(show_header=True, header_style="bold")
                language_table.add_column("Language")
                language_table.add_column("Files")
                language_table.add_column("Percentage")
                
                for language, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
                    language_table.add_row(
                        language or "Unknown",
                        str(count),
                        f"{count / total_count * 100:.1f}%",
                    )
                
                console.print(language_table)
            
            # Display extension breakdown
            if extension_counts:
                console.print("\n[bold]File Extensions:[/bold]")
                extension_table = Table(show_header=True, header_style="bold")
                extension_table.add_column("Extension")
                extension_table.add_column("Files")
                extension_table.add_column("Percentage")
                
                for extension, count in sorted(extension_counts.items(), key=lambda x: x[1], reverse=True)[:15]:  # Limit to top 15
                    extension_table.add_row(
                        extension or "No extension",
                        str(count),
                        f"{count / total_count * 100:.1f}%",
                    )
                
                if len(extension_counts) > 15:
                    console.print(extension_table)
                    console.print(f"... and {len(extension_counts) - 15} more extensions")
                else:
                    console.print(extension_table)
    
    try:
        asyncio.run(run())
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


