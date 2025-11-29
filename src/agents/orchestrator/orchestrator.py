"""
Orchestrator Agent - Conversational Q&A interface for knowledge bases.

Enables users to ask questions about knowledge base content using natural language.
Uses semantic search to find comprehensive knowledge chunks.
"""
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ...core.base_agent import BaseAgent
from ...core.search.semantic_search import search_knowledge_base
from ...agents import get_agent
from .session import SessionHistory
from .agent_calling import call_specialist_agent
from .agent_utils import get_agent_emoji
from .graph.graph import create_agent_graph
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent for knowledge base Q&A.

    Capabilities:
    - Semantic search over comprehensive knowledge chunks
    - Conversation history management (session-only, in-memory)
    - Multi-agent orchestration for deep analysis
    
    Architecture: semantic search with multi-agent orchestration for complex queries.
    """

    def __init__(self, config_path: str = "config/orchestrator.yaml"):
        super().__init__(config_path)
        self.context_id = None
        self.session_id = "default"
        self.conversation_history = None
        self.knowledge_base_context = None
        self.context_cache = {}
        self.last_tool_calls = []
        self.last_agent_calls = []
        self.response_cache = {}
        self.streaming_callback = None
        self.graph = None  # LangGraph instance, created in set_context

    def set_context(self, context_id: str):
        """Set the knowledge base context and initialize conversation history."""
        if self.context_id != context_id:
            self.response_cache.clear()
            self.knowledge_base_context = None
            # Only create new history if context changed
            self.conversation_history = SessionHistory(
                context_id=context_id,
                session_id=self.session_id,
                max_history=10
            )
        elif not self.conversation_history:
            # Create history if it doesn't exist (first time)
            self.conversation_history = SessionHistory(
                context_id=context_id,
                session_id=self.session_id,
                max_history=10
            )

        self.context_id = context_id
        
        # Initialize LangGraph for agent routing
        self._initialize_graph()
    
    def set_streaming_callback(self, callback):
        """Set callback function for streaming events."""
        self.streaming_callback = callback
    
    def _emit_streaming_event(self, event_type: str, message: str, data: Dict[str, Any] = None):
        """Emit a streaming event if callback is set."""
        if self.streaming_callback:
            try:
                self.streaming_callback(event_type, message, data)
            except Exception as e:
                logger.debug(f"Streaming callback error: {e}")

    def _create_chatbot_tools(self) -> List[StructuredTool]:
        """Create comprehensive LangChain tools for chatbot."""
        class SemanticSearchInput(BaseModel):
            query: str = Field(description="Natural language search query about knowledge base content")
            chunk_types: Optional[List[str]] = Field(default=None, description="Optional: Filter by chunk types. Available types: 'section' (markdown sections) or 'document' (full documents). Leave empty for general search.")
            limit: int = Field(default=5, description="Maximum number of results (default: 5)")

        tools = [
            StructuredTool.from_function(
                func=self._semantic_search_tool,
                name="semantic_search",
                description="""Search knowledge base content semantically using meaning and context.
                This is your PRIMARY tool for answering questions. Knowledge chunks contain comprehensive content.
                Use this for ANY question about knowledge base content.
                
                IMPORTANT:
                - Do NOT filter by chunk_types unless you specifically need 'section' or 'document' types
                - If search returns no results, the system will automatically retry without filters
                - Never invent file paths or references - only use information from search results
                - If no results found, say "No relevant content found" rather than making up references""",
                args_schema=SemanticSearchInput
            ),
        ]
        return tools
    
    def _initialize_graph(self):
        """Initialize LangGraph for agent routing."""
        try:
            # Load supervisor prompt
            supervisor_prompt_path = Path("prompts/orchestrator/supervisor.txt")
            if supervisor_prompt_path.exists():
                supervisor_prompt = supervisor_prompt_path.read_text()
            else:
                # Fallback prompt
                supervisor_prompt = """You are the Orchestrator Agent, responsible for routing queries to specialist agents.
                
AVAILABLE AGENTS:
- guardian: Portfolio oversight, monitoring, anomaly detection
- specialist: Technical troubleshooting, detailed analysis
- optimizer: Performance optimization, recommendations
- pathfinder: Forecasting, planning, strategy

