"""Observability and tracing configuration for StoryWritersRoom.

This module provides Langfuse tracing integration for agent workflows,
enabling comprehensive observability of LLM calls, agent execution, and costs.

See: reference/tactical_plans/story_writers_room/in_progress/postgresql_tools/tickets/PGT-010.md
"""

import os
import functools
import warnings
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    Langfuse = None
    LANGFUSE_AVAILABLE = False

# Note: langfuse.decorators may not be available in all versions
# We'll use manual tracing with context managers instead
observe = None
langfuse_context = None

try:
    from langfuse.callback import CallbackHandler
    CALLBACK_HANDLER_AVAILABLE = True
except ImportError:
    CallbackHandler = None
    CALLBACK_HANDLER_AVAILABLE = False

from .langfuse_config import get_langfuse_client, create_langfuse_client


# Global Langfuse client instance
_langfuse_client: Optional[Langfuse] = None


def init_langfuse(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: Optional[str] = None
) -> Optional[Langfuse]:
    """Initialize global Langfuse client for tracing.
    
    Args:
        public_key: Langfuse public key (defaults to LANGFUSE_PUBLIC_KEY)
        secret_key: Langfuse secret key (defaults to LANGFUSE_SECRET_KEY)
        host: Langfuse host URL (defaults to LANGFUSE_HOST)
        
    Returns:
        Langfuse client instance or None if not configured
        
    Note:
        This initializes a global client that can be reused across the application.
        Call this once at application startup.
    """
    global _langfuse_client
    
    if not LANGFUSE_AVAILABLE:
        warnings.warn(
            "Langfuse not available. Install with: pip install langfuse",
            UserWarning
        )
        return None
    
    if _langfuse_client is None:
        _langfuse_client = create_langfuse_client(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
    
    return _langfuse_client


def get_langfuse() -> Optional[Langfuse]:
    """Get the global Langfuse client instance.
    
    Returns:
        Langfuse client instance or None if not initialized
        
    Note:
        Automatically initializes from environment variables if not already initialized.
    """
    global _langfuse_client
    
    if _langfuse_client is None:
        _langfuse_client = get_langfuse_client()
    
    return _langfuse_client


def trace_agent(agent_name: str, trace_name: Optional[str] = None):
    """Decorator for tracing agent execution.
    
    Args:
        agent_name: Name of the agent being traced
        trace_name: Optional custom trace name (defaults to agent_name)
        
    Returns:
        Decorator function
        
    Example:
        @trace_agent("character_analyzer")
        def __call__(self, state):
            # Agent execution will be traced
            return self.llm.invoke(...)
            
    Note:
        Uses context manager internally for tracing.
        If Langfuse is not available, function executes normally without tracing.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            langfuse = get_langfuse()
            
            if langfuse is None:
                # Execute without tracing if Langfuse not available
                return func(*args, **kwargs)
            
            # Create trace for agent execution
            trace_name_final = trace_name or agent_name
            
            # Use start_span for agent execution (creates trace automatically)
            span = langfuse.start_span(
                name=trace_name_final,
                metadata={"agent": agent_name},
                input={"args": str(args)[:500], "kwargs": str(kwargs)[:500]}  # Limit input size
            )
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Set output and end span
                span.output = str(result)[:1000]  # Limit output size
                span.end()
                
                return result
            except Exception as e:
                # Mark span as error
                span.output = None
                span.level = "ERROR"
                span.status_message = str(e)
                span.end()
                raise
        
        return wrapper
    
    return decorator


@contextmanager
def trace_context(
    trace_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
):
    """Context manager for manual trace creation.
    
    Args:
        trace_name: Name of the trace
        metadata: Optional metadata dictionary
        user_id: Optional user identifier
        
    Yields:
        Trace object
        
    Example:
        with trace_context("story_generation", metadata={"job": "savannah_shadows"}) as trace:
            # All operations within this context will be part of the trace
            span = trace.span(name="agent_call")
            result = agent(state)
            span.end(output=result)
    """
    langfuse = get_langfuse()
    
    if langfuse is None:
        # If Langfuse not available, just execute without tracing
        yield None
        return
    
    try:
        # Start trace using start_span (creates trace automatically)
        trace = langfuse.start_span(
            name=trace_name,
            metadata=metadata or {},
            input={"user_id": user_id} if user_id else None
        )
        
        yield trace
        
        # End trace when context exits
        trace.end()
        
    except Exception as e:
        warnings.warn(
            f"Failed to create Langfuse trace: {e}",
            UserWarning
        )
        yield None


def create_langchain_callback_handler(
    trace_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Any]:
    """Create LangChain callback handler for automatic tracing.
    
    Args:
        trace_name: Name for the trace
        metadata: Optional metadata dictionary
        
    Returns:
        CallbackHandler instance or None if Langfuse not available
        
    Example:
        handler = create_langchain_callback_handler("character_analysis")
        llm = ChatOpenAI(callbacks=[handler])
        result = llm.invoke("...")
    """
    if not CALLBACK_HANDLER_AVAILABLE or CallbackHandler is None:
        warnings.warn(
            "Langfuse callback handler not available. "
            "LLM calls will not be automatically traced.",
            UserWarning
        )
        return None
    
    langfuse = get_langfuse()
    if langfuse is None:
        return None
    
    try:
        return CallbackHandler(
            public_key=langfuse.public_key,
            secret_key=langfuse.secret_key,
            host=langfuse.host,
            session_id=None,  # Will be set per execution
            trace_name=trace_name,
            metadata=metadata
        )
    except Exception as e:
        warnings.warn(
            f"Failed to create Langfuse callback handler: {e}",
            UserWarning
        )
        return None


def trace_llm_call(
    model: str,
    prompt: str,
    response: str,
    metadata: Optional[Dict[str, Any]] = None,
    trace_name: Optional[str] = None
) -> Optional[str]:
    """Manually trace an LLM call.
    
    Args:
        model: Model name (e.g., "gpt-4", "claude-3-sonnet")
        prompt: Input prompt text
        response: LLM response text
        metadata: Optional metadata dictionary
        trace_name: Optional trace name
        
    Returns:
        Generation ID if successful, None otherwise
        
    Example:
        gen_id = trace_llm_call(
            model="gpt-4",
            prompt="Analyze this character...",
            response="The character shows...",
            metadata={"agent": "character_analyzer"}
        )
    """
    langfuse = get_langfuse()
    if langfuse is None:
        return None
    
    try:
        # Create generation (creates trace automatically)
        generation = langfuse.start_generation(
            name=trace_name or model,
            model=model,
            input=prompt[:2000],  # Limit input size
            output=response[:2000],  # Limit output size
            metadata=metadata or {}
        )
        
        # End generation
        generation.end()
        
        return generation.id
    except Exception as e:
        warnings.warn(
            f"Failed to trace LLM call: {e}",
            UserWarning
        )
        return None


def flush_traces():
    """Flush pending traces to Langfuse.
    
    Call this before application shutdown to ensure all traces are sent.
    """
    langfuse = get_langfuse()
    if langfuse is not None:
        try:
            langfuse.flush()
        except Exception as e:
            warnings.warn(
                f"Failed to flush Langfuse traces: {e}",
                UserWarning
            )


# Auto-initialize on import if environment variables are set
def _auto_init():
    """Auto-initialize Langfuse if environment variables are set."""
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        init_langfuse()


# Run auto-init
_auto_init()

