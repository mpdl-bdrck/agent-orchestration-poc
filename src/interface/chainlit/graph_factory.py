"""
Graph factory for Chainlit UI.

Creates and initializes LangGraph workflow with all dependencies.
"""
import logging
from pathlib import Path
from typing import Callable, Optional

from src.agents.orchestrator import OrchestratorAgent
from src.agents.orchestrator.graph.graph import create_agent_graph
from src.agents.orchestrator.agent_calling import call_specialist_agent
from src.agents import get_agent

logger = logging.getLogger(__name__)


def create_chainlit_graph(
    context_id: str = "bedrock_kb",
    config_path: Optional[str] = None,
    streaming_callback: Optional[Callable] = None
):
    """
    Create and initialize LangGraph workflow for Chainlit.
    
    This function extracts all dependencies needed for graph creation
    by initializing an OrchestratorAgent instance, then uses those
    dependencies to create the graph.
    
    Args:
        context_id: Knowledge base context identifier
        config_path: Path to orchestrator config file (default: config/orchestrator.yaml)
        streaming_callback: Optional callback (None for Chainlit - events handle display)
    
    Returns:
        Compiled LangGraph workflow ready for astream_events()
    
    Raises:
        Exception: If graph initialization fails
    """
    try:
        # 1. Initialize OrchestratorAgent to get dependencies
        if config_path is None:
            config_path = str(Path("config/orchestrator.yaml"))
        
        orchestrator = OrchestratorAgent(config_path=config_path)
        
        # 2. Set context to load knowledge base
        orchestrator.set_context(context_id)
        
        # 3. Load supervisor prompt
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
            logger.warning(f"Supervisor prompt not found at {supervisor_prompt_path}, using fallback")
        
        # 4. Build orchestrator prompt with context
        orchestrator_prompt = orchestrator._build_system_prompt_with_context()
        
        # 5. Extract dependencies
        llm = orchestrator.llm
        embedding_model = orchestrator.embedding_model
        semantic_search_func = orchestrator._semantic_search_tool
        
        # 6. Create graph using existing function
        # Pass streaming_callback=None for Chainlit (events handle display)
        graph = create_agent_graph(
            llm=llm,
            supervisor_prompt=supervisor_prompt,
            call_specialist_agent_func=call_specialist_agent,
            semantic_search_func=semantic_search_func,
            embedding_model=embedding_model,
            get_agent_func=get_agent,
            orchestrator_prompt=orchestrator_prompt,
            streaming_callback=streaming_callback  # None for Chainlit - events handle display
        )
        
        logger.info(f"✅ Graph factory: Created graph for context_id={context_id}")
        return graph
        
    except Exception as e:
        logger.error(f"❌ Graph factory: Failed to create graph: {e}", exc_info=True)
        raise