Route to appropriate agent or use FINISH if no agents needed."""
            
            # Get orchestrator system prompt for FINISH responses
            orchestrator_prompt = self._build_system_prompt_with_context()
            
            # Create graph
            self.graph = create_agent_graph(
                llm=self.llm,
                supervisor_prompt=supervisor_prompt,
                call_specialist_agent_func=call_specialist_agent,
                semantic_search_func=self._semantic_search_tool,
                embedding_model=self.embedding_model,
                get_agent_func=get_agent,
                orchestrator_prompt=orchestrator_prompt,
                streaming_callback=self._emit_streaming_event if self.streaming_callback else None
            )
        except Exception as e:
            logger.error(f"Failed to initialize graph: {e}", exc_info=True)
            self.graph = None

    def _load_knowledge_base_context(self, context_id: str) -> str:
        """Load knowledge base summary for context injection with caching."""
        if context_id in self.context_cache:
            return self.context_cache[context_id]

        try:
            kb_base_path = "./knowledge-base"
            try:
                import yaml
                config_path = Path("config/config.yaml")
                if config_path.exists():
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                        kb_base_path = config.get('knowledge_base', {}).get('base_path', './knowledge-base')
            except Exception:
                pass
            
            kb_dir = kb_base_path
            if os.path.exists(kb_dir):
                md_files = []
                for root, dirs, files in os.walk(kb_dir):
                    for file in files:
                        if file.endswith('.md'):
                            md_files.append(os.path.join(root, file))
                
                if md_files:
                    kb_path = md_files[0]
                    with open(kb_path, 'r', encoding='utf-8') as f:
                        kb_content = f.read()[:4000]

                    context = f"""
## Knowledge Base Context: {context_id}

{kb_content}

