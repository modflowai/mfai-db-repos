"""
Google GenAI (Gemini) embedding provider implementation.
Uses the Google GenAI SDK to generate text embeddings.
"""
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from mfai_db_repos.lib.embeddings.base import EmbeddingConfig, EmbeddingProvider, EmbeddingVector
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleGenAIEmbeddingConfig(EmbeddingConfig):
    """Configuration for Google GenAI embedding API."""
    
    model: str = "text-embedding-004"
    dimensions: int = 768  # Default dimension for Gemini embeddings
    api_key: Optional[str] = None
    use_vertex_ai: bool = False
    vertex_project: Optional[str] = None
    vertex_location: Optional[str] = None
    vertex_api_version: Optional[str] = None
    task_type: str = "RETRIEVAL_DOCUMENT"  # or "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY", etc.
    output_dimensionality: Optional[int] = None  # If specified, overrides dimensions


class CodeSnippet(BaseModel):
    """Schema for code snippets within the structured analysis."""
    
    language: str
    purpose: str
    code: str
    summary: str

class ComponentProperties(BaseModel):
    """Schema for component properties within the structured analysis."""
    
    component_type: str
    api_elements: List[str]
    required_parameters: List[str]
    optional_parameters: List[str]
    related_components: List[str]

class DocumentHierarchy(BaseModel):
    """Schema for document hierarchy within the structured analysis."""
    
    section: str
    subsection: Optional[str]
    related_pages: List[str]

class StructuredResponseSchema(BaseModel):
    """Schema for comprehensive structured responses from Gemini models."""
    
    title: str
    summary: str
    key_concepts: List[str]
    potential_questions: List[str]
    code_snippets: List[CodeSnippet] = []
    code_snippets_overview: Optional[str] = None
    snippet_count: int = 0
    component_properties: Optional[ComponentProperties] = None
    keywords: List[str]
    related_topics: List[str] = []
    document_type: str
    technical_level: str
    prerequisites: List[str] = []
    document_hierarchy: Optional[DocumentHierarchy] = None


