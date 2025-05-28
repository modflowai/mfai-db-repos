"""
MCP repository preparation command - complete workflow in one command.
"""
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


@click.group()
def mcp():
    """MCP repository preparation commands."""
    pass


@mcp.command()
@click.option("--repo-url", "-u", required=True, help="Repository URL to process")
@click.option("--skip-readme", is_flag=True, help="Skip README generation")
@click.option("--skip-navigation", is_flag=True, help="Skip navigation guide generation")
@click.option("--keep-navigation-file", is_flag=True, help="Keep navigation file in repository directory")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
def prepare(repo_url: str, skip_readme: bool, skip_navigation: bool, keep_navigation_file: bool, verbose: bool):
    """Complete MCP repository preparation workflow.
    
    This command runs the entire workflow:
    1. Process repository with file analysis
    2. Generate comprehensive README
    3. Generate navigation guide with Gemini
    4. Update repository metadata in database
    
    Example:
        python -m mfai_db_repos.cli.main mcp prepare --repo-url https://github.com/modflowai/pest.git
    """
    # Extract repository name from URL
    parsed_url = urlparse(repo_url)
    repo_name = Path(parsed_url.path).stem
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    console.print(f"\n[bold cyan]🚀 MCP Repository Preparation: {repo_name}[/bold cyan]\n")
    
    # Track overall success
    all_success = True
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Step 1: Process repository
        task = progress.add_task("Processing repository with AI analysis...", total=None)
        cmd = [
            sys.executable, "-m", "mfai_db_repos.cli.main", 
            "process", "repository", 
            "--repo-url", repo_url, 
            "--include-readme"
        ]
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        progress.remove_task(task)
        
        if result.returncode != 0:
            console.print("[red]❌ Repository processing failed[/red]")
            console.print(result.stderr)
            return 1
        
        # Extract repository ID from output
        repo_id = None
        for line in result.stdout.split('\n'):
            if 'Created new repository record with ID' in line:
                repo_id = line.split('ID')[-1].strip()
                break
        
        console.print("[green]✓[/green] Repository processed successfully")
        
        # Step 2: Generate README
        if not skip_readme:
            task = progress.add_task("Generating comprehensive README...", total=None)
            cmd = [
                sys.executable, "-m", "mfai_db_repos.tools.readme_builder",
                f"analyzed_repos/{repo_name}",
                "--repo-name", repo_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            progress.remove_task(task)
            
            if result.returncode != 0:
                console.print("[red]❌ README generation failed[/red]")
                console.print(result.stderr)
                all_success = False
            else:
                console.print("[green]✓[/green] README generated successfully")
        
        # Step 3: Generate navigation guide
        if not skip_navigation:
            task = progress.add_task("Generating MCP navigation guide with Gemini...", total=None)
            readme_path = f"analyzed_repos/{repo_name}/README.md"
            nav_path = f"analyzed_repos/{repo_name}/NAVIGATION_FINAL.md"
            
            cmd = [
                sys.executable, "-m", "mfai_db_repos.tools.navigation_gemini",
                readme_path, repo_name,
                "--output", nav_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            progress.remove_task(task)
            
            if result.returncode != 0:
                console.print("[red]❌ Navigation guide generation failed[/red]")
                console.print(result.stderr)
                all_success = False
            else:
                console.print("[green]✓[/green] Navigation guide generated successfully")
                
                # Step 4: Update repository metadata
                task = progress.add_task("Updating repository metadata...", total=None)
                cmd = [
                    sys.executable, "-m", "mfai_db_repos.tools.update_repo_metadata",
                    repo_name,
                    "--navigation-file", nav_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                progress.remove_task(task)
                
                if result.returncode != 0:
                    console.print("[red]❌ Metadata update failed[/red]")
                    console.print(result.stderr)
                    all_success = False
                else:
                    console.print("[green]✓[/green] Repository metadata updated")
                    
                    # Clean up navigation file unless user wants to keep it
                    if Path(nav_path).exists():
                        if keep_navigation_file:
                            console.print(f"[dim]  Navigation file kept at: {nav_path}[/dim]")
                        else:
                            os.remove(nav_path)
                            console.print("[dim]  Cleaned up temporary navigation file[/dim]")
    
    # Final summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Repository: {repo_name}")
    console.print(f"  Location: analyzed_repos/{repo_name}/")
    console.print(f"  README: analyzed_repos/{repo_name}/README.md")
    console.print(f"  Navigation: Stored in database metadata")
    
    if all_success:
        console.print(f"\n[bold green]✨ MCP preparation complete for {repo_name}![/bold green]")
        return 0
    else:
        console.print(f"\n[bold yellow]⚠️  MCP preparation completed with some issues[/bold yellow]")
        return 1