---
*This knowledge base context is provided for reference. Use tools for specific detailed queries.*
"""
                    self.context_cache[context_id] = context
                    return context
            return ""
        except Exception as e:
            logger.warning(f"Failed to load knowledge base context for {context_id}: {e}")
            return ""

    def _semantic_search_tool(self, query: str, chunk_types: Optional[List[str]] = None, limit: int = 5, **kwargs) -> str:
        """Tool wrapper for semantic search with CRAG validation."""
        if not self.context_id:
            return json.dumps({"error": "No knowledge base context set"})

        try:
            limit = int(limit) if limit is not None else 10
            limit = max(1, min(limit, 20))

            crag_applied = False
            crag_stats = None
            results = []
            used_fallback = False
            
            try:
                query_embedding = self.embedding_model.embed_query(query)
                
                # First attempt: search with chunk_types filter if provided
                raw_chunks = search_knowledge_base(
                    context_id=self.context_id,
                    query_text=query,
                    query_embedding=query_embedding,
                    chunk_types=chunk_types,
                    match_limit=limit * 2
                )
                
                # If filtered search returned no results, retry without filter
                if not raw_chunks and chunk_types:
                    logger.info(f"Filtered search with chunk_types={chunk_types} returned no results, retrying without filter")
                    used_fallback = True
                    raw_chunks = search_knowledge_base(
                        context_id=self.context_id,
                        query_text=query,
                        query_embedding=query_embedding,
                        chunk_types=None,  # Remove filter
                        match_limit=limit * 2
                    )
                
                if raw_chunks:
                    crag_validator = self._get_crag_validator()
                    if crag_validator is not None:
                        validation_result = crag_validator.validate_and_correct(
                            query=query,
                            retrieved_chunks=raw_chunks,
                            task_context="answering knowledge base questions conversationally",
                            context_id=self.context_id,
                            min_relevant_chunks=0,  # Allow partial results
                            relevance_threshold=0.5  # Lower threshold for general queries
                        )
                    else:
                        validation_result = {
                            'chunks': raw_chunks[:limit],
                            'relevance_stats': {
                                'relevant_chunks': len(raw_chunks),
                                'total_chunks': len(raw_chunks),
                                'average_score': 0.8
                            },
                            'correction_applied': False
                        }
                    
                    crag_stats = validation_result.get('relevance_stats', {})
                    crag_stats['correction_applied'] = validation_result.get('correction_applied', False)
                    crag_stats['correction_info'] = validation_result.get('correction_info')
                    self._last_crag_result = validation_result
                    results = validation_result['chunks'][:limit]
                    
                    # If CRAG filtered everything out, use raw results
                    if not results and raw_chunks:
                        logger.warning("CRAG validation filtered out all results, using raw results")
                        results = raw_chunks[:limit]
                    
                    crag_applied = True
                    
            except Exception as crag_error:
                logger.warning(f"CRAG validation failed: {crag_error}, falling back to regular search")
                query_embedding = self.embedding_model.embed_query(query)
                results = search_knowledge_base(
                    context_id=self.context_id,
                    query_text=query,
                    query_embedding=query_embedding,
                    chunk_types=None,  # Don't use filter on fallback
                    match_limit=limit
                )

            if not results:
                fallback_msg = " (searched without chunk_type filters)" if used_fallback else ""
                return json.dumps({
                    "results": [],
                    "message": f"No relevant knowledge base content found for this query{fallback_msg}.",
                    "crag_applied": crag_applied,
                    "fallback_used": used_fallback
                })

            formatted_results = []
            for result in results:
                formatted_results.append({
                    "chunk_type": result.get('chunk_type', 'unknown'),
                    "chunk_title": result.get('chunk_title', 'Untitled'),
                    "relevance_score": round(result.get('relevance_score', 0.0), 3),
                    "content": result.get('chunk_content', ''),
                    "metadata": result.get('chunk_metadata', {}),
                    "crag_validated": crag_applied
                })

            response_data = {
                "results": formatted_results,
                "count": len(formatted_results),
                "query": query,
                "crag_applied": crag_applied
            }
            
            if crag_stats:
                response_data["crag_stats"] = crag_stats
            
            if used_fallback:
                response_data["fallback_used"] = True
                response_data["fallback_reason"] = f"Initial search with chunk_types={chunk_types} returned no results"
            
            return json.dumps(response_data, indent=2)

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return json.dumps({"error": str(e)})

    def _execute_graph(self, question: str) -> str:
        """Execute LangGraph for agent routing."""
        if not self.graph:
            return "Error: Graph not initialized. Please set context first."
        
        try:
            # Initialize graph state
            initial_state = {
                "messages": [HumanMessage(content=question)],
                "next": "",
                "current_task_instruction": "",
                "context_id": self.context_id,
                "agent_responses": [],
                "user_question": question
            }
            
            # Execute graph
            final_state = self.graph.invoke(initial_state)
            
            # Extract response from state
            agent_responses = final_state.get("agent_responses", [])
            messages = final_state.get("messages", [])
            
            if agent_responses:
                # Check if we have supervisor response (direct answer)
                if len(agent_responses) == 1 and agent_responses[0].get("agent") == "supervisor":
                    return agent_responses[0].get("response", "No response from supervisor.")
                
                # Check if we have semantic_search response only (semantic_search is a service, not an agent)
                if len(agent_responses) == 1 and (agent_responses[0].get("agent") == "semantic_search" or agent_responses[0].get("service") == "semantic_search"):
                    # For semantic_search, return the response directly (it's already formatted)
                    return agent_responses[0].get("response", "No response from semantic search.")
                
                # Synthesize agent responses for multiple agents
                synthesized = self._synthesize_agent_responses(agent_responses, question)
                return synthesized
            elif messages:
                # Extract from messages if no agent_responses
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    return last_message.content
                return str(last_message)
            else:
                return "No response received."
                
        except Exception as e:
            logger.error(f"Graph execution failed: {e}", exc_info=True)
            return f"Error executing graph: {str(e)}"
    
    def _synthesize_agent_responses(self, agent_responses: List[Dict[str, Any]], question: str) -> str:
        """Synthesize multiple agent responses into a coherent answer."""
        if not agent_responses:
            return "No agent responses to synthesize."
        
        # Build synthesis prompt
        responses_text = "\n\n".join([
            f"**{resp.get('agent', 'Unknown')} Agent**:\n{resp.get('response', 'No response')}"
            for resp in agent_responses
        ])
        
        synthesis_prompt = f"""The user asked: {question}

The following specialist agents have provided their responses:

{responses_text}

