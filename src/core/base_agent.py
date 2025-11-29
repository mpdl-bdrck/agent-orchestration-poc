"""Base agent classes for Agentic CRAG Launchpad."""

import os
# Suppress HuggingFace tokenizer parallelism warning
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging
import warnings

# Suppress Pydantic V1 deprecation warnings from langchain
warnings.filterwarnings('ignore', message='.*Pydantic V1.*', category=UserWarning)
# Suppress HuggingFace connection warnings
warnings.filterwarnings('ignore', message='.*huggingface.*', category=UserWarning)
warnings.filterwarnings('ignore', message='.*Connection.*', category=UserWarning)
warnings.filterwarnings('ignore', message='.*ProtocolError.*', category=UserWarning)

try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
except ImportError:
    ChatOpenAI = None
    OpenAIEmbeddings = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Check for sentence-transformers availability
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from .config import AgentConfig
from ..utils.observability import trace_agent
from .search.semantic_search import search_knowledge_base, validate_knowledge_chunks_exist

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all Agentic CRAG Launchpad agents."""

    def __init__(self, config_path: str):
        self.config = AgentConfig(Path(config_path))
        self._llm = None
        self._llm_error = None
        self.embedding_model = self._create_embedding_model()
        self.prompt = self._create_prompt()
        self.tools = self._load_tools()

        # Knowledge base context - set by calling code
        self.context_id = None

    @property
    def llm(self):
        """Lazy LLM creation with error handling."""
        if self._llm is None and self._llm_error is None:
            try:
                self._llm = self._create_llm()
            except Exception as e:
                self._llm_error = e
                raise e
        return self._llm

    def _get_centralized_llm_config(self) -> Dict[str, Any]:
        """Load centralized LLM configuration from config.yaml."""
        try:
            config_path = Path("config/config.yaml")
            if config_path.exists():
                import yaml
                with open(config_path) as f:
                    global_config = yaml.safe_load(f)
                    return global_config.get("llm", {})
        except Exception as e:
            logger.debug(f"Could not load centralized LLM config: {e}")
        return {}
    
    def _create_llm(self):
        """Create LLM from config with centralized defaults and agent-level overrides."""
        # Load centralized defaults
        centralized_config = self._get_centralized_llm_config()
        
        # Agent-level config (can override centralized defaults)
        agent_llm_config = self.config.llm_config
        
        # Merge: centralized defaults first, then agent overrides
        llm_config = {
            "provider": agent_llm_config.get("provider", centralized_config.get("default_provider", "gemini")),
            "model": agent_llm_config.get("model", centralized_config.get("default_model", "gemini-2.5-flash")),
            "temperature": agent_llm_config.get("temperature", centralized_config.get("default_temperature", 0.7)),
            "max_tokens": agent_llm_config.get("max_tokens", centralized_config.get("default_max_tokens", 2000))
        }
        
        provider = llm_config["provider"]

        if provider == "openai":
            if ChatOpenAI is None:
                raise ValueError("langchain-openai package not installed. Install with: pip install langchain-openai")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            return ChatOpenAI(
                model=llm_config["model"],
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"]
            )
        elif provider == "anthropic":
            if ChatAnthropic is None:
                raise ValueError("langchain-anthropic package not installed. Install with: pip install langchain-anthropic")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            return ChatAnthropic(
                model=llm_config["model"],
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"]
            )
        elif provider == "gemini":
            # Explicitly pass API key to avoid Google Cloud SDK auth fallback
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            # Get model from merged config
            model = llm_config["model"]
            
            # Validate against allowed models list from centralized config
            allowed_models = centralized_config.get("allowed_models", [
                "gemini-2.5-flash",
                "gemini-2.5-pro"
            ])
            
            if model not in allowed_models:
                default_model = centralized_config.get("default_model", "gemini-2.5-flash")
                logger.warning(
                    f"Model '{model}' is not in allowed list {allowed_models}. "
                    f"Overriding to default '{default_model}'"
                )
                model = default_model
            
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                google_api_key=api_key
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create prompt template from config."""
        prompts = self.config.prompts
        return ChatPromptTemplate.from_messages([
            ("system", prompts["system"]),
            ("user", prompts["user"])
        ])

    def _create_embedding_model(self):
        """Create local embedding model for semantic search."""
        # Use local sentence-transformers for consistency with SemanticSearchService
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("❌ sentence-transformers not available, falling back to dummy embeddings")
            # Fallback that returns zero vectors
            class DummyEmbeddings:
                def embed_query(self, text: str) -> List[float]:
                    return [0.0] * 384  # all-MiniLM-L6-v2 dimensions

                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    return [[0.0] * 384 for _ in texts]

            return DummyEmbeddings()

        try:
            model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Local embedding model loaded successfully for semantic search")

            # Create a wrapper class to match the expected interface
            class LocalEmbeddings:
                def __init__(self, model):
                    self.model = model

                def embed_query(self, text: str) -> List[float]:
                    """Generate embedding for a single query."""
                    return self.model.encode(text, show_progress_bar=False).tolist()

                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    """Generate embeddings for multiple documents."""
                    embeddings = self.model.encode(texts, show_progress_bar=False)
                    return embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings

            return LocalEmbeddings(model)

        except Exception as e:
            logger.error(f"❌ Failed to load local embedding model: {e}, falling back to dummy embeddings")
            # Fallback that returns zero vectors
            class DummyEmbeddings:
                def embed_query(self, text: str) -> List[float]:
                    return [0.0] * 384  # all-MiniLM-L6-v2 dimensions

                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    return [[0.0] * 384 for _ in texts]

            return DummyEmbeddings()

    def _load_tools(self) -> List[Any]:
        """Load tools from registry."""
        # TODO: Implement tool loading
        return []

    @trace_agent("base_agent")
    @abstractmethod
    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent logic.
        
        This method is automatically traced by Langfuse if configured.
        All subclasses inherit this tracing capability.
        
        Args:
            input_data: Dictionary containing input data for the agent
            
        Returns:
            Dictionary containing agent output
        """
        pass

    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate agent output against config rules."""
        validation = self.config.validation

        # Check required fields
        for field in validation.get("required_fields", []):
            if field not in output or not output[field]:
                return False

        return True

    def semantic_search(
        self,
        query: str,
        chunk_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base for context using semantic similarity.

        Args:
            query: Natural language search query
            chunk_types: Optional filter for specific chunk types
            limit: Maximum number of results to return

        Returns:
            List of relevant knowledge chunks with metadata and relevance scores
        """
        # Use context_id for knowledge base context
        if not self.context_id:
            logger.warning("No context_id set for semantic search - semantic search disabled")
            return []

        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.embed_query(query)

            # Search the knowledge base using hybrid search
            results = search_knowledge_base(
                query_text=query,
                query_embedding=query_embedding,
                context_id=self.context_id,
                chunk_types=chunk_types,
                match_limit=limit
            )

            logger.debug(f"Semantic search for context {self.context_id} returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Return empty results on failure to maintain agent stability
            return []

    def get_validated_context(
        self,
        query: str,
        task_context: str,
        min_chunks: int = 2,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get semantic context with CRAG validation.

        Applies Corrective RAG (CRAG) to ensure retrieved context is relevant
        and helpful for the specified task.

        Args:
            query: Search query for semantic context
            task_context: Description of the task context
                (e.g., "answering questions about document structure")
            min_chunks: Minimum relevant chunks required (default: 2)
            threshold: Relevance score threshold 0.0-1.0 (default: 0.7)

        Returns:
            List of CRAG-validated context chunks

        Raises:
            ValueError: If context_id is not set
        """
        # Validate knowledge base context
        if not self.context_id:
            raise ValueError("context_id must be set for CRAG validation")

        try:
            # Step 1: Perform semantic search to get raw context
            raw_chunks = self.semantic_search(
                query=query,
                limit=min_chunks * 2  # Get more than needed for CRAG to filter
            )

            if not raw_chunks:
                logger.warning(f"No semantic context found for query: '{query}'")
                return []

            # Step 2: Apply CRAG validation (if available)
            crag_validator = self._get_crag_validator()
            if crag_validator is None:
                # CRAG not available, return raw chunks
                logger.debug("CRAG validator not available, returning raw chunks")
                return raw_chunks[:min_chunks]
                
            validation_result = crag_validator.validate_and_correct(
                query=query,
                retrieved_chunks=raw_chunks,
                task_context=task_context,
                context_id=self.context_id,
                min_relevant_chunks=min_chunks,
                relevance_threshold=threshold
            )

            # Log CRAG performance metrics
            stats = validation_result.get('relevance_stats', {})
            corrections = validation_result.get('correction_applied', False)

            logger.info(
                f"CRAG validation for '{task_context}': "
                f"{stats.get('relevant_chunks', 0)}/{stats.get('total_chunks', 0)} relevant "
                f"(avg score: {stats.get('average_score', 0):.2f})"
                f"{' - correction applied' if corrections else ''}"
            )

            # Step 3: Return validated chunks
            return validation_result['chunks']

        except Exception as e:
            logger.error(f"CRAG validation failed for query '{query}': {e}")
            # Graceful degradation: fall back to unvalidated semantic search
            logger.warning("Falling back to unvalidated semantic search")
            return self.semantic_search(query=query, limit=min_chunks)

    def _get_crag_validator(self):
        """
        Lazy-load CRAG validator instance.

        Returns:
            CRAGValidator: Configured CRAG validator instance
        """
        if not hasattr(self, '_crag_validator'):
            try:
                from .crag.validator import CRAGValidator
                # Use the same provider as the agent's LLM, with fallback
                provider = 'gemini'  # Default provider
                if hasattr(self, 'config') and self.config:
                    provider = self.config.llm_config.get('provider', 'gemini')
                self._crag_validator = CRAGValidator(provider=provider)
                logger.debug(f"Initialized CRAG validator with provider: {provider}")
            except Exception as e:
                # Don't raise - CRAG is optional, system can work without it
                logger.debug(f"CRAG validator not available: {e}. Continuing without CRAG validation.")
                return None

        return self._crag_validator

    def validate_against_knowledge_base(
        self,
        generated_content: Any,
        validation_query: str,
        chunk_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate generated content against knowledge base context.

        Args:
            generated_content: Content to validate (text, dict, etc.)
            validation_query: Query to find relevant knowledge base context
            chunk_types: Optional filter for chunk types

        Returns:
            Validation result with issues found and suggestions
        """
        validation_result = {
            'valid': True,
            'issues': [],
            'suggestions': [],
            'context_used': [],
            'confidence': 0.0
        }

        if not self.context_id:
            validation_result['issues'].append("No context_id set for validation")
            validation_result['valid'] = False
            return validation_result

        try:
            # Get relevant context from knowledge base
            context_chunks = self.semantic_search(
                query=validation_query,
                chunk_types=chunk_types,
                limit=3  # Get top 3 most relevant chunks
            )

            if not context_chunks:
                validation_result['issues'].append("No relevant knowledge base context found")
                validation_result['confidence'] = 0.0
                return validation_result

            validation_result['context_used'] = [
                {
                    'chunk_type': chunk['chunk_type'],
                    'title': chunk['chunk_title'],
                    'relevance_score': chunk.get('relevance_score', 0)
                }
                for chunk in context_chunks
            ]

            # Perform content validation
            issues, suggestions = self._validate_content_against_context(
                generated_content, context_chunks
            )

            validation_result['issues'] = issues
            validation_result['suggestions'] = suggestions
            validation_result['valid'] = len(issues) == 0

            # Calculate confidence based on context relevance and issues found
            avg_relevance = sum(chunk.get('relevance_score', 0) for chunk in context_chunks) / len(context_chunks)
            issue_penalty = len(issues) * 0.2  # Each issue reduces confidence by 20%
            validation_result['confidence'] = max(0.0, min(1.0, avg_relevance - issue_penalty))

            logger.info(f"Validation completed: {len(issues)} issues found, confidence {validation_result['confidence']:.2f}")
            return validation_result

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_result['issues'].append(f"Validation error: {str(e)}")
            validation_result['valid'] = False
            return validation_result

    def _validate_content_against_context(
        self,
        content: Any,
        context_chunks: List[Dict[str, Any]]
    ) -> tuple[List[str], List[str]]:
        """
        Validate content against knowledge base context.

        This is a base implementation that can be overridden by specific agents.
        Returns (issues, suggestions) where issues are problems found and
        suggestions are recommendations for improvement.
        """
        issues = []
        suggestions = []

        # Convert content to string for basic text analysis
        if isinstance(content, dict):
            content_text = str(content)
        elif isinstance(content, list):
            content_text = ' '.join(str(item) for item in content)
        else:
            content_text = str(content)

        content_lower = content_text.lower()

        # Basic validation - check for obvious factual contradictions
        # This is a simple implementation; specific agents should override this

        # Aggregate context text for analysis
        context_texts = [chunk.get('chunk_content', '') for chunk in context_chunks]
        combined_context = ' '.join(context_texts).lower()

        # Example validations (these would be more sophisticated in real implementation)
        if 'timeline' in combined_context and 'happened before' in content_lower:
            # Could check for timeline consistency
            suggestions.append("Consider timeline accuracy against knowledge base content")

        if len(context_chunks) == 0:
            issues.append("No relevant knowledge base context available for validation")
        elif len(context_chunks) > 0 and len(content_text.strip()) < 10:
            suggestions.append("Content appears too brief for thorough validation")

        return issues, suggestions

    def set_context(self, context_id: str):
        """
        Set the knowledge base context for semantic search operations.

        Args:
            context_id: Knowledge base context identifier
        """
        self.context_id = context_id
        logger.info(f"Set knowledge base context: {context_id}")

    def check_knowledge_base_availability(self) -> Dict[str, Any]:
        """
        Check if knowledge chunks are available for this context.

        Returns:
            Status information about knowledge base availability
        """
        if not self.context_id:
            return {'available': False, 'error': 'No context_id set'}

        try:
            status = validate_knowledge_chunks_exist(context_id=self.context_id)
            return {
                'available': status.get('exists', False),
                'total_chunks': status.get('total_chunks', 0),
                'chunk_types': status.get('chunk_types', {}),
                'error': status.get('error') if not status.get('exists') else None
            }
        except Exception as e:
            logger.error(f"Failed to check knowledge base availability: {e}")
            return {'available': False, 'error': str(e)}

    def generate_enriched_chunk(self, entity_data, enrichment_result) -> 'OutlineChunk':
        """
        Generate semantic chunk from enrichment results.

        Args:
            entity_data: Original entity data object
            enrichment_result: Results from enrichment analysis

        Returns:
            OutlineChunk object with enriched content
        """
        from ..utils.outline_chunker import OutlineChunk

        # Build enriched content from entity data and enrichment results
        enriched_content = self._build_enriched_content(entity_data, enrichment_result)

        return OutlineChunk(
            chunk_type=f"entity_enriched_{getattr(entity_data, 'type', 'unknown')}",
            title=f"Enriched: {getattr(entity_data, 'name', 'Unknown Entity')}",
            content=enriched_content,
            sequence_order=getattr(entity_data, 'id', 0),
            metadata={
                'context_id': self.context_id,
                'entity_id': getattr(entity_data, 'id', None),
                'entity_name': getattr(entity_data, 'name', 'Unknown'),
                'entity_type': getattr(entity_data, 'type', 'unknown'),
                'enrichment_agent': self.__class__.__name__,
                'enrichment_depth': 'detailed'
            }
        )

    def _store_enriched_chunk(self, chunk: 'OutlineChunk'):
        """
        Store enriched chunk with embedding.

        Args:
            chunk: OutlineChunk to store
        """
        from ..core.search.semantic_search import SemanticSearchService

        # Set context_id in chunk metadata if not already set
        if not chunk.metadata.get('context_id') and self.context_id:
            chunk.metadata['context_id'] = self.context_id

        service = SemanticSearchService()
        service.store_outline_chunks([chunk])

    def _build_enriched_content(self, entity_data, enrichment_result) -> str:
        """
        Build enriched semantic content from entity data and enrichment results.

        Args:
            entity_data: Original entity data
            enrichment_result: Enrichment analysis results

        Returns:
            Rich semantic content string
        """
        context_parts = [f"Enriched Entity: {getattr(entity_data, 'name', 'Unknown')}"]

        # Add original entity information
        if hasattr(entity_data, 'summary') and entity_data.summary:
            context_parts.append(f"Summary: {entity_data.summary}")

        if hasattr(entity_data, 'description') and entity_data.description:
            context_parts.append(f"Description: {entity_data.description}")

        # Add enrichment-specific content based on agent type
        if isinstance(enrichment_result, dict):
            for key, value in enrichment_result.items():
                if value and key not in ['entity_id', 'name', 'type']:  # Skip basic fields
                    context_parts.append(f"{key.replace('_', ' ').title()}: {value}")

        elif enrichment_result:  # If it's a string or other format
            context_parts.append(f"Enrichment Details: {enrichment_result}")

        return "\n\n".join(context_parts)

    def run_with_cross_enhancement(self, entity_data):
        """
        Run agent analysis with access to enriched chunks from other agents.

        Args:
            entity_data: The entity data to analyze

        Returns:
            Enhanced analysis result using cross-agent context
        """
        # Get cross-agent context from other agents' enriched chunks
        cross_context = self._get_cross_agent_context(entity_data)

        # Perform analysis with cross-agent enhancement
        enhanced_result = self._analyze_with_cross_context(entity_data, cross_context)

        # Generate and store enriched chunk
        enriched_chunk = self.generate_enriched_chunk(entity_data, enhanced_result)
        self._store_enriched_chunk(enriched_chunk)

        return enhanced_result

    def _get_cross_agent_context(self, entity_data) -> List[Dict[str, Any]]:
        """
        Query enriched chunks from other agents for cross-enhancement context.

        Args:
            entity_data: Current entity being analyzed

        Returns:
            List of relevant enriched chunks from other agents
        """
        context_queries = self._get_cross_context_queries(entity_data)
        combined_context = []

        for query in context_queries:
            try:
                # Query enriched chunks specifically (entity_enriched_* types)
                context = self.semantic_search(
                    query=query,
                    chunk_types=['entity_enriched_character', 'entity_enriched_setting',
                                'entity_enriched_object', 'entity_enriched_theme',
                                'entity_enriched_force'],
                    limit=2
                )
                combined_context.extend(context)
            except Exception as e:
                logger.warning(f"Failed to get cross-agent context for query '{query}': {e}")

        return combined_context

    def _get_cross_context_queries(self, entity_data) -> List[str]:
        """
        Generate cross-context queries specific to this agent and entity.

        This method should be overridden by each agent to provide relevant queries.

        Args:
            entity_data: Current entity being analyzed

        Returns:
            List of semantic queries for cross-agent enhancement
        """
        # Default implementation - agents should override this
        entity_name = getattr(entity_data, 'name', 'Unknown')
        return [f"enriched information related to {entity_name}"]

    def _analyze_with_cross_context(self, entity_data, cross_context: List[Dict[str, Any]]):
        """
        Perform analysis using cross-agent context.

        This method should be overridden by each agent to use cross-context.

        Args:
            entity_data: Current entity being analyzed
            cross_context: Context from other agents' enriched chunks

        Returns:
            Enhanced analysis result
        """
        # Default implementation - agents should override this
        # For backward compatibility, this calls the original analysis method
        # Agents can override this to use cross_context for better analysis
        return self._analyze_entity(entity_data)

    def _analyze_entity(self, entity_data):
        """
        Default entity analysis method - to be overridden by agents.

        Args:
            entity_data: Entity data to analyze

        Returns:
            Analysis result
        """
        # Default implementation - agents should override this
        raise NotImplementedError("Agents must implement _analyze_entity method")
