"""
Corrective RAG (CRAG) Validator for Agentic CRAG Launchpad

Implements relevance grading and correction for retrieved semantic context.
Ensures retrieved chunks are actually helpful for the specified task.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from ..search.semantic_search import search_knowledge_base

logger = logging.getLogger(__name__)


class CRAGValidator:
    """
    Corrective RAG Validator for Agentic CRAG Launchpad.

    Grades retrieved semantic chunks for relevance to specified tasks.
    Applies corrections (query rewriting) when relevance is insufficient.
    """

    def __init__(self, provider: str = "gemini"):
        """
        Initialize CRAG Validator.

        Args:
            provider: LLM provider to use ('openai', 'anthropic', or 'gemini')
        """
        self.provider = provider
        self.grader_llm = self._create_llm()

    def _create_llm(self):
        """Create LLM instance for grading."""
        import os
        
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            ChatOpenAI = None
            
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            ChatAnthropic = None
            
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_google_genai import HarmCategory, HarmBlockThreshold

        if self.provider == "openai":
            if ChatOpenAI is None:
                raise ValueError("langchain-openai package not installed. Install with: pip install langchain-openai")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            return ChatOpenAI(
                model="gpt-4",
                temperature=0.1,
                max_tokens=500
            )
        elif self.provider == "anthropic":
            if ChatAnthropic is None:
                raise ValueError("langchain-anthropic package not installed. Install with: pip install langchain-anthropic")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            return ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=0.1,
                max_tokens=500
            )
        elif self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            # Load centralized model config (CRAG validator uses faster model for grading)
            try:
                import yaml
                from pathlib import Path
                config_path = Path("config/config.yaml")
                if config_path.exists():
                    with open(config_path) as f:
                        global_config = yaml.safe_load(f)
                        centralized_llm = global_config.get("llm", {})
                        # Use default model from centralized config
                        model = centralized_llm.get("default_model", "gemini-2.5-flash")
                else:
                    model = "gemini-2.5-flash"
            except Exception:
                model = "gemini-2.5-flash"
            
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=0.1,
                max_tokens=500,
                google_api_key=api_key,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _ensure_config_exists(self, config_path: str):
        """Create default CRAG validator config if it doesn't exist."""
        import yaml

        config_dir = Path(config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)

        if not Path(config_path).exists():
            default_config = {
                "agent_id": "crag_validator",
                "agent_name": "CRAG Validator",
                "agent_type": "validator",
                "version": "1.0",
                "llm": {
                    "provider": "gemini",
                    "model": "gemini-1.5-flash-002",  # Use centralized default model for grading
                    "temperature": 0.1,  # Low temperature for consistent grading
                    "max_tokens": 500
                },
                "prompts": {
                    "system": "crag_grader_system.txt",
                    "user": "crag_grader_user.txt"
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)

            logger.info(f"Created default CRAG validator config: {config_path}")

    def validate_and_correct(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        task_context: str,
        context_id: str,
        min_relevant_chunks: int = 2,
        relevance_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Main CRAG validation and correction method.

        Args:
            query: Original user query
            retrieved_chunks: Chunks from semantic search
            task_context: Description of the task context
            context_id: Knowledge base context identifier
            min_relevant_chunks: Minimum relevant chunks needed
            relevance_threshold: Minimum relevance score (0.0-1.0)

        Returns:
            Dict with validated chunks and correction info
        """
        logger.info(f"CRAG validation for query: '{query[:50]}...'")

        # Grade each chunk for relevance
        graded_chunks = []
        for i, chunk in enumerate(retrieved_chunks):
            logger.debug(f"Grading chunk {i+1}/{len(retrieved_chunks)}")
            grade = self._grade_chunk_relevance(
                query=query,
                chunk=chunk,
                task_context=task_context
            )
            graded_chunk = {
                **chunk,
                'relevance_score': grade['score'],
                'relevance_reasoning': grade['reasoning'],
                'is_relevant': grade['score'] >= relevance_threshold
            }
            graded_chunks.append(graded_chunk)

        # Count relevant chunks
        relevant_chunks = [c for c in graded_chunks if c['is_relevant']]
        total_relevant = len(relevant_chunks)

        logger.info(f"CRAG results: {total_relevant}/{len(graded_chunks)} chunks relevant")

        # Check if we need correction
        correction_applied = False
        correction_result = None

        if total_relevant < min_relevant_chunks:
            logger.info(f"Insufficient relevant chunks ({total_relevant} < {min_relevant_chunks}), applying correction")
            correction_result = self._apply_correction(
                query=query,
                task_context=task_context,
                context_id=context_id,
                original_chunks=graded_chunks
            )
            correction_applied = True

        return {
            'chunks': relevant_chunks if not correction_applied else relevant_chunks + correction_result.get('additional_chunks', []),
            'all_graded_chunks': graded_chunks,  # Include all for analysis
            'correction_applied': correction_applied,
            'correction_info': correction_result,
            'relevance_stats': {
                'total_chunks': len(graded_chunks),
                'relevant_chunks': total_relevant,
                'average_score': sum(c['relevance_score'] for c in graded_chunks) / len(graded_chunks) if graded_chunks else 0,
                'min_relevant_needed': min_relevant_chunks,
                'threshold_used': relevance_threshold
            }
        }

    def _grade_chunk_relevance(
        self,
        query: str,
        chunk: Dict[str, Any],
        task_context: str
    ) -> Dict[str, Any]:
        """
        Grade a single chunk for relevance to the task.

        Uses LLM to evaluate how helpful the chunk content is for the specified task.
        """
        # Create grading prompt
        system_prompt = """You are a CRAG (Corrective RAG) Grader evaluating the relevance of retrieved knowledge base context for a specific task.

Your job is to determine if this context chunk will actually help with the task. Be strict but fair.

Rate relevance on a 0.0-1.0 scale:
- 1.0: Essential context that directly helps with this specific task
- 0.8-0.9: Very helpful context related to the task
- 0.6-0.7: Somewhat helpful but not directly relevant
- 0.3-0.5: Marginally related, might be useful
- 0.0-0.2: Not relevant or potentially misleading for this task

Focus on: Does this context help answer the question or complete the task effectively?"""

        user_prompt = f"""
TASK CONTEXT: {task_context}

USER QUERY: {query}

CONTEXT CHUNK TITLE: {chunk.get('chunk_title', 'Unknown')}
CONTEXT CHUNK TYPE: {chunk.get('chunk_type', 'Unknown')}
CONTEXT CHUNK CONTENT:
{chunk.get('chunk_content', '')}

Evaluate if this context chunk is relevant and helpful for the task.

SCORE: [0.0-1.0]
REASONING: [2-3 sentences explaining the score]"""

        try:
            # Use LLM to grade (use invoke, not stream, to avoid streaming issues)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Ensure we're using invoke (not stream) to avoid "No generations found in stream" errors
            response = self.grader_llm.invoke(messages)
            
            # Handle different response types
            if hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                # Try to extract content from response object
                response_text = str(response)
                if hasattr(response, 'text'):
                    response_text = response.text
                elif hasattr(response, 'message'):
                    if hasattr(response.message, 'content'):
                        response_text = response.message.content
                    else:
                        response_text = str(response.message)

            # Parse the response
            return self._parse_grade_response(response_text)

        except Exception as e:
            logger.error(f"Error grading chunk relevance: {e}", exc_info=True)
            # Return neutral score on error
            return {
                'score': 0.5,
                'reasoning': f'Grading failed due to error: {e}'
            }

    def _parse_grade_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM grading response into structured format.

        Expected format:
        SCORE: 0.8
        REASONING: This context is very helpful because...
        """
        lines = response_text.strip().split('\n')
        score = 0.5  # Default neutral score
        reasoning = "Could not parse grading response"

        for line in lines:
            line = line.strip()
            if line.upper().startswith('SCORE:'):
                try:
                    score_text = line.split(':', 1)[1].strip()
                    score = float(score_text)
                    score = max(0.0, min(1.0, score))  # Clamp to 0.0-1.0
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse score from: {line}")
            elif line.upper().startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()

        return {
            'score': score,
            'reasoning': reasoning
        }

    def _apply_correction(
        self,
        query: str,
        task_context: str,
        context_id: str,
        original_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply correction when insufficient relevant chunks found.

        Currently implements query rewriting. Could be extended to web search.
        """
        logger.info("Applying CRAG correction via query rewriting")

        # Rewrite the query to be more specific
        rewritten_query = self._rewrite_query(query, task_context, original_chunks)

        # Search again with rewritten query
        # Generate embedding for rewritten query (simplified - in production would use embedding model)
        # For now, we'll need to pass query_embedding - this is a limitation we'll address
        # For correction, we can use the original query embedding as approximation
        additional_chunks = search_knowledge_base(
            query_text=rewritten_query,
            query_embedding=None,  # Will need to generate embedding - simplified for now
            context_id=context_id,
            match_limit=5  # Get more results with rewritten query
        )

        # Grade the additional chunks too
        graded_additional = []
        for chunk in additional_chunks:
            grade = self._grade_chunk_relevance(
                query=query,  # Use original query for grading
                chunk=chunk,
                task_context=task_context
            )
            graded_chunk = {
                **chunk,
                'relevance_score': grade['score'],
                'relevance_reasoning': grade['reasoning'],
                'is_relevant': grade['score'] >= 0.7,
                'from_correction': True
            }
            graded_additional.append(graded_chunk)

        # Return only the relevant additional chunks
        relevant_additional = [c for c in graded_additional if c['is_relevant']]

        return {
            'type': 'query_rewrite',
            'original_query': query,
            'rewritten_query': rewritten_query,
            'additional_chunks': relevant_additional,
            'correction_stats': {
                'additional_chunks_found': len(additional_chunks),
                'additional_chunks_relevant': len(relevant_additional)
            }
        }

    def _rewrite_query(self, original_query: str, task_context: str, original_chunks: List[Dict[str, Any]]) -> str:
        """
        Rewrite the query to find better context based on what was missing.
        """
        # Analyze what types of chunks we got and what we might be missing
        chunk_types = [c.get('chunk_type', 'unknown') for c in original_chunks]
        avg_score = sum(c.get('relevance_score', 0) for c in original_chunks) / len(original_chunks) if original_chunks else 0

        system_prompt = """You are a query rewriter for a knowledge base assistant. Your task is to rewrite user queries to find better knowledge base context when the initial search didn't provide sufficiently relevant results."""

        user_prompt = f"""
ORIGINAL QUERY: "{original_query}"
TASK CONTEXT: "{task_context}"

INITIAL SEARCH RESULTS:
- Found {len(original_chunks)} chunks
- Chunk types: {', '.join(set(chunk_types))}
- Average relevance score: {avg_score:.2f}

The initial search didn't find enough relevant context. Rewrite the query to be more specific and focused on finding knowledge base content that would actually help with this task.

Focus on:
- Specific information needed for the task
- Concrete details rather than general concepts
- Relevant topics, categories, or document sections

REWRITTEN QUERY:"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = self.grader_llm.invoke(messages)
            rewritten = response.content if hasattr(response, 'content') else str(response)
            rewritten = rewritten.strip().strip('"')

            logger.info(f"Query rewritten: '{original_query}' -> '{rewritten}'")
            return rewritten

        except Exception as e:
            logger.error(f"Error rewriting query: {e}")
            # Return original query on error
            return original_query

    def get_relevance_report(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable report of CRAG validation results.
        """
        stats = validation_result.get('relevance_stats', {})
        correction = validation_result.get('correction_info', {})

        report = ".1f"".1f"f"""
CRAG Validation Report:
- Total chunks evaluated: {stats.get('total_chunks', 0)}
- Relevant chunks found: {stats.get('relevant_chunks', 0)}
- Average relevance score: {stats.get('average_score', 0):.2f}
- Minimum relevant needed: {stats.get('min_relevant_needed', 2)}
- Relevance threshold: {stats.get('threshold_used', 0.7)}
"""

        if validation_result.get('correction_applied'):
            report += f"""
Correction Applied: {correction.get('type', 'unknown')}
- Original query: "{correction.get('original_query', '')}"
- Rewritten query: "{correction.get('rewritten_query', '')}"
- Additional relevant chunks: {correction.get('correction_stats', {}).get('additional_chunks_relevant', 0)}
"""

        return report
