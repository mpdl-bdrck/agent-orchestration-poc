"""Display utilities for "glass box" CLI output."""

import sys
from typing import List, Dict, Any, Optional, ContextManager
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich import box

console = Console()


class GlassBoxDisplay:
    """Display manager for "glass box" terminal output."""
    
    # Color scheme
    REASONING_COLOR = "yellow"
    ANSWER_COLOR = "green"
    TOOL_CALL_COLOR = "cyan"
    AGENT_COLOR = "magenta"
    ERROR_COLOR = "red"
    INFO_COLOR = "blue"
    USER_COLOR = "cyan"
    ORCHESTRATOR_COLOR = "green"
    
    # Agent color mapping
    AGENT_COLORS = {
        'guardian': 'blue',      # 🛡️ Shield - trust/protection
        'specialist': 'yellow',  # 🔧 Wrench - technical/attention
        'optimizer': 'magenta',  # 🎯 Target - precision optimization
        'pathfinder': 'green',   # 🧭 Compass - navigation/guidance
        'orchestrator': 'white'  # 🧠 Brain - coordination/intelligence
    }
    
    # Agent emoji mapping
    AGENT_EMOJIS = {
        'guardian': '🛡️',
        'specialist': '🔧',
        'optimizer': '🎯',
        'pathfinder': '🧭',
        'orchestrator': '🧠'
    }
    
    def __init__(self):
        self.console = Console()
    
    def get_agent_color(self, agent_name: str) -> str:
        """Get color for agent."""
        return self.AGENT_COLORS.get(agent_name.lower(), 'white')
    
    def get_agent_emoji(self, agent_name: str) -> str:
        """Get emoji for agent."""
        return self.AGENT_EMOJIS.get(agent_name.lower(), '🤖')
    
    def show_reasoning(self, message: str):
        """Display reasoning/internal monologue."""
        self.console.print(f"[dim {self.REASONING_COLOR}][REASONING][/dim {self.REASONING_COLOR}] {message}")
    
    def show_tool_call(self, tool_name: str, args: Dict[str, Any] = None):
        """Display tool call."""
        args_str = ""
        if args:
            # Format args nicely
            args_list = [f"{k}={v}" for k, v in args.items() if v]
            args_str = f"({', '.join(args_list)})" if args_list else ""
        
        self.console.print(
            f"[dim {self.TOOL_CALL_COLOR}][TOOL][/dim {self.TOOL_CALL_COLOR}] {tool_name}{args_str}"
        )
    
    def show_crag_metrics(self, stats: Dict[str, Any]):
        """Display CRAG validation metrics."""
        relevant = stats.get('relevant_chunks', 0)
        total = stats.get('total_chunks', 0)
        avg_score = stats.get('average_score', 0.0)
        correction_applied = stats.get('correction_applied', False)
        correction_info = stats.get('correction_info')
        
        metrics_text = f"CRAG Validation: {relevant}/{total} chunks validated (avg relevance: {avg_score:.2f})"
        
        if correction_applied and correction_info:
            rewritten = correction_info.get('rewritten_query', '')
            metrics_text += f" | Query rewritten: '{rewritten}'"
        
        self.console.print(f"[{self.INFO_COLOR}]🔍 {metrics_text}[/{self.INFO_COLOR}]")
    
    def show_user_question(self, question: str):
        """Display user question with label (deprecated - handled in main.py now)."""
        # This method is kept for compatibility but the actual display
        # is handled directly in main.py to avoid Rich Console interference
        pass
    
    def show_orchestrator_response(self, response: str):
        """Display orchestrator response in a box."""
        emoji = self.get_agent_emoji('orchestrator')
        color = self.get_agent_color('orchestrator')
        panel = Panel(
            response,
            title=f"{emoji} Orchestrator Agent",
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    # DEPRECATED: Manual ASCII box drawing methods - kept for backward compatibility
    # Use create_agent_streaming_context() and create_orchestrator_streaming_context() instead
    def start_streaming_orchestrator_response(self):
        """DEPRECATED: Use create_orchestrator_streaming_context() instead."""
        emoji = self.get_agent_emoji('orchestrator')
        color = self.get_agent_color('orchestrator')
        
        # Print header for streaming box
        self.console.print(f"[{color}]╭─ {emoji} Orchestrator Agent[/{color}]")
        self.console.print(f"[{color}]│[/{color}] ", end="")
        return color
    
    def stream_orchestrator_text(self, text: str, orchestrator_color: str):
        """DEPRECATED: Use create_orchestrator_streaming_context() instead."""
        # Print each character with orchestrator color
        if text == '\n':
            self.console.print()
            self.console.print(f"[{orchestrator_color}]│[/{orchestrator_color}] ", end="")
        else:
            self.console.print(text, end="", style=orchestrator_color)
    
    def end_streaming_orchestrator_response(self, orchestrator_color: str):
        """DEPRECATED: Use create_orchestrator_streaming_context() instead."""
        self.console.print()
        # Print complete bottom border matching header format
        self.console.print(f"[{orchestrator_color}]╰──────────────────────────────────────────────────────────────────────────────╯[/{orchestrator_color}]")
        self.console.print()
    
    def show_agent_response(self, agent_name: str, response: str, emoji: str = None):
        """Display agent response in a colored box."""
        agent_lower = agent_name.lower()
        agent_emoji = emoji or self.get_agent_emoji(agent_lower)
        agent_color = self.get_agent_color(agent_lower)
        agent_display_name = agent_name.replace('_', ' ').title()
        
        panel = Panel(
            response,
            title=f"{agent_emoji} {agent_display_name} Agent",
            border_style=agent_color,
            box=box.ROUNDED,
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def create_agent_streaming_context(self, agent_name: str, emoji: str = None) -> 'AgentStreamingContext':
        """
        Create a streaming context manager for agent responses using Rich Live + Panel.
        
        Usage:
            with display.create_agent_streaming_context("guardian") as stream:
                stream.add_text("Hello")
                stream.add_text(" World")
        """
        agent_lower = agent_name.lower()
        agent_emoji = emoji or self.get_agent_emoji(agent_lower)
        agent_color = self.get_agent_color(agent_lower)
        agent_display_name = agent_name.replace('_', ' ').title()
        
        return AgentStreamingContext(
            self.console,
            agent_emoji,
            agent_color,
            agent_display_name
        )
    
    def create_orchestrator_streaming_context(self) -> 'OrchestratorStreamingContext':
        """
        Create a streaming context manager for orchestrator responses using Rich Live + Panel.
        
        Usage:
            with display.create_orchestrator_streaming_context() as stream:
                stream.add_text("Hello")
                stream.add_text(" World")
        """
        emoji = self.get_agent_emoji('orchestrator')
        color = self.get_agent_color('orchestrator')
        
        return OrchestratorStreamingContext(self.console, emoji, color)
    
    # DEPRECATED: Manual ASCII box drawing methods - kept for backward compatibility
    # Use create_agent_streaming_context() instead
    def start_streaming_agent_response(self, agent_name: str, emoji: str = None):
        """DEPRECATED: Use create_agent_streaming_context() instead."""
        agent_lower = agent_name.lower()
        agent_emoji = emoji or self.get_agent_emoji(agent_lower)
        agent_color = self.get_agent_color(agent_lower)
        agent_display_name = agent_name.replace('_', ' ').title()
        
        # Print header for streaming box
        self.console.print(f"[{agent_color}]╭─ {agent_emoji} {agent_display_name} Agent[/{agent_color}]")
        self.console.print(f"[{agent_color}]│[/{agent_color}] ", end="")
        return agent_color
    
    def stream_agent_text(self, text: str, agent_color: str):
        """DEPRECATED: Use create_agent_streaming_context() instead."""
        # Print each character with agent color
        if text == '\n':
            self.console.print()
            self.console.print(f"[{agent_color}]│[/{agent_color}] ", end="")
        else:
            self.console.print(text, end="", style=agent_color)
    
    def end_streaming_agent_response(self, agent_color: str):
        """DEPRECATED: Use create_agent_streaming_context() instead."""
        self.console.print()
        # Print complete bottom border matching header format
        self.console.print(f"[{agent_color}]╰──────────────────────────────────────────────────────────────────────────────╯[/{agent_color}]")
        self.console.print()
    
    def show_final_answer(self, answer: str):
        """Display final answer - now uses orchestrator formatting."""
        self.show_orchestrator_response(answer)
    
    def start_streaming_answer(self):
        """Start streaming answer display (returns a Live context manager)."""
        from rich.live import Live
        from rich.markdown import Markdown
        
        # Create a panel that will be updated
        panel = Panel(
            "",
            border_style="green",
            box=box.ROUNDED
        )
        live = Live(panel, refresh_per_second=10, console=self.console)
        return live
    
    def stream_text(self, text: str):
        """Stream a chunk of text (prints immediately without newline)."""
        self.console.print(text, end="", style="green")
    
    def show_multi_agent_orchestration(self, agents: List[str]):
        """Display multi-agent orchestration header."""
        agents_str = ", ".join([a.replace('_', ' ').title() for a in agents])
        self.console.print(
            f"\n[{self.AGENT_COLOR}]🔄 Multi-Agent Orchestration: {agents_str}[/{self.AGENT_COLOR}]\n"
        )
    
    def show_error(self, message: str):
        """Display error message."""
        self.console.print(f"[{self.ERROR_COLOR}]❌ Error: {message}[/{self.ERROR_COLOR}]")
    
    def show_info(self, message: str):
        """Display info message."""
        self.console.print(f"[{self.INFO_COLOR}]ℹ️  {message}[/{self.INFO_COLOR}]")
    
    def show_tool_results(self, tool_name: str, results: Dict[str, Any]):
        """Display tool results summary."""
        if tool_name == 'semantic_search':
            count = results.get('count', 0)
            crag_applied = results.get('crag_applied', False)
            status = "CRAG-validated" if crag_applied else "found"
            self.console.print(
                f"[{self.TOOL_CALL_COLOR}]✓ Semantic search {status}: {count} results[/{self.TOOL_CALL_COLOR}]"
            )
    
    def show_welcome(self, context_id: str = None):
        """Display welcome message."""
        welcome_text = Text()
        welcome_text.append("Agent Orchestration POC", style="bold green")
        welcome_text.append("\n", style="dim")
        
        if context_id:
            welcome_text.append(f"Type your questions or 'exit' to quit", style="dim")
        
        panel = Panel(
            welcome_text,
            border_style="green",
            box=box.ROUNDED
        )
        self.console.print(panel)
        self.console.print()
    
    def show_prompt(self):
        """Display input prompt."""
        self.console.print("[bold cyan]>[/bold cyan] ", end="")
    
    def clear_screen(self):
        """Clear the screen."""
        self.console.clear()


class AgentStreamingContext:
    """Context manager for streaming agent responses using Rich Live + Panel."""
    
    def __init__(self, console: Console, emoji: str, color: str, display_name: str):
        self.console = console
        self.emoji = emoji
        self.color = color
        self.display_name = display_name
        self.text = ""
        self.live = None
    
    def __enter__(self):
        """Enter the context manager and start Live display."""
        initial_panel = Panel(
            "",
            title=f"{self.emoji} {self.display_name} Agent",
            title_align="left",
            border_style=self.color,
            box=box.ROUNDED,
            padding=(0, 1),
            expand=False
        )
        self.live = Live(
            initial_panel,
            refresh_per_second=10,
            console=self.console,
            transient=False  # Keep panel after streaming completes
        )
        self.live.__enter__()
        return self
    
    def add_text(self, text: str):
        """Add text to the streaming response."""
        self.text += text
        # Create styled text with agent color
        styled_text = Text(self.text, style=self.color)
        panel = Panel(
            styled_text,
            title=f"{self.emoji} {self.display_name} Agent",
            title_align="left",
            border_style=self.color,
            box=box.ROUNDED,
            padding=(0, 1),
            expand=False
        )
        if self.live:
            self.live.update(panel)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and close Live display."""
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)
            self.live = None


class OrchestratorStreamingContext:
    """Context manager for streaming orchestrator responses using Rich Live + Panel."""
    
    def __init__(self, console: Console, emoji: str, color: str):
        self.console = console
        self.emoji = emoji
        self.color = color
        self.text = ""
        self.live = None
    
    def __enter__(self):
        """Enter the context manager and start Live display."""
        initial_panel = Panel(
            "",
            title=f"{self.emoji} Orchestrator Agent",
            title_align="left",
            border_style=self.color,
            box=box.ROUNDED,
            padding=(0, 1),
            expand=False
        )
        self.live = Live(
            initial_panel,
            refresh_per_second=10,
            console=self.console,
            transient=False  # Keep panel after streaming completes
        )
        self.live.__enter__()
        return self
    
    def add_text(self, text: str):
        """Add text to the streaming response."""
        self.text += text
        # Create styled text with orchestrator color
        styled_text = Text(self.text, style=self.color)
        panel = Panel(
            styled_text,
            title=f"{self.emoji} Orchestrator Agent",
            title_align="left",
            border_style=self.color,
            box=box.ROUNDED,
            padding=(0, 1),
            expand=False
        )
        if self.live:
            self.live.update(panel)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and close Live display."""
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)
            self.live = None

