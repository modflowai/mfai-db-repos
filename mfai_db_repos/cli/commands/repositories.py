"""
CLI commands for managing Git repositories.
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

from mfai_db_repos.core.services.repository_service import RepositoryService
from mfai_db_repos.lib.database.connection import session_context
from mfai_db_repos.lib.database.repository import RepositoryRepository
from mfai_db_repos.lib.database.repository_file import RepositoryFileRepository
from mfai_db_repos.lib.git.repository import GitRepository
from mfai_db_repos.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)
console = Console()


@click.group(name="repositories", help="Manage Git repositories")
def repositories_group():
    """Command group for repository operations."""


@repositories_group.command(name="add", help="Add a new repository")
@click.argument("url", required=True)
@click.option(
    "--name",
    help="Repository name (defaults to name derived from URL)",
    type=str,
)
@click.option(
    "--branch",
    "-b",
    help="Branch to clone (defaults to configured default)",
    type=str,
)
@click.option(
    "--clone-path",
    help="Custom clone path (defaults to configured path)",
    type=click.Path(),
)
@click.option(
    "--process",
    is_flag=True,
    default=True,
    help="Process repository files after adding",
)
@click.option(
    "--verbose", "-v",
    help="Enable verbose logging",
    is_flag=True,
    default=False,
)
@click.option(
    "--github-token",
    help="GitHub personal access token for private repositories",
    type=str,
    metavar="TOKEN",
    envvar="GITHUB_TOKEN",
)
def add_repository(
    url: str,
    name: Optional[str],
    branch: Optional[str],
    clone_path: Optional[str],
    process: bool,
    verbose: bool,
    github_token: Optional[str] = None,
):
    """Add a new Git repository."""
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    # Set GitHub token in configuration if provided
    if github_token:
        from gitcontext.utils.config import config
        config.update(**{"git.github_token": github_token})
        console.print(f"Using provided GitHub token for authentication")
    
    async def run():
        async with session_context() as session:
            # Create repositories service
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            # Check if repository already exists
            existing_repo = await repo_repo.get_by_url(url)
            if existing_repo:
                console.print(f"[yellow]Repository already exists:[/yellow] {existing_repo.name} (ID: {existing_repo.id})")
                return
            
            # Create repository service
            repo_service = RepositoryService(repo_repo=repo_repo, file_repo=file_repo)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                # Add task for cloning
                clone_task = progress.add_task(f"Cloning repository: {url}", total=1.0)
                
                # Create repository
                try:
                    # Prepare parameters
                    params = {
                        "url": url,
                        "name": name,
                        "default_branch": branch,
                    }
                    
                    if clone_path:
                        params["clone_path"] = Path(clone_path)
                    
                    # Create repository
                    repository = await repo_service.add_repository(**params)
                    
                    if not repository:
                        progress.update(clone_task, description="[red]Failed to create repository[/red]")
                        return
                    
                    # Update progress
                    progress.update(clone_task, completed=1.0, description=f"Repository created: {repository.name}")
                    
                    # Process files if requested
                    if process:
                        file_task = progress.add_task(f"Processing files...", total=None)
                        file_count = await repo_service.process_repository_files(repository.id)
                        progress.update(file_task, completed=1.0, description=f"Processed {file_count} files")
                    
                    # Show repository information
                    console.print(f"\n[green]Repository added successfully:[/green] {repository.name} (ID: {repository.id})")
                    console.print(f"URL: {repository.url}")
                    console.print(f"Default branch: {repository.default_branch}")
                    console.print(f"Clone path: {repository.clone_path}")
                    
                    if file_count := await file_repo.count_by_repository_id(repository.id):
                        console.print(f"Files: {file_count}")
                    
                except Exception as e:
                    progress.update(clone_task, description=f"[red]Error: {str(e)}[/red]")
                    logger.error(f"Failed to add repository: {e}")
    
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


@repositories_group.command(name="list", help="List all repositories")
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show detailed information",
)
def list_repositories(verbose: bool):
    """List all repositories."""
    async def run():
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            # Get all repositories
            repositories = await repo_repo.get_all()
            
            if not repositories:
                console.print("[yellow]No repositories found[/yellow]")
                return
            
            # Create table
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID")
            table.add_column("Name")
            table.add_column("URL")
            table.add_column("Files")
            table.add_column("Status")
            
            if verbose:
                table.add_column("Branch")
                table.add_column("Last Updated")
            
            # Add rows for each repository
            for repo in repositories:
                # Get file count
                file_count = await file_repo.count_by_repository_id(repo.id)
                
                # Add row
                row = [
                    str(repo.id),
                    repo.name,
                    repo.url,
                    str(file_count),
                    repo.status,
                ]
                
                if verbose:
                    row.append(repo.default_branch or "N/A")
                    row.append(repo.updated_at.strftime("%Y-%m-%d %H:%M:%S") if repo.updated_at else "N/A")
                
                table.add_row(*row)
            
            # Print table
            console.print(table)
    
    try:
        asyncio.run(run())
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@repositories_group.command(name="get", help="Get repository details")
@click.argument("repository_id", type=int)
def get_repository(repository_id: int):
    """Get details about a repository."""
    async def run():
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            # Get repository
            repository = await repo_repo.get_by_id(repository_id)
            
            if not repository:
                console.print(f"[red]Repository with ID {repository_id} not found[/red]")
                return
            
            # Create a Git repository instance to get stats
            git_repo = GitRepository(
                url=repository.url,
                clone_path=repository.clone_path,
                branch=repository.default_branch,
            )
            
            # Get file count
            file_count = await file_repo.count_by_repository_id(repository.id)
            files_with_embeddings = file_count - await file_repo.count_files_without_embeddings(repository.id)
            
            # Display repository information
            console.print(f"[bold]Repository:[/bold] {repository.name} (ID: {repository.id})")
            console.print(f"[bold]URL:[/bold] {repository.url}")
            console.print(f"[bold]Default branch:[/bold] {repository.default_branch or 'Not set'}")
            console.print(f"[bold]Clone path:[/bold] {repository.clone_path or 'Not cloned'}")
            console.print(f"[bold]Status:[/bold] {repository.status}")
            console.print(f"[bold]Files:[/bold] {file_count} ({files_with_embeddings} with embeddings)")
            console.print(f"[bold]Created:[/bold] {repository.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print(f"[bold]Last updated:[/bold] {repository.updated_at.strftime('%Y-%m-%d %H:%M:%S') if repository.updated_at else 'Never'}")
            
            # Get Git stats if possible
            if git_repo.is_cloned():
                console.print("\n[bold]Git Repository Statistics:[/bold]")
                
                stats = git_repo.get_repo_stats()
                for key, value in stats.items():
                    if key != "status":  # Skip status since we already showed it
                        console.print(f"[bold]{key.replace('_', ' ').title()}:[/bold] {value}")
    
    try:
        asyncio.run(run())
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@repositories_group.command(name="update", help="Update a repository")
@click.argument("repository_id", type=int)
@click.option(
    "--process",
    is_flag=True,
    default=True,
    help="Process new or updated files after updating",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging",
)
@click.option(
    "--github-token",
    help="GitHub personal access token for private repositories",
    type=str,
    metavar="TOKEN",
    envvar="GITHUB_TOKEN",
)
def update_repository(repository_id: int, process: bool, verbose: bool, github_token: Optional[str] = None):
    """Update a repository to the latest commit."""
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    # Set GitHub token in configuration if provided
    if github_token:
        from gitcontext.utils.config import config
        config.update(**{"git.github_token": github_token})
        console.print(f"Using provided GitHub token for authentication")
    
    async def run():
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            # Get repository
            repository = await repo_repo.get_by_id(repository_id)
            
            if not repository:
                console.print(f"[red]Repository with ID {repository_id} not found[/red]")
                return
            
            # Create repository service
            repo_service = RepositoryService(repo_repo=repo_repo, file_repo=file_repo)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                # Add task for updating
                update_task = progress.add_task(f"Updating repository: {repository.name}", total=1.0)
                
                try:
                    # Update repository
                    success, changed_files = await repo_service.update_repository(repository_id)
                    
                    if not success:
                        progress.update(update_task, description="[red]Failed to update repository[/red]")
                        return
                    
                    # Update progress
                    progress.update(
                        update_task, 
                        completed=1.0, 
                        description=f"Repository updated: {len(changed_files)} files changed"
                    )
                    
                    # Process files if requested and there are changes
                    if process and changed_files:
                        file_task = progress.add_task(f"Processing changed files...", total=None)
                        file_count = await repo_service.process_repository_files(
                            repository_id, files=changed_files
                        )
                        progress.update(
                            file_task, 
                            completed=1.0, 
                            description=f"Processed {file_count} files"
                        )
                    
                    # Show repository information
                    console.print(f"\n[green]Repository updated successfully:[/green] {repository.name}")
                    console.print(f"Changed files: {len(changed_files)}")
                    
                    if verbose and changed_files:
                        console.print("\n[bold]Changed files:[/bold]")
                        for file in changed_files[:20]:  # Limit display to 20 files
                            console.print(f"- {file}")
                        
                        if len(changed_files) > 20:
                            console.print(f"... and {len(changed_files) - 20} more files")
                    
                except Exception as e:
                    progress.update(update_task, description=f"[red]Error: {str(e)}[/red]")
                    logger.error(f"Failed to update repository: {e}")
    
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


@repositories_group.command(name="delete", help="Delete a repository")
@click.argument("repository_id", type=int)
@click.option(
    "--confirm",
    is_flag=True,
    default=False,
    help="Confirm deletion without prompting",
)
@click.option(
    "--keep-files",
    is_flag=True,
    default=False,
    help="Keep repository files on disk",
)
def delete_repository(repository_id: int, confirm: bool, keep_files: bool):
    """Delete a repository."""
    async def run():
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            
            # Get repository
            repository = await repo_repo.get_by_id(repository_id)
            
            if not repository:
                console.print(f"[red]Repository with ID {repository_id} not found[/red]")
                return
            
            # Confirm deletion if not already confirmed
            if not confirm:
                console.print(f"[yellow]Warning:[/yellow] This will delete the repository '{repository.name}' (ID: {repository.id})")
                console.print("All file data and embeddings for this repository will be deleted from the database.")
                
                if not keep_files and repository.clone_path:
                    console.print(f"The repository files at '{repository.clone_path}' will also be removed.")
                
                confirmed = click.confirm("Are you sure you want to proceed?", default=False)
                if not confirmed:
                    console.print("[yellow]Operation cancelled by user[/yellow]")
                    return
            
            # Create repository service
            repo_service = RepositoryService(repo_repo=repo_repo)
            
            # Delete repository
            success = await repo_service.delete_repository(repository_id, keep_files=keep_files)
            
            if success:
                console.print(f"[green]Repository '{repository.name}' successfully deleted[/green]")
            else:
                console.print(f"[red]Failed to delete repository '{repository.name}'[/red]")
    
    try:
        asyncio.run(run())
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)