Please synthesize these responses into a clear, coherent answer that directly addresses the user's question. 
Combine insights from all agents where relevant, and present the information in a natural, conversational way."""
        
        try:
            messages = [
                SystemMessage(content="You are synthesizing responses from multiple specialist agents into a coherent answer."),
                HumanMessage(content=synthesis_prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fallback: just concatenate responses
            return "\n\n".join([f"**{resp.get('agent')}**: {resp.get('response')}" for resp in agent_responses])

    def chat(self, question: str, context_id: Optional[str] = None) -> str:
        """Process a user question and return an answer using multi-agent discussion or tools."""
        # Only set context if it's different or not set
        if context_id and context_id != self.context_id:
            self.set_context(context_id)
        elif not self.context_id and context_id:
            self.set_context(context_id)
        elif not self.conversation_history and self.context_id:
            # Ensure history exists if context was set but history wasn't initialized
            self.conversation_history = SessionHistory(
                context_id=self.context_id,
                session_id=self.session_id,
                max_history=10
            )

        if self.context_id and not self.knowledge_base_context:
            self.knowledge_base_context = self._load_knowledge_base_context(self.context_id)

        if not self.context_id:
            return "Error: No knowledge base context. Please specify context_id."

        cache_key = f"{self.context_id}:{question.strip().lower()}"
        if cache_key in self.response_cache:
            cached_response = self.response_cache[cache_key]
            self.conversation_history.add_exchange(question, cached_response)
            return cached_response

        # ALWAYS invoke the graph - the supervisor node uses structured output to route
        # No hardcoded detection - the LLM in the supervisor node makes all routing decisions
        if not self.graph:
            return "Error: Graph not initialized. Please set context first."
        
        response = self._execute_graph(question)
        
        # Graph handles all routing internally - no tool calls to track
        self.conversation_history.add_exchange(question, response, [])
        self.response_cache[cache_key] = response
        return response

    def _build_conversation_messages(self, current_question: str) -> List:
        """Build conversation messages with history and context."""
        messages = []
        system_prompt = self._build_system_prompt_with_context()
        messages.append(SystemMessage(content=system_prompt))

        recent_history = self.conversation_history.get_recent_history(num_exchanges=5)
        for entry in recent_history:
            if entry['role'] == 'user':
                messages.append(HumanMessage(content=entry['content']))
            elif entry['role'] == 'assistant':
                # Include tool calls in assistant messages to help LLM understand what data was retrieved
                content = entry['content']
                tool_calls = entry.get('tool_calls', [])
                # Tool calls are now handled by graph pattern
                # No need to add tool info for legacy call_specialist_agents
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=current_question))
        return messages

    def _build_system_prompt_with_context(self) -> str:
        """Build system prompt with knowledge base and conversation context."""
        base_prompt = self.config.prompts['system']

        if self.knowledge_base_context:
            base_prompt += self.knowledge_base_context

        tool_guidance = f"""

## Tool Usage - INTELLIGENT DECISION MAKING

You are the intelligent Orchestrator - the coordination layer that makes smart decisions about how to answer questions.

AVAILABLE TOOLS:
1. **semantic_search** - Search knowledge base content for general questions, definitions, explanations

**Note**: Agent routing is handled automatically via LangGraph supervisor pattern. Questions requiring specialist agents will be routed appropriately.

AVAILABLE SPECIALIST AGENTS:
- **guardian** (🛡️): Portfolio oversight, monitoring, anomaly detection, health assessment, portfolio pacing analysis with daily trend data
  - **Has portfolio pacing tool** that provides daily spend trends - use Guardian for ANY questions about portfolio data, pacing, trends, or calculations on portfolio data
  - **If Guardian was just called**, it already has the portfolio data - use Guardian again for follow-up questions about that data
- **specialist** (🔧): Technical troubleshooting, detailed analysis, issue investigation
- **optimizer** (🎯): Performance optimization, recommendations, efficiency improvements
- **pathfinder** (🧭): Forecasting, planning, strategy, navigation

## DECISION FRAMEWORK

You can answer questions in three ways:

1. **Answer directly** (no tools needed):
   - Questions you can answer from your own knowledge (e.g., "how many agents do you have", "what is your role", "what agents are available")
   - Simple factual questions about the system itself that are already in your system prompt
   - Questions where you already have the information without needing to search
   - **Example**: "How many agents do you have at your disposal?" → Answer directly without calling tools

2. **Use semantic_search for:**
   - General questions about platform features, concepts, definitions
   - Documentation and specification queries
   - Procedural or operational questions
   - Questions requiring knowledge base content

