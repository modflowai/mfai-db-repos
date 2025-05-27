# Single File Update Feature

## Overview

The single file update feature allows you to update individual files in a repository without reprocessing the entire repository. This is particularly useful for frequently changing files like README.md or documentation files.

## Usage

### Command Line Interface

```bash
# Update README.md in repository with ID 1
python -m mfai_db_repos.cli.main process file --repo-id 1 --filepath README.md

# Update a documentation file with README context
python -m mfai_db_repos.cli.main process file --repo-id 2 --filepath docs/guide.md --include-readme

# Update with verbose logging
python -m mfai_db_repos.cli.main process file --repo-id 1 --filepath README.md -v
```

### Programmatic Usage

```python
from mfai_db_repos.core.services.processing_service import RepositoryProcessingService

# Create service
service = RepositoryProcessingService()

# Update a single file
success = await service.update_single_file(
    repo_id=1,
    filepath="README.md",
    include_readme=False,  # Don't include README in its own analysis
)

if success:
    print("File updated successfully!")
```

## How It Works

1. **Repository Update**: First pulls the latest changes from the git repository
2. **File Verification**: Checks if the specified file exists
3. **Content Processing**: Extracts and processes the file content
4. **Analysis & Embeddings**: Regenerates structured analysis and vector embeddings
5. **Database Update**: Updates existing record or creates new one if file is new

## Use Cases

### Updating README.md with Table of Contents

When you add a table of contents to README files:

```bash
# First, update README.md in your git repository with TOC
# Then update just that file in the database
python -m mfai_db_repos.cli.main process file --repo-id 1 --filepath README.md
```

### Updating Documentation Files

For documentation that changes frequently:

```bash
# Update specific documentation files
python -m mfai_db_repos.cli.main process file --repo-id 2 --filepath docs/api.md --include-readme
python -m mfai_db_repos.cli.main process file --repo-id 2 --filepath docs/changelog.md
```

### Updating Configuration Files

When configuration files change:

```bash
# Update configuration files that may have new parameters
python -m mfai_db_repos.cli.main process file --repo-id 3 --filepath config/settings.yaml
```

## Performance Benefits

- **Faster Updates**: Updates single file instead of entire repository
- **Resource Efficient**: Uses less API calls for embeddings and analysis
- **Targeted Updates**: Only regenerates data for changed files
- **Preserves History**: Maintains the rest of the repository's indexed data

## Notes

- The repository must already exist in the database
- The file path should be relative to the repository root
- The command will pull latest changes from git before processing
- If the file doesn't exist yet, it will be created as a new entry