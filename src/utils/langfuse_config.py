"""Langfuse client configuration and initialization."""

import os
import warnings
from typing import Optional

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    Langfuse = None
    LANGFUSE_AVAILABLE = False


def create_langfuse_client(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: Optional[str] = None
) -> Optional[Langfuse]:
    """Create a Langfuse client instance.
    
    Args:
        public_key: Langfuse public key (defaults to LANGFUSE_PUBLIC_KEY env var)
        secret_key: Langfuse secret key (defaults to LANGFUSE_SECRET_KEY env var)
        host: Langfuse host URL (defaults to LANGFUSE_HOST env var or https://cloud.langfuse.com)
        
    Returns:
        Langfuse client instance or None if not configured/available
    """
    if not LANGFUSE_AVAILABLE:
        return None
    
    # Get values from arguments or environment variables
    public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    # If no credentials provided, return None (optional feature)
    if not public_key or not secret_key:
        return None
    
    try:
        return Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
    except Exception as e:
        warnings.warn(
            f"Failed to create Langfuse client: {e}",
            UserWarning
        )
        return None


def get_langfuse_client() -> Optional[Langfuse]:
    """Get Langfuse client from environment variables.
    
    Returns:
        Langfuse client instance or None if not configured/available
    """
    return create_langfuse_client()

