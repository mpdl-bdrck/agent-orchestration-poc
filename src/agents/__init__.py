"""Agent registry for Agentic CRAG Launchpad."""

from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Agent registry - stores agent classes
_agent_registry = {}
# Agent instances cache
_agent_instances = {}


def register_agent(name: str, agent_class, config_path: str = None):
    """Register an agent class with optional config path."""
    _agent_registry[name] = {
        'class': agent_class,
        'config_path': config_path
    }


def get_agent(agent_name: str):
    """
    Get an agent instance by name.
    
    Args:
        agent_name: Name of the agent (e.g., 'content_analyzer')
        
    Returns:
        Agent instance
        
    Raises:
        ValueError: If agent not found
    """
    if agent_name not in _agent_registry:
        raise ValueError(f"Agent '{agent_name}' not found. Available agents: {list(_agent_registry.keys())}")
    
    # Return cached instance if available
    if agent_name in _agent_instances:
        return _agent_instances[agent_name]
    
    # Create new instance
    agent_info = _agent_registry[agent_name]
    agent_class = agent_info['class']
    config_path = agent_info['config_path']
    
    if config_path:
        agent = agent_class(config_path=config_path)
    else:
        agent = agent_class()
    
    # Cache the instance
    _agent_instances[agent_name] = agent
    
    return agent


# Auto-register Bedrock platform specialist agents with config paths
from .specialists.guardian_agent import GuardianAgent
from .specialists.specialist_agent import SpecialistAgent
from .specialists.optimizer_agent import OptimizerAgent
from .specialists.pathfinder_agent import PathfinderAgent

# Get config directory path
_config_dir = Path(__file__).parent.parent.parent / "config"

register_agent('guardian', GuardianAgent, str(_config_dir / "guardian_agent.yaml"))
register_agent('specialist', SpecialistAgent, str(_config_dir / "specialist_agent.yaml"))
register_agent('optimizer', OptimizerAgent, str(_config_dir / "optimizer_agent.yaml"))
register_agent('pathfinder', PathfinderAgent, str(_config_dir / "pathfinder_agent.yaml"))

