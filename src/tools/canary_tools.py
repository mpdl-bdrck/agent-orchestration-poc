"""
Canary Tools - Minimal test tools for isolating agent loop issues.
"""
from langchain_core.tools import tool


@tool
def echo_tool(input_text: str) -> str:
    """
    Repeats the input text back to the user. Use this for greetings and testing.

    Args:
        input_text: The text to echo back

    Returns:
        The echoed text with CANARY prefix
    """
    # Simple, crash-proof logic
    if isinstance(input_text, list):
        input_text = input_text[0] if input_text else "empty"

    return f"CANARY ECHO: {str(input_text)}"
