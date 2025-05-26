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
    code: str = ""  # Keep empty to avoid JSON escaping issues
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
    
    def _encode_content_base64(self, content: str) -> str:
        """Encode content as base64 to prevent JSON parsing errors.
        
        This is the most robust way to handle code content with complex
        escape sequences, quotes, and special characters.
        
        Args:
            content: Raw content to encode
            
        Returns:
            Base64-encoded content safe for JSON transmission
        """
        import base64
        
        # Encode the content as base64
        content_bytes = content.encode('utf-8')
        encoded = base64.b64encode(content_bytes).decode('ascii')
        return encoded

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
            analysis_model = "gemini-2.0-flash"
            
            # Handle content truncation before encoding
            max_chars = 485000 if readme_content else 500000  # Leave room for README content (500k - 15k)
            if len(content) > max_chars:
                logger.warning(f"File content truncated from {len(content)} to {max_chars} characters for analysis")
                content = content[:max_chars]
            
            # Encode content as base64 to prevent JSON parsing errors
            encoded_content = self._encode_content_base64(content)
            
            # Handle README content length validation and encoding
            readme_section = ""
            if readme_content:
                max_readme_chars = 15000  # Reserve space for README content 
                if len(readme_content) > max_readme_chars:
                    logger.warning(f"README content truncated from {len(readme_content)} to {max_readme_chars} characters")
                    readme_content = readme_content[:max_readme_chars]
                
                # Encode README content as base64
                encoded_readme = self._encode_content_base64(readme_content)
                
                readme_section = f"""
# Repository Context (from README, base64-encoded):
{encoded_readme}

"""
            
            # Create detailed analysis prompt with instructions
            analysis_prompt = f"""
# Analysis Task
{readme_section}The following file content is base64-encoded to preserve special characters and escape sequences.
Analyze this file and provide comprehensive structured information according to the instructions below:

# File Content (base64-encoded):
{encoded_content}

# Analysis Instructions:

## Important: Content Handling
- The file content and README (if present) are base64-encoded to preserve special characters
- Decode the base64 content to understand what to analyze
- When generating your JSON response, be extremely careful with escaping
- Do NOT include raw code snippets in your response - only describe them

## Document Analysis:
- Use the repository context (if provided) to better understand the project's purpose and domain
- Analyze the content considering its domain (groundwater modeling, parameter estimation, scientific computing)
- For code files: identify algorithms, numerical methods, and computational patterns
- For documentation: identify concepts, procedures, specifications, and guidelines
- For scientific content: identify theories, equations, methodologies, and assumptions
- Note relationships between components, models, or concepts

## Title Creation:
- Create a concise title that clearly indicates the document's purpose
- Format consistently with naming conventions
- Include specific class/function names if it's code

## Semantic Summary Generation:
- Create a comprehensive summary (250-400 words) that captures the semantic essence of the document
- Use the repository context to explain how this content fits into the broader system or domain
- For code: describe algorithms, numerical methods, and computational purpose
- For documentation: explain concepts, procedures, and practical applications
- For scientific content: describe theories, methodologies, and significance
- Include specific technical terms, parameter names, equations, or method names where relevant
- Consider the audience: scientists, engineers, modelers, consultants, researchers

## Key Concepts Extraction:
- Identify 5-10 core concepts discussed in the document
- Include both explicit concepts (mentioned by name) and implicit concepts

## Potential Questions Generation:
- Generate 8-12 natural language questions that this document would answer
- Consider diverse user perspectives (scientists, engineers, modelers, researchers, consultants)
- Include technical, practical, theoretical, and troubleshooting questions as appropriate
- Match question complexity to the document's technical level
- For scientific/modeling content: include domain-specific terminology
- For documentation: include how-to and configuration questions
- For code: include implementation and usage questions

## Code Snippet Analysis:
- Identify code examples and their context
- For each snippet, provide:
  - The language
  - What the code demonstrates (purpose)
  - A summary of what it does
  - IMPORTANT: Leave the 'code' field empty - do not include actual code to avoid JSON escaping issues

## Component Properties Extraction:
- Identify the component type
- Document key API elements (classes, functions, methods, parameters)
- List required and optional elements
- Note interactions with other components

## Keyword Extraction:
- Extract 15-20 keywords that represent important terms in the domain
- Include technical terms, parameter names, solver names, model types
- Include domain-specific terminology (e.g., hydraulic conductivity, regularization, convergence)
- Include software/package names, file formats, and standards where relevant

# Response Format:
Provide a valid JSON response following the structure as defined in the response schema.
"""
        
            # Request structured output from Gemini
            # Use a custom format to avoid JSON parsing issues
            custom_prompt = analysis_prompt + """

# Response Format:
Instead of JSON, return your response in this exact format with clear delimiters:

===TITLE===
[Your title here]

===SUMMARY===
[Your summary here]

===KEY_CONCEPTS===
- concept1
- concept2
- concept3
[etc...]

===POTENTIAL_QUESTIONS===
- question1
- question2
- question3
[etc...]

===KEYWORDS===
- keyword1
- keyword2
- keyword3
[etc...]

===DOCUMENT_TYPE===
[code/documentation/configuration/etc]

===TECHNICAL_LEVEL===
[beginner/intermediate/advanced]

===CODE_SNIPPETS_COUNT===
[number]

===CODE_SNIPPETS_OVERVIEW===
[Optional overview of code snippets]

===RELATED_TOPICS===
- topic1
- topic2
[etc...]

===PREREQUISITES===
- prerequisite1
- prerequisite2
[etc...]

===END===
"""
            
            response = await self.async_client.models.generate_content(
                model=analysis_model,
                contents=custom_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=8192,
                ),
            )
            
            # Parse the custom format response
            logger.debug(f"Raw Gemini response length: {len(response.text)} characters")
            
            # Parse the custom format
            def parse_section(text: str, start_marker: str, end_marker: str = None) -> str:
                """Extract content between markers."""
                start_idx = text.find(start_marker)
                if start_idx == -1:
                    return ""
                    
                start_idx += len(start_marker)
                
                if end_marker:
                    end_idx = text.find(end_marker, start_idx)
                    if end_idx == -1:
                        return text[start_idx:].strip()
                    return text[start_idx:end_idx].strip()
                else:
                    # Find next section marker
                    next_marker_idx = text.find("\n===", start_idx)
                    if next_marker_idx == -1:
                        return text[start_idx:].strip()
                    return text[start_idx:next_marker_idx].strip()
            
            def parse_list_section(text: str, start_marker: str) -> List[str]:
                """Extract list items from a section."""
                section = parse_section(text, start_marker)
                if not section:
                    return []
                    
                items = []
                for line in section.split('\n'):
                    line = line.strip()
                    if line.startswith('- '):
                        items.append(line[2:])
                    elif line and not line.startswith('['):
                        items.append(line)
                        
                return items
            
            response_text = response.text
            
            # Extract all sections
            title = parse_section(response_text, "===TITLE===")
            summary = parse_section(response_text, "===SUMMARY===")
            key_concepts = parse_list_section(response_text, "===KEY_CONCEPTS===")
            potential_questions = parse_list_section(response_text, "===POTENTIAL_QUESTIONS===")
            keywords = parse_list_section(response_text, "===KEYWORDS===")
            document_type = parse_section(response_text, "===DOCUMENT_TYPE===")
            technical_level = parse_section(response_text, "===TECHNICAL_LEVEL===")
            
            # Handle optional fields
            snippets_count_str = parse_section(response_text, "===CODE_SNIPPETS_COUNT===")
            try:
                snippet_count = int(snippets_count_str) if snippets_count_str else 0
            except:
                snippet_count = 0
                
            code_snippets_overview = parse_section(response_text, "===CODE_SNIPPETS_OVERVIEW===")
            related_topics = parse_list_section(response_text, "===RELATED_TOPICS===")
            prerequisites = parse_list_section(response_text, "===PREREQUISITES===")
            
            # Create the structured response - NO FALLBACKS
            # If critical fields are missing, this should fail so we can debug
            if not title:
                raise ValueError("Failed to extract title from Gemini response")
            if not summary:
                raise ValueError("Failed to extract summary from Gemini response")
            if not key_concepts:
                raise ValueError("Failed to extract key_concepts from Gemini response")
            if not potential_questions:
                raise ValueError("Failed to extract potential_questions from Gemini response")
            if not keywords:
                raise ValueError("Failed to extract keywords from Gemini response")
            if not document_type:
                raise ValueError("Failed to extract document_type from Gemini response")
            if not technical_level:
                raise ValueError("Failed to extract technical_level from Gemini response")
            
            analysis_result = StructuredResponseSchema(
                title=title,
                summary=summary,
                key_concepts=key_concepts,
                potential_questions=potential_questions,
                keywords=keywords,
                document_type=document_type,
                technical_level=technical_level,
                code_snippets=[],  # Empty to avoid JSON issues
                code_snippets_overview=code_snippets_overview if code_snippets_overview else None,
                snippet_count=snippet_count,
                related_topics=related_topics,
                prerequisites=prerequisites
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error generating structured analysis: {str(e)}")
            raise