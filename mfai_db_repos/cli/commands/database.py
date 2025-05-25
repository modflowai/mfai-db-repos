"""
CLI commands for database management.
"""
import logging
import sys
import asyncio

import click
from rich.console import Console

from mfai_db_repos.lib.database.management import reset_database, remove_repository, init_database_extensions, init_database_schema
from mfai_db_repos.utils.logger import setup_logging

console = Console()


@click.group(name="database", help="Database management operations")
def database_group():
    """Command group for database operations."""


@database_group.command(name="reset", help="Reset the database (WARNING: Deletes all data)")
@click.option(
    "--force", "-f",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show verbose output",
)
def reset_command(force: bool, verbose: bool):
    """Reset the database by stopping containers, removing volumes, and starting fresh."""
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    # Confirm the action unless --force is used
    if not force:
        console.print("[bold red]WARNING:[/bold red] This will delete all data in the database.")
        confirmation = click.prompt("Are you sure you want to proceed? Type 'yes' to confirm", type=str)
        if confirmation.lower() != "yes":
            console.print("Operation cancelled.")
            return
    
    # Reset the database
    console.print("Resetting database...", style="yellow")
    success, message = reset_database()
    
    if success:
        console.print(f"[green]Success:[/green] {message}")
    else:
        console.print(f"[red]Error:[/red] {message}")
        sys.exit(1)


@database_group.command(name="debug-env", help="Debug environment variables and configuration")
def debug_env_command():
    """Show environment variables and configuration to debug connection issues."""
    import os
    
    # Print current directory
    console.print(f"[bold]Current directory:[/bold] {os.getcwd()}")
    
    # Check .env file existence
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path):
        console.print(f"[green].env file exists:[/green] {env_path}")
        with open(env_path, 'r') as f:
            content = f.read()
            # Mask sensitive info
            content = content.replace(r'(DB_PASSWORD=.+)', r'DB_PASSWORD=******')
            content = content.replace(r'(DB_USER=.+)', r'DB_USER=******')
            console.print(f"[bold].env file content:[/bold]\n{content}")
    else:
        console.print(f"[red].env file does not exist:[/red] {env_path}")
    
    # Show relevant environment variables
    db_vars = {k: v for k, v in os.environ.items() if k.startswith('DB_')}
    console.print(f"[bold]DB Environment Variables:[/bold]")
    for k, v in db_vars.items():
        if 'PASSWORD' in k:
            console.print(f"{k}: ******")
        else:
            console.print(f"{k}: {v}")
    
    # Show config that was loaded
    from mfai_db_repos.utils.config import config
    db_config = config.config.database
    console.print(f"[bold]Loaded configuration:[/bold]")
    console.print(f"Host: {db_config.host}")
    console.print(f"Port: {db_config.port}")
    console.print(f"Database: {db_config.database}")
    console.print(f"User: {db_config.user}")
    console.print(f"SSL Mode: {db_config.sslmode}")
    console.print(f"Is Serverless: {db_config.is_serverless}")
    console.print(f"Use Connection Pooler: {db_config.use_connection_pooler}")


@database_group.command(name="init", help="Initialize database extensions and schema (required for Neon DB)")
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show verbose output",
)
@click.option(
    "--skip-schema", 
    is_flag=True,
    default=False,
    help="Skip initializing database schema, only create extensions",
)
def init_command(verbose: bool, skip_schema: bool):
    """Initialize required database extensions and schema."""
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    # Log connection information
    from mfai_db_repos.utils.config import config
    db_config = config.config.database
    console.print(f"[yellow]Database connection:[/yellow] {db_config.host}:{db_config.port}/{db_config.database} (user: {db_config.user})")
    console.print(f"[yellow]SSL Mode:[/yellow] {db_config.sslmode}, [yellow]Serverless:[/yellow] {db_config.is_serverless}")
    
    async def run_init():
        # Initialize database extensions
        console.print("Initializing database extensions...", style="yellow")
        ext_success, ext_message = await init_database_extensions()
        
        if not ext_success:
            console.print(f"[red]Error:[/red] {ext_message}")
            sys.exit(1)
        
        console.print(f"[green]Success:[/green] {ext_message}")
        
        # Initialize database schema
        if not skip_schema:
            console.print("Initializing database schema...", style="yellow")
            schema_success, schema_message = await init_database_schema()
            
            if not schema_success:
                console.print(f"[red]Error:[/red] {schema_message}")
                sys.exit(1)
            
            console.print(f"[green]Success:[/green] {schema_message}")
        
        return True
    
    asyncio.run(run_init())


@database_group.command(name="remove-repo", help="Remove a repository and all its files from the database")
@click.argument("repository", required=True)
@click.option(
    "--force", "-f",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show verbose output",
)
def remove_repo_command(repository, force: bool, verbose: bool):
    """
    Remove a repository and all its files from the database.
    
    REPOSITORY can be an ID, name, or URL of the repository to remove.
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    # Try to convert repository to int if it's a numeric string
    repo_identifier = repository
    try:
        if repository.isdigit():
            repo_identifier = int(repository)
    except (ValueError, AttributeError):
        pass
    
    # Confirm the action unless --force is used
    if not force:
        console.print(f"[bold red]WARNING:[/bold red] This will permanently delete the repository '{repository}' and all its files.")
        confirmation = click.prompt("Are you sure you want to proceed? Type 'yes' to confirm", type=str)
        if confirmation.lower() != "yes":
            console.print("Operation cancelled.")
            return
    
    # Remove the repository
    console.print(f"Removing repository '{repository}'...", style="yellow")
    
    async def run_remove():
        success, message = await remove_repository(repo_identifier)
        
        if success:
            console.print(f"[green]Success:[/green] {message}")
        else:
            console.print(f"[red]Error:[/red] {message}")
            sys.exit(1)
    
    asyncio.run(run_remove())