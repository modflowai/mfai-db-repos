"""
Navigation Guide Generator using Gemini 2.5 Pro.

This tool uses Google's Gemini to analyze comprehensive READMEs and generate
intelligent navigation guides for MCP tools.
"""
import os
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from mfai_db_repos.utils.logger import get_logger
from mfai_db_repos.utils.env import load_env

# Load environment variables
load_env()

logger = get_logger(__name__)


class NavigationGeminiGenerator:
    """Generates navigation guides using Gemini 2.5 Pro."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-pro-preview-05-06"
        
    def generate_navigation(self, readme_path: str, repo_name: str) -> str:
        """Generate navigation guide from comprehensive README.
        
        Args:
            readme_path: Path to the comprehensive README file
            repo_name: Name of the repository
            
        Returns:
            Navigation guide as markdown
        """
        # Read the comprehensive README
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Create the prompt
        prompt = f"""You are creating a navigation guide for the {repo_name} repository to help LLMs choose the right search tools and find information efficiently.

Given this comprehensive README with all file analyses:

{readme_content}

Generate a concise navigation guide (maximum 150 lines) with these exact sections:

# {repo_name.upper()} - MCP Navigation Guide

## 🎯 Primary Purpose
[One powerful sentence that captures what this repository is THE authority on]

## 🔍 When to Search This Repository
- **Perfect for:** [3-5 specific query types this repo excels at]
- **Not suitable for:** [2-3 query types to search elsewhere]

## 🔧 Search Tool Selection

### Use FTS (Full-Text Search) for:
[List 10-15 ACTUAL important terms/parameters users would search for, like NOPTMAX, PHIMLIM, etc. - not generic words]
- Include specific parameter names from control files
- Include exact error message patterns
- Include command-line options

### Use Vector Search for:
[List 5-7 conceptual query patterns with examples]
- "How to..." queries with specific examples
- "What is..." queries with specific examples  
- "Why does..." queries with specific examples

## 📊 Common Query Patterns
| User Intent | Example Query | Best Tool | Why |
|------------|---------------|-----------|-----|
[5-7 rows of ACTUAL queries users would make, not generic patterns]

## 🏆 Repository Expertise Ranking
[What this repository is the ABSOLUTE AUTHORITY on - rank 1-10]
- [Topic]: 10/10 - [Why it's authoritative]
- [Topic]: 9/10 - [Why it's authoritative]
[Include 5-7 topics]

## 🔗 Integration & Workflow Context
- **Reads from:** [What file types/tools provide input]
- **Outputs to:** [What this tool produces]
- **Works with:** [Other tools in typical workflows]
- **Typical workflow:** [One sentence describing common use]

## 💡 Power User Tips
[3-5 specific search strategies for getting the best results]

## ⚡ Quick Reference Patterns
If looking for...
- Control file parameters → FTS: "PARAMETER_NAME"
- Error explanations → FTS: "exact error message"  
- Conceptual understanding → Vector: "explain concept"
- Workflow guidance → Vector: "how to achieve goal"

Remember: Be SPECIFIC. Extract ACTUAL parameters, errors, and concepts from the content, not generic examples."""
        
        try:
            # Generate response
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more focused output
                    max_output_tokens=8192,  # Increased for complete output
                    candidate_count=1
                )
            )
            
            # Extract the generated navigation guide
            if not response:
                logger.error("Gemini response is None")
                raise ValueError("No response from Gemini")
            
            # Try different ways to extract text based on response structure
            navigation_guide = None
            
            # For google.genai response format
            if hasattr(response, 'text'):
                navigation_guide = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                # Try to get from first candidate
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        navigation_guide = candidate.content.parts[0].text
                    elif hasattr(candidate.content, 'text'):
                        navigation_guide = candidate.content.text
            
            if navigation_guide is None or navigation_guide == "":
                logger.error("Could not extract text from Gemini response")
                logger.error(f"Response type: {type(response)}")
                if hasattr(response, '__dict__'):
                    logger.error(f"Response attributes: {response.__dict__.keys()}")
                raise ValueError("Gemini returned no content")
            
            # Clean up any potential formatting issues
            navigation_guide = navigation_guide.strip()
            
            return navigation_guide
            
        except Exception as e:
            logger.error(f"Failed to generate navigation with Gemini: {e}")
            raise
    
    def save_navigation(self, navigation_content: str, output_path: str) -> str:
        """Save the navigation guide to a file.
        
        Args:
            navigation_content: The generated navigation guide
            output_path: Path to save the navigation guide
            
        Returns:
            Path where navigation was saved
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(navigation_content)
        
        logger.info(f"Navigation guide saved to {output_path}")
        return str(output_path)


def main():
    """Main function to generate navigation guide."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate navigation guide using Gemini")
    parser.add_argument("readme_path", help="Path to comprehensive README")
    parser.add_argument("repo_name", help="Repository name")
    parser.add_argument("--output", help="Output path (defaults to NAVIGATION_GEMINI.md)", 
                       default=None)
    
    args = parser.parse_args()
    
    # Create generator
    generator = NavigationGeminiGenerator()
    
    # Generate navigation
    print(f"Generating navigation guide for {args.repo_name}...")
    navigation = generator.generate_navigation(args.readme_path, args.repo_name)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        readme_dir = Path(args.readme_path).parent
        output_path = readme_dir / "NAVIGATION_GEMINI.md"
    
    # Save navigation
    saved_path = generator.save_navigation(navigation, output_path)
    print(f"Navigation guide saved to: {saved_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())