class GoogleGenAIEmbeddingProvider(EmbeddingProvider):
    """Google GenAI (Gemini) implementation of embedding provider."""
    
    def __init__(self, config: GoogleGenAIEmbeddingConfig):
        """Initialize Google GenAI embedding provider with configuration.
        
        Args:
            config: GoogleGenAIEmbeddingConfig instance with provider settings
        """
        super().__init__(config)
        self.config = config
        
        # Initialize the Google GenAI client
        if config.use_vertex_ai:
            self.client = genai.Client(
                vertexai=True,
                project=config.vertex_project,
                location=config.vertex_location,
                http_options=types.HttpOptions(api_version=config.vertex_api_version) if config.vertex_api_version else None
            )
        else:
            self.client = genai.Client(api_key=config.api_key)
            
        # Create async client
        self.async_client = self.client.aio
        
        logger.info(f"Initialized Google GenAI embedding provider with model: {config.model}")
    
    async def embed_text(self, text: str) -> EmbeddingVector:
        """Generate an embedding for a single text input.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingVector with the generated embedding
        """
        try:
            embed_config = None
            if self.config.output_dimensionality:
                embed_config = types.EmbedContentConfig(
                    task_type=self.config.task_type,
                    output_dimensionality=self.config.output_dimensionality
                )
                
            response = await self.async_client.models.embed_content(
                model=self.config.model,
                contents=text,
                config=embed_config
            )
            
            # Extract the embedding vector from the response
            embedding = response.embedding.values
            
            return EmbeddingVector(
                vector=embedding,
                model=self.config.model
            )
        except Exception as e:
            logger.error(f"Error generating Google GenAI embedding: {str(e)}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """Generate embeddings for a batch of text inputs.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of EmbeddingVector objects
        """
        if not texts:
            return []
        
        try:
            embed_config = None
            if self.config.output_dimensionality:
                embed_config = types.EmbedContentConfig(
                    task_type=self.config.task_type,
                    output_dimensionality=self.config.output_dimensionality
                )
                
            response = await self.async_client.models.embed_content(
                model=self.config.model,
                contents=texts,
                config=embed_config
            )
            
            # Extract embedding vectors from the response
            result = []
            for embedding in response.embeddings:
                result.append(
                    EmbeddingVector(
                        vector=embedding.values,
                        model=self.config.model
                    )
                )
            
            return result
        except Exception as e:
            logger.error(f"Error generating batch Google GenAI embeddings: {str(e)}")
            raise
    
    async def embed_file_content(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> EmbeddingVector:
        """Generate an embedding for file content.
        
        Args:
            content: File content to embed
            metadata: Optional metadata about the file
            
        Returns:
            EmbeddingVector with the generated embedding
        """
        # For GenAI, we simply embed the content directly
        # Truncate content if it's too long
        max_chars = 60000  # Approximate limit to stay within token limits
        if len(content) > max_chars:
            logger.warning(f"File content truncated from {len(content)} to {max_chars} characters for embedding")
            content = content[:max_chars]
            
        return await self.embed_text(content)
    
    async def generate_structured_analysis(self, content: str, readme_content: Optional[str] = None) -> StructuredResponseSchema:
        """Generate a structured analysis of file content using Gemini model.
        
        Args:
            content: File content to analyze
            readme_content: Optional README content to provide repository context
            
        Returns:
            StructuredResponseSchema with structured analysis of the content
        """
        try:
            # Use a more capable model for structured analysis
            analysis_model = "gemini-2.5-flash-preview-05-20"
            
            # Handle README content length validation and truncation
            readme_section = ""
            if readme_content:
                max_readme_chars = 15000  # Reserve space for README content 
                if len(readme_content) > max_readme_chars:
                    logger.warning(f"README content truncated from {len(readme_content)} to {max_readme_chars} characters")
                    readme_content = readme_content[:max_readme_chars]
                
                readme_section = f"""
# Repository Context (from README):
{readme_content}

"""
            
            # Truncate file content if it's too long (adjust based on README presence)
            max_chars = 45000 if readme_content else 60000  # Leave room for README content
            if len(content) > max_chars:
                logger.warning(f"File content truncated from {len(content)} to {max_chars} characters for analysis")
                content = content[:max_chars]
            
            # Create detailed analysis prompt with instructions
            analysis_prompt = f"""
# Analysis Task
{readme_section}Analyze the following file content and provide comprehensive structured information according to the instructions below:

{content}

# Analysis Instructions:

## Document Analysis:
- Use the repository context (if provided) to better understand the project's purpose and architecture
- Analyze the content to identify the key components, patterns, and architecture
- For code files, identify the programming paradigms, design patterns, and architecture
- Note dependencies and relationships between components

## Title Creation:
- Create a concise title that clearly indicates the document's purpose
- Format consistently with naming conventions
- Include specific class/function names if it's code

## Semantic Summary Generation:
- Create a comprehensive summary (250-400 words) that captures the semantic essence of the document
- Use the repository context to explain how this code or content fits into the broader project architecture
- For code files, describe its purpose, when to use it, and how it differs from similar components
- Include specific class names, method signatures, parameter names, and return types where relevant

## Key Concepts Extraction:
- Identify 5-10 core concepts discussed in the document
- Include both explicit concepts (mentioned by name) and implicit concepts

## Potential Questions Generation:
- Generate 8-12 natural language questions that this document would answer
- Include different query formulations that developers might use

## Code Snippet Analysis:
- Extract all code examples with their context
- For each snippet, identify:
  - The language
  - What the code demonstrates
  - Key classes, methods, and parameters used
  - Expected output or behavior

## Component Properties Extraction:
- Identify the component type
- Document key API elements (classes, functions, methods, parameters)
- List required and optional elements
- Note interactions with other components

## Keyword Extraction:
- Extract 15-20 keywords that represent important technical terms
- Include specific class names, parameter names, and method names

# Response Format:
Provide a valid JSON response following the structure as defined in the response schema.
"""
        
            # Request structured output from Gemini
            response = await self.async_client.models.generate_content(
                model=analysis_model,
                contents=analysis_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_schema=StructuredResponseSchema,
                ),
            )
            
            # Parse the structured response
            analysis_result = StructuredResponseSchema.model_validate_json(response.text)
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error generating structured analysis: {str(e)}")
            # Return a minimal valid response in case of error
            return StructuredResponseSchema(
                title="Error analyzing content",
                summary="An error occurred during content analysis",
                key_concepts=["error"],
                keywords=["error"]
            )