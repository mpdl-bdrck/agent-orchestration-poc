"""
Session History Management

Manages conversation state and history in memory only (session-only).
"""
from typing import List, Dict, Optional


class SessionHistory:
    """Manages conversation state and history in memory only (session-only)."""

    def __init__(self, context_id: str, session_id: str = "default", max_history: int = 10):
        self.context_id = context_id
        self.session_id = session_id
        self.max_history = max_history  # Keep last N exchanges
        self.messages: List[Dict[str, str]] = []

    def add_exchange(self, user_message: str, assistant_message: str, tool_calls: Optional[List[Dict]] = None):
        """Add a user-assistant exchange to in-memory history only."""
        # Add to in-memory list only (NO DATABASE OPERATIONS)
        user_entry = {
            'role': 'user',
            'content': user_message,
            'timestamp': 'now'
        }
        assistant_entry = {
            'role': 'assistant',
            'content': assistant_message,
            'timestamp': 'now',
            'tool_calls': tool_calls or []
        }

        self.messages.append(user_entry)
        self.messages.append(assistant_entry)

        # Keep only last max_history exchanges
        if len(self.messages) > self.max_history * 2:
            self.messages = self.messages[-self.max_history * 2:]

    def get_recent_history(self, num_exchanges: int = 5) -> List[Dict[str, str]]:
        """Get recent conversation history."""
        return self.messages[-num_exchanges * 2:] if len(self.messages) > num_exchanges * 2 else self.messages

    def clear(self):
        """Clear conversation history."""
        self.messages = []

