"""
Repository processing service for complete file processing workflow.

This module provides a comprehensive service for processing repositories
with a complete workflow including file extraction, content analysis,
embedding generation, and database storage.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from mfai_db_repos.lib.database.connection import session_context
from mfai_db_repos.lib.database.repository import RepositoryRepository
from mfai_db_repos.lib.database.repository_file import RepositoryFileRepository
from mfai_db_repos.lib.database.models import RepositoryFile
from mfai_db_repos.lib.embeddings.manager import EmbeddingManager, ProviderType
from mfai_db_repos.lib.embeddings.google_genai import GoogleGenAIEmbeddingConfig
from mfai_db_repos.lib.embeddings.openai import OpenAIEmbeddingConfig
from mfai_db_repos.lib.git.repository import GitRepository, RepoStatus
from mfai_db_repos.lib.file_processor.extractor import FileExtractor
from mfai_db_repos.utils.env import get_env, get_int_env, get_float_env
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


# Note: We no longer need this function since PostgreSQL generates tsvector automatically 
# using a generated column. Keeping it for reference but marking as deprecated.
def generate_tsvector(content: str) -> None:
    """
    DEPRECATED: No longer needed as PostgreSQL generates tsvector using GENERATED ALWAYS column.
    
    This function is kept for reference only and will be removed in a future version.
    The database now automatically generates tsvector content from the text content.
    
    Args:
        content: Text content (ignored)
        
    Returns:
        None, as this functionality is now handled by PostgreSQL
    """
    # Just return None as this is no longer used
    return None


def extract_tags_from_analysis(analysis: Dict[str, Any]) -> List[str]:
    """
    Extract tags from the analysis output.
    
    Args:
        analysis: Analysis dictionary from Gemini
        
    Returns:
        List of tags
    """
    tags = set()
    
    # Add keywords as tags
    if 'keywords' in analysis and analysis['keywords']:
        tags.update(analysis['keywords'])
    
    # Add key concepts as tags
    if 'key_concepts' in analysis and analysis['key_concepts']:
        tags.update(analysis['key_concepts'])
        
    # Add related topics
    if 'related_topics' in analysis and analysis['related_topics']:
        tags.update(analysis['related_topics'])
        
    # Return as sorted list of strings
    return sorted(tags)


class RepositoryProcessingService:
    """Service for comprehensive repository processing."""
    
    def __init__(
        self,
        batch_size: Optional[int] = None,
        parallel_workers: Optional[int] = None,
    ):
        """Initialize the repository processing service.
        
        Args:
            batch_size: Number of files to process in each batch (defaults to env BATCH_SIZE)
            parallel_workers: Number of parallel workers for API calls (defaults to env PARALLEL_WORKERS)
        """
        self.batch_size = batch_size or get_int_env("BATCH_SIZE", 5)
        self.parallel_workers = parallel_workers or get_int_env("PARALLEL_WORKERS", 5)
        
    async def create_embedding_manager(self) -> EmbeddingManager:
        """
        Create and configure the embedding manager with both
        OpenAI (for embeddings) and Google GenAI (for analysis).
        
        Returns:
            Configured EmbeddingManager instance
        """
        # Load API keys from environment variables
        openai_api_key = get_env("OPENAI_API_KEY")
        google_api_key = get_env("GOOGLE_API_KEY")
        
        if not openai_api_key:
            logger.warning("OpenAI API key not set in .env, embeddings will fail")
        
        if not google_api_key:
            logger.warning("Google API key not set in .env, structured analysis will fail")
        
        # Create OpenAI config
        openai_config = OpenAIEmbeddingConfig(
            api_key=openai_api_key,
            model="text-embedding-3-small",  # Default model
            batch_size=self.batch_size,
            max_parallel_requests=self.parallel_workers
        )
        
        # Create Google GenAI config
        google_config = GoogleGenAIEmbeddingConfig(
            api_key=google_api_key,
            model="gemini-2.0-flash",  # Default model - better for structured output with LaTeX
            batch_size=1,  # Process one file at a time for analysis
            max_parallel_requests=self.parallel_workers
        )
        
        # Create manager with both providers
        manager = EmbeddingManager(
            primary_provider=ProviderType.OPENAI,
            secondary_provider=ProviderType.GOOGLE_GENAI,
            primary_config=openai_config,
            secondary_config=google_config,
            max_parallel_requests=self.parallel_workers,
            batch_size=self.batch_size,
            rate_limit_per_minute=100
        )
        
        return manager
        
    async def get_or_create_repository(
        self, 
        repo_url: str, 
        branch: Optional[str] = None
    ) -> Optional[Tuple[int, GitRepository]]:
        """
        Get or create a repository record in the database and initialize the Git repository.
        
        Args:
            repo_url: Repository URL
            branch: Optional branch name
            
        Returns:
            Tuple of (repo_id, GitRepository) or None if failed
        """
        db_repo = None
        
        # Use a single session for the entire operation
        async with session_context() as session:
            try:
                # Begin transaction
                repo_repo = RepositoryRepository(session)
                
                # Check if repository exists
                db_repo = await repo_repo.get_by_url(repo_url)
                
                if db_repo:
                    logger.info(f"Repository {repo_url} already exists in the database with ID {db_repo.id}")
                    # Update repository status
                    await repo_repo.update_status(db_repo.id, RepoStatus.CLONING.value)
                else:
                    # Create repository record
                    db_repo = await repo_repo.create(
                        url=repo_url,
                        name=Path(repo_url).stem if "/" in repo_url else repo_url,
                        default_branch=branch,
                        clone_path=None,  # Use default clone path from config
                    )
                    
                    if not db_repo:
                        logger.error(f"Failed to create repository record for {repo_url}")
                        return None
                    
                    logger.info(f"Created new repository record with ID {db_repo.id}")
                    # Update repository status
                    await repo_repo.update_status(db_repo.id, RepoStatus.CLONING.value)
                
                # Commit to ensure repository exists in database
                await session.commit()
            except Exception as e:
                logger.error(f"Error creating repository record: {str(e)}")
                await session.rollback()
                return None
        
        # Initialize Git repository
        git_repo = GitRepository(repo_url, None, branch)
        
        # Clone repository if not already cloned
        if not git_repo.is_cloned() and not git_repo.clone():
            logger.error(f"Failed to clone repository {repo_url}")
            async with session_context() as session:
                repo_repo = RepositoryRepository(session)
                await repo_repo.update_status(db_repo.id, RepoStatus.ERROR.value)
            return None
        
        # Get the actual branch name that was used during cloning
        actual_branch = git_repo.branch
        
        # Update repository with the actual branch name
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            if db_repo.default_branch != actual_branch:
                logger.info(f"Updating repository default branch from {db_repo.default_branch} to {actual_branch}")
                # Update branch name in the repository record
                db_repo.default_branch = actual_branch
                await repo_repo.update(db_repo)
        
        # Update repository
        success, changed_files = git_repo.update()
        if not success:
            logger.error(f"Failed to update repository {repo_url}")
            async with session_context() as session:
                repo_repo = RepositoryRepository(session)
                await repo_repo.update_status(db_repo.id, RepoStatus.ERROR.value)
            return None
        
        # Update repository status to indexing
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            await repo_repo.update_status(db_repo.id, RepoStatus.INDEXING.value)
        
        return (db_repo.id, git_repo)
    
    async def extract_readme_content(self, git_repo: GitRepository) -> Optional[str]:
        """
        Extract README.md content from the repository.
        
        Args:
            git_repo: GitRepository instance
            
        Returns:
            README content as string or None if not found
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            logger.error("Repository is not cloned")
            return None
        
        repo_path = Path(git_repo.repo.working_dir)
        # Common README filenames to check
        readme_filenames = [
            "README.md", "readme.md", "Readme.md", 
            "README.MD", "README.txt", "readme.txt",
            "README.rst", "readme.rst", "README"
        ]
        
        for filename in readme_filenames:
            readme_path = repo_path / filename
            
            # Check if file exists or is a symlink (even if broken)
            try:
                if readme_path.exists() or readme_path.is_symlink():
                    # Try to read the content directly first (handles symlinks better)
                    try:
                        # Use os.path.realpath for better symlink resolution
                        import os
                        if readme_path.is_symlink():
                            resolved_str = os.path.realpath(str(readme_path)).strip()
                        else:
                            resolved_str = str(readme_path)
                        
                        with open(resolved_str, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if content and content.strip():
                            logger.info(f"Found README at: {filename}")
                            return content
                    except Exception as read_error:
                        logger.debug(f"Direct read failed for {filename}: {read_error}")
                        
                        # Fallback to FileExtractor
                        try:
                            extractor = FileExtractor(
                                max_file_size_mb=get_float_env("MAX_FILE_SIZE_MB", 10),
                            )
                            content = extractor.extract_content(readme_path)
                            if content and content.strip():
                                logger.info(f"Found README at: {filename}")
                                logger.debug(f"README content length: {len(content)} characters")
                                return content
                            else:
                                logger.debug(f"FileExtractor returned empty content for {filename}")
                        except Exception as extractor_error:
                            logger.debug(f"FileExtractor failed for {filename}: {extractor_error}")
            except Exception as e:
                logger.warning(f"Error reading README file {filename}: {str(e)}")
                continue
        
        return None
    
    async def extract_repository_files(
        self, 
        repo_id: int, 
        git_repo: GitRepository, 
        limit: Optional[int] = None,
        include_tests: bool = False
    ) -> List[str]:
        """
        Extract files from the repository and return their relative paths.
        
        Args:
            repo_id: Repository ID
            git_repo: GitRepository instance
            limit: Optional limit on number of files to extract
            include_tests: Whether to include test files and directories
            
        Returns:
            List of file paths relative to repository root
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            logger.error("Repository is not cloned")
            return []
        
        # Initialize file extractor with configuration
        extractor = FileExtractor(
            max_file_size_mb=get_float_env("MAX_FILE_SIZE_MB", 10),
        )
        
        # Get all files recursively
        repo_path = Path(git_repo.repo.working_dir)
        all_files = []
        
        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in Path(root).parts:
                continue
            
            # Process files
            for filename in files:
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(repo_path))
                
                # Set up exclude patterns based on include_tests flag
                exclude_patterns = None  # Use default exclude patterns
                if include_tests:
                    # If including tests, create a custom exclude patterns list without test exclusions
                    exclude_patterns = [
                        # Common version control directories
                        "**/.git/**", 
                        # Virtual environments
                        "**/venv/**", "**/.venv/**", 
                        # Python cache files
                        "**/__pycache__/**", "**/.pytest_cache/**",
                    ]
                
                # Check if the file should be processed
                if extractor.should_process_file(
                    filepath,
                    None,  # Use default include patterns 
                    exclude_patterns  # Use custom exclude patterns if include_tests=True
                ):
                    all_files.append(rel_path)
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            all_files = all_files[:limit]
        
        logger.info(f"Found {len(all_files)} files to process in repository")
        return all_files
    
    async def process_file(
        self, 
        file_path: str, 
        repo_id: int, 
        git_repo: GitRepository,
        embedding_manager: EmbeddingManager,
        readme_content: Optional[str] = None
    ) -> Optional[RepositoryFile]:
        """
        Process a single file from the repository with the complete workflow.
        
        Args:
            file_path: Path to the file relative to the repository root
            repo_id: Repository ID
            git_repo: GitRepository instance
            embedding_manager: EmbeddingManager instance
            readme_content: Optional README content to include in analysis
            
        Returns:
            RepositoryFile object or None if processing failed
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return None
        
        # Get full file path
        repo_path = Path(git_repo.repo.working_dir)
        full_path = repo_path / file_path
        
        # Initialize file extractor
        extractor = FileExtractor(
            max_file_size_mb=get_float_env("MAX_FILE_SIZE_MB", 10),
        )
        
        try:
            # 1. Extract file metadata
            metadata = extractor.get_file_metadata(full_path)
            
            # 2. Extract file content
            content = extractor.extract_content(full_path)
            
            # Skip empty files
            if content is None or content.strip() == "":
                logger.debug(f"Skipping empty file: {file_path}")
                return None
            
            # 3. Get git metadata including commit hash
            commit_hash = git_repo.get_file_commit_hash(file_path)
            
            # 4. Generate tsvector for PostgreSQL full-text search
            content_tsvector = generate_tsvector(content)
            
            # 5. Generate structured analysis using Google Gemini
            analysis = await embedding_manager.analyze_file_content(content, readme_content)
            
            # 6. Extract metadata fields
            file_type = analysis.get('document_type', 'Unknown')
            technical_level = analysis.get('technical_level', 'Unknown')
            tags = extract_tags_from_analysis(analysis)
            
            # 7. Create embedding string from analysis
            embedding_text = f"""
            Filename: {Path(file_path).name}
            Filepath: {file_path}
            Repository: {Path(git_repo.repo.working_dir).name}
            
            Title: {analysis.get('title', 'No title')}
            
            Summary: {analysis.get('summary', 'No summary')}
            
            Key Concepts: {', '.join(analysis.get('key_concepts', []))}
            
            Potential Questions: {' '.join(analysis.get('potential_questions', []))}
            
            Keywords: {', '.join(analysis.get('keywords', []))}
            
            Document Type: {file_type}
            
            Technical Level: {technical_level}
            
            Related Topics: {', '.join(analysis.get('related_topics', []))}
            
            Prerequisites: {', '.join(analysis.get('prerequisites', []))}
            """
            
            # Add code snippets if available
            if analysis.get('code_snippets') and len(analysis.get('code_snippets', [])) > 0:
                snippet_texts = []
                for i, snippet in enumerate(analysis.get('code_snippets', [])):
                    snippet_text = f"Snippet {i+1} ({snippet.get('language', 'unknown')}): {snippet.get('purpose', '')}\n{snippet.get('summary', '')}"
                    snippet_texts.append(snippet_text)
                
                joined_snippets = "\n".join(snippet_texts)
                embedding_text += f"""
            Code Snippets:
            {joined_snippets}
            """
                
                if analysis.get('code_snippets_overview'):
                    embedding_text += f"""
            Code Snippets Overview: {analysis.get('code_snippets_overview')}
            """
            
            # Add component properties if available
            if analysis.get('component_properties'):
                cp = analysis.get('component_properties', {})
                embedding_text += f"""
            Component Type: {cp.get('component_type', 'Unknown')}
            API Elements: {', '.join(cp.get('api_elements', []))}
            Required Parameters: {', '.join(cp.get('required_parameters', []))}
            Optional Parameters: {', '.join(cp.get('optional_parameters', []))}
            Related Components: {', '.join(cp.get('related_components', []))}
            """
            
            # 8. Generate embedding from the analysis text
            embedding_vector = await embedding_manager.embed_text(embedding_text)
            
            # Convert embedding to list if it's a numpy array
            embedding_list = embedding_vector.vector.tolist() if hasattr(embedding_vector.vector, 'tolist') else list(embedding_vector.vector)
            
            # Get repository information for file record
            async with session_context() as session:
                repo_repo = RepositoryRepository(session)
                repository = await repo_repo.get_by_id(repo_id)
                
                if not repository:
                    logger.error(f"Repository with ID {repo_id} not found")
                    return None
                
                # Create a dictionary with all fields except content_tsvector
                repo_file_data = {
                    # Repository info
                    "repo_id": repo_id,
                    "repo_url": repository.url,
                    "repo_name": repository.name,
                    "repo_branch": repository.default_branch,
                    "repo_commit_hash": commit_hash,
                    "repo_metadata": {"git_status": "added", "file_type": metadata["file_type"]},
                    
                    # File info
                    "filepath": file_path,
                    "filename": Path(file_path).name,
                    "extension": Path(file_path).suffix.lower(),
                    "file_size": metadata["file_size"],
                    "last_modified": metadata["last_modified"],
                    "git_status": "added",
                    
                    # Content and analysis (excluding content_tsvector)
                    "content": content,
                    "analysis": analysis,
                    "tags": tags,
                    "file_type": file_type,
                    "technical_level": technical_level,
                    
                    # Embedding
                    "embedding_string": embedding_text,
                    "embedding": embedding_list,
                    
                    # Timestamps
                    "indexed_at": datetime.utcnow(),
                }
                
                # Create file object (Don't save to DB yet - that happens in process_file_batch)
                repo_file = RepositoryFile(**repo_file_data)
                
                return repo_file
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return None
    
    async def process_file_batch(
        self,
        file_paths: List[str],
        repo_id: int,
        git_repo: GitRepository,
        embedding_manager: EmbeddingManager,
        batch_index: int,
        total_batches: int,
        readme_content: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Process a batch of files with a single transaction.
        
        Args:
            file_paths: List of file paths to process
            repo_id: Repository ID
            git_repo: GitRepository instance
            embedding_manager: EmbeddingManager instance
            batch_index: Index of the current batch (for logging)
            total_batches: Total number of batches (for logging)
            readme_content: Optional README content to include in analysis
            
        Returns:
            Tuple of (success_count, failure_count)
        """
        # Process all files in this batch
        logger.info(f"Processing batch {batch_index+1}/{total_batches} with {len(file_paths)} files")
        
        # Verify repository exists before processing
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            repository = await repo_repo.get_by_id(repo_id)
            if not repository:
                logger.error(f"Repository with ID {repo_id} not found, cannot process files")
                return (0, len(file_paths))  # All files failed
        
        # Create a semaphore to limit the number of concurrent API requests
        # This helps avoid overwhelming the API and hitting rate limits
        max_concurrent = min(self.parallel_workers, len(file_paths))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Define a helper function to process a single file with the semaphore
        async def process_single_file(file_path: str, file_index: int):
            async with semaphore:
                logger.info(f"Batch {batch_index+1}/{total_batches} - Processing file {file_index+1}/{len(file_paths)}: {file_path}")
                
                # Get file metadata and extract content
                if not git_repo.is_cloned() or not git_repo.repo:
                    logger.error(f"Repository is not properly cloned")
                    return None
                
                # Get full file path
                repo_path = Path(git_repo.repo.working_dir)
                full_path = repo_path / file_path
                
                try:
                    # Initialize file extractor
                    extractor = FileExtractor(
                        max_file_size_mb=get_float_env("MAX_FILE_SIZE_MB", 10),
                    )
                    
                    # Extract file metadata
                    metadata = extractor.get_file_metadata(full_path)
                    
                    # Extract file content
                    content = extractor.extract_content(full_path)
                    
                    # Skip empty files
                    if content is None or content.strip() == "":
                        logger.debug(f"Skipping empty file: {file_path}")
                        return None
                    
                    # Get git metadata including commit hash
                    commit_hash = git_repo.get_file_commit_hash(file_path)
                    
                    # Generate structured analysis using Google Gemini with retry logic
                    max_retries = 10
                    retry_delay = 2  # Initial delay in seconds
                    
                    for retry_attempt in range(max_retries):
                        try:
                            analysis = await embedding_manager.analyze_file_content(content, readme_content)
                            
                            # Check if required fields exist
                            if not analysis.get('document_type') or not analysis.get('technical_level'):
                                raise ValueError("Missing required fields in analysis response")
                                
                            # Successfully got analysis, exit retry loop
                            break
                            
                        except Exception as e:
                            if retry_attempt < max_retries - 1:
                                # Calculate exponential backoff delay
                                backoff_delay = retry_delay * (2 ** retry_attempt)
                                logger.info(f"Retry {retry_attempt+1}/{max_retries} for {file_path}: {str(e)} - waiting {backoff_delay}s")
                                await asyncio.sleep(backoff_delay)
                            else:
                                # Last attempt failed, create a basic analysis structure
                                logger.warning(f"All {max_retries} analysis attempts failed for {file_path}")
                                analysis = {
                                    "title": f"File: {Path(file_path).name}",
                                    "summary": f"Content from {file_path}",
                                    "document_type": "Unknown",
                                    "technical_level": "Unknown",
                                    "key_concepts": [],
                                    "potential_questions": [],
                                    "keywords": [Path(file_path).stem, Path(file_path).suffix.replace('.', '')],
                                    "related_topics": []
                                }
                    
                    # Extract metadata fields
                    file_type = analysis.get('document_type', 'Unknown')
                    technical_level = analysis.get('technical_level', 'Unknown')
                    tags = extract_tags_from_analysis(analysis)
                    
                    # Create embedding string from analysis
                    embedding_text = f"""
                    Filename: {Path(file_path).name}
                    Filepath: {file_path}
                    Repository: {repository.name}
                    
                    Title: {analysis.get('title', 'No title')}
                    
                    Summary: {analysis.get('summary', 'No summary')}
                    
                    Key Concepts: {', '.join(analysis.get('key_concepts', []))}
                    
                    Potential Questions: {' '.join(analysis.get('potential_questions', []))}
                    
                    Keywords: {', '.join(analysis.get('keywords', []))}
                    
                    Document Type: {file_type}
                    
                    Technical Level: {technical_level}
                    
                    Related Topics: {', '.join(analysis.get('related_topics', []))}
                    
                    Prerequisites: {', '.join(analysis.get('prerequisites', []))}
                    """
                    
                    # Add code snippets if available
                    if analysis.get('code_snippets') and len(analysis.get('code_snippets', [])) > 0:
                        snippet_texts = []
                        for j, snippet in enumerate(analysis.get('code_snippets', [])):
                            snippet_text = f"Snippet {j+1} ({snippet.get('language', 'unknown')}): {snippet.get('purpose', '')}\n{snippet.get('summary', '')}"
                            snippet_texts.append(snippet_text)
                        
                        joined_snippets = "\n".join(snippet_texts)
                        embedding_text += f"""
                    Code Snippets:
                    {joined_snippets}
                    """
                        
                        if analysis.get('code_snippets_overview'):
                            embedding_text += f"""
                    Code Snippets Overview: {analysis.get('code_snippets_overview')}
                    """
                    
                    # Add component properties if available
                    if analysis.get('component_properties'):
                        cp = analysis.get('component_properties', {})
                        embedding_text += f"""
                    Component Type: {cp.get('component_type', 'Unknown')}
                    API Elements: {', '.join(cp.get('api_elements', []))}
                    Required Parameters: {', '.join(cp.get('required_parameters', []))}
                    Optional Parameters: {', '.join(cp.get('optional_parameters', []))}
                    Related Components: {', '.join(cp.get('related_components', []))}
                    """
                    
                    # Generate embedding from the analysis text
                    embedding_vector = await embedding_manager.embed_text(embedding_text)
                    
                    # Convert embedding to list if it's a numpy array
                    embedding_list = embedding_vector.vector.tolist() if hasattr(embedding_vector.vector, 'tolist') else list(embedding_vector.vector)
                    
                    # Return the processed file data
                    return {
                        "filepath": file_path,
                        "filename": Path(file_path).name,
                        "extension": Path(file_path).suffix.lower(),
                        "content": content,
                        "commit_hash": commit_hash,
                        "metadata": metadata,
                        "analysis": analysis,
                        "tags": tags,
                        "file_type": file_type,
                        "technical_level": technical_level,
                        "embedding_string": embedding_text,
                        "embedding": embedding_list
                    }
                
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    return None
        
        # Process all files concurrently using asyncio.gather
        tasks = [process_single_file(file_path, i) for i, file_path in enumerate(file_paths)]
        file_results = await asyncio.gather(*tasks)
        
        # Filter out None results and track failed files
        processed_files = []
        failed_file_paths = []
        
        for i, result in enumerate(file_results):
            if result is not None:
                processed_files.append(result)
            else:
                failed_file_paths.append(file_paths[i])
        
        success_count = len(processed_files)
        failure_count = len(failed_file_paths)
        
        # Save all processed files in a single transaction
        if processed_files:
            async with session_context() as session:
                try:
                    file_repo = RepositoryFileRepository(session)
                    
                    # Check for existing files and delete them
                    for file_data in processed_files:
                        filepath = file_data["filepath"]
                        existing_file = await file_repo.get_by_path(repo_id, filepath)
                        if existing_file:
                            await file_repo.delete(existing_file.id)
                            logger.debug(f"Deleted existing file: {filepath}")
                    
                    # Get repository for metadata
                    repo_repo = RepositoryRepository(session)
                    repository = await repo_repo.get_by_id(repo_id)
                    
                    # Verify repository exists
                    if not repository:
                        logger.error(f"Repository with ID {repo_id} not found when saving files")
                        return (0, len(file_paths), file_paths)
                    
                    # Create and add new files
                    for file_data in processed_files:
                        # Create a dictionary with all fields except content_tsvector
                        repo_file_data = {
                            # Repository info
                            "repo_id": repo_id,
                            "repo_url": repository.url,
                            "repo_name": repository.name,
                            "repo_branch": repository.default_branch,
                            "repo_commit_hash": file_data["commit_hash"],
                            "repo_metadata": {"git_status": "added", "file_type": file_data["metadata"]["file_type"]},
                            
                            # File info
                            "filepath": file_data["filepath"],
                            "filename": file_data["filename"],
                            "extension": file_data["extension"],
                            "file_size": file_data["metadata"]["file_size"],
                            "last_modified": file_data["metadata"]["last_modified"],
                            "git_status": "added",
                            
                            # Content and analysis (excluding content_tsvector)
                            "content": file_data["content"],
                            "analysis": file_data["analysis"],
                            "tags": file_data["tags"],
                            "file_type": file_data["file_type"],
                            "technical_level": file_data["technical_level"],
                            
                            # Embedding
                            "embedding_string": file_data["embedding_string"],
                            "embedding": file_data["embedding"],
                            
                            # Timestamps
                            "indexed_at": datetime.utcnow(),
                        }
                        
                        # Create the RepositoryFile object (content_tsvector will be generated by PostgreSQL)
                        repo_file = RepositoryFile(**repo_file_data)
                        
                        session.add(repo_file)
                    
                    # Commit the transaction
                    await session.commit()
                    logger.info(f"Saved {len(processed_files)} files to database")
                except Exception as e:
                    logger.error(f"Database transaction failed: {str(e)}")
                    await session.rollback()
                    # Count all files as failures
                    failure_count = len(file_paths)
                    success_count = 0
                    failed_file_paths = file_paths
        
        logger.info(f"Batch {batch_index+1}/{total_batches} completed: {success_count} succeeded, {failure_count} failed")
        return (success_count, failure_count, failed_file_paths)
    
    async def process_repository(
        self,
        repo_url: Optional[str] = None,
        repo_id: Optional[int] = None,
        branch: Optional[str] = None,
        limit: Optional[int] = None,
        include_tests: bool = False,
        include_readme: bool = False,
    ) -> Tuple[int, int, List[str]]:
        """
        Process a repository with the complete workflow.
        
        Args:
            repo_url: Repository URL (if not provided, repo_id must be specified)
            repo_id: Repository ID (if not provided, repo_url must be specified)
            branch: Optional branch name
            limit: Optional limit on number of files to process
            include_tests: Whether to include test files and directories (default: False)
            include_readme: Whether to include README.md content in file analysis (default: False)
            
        Returns:
            Tuple of (success_count, failure_count, failed_files_list)
        """
        total_success = 0
        total_failure = 0
        failed_files = []
        
        # Get or create repository
        if repo_url:
            repo_info = await self.get_or_create_repository(repo_url, branch)
            if not repo_info:
                return (0, 0, [])
            repo_id, git_repo = repo_info
        elif repo_id:
            # Get existing repository
            async with session_context() as session:
                repo_repo = RepositoryRepository(session)
                repository = await repo_repo.get_by_id(repo_id)
                
                if not repository:
                    logger.error(f"Repository with ID {repo_id} not found")
                    return (0, 0, [])
                
                # Initialize Git repository
                git_repo = GitRepository(repository.url, repository.clone_path, repository.default_branch)
                
                if not git_repo.is_cloned():
                    logger.error(f"Repository is not cloned. Please clone it first.")
                    return (0, 0, [])
                
                # Get the actual branch name
                actual_branch = git_repo.get_current_branch()
                
                # If repository has null default_branch, update it with the actual branch
                if actual_branch and (repository.default_branch is None or repository.default_branch == ""):
                    logger.info(f"Updating repository default branch to {actual_branch}")
                    repository.default_branch = actual_branch
                    await repo_repo.update(repository)
                
                # Update repository status
                await repo_repo.update_status(repo_id, RepoStatus.INDEXING.value)
        else:
            logger.error("Either repo_url or repo_id must be specified")
            return (0, 0, [])
        
        # Extract README content if requested
        readme_content = None
        if include_readme:
            readme_content = await self.extract_readme_content(git_repo)
            if readme_content:
                logger.info("README.md content extracted successfully")
            else:
                logger.info("No README.md found in repository")

        # Create embedding manager
        embedding_manager = await self.create_embedding_manager()
        
        # Extract files from repository
        file_paths = await self.extract_repository_files(repo_id, git_repo, limit, include_tests)
        
        if not file_paths:
            logger.info(f"No files found for repository ID {repo_id}")
            return (0, 0, [])
        
        total_files = len(file_paths)
        logger.info(f"Found {total_files} files to process")
        
        # Create batches of files
        batches = [file_paths[i:i + self.batch_size] for i in range(0, total_files, self.batch_size)]
        total_batches = len(batches)
        logger.info(f"Split into {total_batches} batches of {self.batch_size} files (max)")
        
        # Process batches in parallel, but limit the number of concurrent batches
        # This limits the total concurrent processing while still being faster than sequential processing
        max_concurrent_batches = min(3, total_batches)  # Process up to 3 batches concurrently
        batch_semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_batch_with_semaphore(batch, batch_index):
            async with batch_semaphore:
                return await self.process_file_batch(
                    batch,
                    repo_id,
                    git_repo,
                    embedding_manager,
                    batch_index,
                    total_batches,
                    readme_content
                )
        
        # Create tasks for all batches
        batch_tasks = [process_batch_with_semaphore(batch, i) for i, batch in enumerate(batches)]
        
        # Process all batches and gather results
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Process results
        for i, (batch_success, batch_failure, batch_failed_files) in enumerate(batch_results):
            total_success += batch_success
            total_failure += batch_failure
            failed_files.extend(batch_failed_files)
            
            logger.info(f"Completed batch {i+1}/{total_batches}: {batch_success} succeeded, {batch_failure} failed")
            
        logger.info(f"All batches completed: {total_success + total_failure}/{total_files} files processed ({total_success} succeeded, {total_failure} failed)")
        
        # Update repository status and last indexed time
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            repository = await repo_repo.get_by_id(repo_id)
            if repository:
                # Update repository properties
                repository.status = RepoStatus.READY.value
                repository.last_indexed_at = datetime.utcnow()
                repository.last_commit_hash = git_repo.get_last_commit()
                repository.file_count = total_success
                
                # Save the changes
                await repo_repo.update(repository)
        
        logger.info(f"Repository processing completed: {total_success} succeeded, {total_failure} failed")
        
        # Log failed files if any
        if failed_files:
            logger.info("\nFailed files:")
            for failed_file in failed_files:
                logger.info(f"  - {failed_file}")
        
        return (total_success, total_failure, failed_files)
    
    async def update_single_file(
        self,
        repo_id: int,
        filepath: str,
        include_readme: bool = False,
    ) -> bool:
        """
        Update a single file in an existing repository.
        
        Args:
            repo_id: Repository ID
            filepath: Path to the file relative to repository root (e.g., "README.md")
            include_readme: Whether to include README.md content in file analysis
            
        Returns:
            True if successful, False otherwise
        """
        # Get repository
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            repository = await repo_repo.get_by_id(repo_id)
            
            if not repository:
                logger.error(f"Repository with ID {repo_id} not found")
                return False
            
            # Initialize Git repository
            git_repo = GitRepository(repository.url, repository.clone_path, repository.default_branch)
            
            if not git_repo.is_cloned():
                logger.error(f"Repository is not cloned. Please clone it first.")
                return False
            
            # Update repository to get latest changes
            success, changed_files = git_repo.update()
            if not success:
                logger.error(f"Failed to update repository")
                return False
            
            logger.info(f"Repository updated successfully")
        
        # Check if file exists in repository
        repo_path = Path(git_repo.repo.working_dir)
        full_path = repo_path / filepath
        
        if not full_path.exists():
            logger.error(f"File {filepath} not found in repository")
            return False
        
        # Extract README content if requested and it's not the file being updated
        readme_content = None
        if include_readme and filepath.lower() != "readme.md":
            readme_content = await self.extract_readme_content(git_repo)
            if readme_content:
                logger.info("README.md content extracted for context")
        
        # Create embedding manager
        embedding_manager = await self.create_embedding_manager()
        
        # Process the single file
        logger.info(f"Processing file: {filepath}")
        
        try:
            # Process the file
            repo_file = await self.process_file(
                filepath,
                repo_id,
                git_repo,
                embedding_manager,
                readme_content
            )
            
            if not repo_file:
                logger.error(f"Failed to process file {filepath}")
                return False
            
            # Save or update the file in database
            async with session_context() as session:
                file_repo = RepositoryFileRepository(session)
                
                # Check if file already exists
                existing_file = await file_repo.get_by_path(repo_id, filepath)
                
                if existing_file:
                    logger.info(f"Updating existing file: {filepath}")
                    # Update existing file with new data
                    existing_file.content = repo_file.content
                    existing_file.embedding = repo_file.embedding
                    existing_file.embedding_string = repo_file.embedding_string
                    existing_file.analysis = repo_file.analysis
                    existing_file.tags = repo_file.tags
                    existing_file.file_type = repo_file.file_type
                    existing_file.technical_level = repo_file.technical_level
                    existing_file.file_size = repo_file.file_size
                    existing_file.last_modified = repo_file.last_modified
                    existing_file.repo_commit_hash = repo_file.repo_commit_hash
                    existing_file.indexed_at = datetime.utcnow()
                    
                    # Save changes
                    await file_repo.update(existing_file)
                else:
                    logger.info(f"Creating new file: {filepath}")
                    # Add new file
                    session.add(repo_file)
                    await session.commit()
                
                logger.info(f"Successfully updated file: {filepath}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating file {filepath}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False