3. **Agent Routing (Automatic via LangGraph):**
   - Complex questions requiring specialized expertise are automatically routed via LangGraph supervisor pattern
   - Portfolio monitoring and health assessment → Guardian agent
   - Performance optimization → Optimizer agent
   - Technical troubleshooting → Specialist agent
   - Strategic planning and forecasting → Pathfinder agent
   - Agent introductions or multi-agent requests → All relevant agents

**Decision Process:**
   - **FIRST**: Check if you can answer directly from your own knowledge (system prompt, conversation history)
   - **SECOND**: If knowledge base content is needed, use semantic_search
   - **THIRD**: If specialized agent expertise is required, the LangGraph supervisor will route automatically
   - **IMPORTANT: Check conversation history** - If Guardian agent was just called and has portfolio/pacing data, follow-up questions about that same data should go to Guardian
   - **For portfolio/pacing questions**: Guardian agent has access to portfolio pacing tool with daily trend data - use Guardian for follow-up questions about the same portfolio data
   - Select appropriate agents based on question content AND conversation context
   - Explain your reasoning transparently

## RESPONSE GUIDELINES

- **Answer directly when you know the answer** - don't use tools unnecessarily for questions you can answer from your own knowledge
- **Show your reasoning** when calling tools or agents: "This requires portfolio analysis, so I'll call the Guardian agent..."
- **Be transparent** about your decision process (direct answer, semantic search, or agent routing)
- **Stream responses** from both orchestrator reasoning and agent responses
- **When agent responses are returned**, synthesize them into a clear, conversational answer that directly addresses the user's question
- **Agent responses are displayed separately** in colored boxes - your job is to provide a synthesized summary that answers the question
- **Synthesize multiple agent responses** when multiple agents are called
- **NEVER invent file paths or references** - only use information from actual search results
- **If search returns no results**, say "No relevant content found" - do not make up file names or paths
- **Do NOT filter by chunk_types** unless absolutely necessary - leave it empty for general searches

## Current Conversation Context

You are in an ongoing conversation. The user may:
- Ask follow-up questions referring to previous answers
- Use pronouns or references (e.g., "tell me more about him", "what about that place")
- Request clarification or deeper analysis
- Change topics entirely

Use conversation history to understand context and references.
"""
        base_prompt += tool_guidance
        return base_prompt

    def _get_llm_response_with_tools(self, messages: List) -> str:
        """Get LLM response with tool calling capability."""
        try:
            llm_with_tools = self.llm.bind_tools(self.tools)
            from ...utils.agent_loop import execute_agent_loop
            
            result = execute_agent_loop(
                llm_with_tools=llm_with_tools,
                messages=messages,
                tools=self.tools,
                job_name=self.context_id or "unknown",
                max_iterations=5,
                streaming_callback=self._emit_streaming_event if self.streaming_callback else None,
                stream_response=True
            )

            self.last_tool_calls = result.get("tool_calls", [])

            # Check if the response contains agent calling results
            # Priority: Use formatted agent responses if available, otherwise use LLM response
            response_text = result.get("response", "")
            formatted_agent_response = None
            
            # Tool calls are now handled by graph pattern
            # Only semantic_search tool calls are processed here
            
            # Always use LLM's synthesized response
            # Agent responses were already displayed via streaming callback
            # The LLM should have seen the agent responses in tool results and synthesized them
            return response_text

        except Exception as e:
            error_msg = str(e)
            if "API_KEY" in error_msg or "API Key" in error_msg:
                return "🧠 I'm sorry, but I need a valid API key to access the AI services. Please configure your Gemini API key to use the chatbot features. You can still use the semantic search tools directly with the `semantic-search` command."
            else:
                return f"Error in LLM processing: {error_msg}"

    def __call__(self, state: Any) -> Dict[str, Any]:
        """Execute the agent logic (required by BaseAgent interface)."""
        return {
            'status': 'Orchestrator Agent is ready for conversation',
            'message': 'Use chat() method for conversational Q&A about knowledge bases',
            'capabilities': ['semantic_search', 'conversation_history']
        }

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()

    def get_conversation_summary(self) -> str:
        """Get summary of conversation so far."""
        if not self.conversation_history.messages:
            return "No conversation history."

        exchanges = len(self.conversation_history.messages) // 2
        return f"Conversation has {exchanges} exchanges."

