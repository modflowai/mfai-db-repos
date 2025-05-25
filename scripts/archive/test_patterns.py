#!/usr/bin/env python3
"""
Script to test the pattern matching logic for file filtering.
"""
import os
import sys
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the pattern matching from extractor
from gitcontext.lib.file_processor.extractor import FileExtractor

def test_pattern_matching():
    """Test the pattern matching logic with various patterns and paths."""
    extractor = FileExtractor()
    
    # Test patterns
    patterns = {
        "include": [
            "**/*.py",
            "**/*.md"
        ],
        "exclude": [
            "**/.git/**", 
            "**/node_modules/**", 
            "**/__pycache__/**"
        ]
    }
    
    # Test paths
    test_paths = [
        "/path/to/repo/file.py",
        "/path/to/repo/file.md", 
        "/path/to/repo/file.txt",
        "/path/to/repo/.git/config",
        "/path/to/repo/subfolder/file.py",
        "/path/to/repo/subfolder/deep/file.py",
        "/path/to/repo/__pycache__/file.py",
        "/path/to/repo/node_modules/package/file.js",
        "file.py",
        "README.md"
    ]
    
    print("Testing pattern matching logic...")
    
    # Function to convert glob pattern to regex (original)
    def glob_to_regex_original(pattern):
        regex = pattern.replace(".", r"\.").replace("**/", ".*").replace("*", "[^/]*").replace("?", ".")
        regex = f"^{regex}$"
        return regex
    
    # Improved function to convert glob pattern to regex
    def glob_to_regex_improved(pattern):
        # Handle special case of ** (match any directory depth)
        if "**" in pattern:
            # Replace **/ with a special marker that won't conflict with other patterns
            pattern = pattern.replace("**/", "__DOUBLE_STAR__")
            # Replace standard glob special characters
            pattern = pattern.replace(".", r"\.").replace("*", "[^/]*").replace("?", ".")
            # Replace the marker with the correct regex for matching any directory depth
            pattern = pattern.replace("__DOUBLE_STAR__", "(?:.*/)?")
            # Make sure we match the whole path
            return f"^{pattern}$"
        else:
            # Handle simple glob patterns
            pattern = pattern.replace(".", r"\.").replace("*", "[^/]*").replace("?", ".")
            return f"^{pattern}$"
    
    # Test both regex conversion methods
    print("\nOriginal regex conversion:")
    for pattern in patterns["include"] + patterns["exclude"]:
        print(f"  {pattern} -> {glob_to_regex_original(pattern)}")
    
    print("\nImproved regex conversion:")
    for pattern in patterns["include"] + patterns["exclude"]:
        print(f"  {pattern} -> {glob_to_regex_improved(pattern)}")
    
    # Test pattern matching with both methods
    print("\nPattern matching test:")
    print(f"{'Path':<40} | {'Original Match':<20} | {'Improved Match':<20}")
    print("-" * 80)
    
    for path in test_paths:
        # Test with original method
        orig_include = any(re.match(glob_to_regex_original(p), path) for p in patterns["include"])
        orig_exclude = any(re.match(glob_to_regex_original(p), path) for p in patterns["exclude"])
        orig_result = "Include" if orig_include and not orig_exclude else "Exclude"
        
        # Test with improved method
        impr_include = any(re.match(glob_to_regex_improved(p), path) for p in patterns["include"])
        impr_exclude = any(re.match(glob_to_regex_improved(p), path) for p in patterns["exclude"])
        impr_result = "Include" if impr_include and not impr_exclude else "Exclude"
        
        print(f"{path:<40} | {orig_result:<20} | {impr_result:<20}")
    
    # Test with actual repository paths from flopy
    print("\nTesting with real repository paths from flopy:")
    repo_path = Path("/home/danilopezmella/.gitcontext/repositories/flopy")
    
    if repo_path.exists():
        # Find some .py and .md files
        py_files = list(repo_path.glob("**/*.py"))[:5]
        md_files = list(repo_path.glob("**/*.md"))[:5]
        
        test_files = py_files + md_files
        
        for file_path in test_files:
            rel_path = file_path.relative_to(repo_path)
            path_str = str(rel_path)
            
            # Test with original method
            orig_include = any(re.match(glob_to_regex_original(p), path_str) for p in patterns["include"])
            orig_exclude = any(re.match(glob_to_regex_original(p), path_str) for p in patterns["exclude"])
            orig_result = "Include" if orig_include and not orig_exclude else "Exclude"
            
            # Test with improved method
            impr_include = any(re.match(glob_to_regex_improved(p), path_str) for p in patterns["include"])
            impr_exclude = any(re.match(glob_to_regex_improved(p), path_str) for p in patterns["exclude"])
            impr_result = "Include" if impr_include and not impr_exclude else "Exclude"
            
            print(f"{path_str:<40} | {orig_result:<20} | {impr_result:<20}")
    else:
        print(f"Repository path {repo_path} does not exist.")
    
    # Return the improved regex conversion function for implementation
    return glob_to_regex_improved


if __name__ == "__main__":
    # Run the tests
    improved_func = test_pattern_matching()
    
    # Print implementation suggestion
    print("\nRecommended implementation for _matches_glob_pattern:")
    print("""
    def _matches_glob_pattern(self, filepath: str, pattern: str) -> bool:
        \"\"\"Check if a filepath matches a glob pattern.
        
        Args:
            filepath: Path to check
            pattern: Glob pattern
            
        Returns:
            True if the path matches the pattern, False otherwise
        \"\"\"
        # Handle special case of ** (match any directory depth)
        if "**" in pattern:
            # Replace **/ with a special marker that won't conflict with other patterns
            pattern = pattern.replace("**/", "__DOUBLE_STAR__")
            # Replace standard glob special characters
            pattern = pattern.replace(".", r"\\.").replace("*", "[^/]*").replace("?", ".")
            # Replace the marker with the correct regex for matching any directory depth
            pattern = pattern.replace("__DOUBLE_STAR__", "(?:.*/)?")
            # Make sure we match the whole path
            regex_pattern = f"^{pattern}$"
        else:
            # Handle simple glob patterns
            regex_pattern = pattern.replace(".", r"\\.").replace("*", "[^/]*").replace("?", ".")
            regex_pattern = f"^{regex_pattern}$"
        
        return bool(re.match(regex_pattern, filepath))
    """)