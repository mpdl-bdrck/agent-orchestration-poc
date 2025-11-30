"""CLI entry point for Agent Orchestration POC."""

import os
# Suppress HuggingFace tokenizer parallelism warning
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import argparse
import sys
import warnings
from pathlib import Path
from typing import Dict, Any

# Suppress Pydantic V1 deprecation warnings from langchain
warnings.filterwarnings('ignore', message='.*Pydantic V1.*', category=UserWarning)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Imports after path setup (intentional)
from src.agents.orchestrator import OrchestratorAgent  # noqa: E402
from src.interface.cli.display import GlassBoxDisplay  # noqa: E402

import logging  # noqa: E402

logging.basicConfig(
    level=logging.WARNING,  # Reduce noise in CLI
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CLIChat:
    """CLI chat interface for knowledge base Q&A."""
    
    def __init__(self, context_id: str = None, config_path: str = None):
        """
        Initialize CLI chat.
        
        Args:
            context_id: Knowledge base context identifier
            config_path: Path to orchestrator config file
        """
        self.context_id = context_id
        self.display = GlassBoxDisplay()
        self._last_streamed = False  # Track if last response was streamed
        
        # Rich Live streaming contexts
        self._agent_streaming_contexts = {}  # {agent_name: AgentStreamingContext}
        self._orchestrator_streaming_context = None
        
        # Initialize orchestrator agent
        try:
            if config_path:
                config_full_path = Path(config_path)
            else:
                config_full_path = project_root / "config" / "orchestrator.yaml"
            
            self.orchestrator = OrchestratorAgent(config_path=str(config_full_path))
            
            # Set streaming callback for real-time updates
            self.orchestrator.set_streaming_callback(self._handle_streaming_event)
            
            if context_id:
                self.orchestrator.set_context(context_id)
                
        except Exception as e:
            self.display.show_error(f"Failed to initialize orchestrator: {e}")
            raise
    
    def _handle_streaming_event(self, event_type: str, message: str, data: Dict[str, Any] = None):
        """Handle streaming events from orchestrator for real-time display."""
        if event_type == "reasoning":
            self.display.show_reasoning(message)
        elif event_type == "routing":
            self.display.show_reasoning(f"Routing to: {message}")
        elif event_type == "agent_call":
            agent_name = data.get('agent', '') if data else message
            self.display.show_reasoning(f"Calling {agent_name} agent...")
        elif event_type == "search_call":
            # Handle semantic_search as a tool call for visibility
            self.display.show_tool_call("semantic_search", {"query": data.get("query", "") if data else ""})
        elif event_type == "tool_call":
            tool_name = data.get('tool', message) if data else message
            args = data.get('args', {}) if data else {}
            self.display.show_tool_call(tool_name, args)
        elif event_type == "tool_result":
            tool_name = data.get('tool', '') if data else ''
            tool_output = data.get('result', message) if data else message
            
            # Show actual tool output for debugging/transparency
            if tool_name == 'analyze_portfolio_pacing':
                # Display the actual tool output
                self.display.show_reasoning(f"📊 Tool Output ({tool_name}):")
                # Show tool output in a readable format
                if isinstance(tool_output, str):
                    # Truncate if too long, but show enough to see what tool returned
                    display_output = tool_output[:500] + "..." if len(tool_output) > 500 else tool_output
                    self.display.show_reasoning(f"   {display_output}")
                else:
                    self.display.show_reasoning(f"   {str(tool_output)[:500]}")
            elif tool_name == 'semantic_search':
                count = data.get('count', 0) if data else 0
                self.display.show_reasoning(f"✅ Semantic search found {count} results")
            else:
                # Generic tool result display
                if tool_output:
                    display_output = str(tool_output)[:300] + "..." if len(str(tool_output)) > 300 else str(tool_output)
                    self.display.show_reasoning(f"📊 Tool Output ({tool_name}): {display_output}")
        elif event_type == "agent_response":
            # Agent response using Rich Live + Panel
            agent_name = data.get('agent', '') if data else ''
            if agent_name and message:
                # Check if message is raw JSON - if so, hide it and just show status
                import json
                try:
                    # Try to parse as JSON
                    json.loads(message.strip())
                    # If it's valid JSON, don't show the raw output
                    # Just show a status message that analysis is complete
                    self.display.show_reasoning(f"✅ {agent_name.title()} analysis complete")
                    self._agent_responses_shown = True
                except (json.JSONDecodeError, ValueError):
                    # Not JSON, use Rich Live for streaming
                    if agent_name not in self._agent_streaming_contexts:
                        # Create new streaming context
                        context = self.display.create_agent_streaming_context(agent_name)
                        context.__enter__()
                        self._agent_streaming_contexts[agent_name] = context
                    
                    # Add text to streaming context (character by character for smooth streaming)
                    context = self._agent_streaming_contexts[agent_name]
                    for char in message:
                        context.add_text(char)
                    
                    self._agent_responses_shown = True
            else:
                self.display.show_reasoning(f"✅ {agent_name.title() if agent_name else 'Agent'} analysis complete")
        elif event_type == "status":
            self.display.show_reasoning(message)
        elif event_type == "stream_text":
            # Stream orchestrator text using Rich Live + Panel
            if self._orchestrator_streaming_context is None:
                # Create new streaming context
                self._orchestrator_streaming_context = self.display.create_orchestrator_streaming_context()
                self._orchestrator_streaming_context.__enter__()
            
            # Add text to streaming context (character by character for smooth streaming)
            for char in message:
                self._orchestrator_streaming_context.add_text(char)
            self._last_streamed = True
    
    def run(self):
        """Run the chat loop."""
        self.display.show_welcome(self.context_id)
        
        if not self.context_id:
            self.display.show_info("No context_id specified. Please set one with --context-id")
            return
        
        if not self.orchestrator.context_id:
            self.display.show_error("Failed to set context. Exiting.")
            return
        
        # Chat loop
        while True:
            try:
                # Show prompt
                self.display.show_prompt()
                # Get input - it will echo, but we'll overwrite it immediately
                user_input = input().strip()
                
                if not user_input:
                    # Clear the echoed empty line
                    sys.stdout.write("\033[A\033[2K")
                    sys.stdout.flush()
                    continue
                
                # CRITICAL: Overwrite the echoed line immediately using raw ANSI codes
                # \033[A = move cursor up, \033[2K = clear entire line, \r = return to start
                sys.stdout.write("\033[A\033[2K\r")
                # Print "You:" with cyan color using ANSI codes (bypass Rich to avoid interference)
                # \033[1;36m = bold cyan, \033[0m = reset
                sys.stdout.write(f"\033[1;36mYou:\033[0m {user_input}\n")
                sys.stdout.flush()
                # Add spacing
                self.display.console.print()
                
                # Handle commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self.display.show_info("Goodbye!")
                    break
                
                if user_input.lower() == 'clear':
                    self.display.clear_screen()
                    self.display.show_welcome(self.context_id)
                    continue
                
                if user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                # Process question
                self._process_question(user_input)
                
            except KeyboardInterrupt:
                self.display.show_info("\nGoodbye!")
                break
            except EOFError:
                self.display.show_info("\nGoodbye!")
                break
            except Exception as e:
                self.display.show_error(f"Error: {e}")
                logger.exception("Error in chat loop")
    
    def _process_question(self, question: str):
        """Process a user question."""
        # Show user question with "You:" label (input was already entered, no echo needed)
        self.display.show_user_question(question)
        
        # Note: Reasoning is now shown via streaming callback in real-time
        # The orchestrator will emit streaming events that will be displayed as they happen
        
        # Track if we've shown agent responses via streaming
        self._agent_responses_shown = False
        
        # Initialize streaming contexts
        self._agent_streaming_contexts = {}
        self._orchestrator_streaming_context = None
        
        # Get response from orchestrator (streaming events will be emitted during processing)
        try:
            response = self.orchestrator.chat(question, context_id=self.context_id)
            
            # Close all streaming contexts
            # Close agent streaming contexts
            for agent_name, context in self._agent_streaming_contexts.items():
                try:
                    context.__exit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Error closing agent streaming context for {agent_name}: {e}")
            self._agent_streaming_contexts = {}
            
            # Close orchestrator streaming context
            if self._orchestrator_streaming_context is not None:
                try:
                    self._orchestrator_streaming_context.__exit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Error closing orchestrator streaming context: {e}")
                self._orchestrator_streaming_context = None
            
            # CRITICAL: If agent responses were shown via streaming, NEVER show orchestrator response
            # Also skip if response is empty (single agent responses that were already displayed)
            # The orchestrator should return empty string for single agent responses
            if hasattr(self, '_agent_responses_shown') and self._agent_responses_shown:
                # Agent already responded via streaming - DO NOT show orchestrator response (it's a duplicate)
                logger.debug("Agent response already shown via streaming - skipping orchestrator response to prevent duplicate")
                self.display.console.print()
            elif response and response.strip():
                # Only show orchestrator response if no agent responded AND response is not empty
                if not hasattr(self, '_last_streamed') or not self._last_streamed:
                    # Show orchestrator response in box (non-streamed)
                    logger.warning(f"⚠️ CLI: Showing orchestrator response even though agent responded. Response length: {len(response)}")
                    self.display.show_orchestrator_response(response)
                # If streamed, box was already closed above
            else:
                # Response is empty - just add spacing
                logger.debug("Orchestrator returned empty response - skipping display")
                self.display.console.print()
            
            # Show tool usage and agent calls in compact footer format
            footer_parts = []
            
            # Collect tool calls (shown dimmed)
            if hasattr(self.orchestrator, 'last_tool_calls') and self.orchestrator.last_tool_calls:
                tool_names = [tc.get('tool', 'unknown') for tc in self.orchestrator.last_tool_calls]
                if tool_names:
                    footer_parts.append(f"[dim cyan]Tools: {', '.join(tool_names)}[/dim cyan]")
                
                # Parse and show CRAG metrics if available
                for tool_call in self.orchestrator.last_tool_calls:
                    tool_name = tool_call.get('tool', 'unknown')
                    tool_result = tool_call.get('result', '')
                    
                    if tool_name == 'semantic_search' and isinstance(tool_result, str):
                        try:
                            import json
                            result_data = json.loads(tool_result)
                            if result_data.get('crag_applied') and result_data.get('crag_stats'):
                                crag_stats = result_data.get('crag_stats', {})
                                relevant = crag_stats.get('relevant_chunks', 0)
                                total = crag_stats.get('total_chunks', 0)
                                avg_score = crag_stats.get('average_score', 0)
                                footer_parts.append(f"[dim blue]🔍 CRAG: {relevant}/{total} validated (avg: {avg_score:.2f})[/dim blue]")
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass
            
            # Show specialist agents used (compact format)
            if hasattr(self.orchestrator, 'last_agent_calls') and self.orchestrator.last_agent_calls:
                agent_list = []
                for agent_call in self.orchestrator.last_agent_calls:
                    agent_name = agent_call.get('agent', '')
                    agent_lower = agent_name.lower()
                    emoji = self.display.get_agent_emoji(agent_lower)
                    color = self.display.get_agent_color(agent_lower)
                    agent_display_name = agent_name.replace('_', ' ').title()
                    agent_list.append(f"[{color}]{emoji} {agent_display_name}[/{color}]")
                
                if agent_list:
                    footer_parts.append(f"[dim]Agents: {' | '.join(agent_list)}[/dim]")
            
            # Show footer if we have any info
            if footer_parts:
                self.display.console.print()
                self.display.console.print(" | ".join(footer_parts))
                self.display.console.print()
            
        except Exception as e:
            # Cleanup streaming contexts on error
            for agent_name, context in self._agent_streaming_contexts.items():
                try:
                    context.__exit__(None, None, None)
                except Exception:
                    pass
            self._agent_streaming_contexts = {}
            
            if self._orchestrator_streaming_context is not None:
                try:
                    self._orchestrator_streaming_context.__exit__(None, None, None)
                except Exception:
                    pass
                self._orchestrator_streaming_context = None
            
            self.display.show_error(f"Failed to get response: {e}")
            logger.exception("Error processing question")
    
    def _show_help(self):
        """Show help message."""
        help_text = """
Available commands:
  help          - Show this help message
  clear         - Clear the screen
  exit/quit/q   - Exit the chat

Ask questions about your knowledge base content.
The system will use semantic search and multi-agent orchestration
to provide comprehensive answers.
        """
        self.display.show_info(help_text)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Agent Orchestration POC - Knowledge Base Q&A CLI'
    )
    parser.add_argument(
        '--context-id',
        type=str,
        required=True,
        help='Knowledge base context identifier'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to orchestrator config file (default: config/orchestrator.yaml)'
    )
    
    args = parser.parse_args()
    
    try:
        chat = CLIChat(context_id=args.context_id, config_path=args.config)
        chat.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

