"""
Canary Agent - Minimal test agent for isolating agent loop issues.
"""
import logging
from typing import List, Any, Dict
from pathlib import Path

from langchain_core.tools import StructuredTool

from ..base_specialist import BaseSpecialistAgent
from ...tools.canary_tools import echo_tool

logger = logging.getLogger(__name__)


class CanaryAgent(BaseSpecialistAgent):
    """
    Canary Agent for testing agent loop functionality.

    This is a minimal agent designed to isolate whether tool execution issues
    are specific to complex agents (like Guardian) or affect the core agent loop.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the Canary Agent.

        Args:
            config_path: Path to agent configuration YAML file
        """
        if config_path is None:
            from pathlib import Path
            package_dir = Path(__file__).parent.parent.parent
            config_path = str(package_dir / "config" / "canary_agent.yaml")
        super().__init__(config_path)

        # Load tools - only the echo tool
        self.tools = self._load_tools()
        self.streaming_callback = None  # Callback for streaming events

    def set_streaming_callback(self, callback):
        """Set streaming callback for emitting events."""
        self.streaming_callback = callback

    def _load_tools(self) -> List[StructuredTool]:
        """Load Canary-specific tools."""
        try:
            # echo_tool is already a StructuredTool from @tool decorator
            # Just return it directly in a list
            tools = [echo_tool]
            logger.info(f"Canary agent loaded {len(tools)} tool(s)")
            return tools
        except Exception as e:
            logger.error(f"Failed to load Canary tools: {e}", exc_info=True)
            return []

    def _get_system_prompt(self, supervisor_instruction: str = None) -> str:
        """Get system prompt with optional supervisor instruction."""
        base_prompt = """You are the Canary Agent, a minimal test agent designed to verify that the agent execution loop is working correctly.

Your ONLY purpose is to test tool execution. You have access to exactly ONE tool: echo_tool.

RULES:
- ALWAYS use the echo_tool when asked to say hello, greet, or echo anything
- AFTER calling the tool, you MUST provide a final text response that incorporates the tool result
- NEVER refuse to use the tool - it is designed to be safe
- Keep responses simple and direct
- If asked who you are, use the echo_tool to introduce yourself, then provide a final response

EXAMPLE:
User: "Say hello"
Step 1: Use echo_tool with input_text="Hello from the Canary Agent!"
Step 2: After receiving the tool result, provide your final response: "Hello from the Canary Agent!"

CRITICAL: After every tool call, you MUST provide a final text response. Do not stop after just calling the tool.

The echo_tool is crash-proof and will always work. Use it for all interactions."""

        # Inject supervisor instruction if provided
        if supervisor_instruction:
            base_prompt += f"""

<supervisor_instruction>
{supervisor_instruction}
</supervisor_instruction>

CRITICAL: Follow the Supervisor's instruction exactly."""

        return base_prompt

    def _emit_streaming_event(self, event_type: str, message: str, data: Dict[str, Any] = None):
        """Emit a streaming event if callback is set."""
        if self.streaming_callback:
            try:
                self.streaming_callback(event_type, message, data)
            except Exception as e:
                logger.debug(f"Streaming callback error: {e}")

    def analyze(self, question: str, context: str, supervisor_instruction: str = None) -> Dict[str, Any]:
        """
        Perform Canary analysis using tool execution.
        
        Args:
            question: The question to analyze
            context: Relevant context (ignored for canary)
            supervisor_instruction: Optional instruction from supervisor
            
        Returns:
            Analysis result dictionary with 'answer' key
        """
        try:
            logger.info(f"Canary agent analyzing question: {question[:100]}")
            logger.info(f"Canary agent has {len(self.tools)} tool(s)")
            
            if not self.tools:
                # No tools available - fallback to simple response
                logger.warning("Canary agent has no tools - using fallback response")
                fallback_response = "CANARY ECHO: Hello! I'm the Canary Agent, a test agent."
                if self.streaming_callback:
                    self.streaming_callback("agent_response", fallback_response, {"agent": "canary"})
                return {
                    'answer': fallback_response,
                    'specialist_type': self.specialist_type,
                    'question': question
                }
            
            # Use tool execution like Guardian agent
            from langchain_core.messages import SystemMessage, HumanMessage
            from ...utils.agent_loop import execute_agent_loop

            # Build prompts
            system_prompt = self._get_system_prompt(supervisor_instruction)
            user_prompt = self._build_user_prompt(question, context)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Bind tools to LLM
            llm_with_tools = self.llm.bind_tools(self.tools)

            # Execute agent loop
            result = execute_agent_loop(
                llm_with_tools=llm_with_tools,
                messages=messages,
                tools=self.tools,
                job_name="canary_test",
                max_iterations=3,
                streaming_callback=self._emit_streaming_event if self.streaming_callback else None,
                stream_response=True
            )

            # Get the final response
            final_response = result.get('response', '')
            logger.info(f"Canary agent got response length: {len(final_response)}")
            
            if not final_response:
                logger.warning("Canary agent got empty response - using fallback")
                final_response = "CANARY ECHO: Hello! I'm the Canary Agent."
            
            # Emit agent_response event so CLI can display it
            if self.streaming_callback and final_response:
                try:
                    # Check if it's JSON - if so, don't emit (orchestrator will synthesize)
                    import json
                    json.loads(final_response.strip())
                    # It's JSON, don't emit via streaming callback
                except (json.JSONDecodeError, ValueError):
                    # Not JSON, emit the response
                    self.streaming_callback("agent_response", final_response, {"agent": "canary"})
            
            return {
                'answer': final_response,
                'specialist_type': self.specialist_type,
                'question': question
            }
        except Exception as e:
            logger.error(f"Canary agent analyze failed: {e}", exc_info=True)
            error_response = f"CANARY ERROR: {str(e)}"
            if self.streaming_callback:
                self.streaming_callback("agent_response", error_response, {"agent": "canary"})
            return {
                'answer': error_response,
                'specialist_type': self.specialist_type,
                'question': question
            }

    def __call__(self, state: Any) -> str:
        """
        Execute Canary analysis (required by BaseAgent interface).

        Args:
            state: Can be a question string or dict with 'question' and 'context'

        Returns:
            Analysis result as string
        """
        if isinstance(state, str):
            question = state
            context = ""
        elif isinstance(state, dict):
            question = state.get('question', '')
            context = state.get('context', '')
        else:
            question = str(state)
            context = ""

        # Use analyze() method which has the tool execution logic
        result = self.analyze(question, context)
        return result.get('answer', str(result))
