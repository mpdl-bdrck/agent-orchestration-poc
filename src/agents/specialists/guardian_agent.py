"""
Guardian Agent - Portfolio Oversight Specialist

The Guardian Agent provides system-wide monitoring, anomaly detection, and portfolio
health assessment using the campaign-portfolio-pacing tool.
"""

import logging
import json
import traceback
from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool  # Type hint only - we use @tool decorator

from ..base_specialist import BaseSpecialistAgent
from ...utils.observability import trace_agent
from ...utils.tool_instructions import build_toolkit_reference

logger = logging.getLogger(__name__)


class GuardianAgent(BaseSpecialistAgent):
    """
    Guardian Agent for portfolio oversight and monitoring.
    
    Responsibilities:
    - System-wide monitoring and anomaly detection
    - Portfolio health assessment using portfolio pacing tool
    - Performance aggregation across campaigns/deals
    - Delegation to specialized agents
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the Guardian Agent.

        Args:
            config_path: Path to agent configuration YAML file
        """
        if config_path is None:
            from pathlib import Path
            package_dir = Path(__file__).parent.parent.parent
            config_path = str(package_dir / "config" / "guardian_agent.yaml")
        super().__init__(config_path)
        
        # Load tools (can be disabled via feature flag)
        self.tools = self._load_tools()
        self.streaming_callback = None  # Callback for streaming events
        self._toolkit_reference = None  # Cache for toolkit reference
        
        # Log tool status
        if self.tools:
            logger.info(f"Guardian agent initialized with {len(self.tools)} tool(s)")
        else:
            logger.info("Guardian agent initialized WITHOUT tools (feature flag disabled)")
    
    def _get_system_prompt(self, supervisor_instruction: str = None) -> str:
        """Get system prompt with toolkit reference and optional supervisor instruction."""
        base_prompt = self.config.prompts.get('system', '')
        
        # Inject supervisor instruction using XML tags for better LLM attention
        if supervisor_instruction:
            base_prompt += f"""

<supervisor_instruction>
{supervisor_instruction}
</supervisor_instruction>

CRITICAL: The text above is a direct order from the Orchestrator Supervisor. 
Follow the Supervisor's instruction exactly. If the instruction implies a greeting, introduction, 
or general question that doesn't require portfolio data, reply with text only. Do NOT call tools 
unless portfolio data is explicitly needed for the response.
"""
        
        # Build toolkit reference from available tools
        if self.tools and not self._toolkit_reference:
            self._toolkit_reference = build_toolkit_reference(self.tools)
        
        # Append toolkit reference if available
        if self._toolkit_reference:
            return f"{base_prompt}\n\n{self._toolkit_reference}"
        
        return base_prompt
    
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
    
    def _extract_account_info(self, question: str) -> Dict[str, Any]:
        """
        Extract account_id and advertiser from user question.
        
        Maps advertiser names to account IDs:
        - "Eli Lilly", "Lilly" → account_id=17, advertiser="Lilly"
        - Default: account_id=17 (Tricoast Media LLC)
        
        Args:
            question: User's question
            
        Returns:
            Dict with account_id and advertiser_filter
        """
        # Default demo account
        account_id = "17"  # Tricoast Media LLC
        advertiser_filter = None
        
        question_lower = question.lower()
        
        # Map advertiser names to account info
        advertiser_mappings = {
            "eli lilly": {"account_id": "17", "advertiser": "Lilly"},
            "lilly": {"account_id": "17", "advertiser": "Lilly"},
            "tricoast": {"account_id": "17", "advertiser": None},
        }
        
        # Check for advertiser mentions
        for advertiser_key, account_info in advertiser_mappings.items():
            if advertiser_key in question_lower:
                account_id = account_info["account_id"]
                advertiser_filter = account_info["advertiser"]
                break
        
        # Check for explicit account ID mentions (e.g., "account 17", "account #17")
        import re
        account_match = re.search(r'account\s*(?:#|id)?\s*(\d+)', question_lower)
        if account_match:
            account_id = account_match.group(1)
        
        return {
            "account_id": account_id,
            "advertiser_filter": advertiser_filter
        }

    def _load_tools(self) -> List[StructuredTool]:
        """
        Load Guardian-specific tools using the Canary pattern (@tool decorator).
        
        Uses the real portfolio pacing tool that queries PostgreSQL and Redshift
        for actual campaign data and portfolio metrics.
        
        FEATURE FLAG: Set GUARDIAN_TOOLS_ENABLED=false to disable tool access.
        """
        import os
        
        # FEATURE FLAG: Guardian tools are DISABLED by default to prevent unwanted tool calls
        # during introductions/greetings. Set GUARDIAN_TOOLS_ENABLED=true to re-enable.
        # 
        # To re-enable tools:
        # 1. Set environment variable: export GUARDIAN_TOOLS_ENABLED=true
        # 2. Uncomment the tool loading code below
        # 3. Change default below from 'false' to 'true' if desired
        
        # Feature flag: Check environment variable first, then config
        tools_enabled = os.getenv('GUARDIAN_TOOLS_ENABLED', 'false').lower() in ('true', '1', 'yes')
        
        # Also check config file if available
        if hasattr(self.config, 'tools_enabled'):
            tools_enabled = self.config.tools_enabled
        
        if not tools_enabled:
            logger.info("⚠️  Guardian tools DISABLED (default). Set GUARDIAN_TOOLS_ENABLED=true to enable.")
            return []
        
        # Tool loading code - enabled when feature flag is true
        try:
            # Use absolute import to avoid relative import cache corruption issues
            from src.tools.portfolio_pacing_tool import analyze_portfolio_pacing
            logger.info("✅ Loaded real portfolio pacing tool (database-backed)")
            # Just return the function. LangChain handles the rest.
            # The @tool decorator makes it a StructuredTool automatically.
            return [analyze_portfolio_pacing]
        except Exception as e:
            logger.error(f"Could not load portfolio pacing tool: {e}", exc_info=True)
            return []


    def analyze_without_tools(self, question: str, context: str, supervisor_instruction: str = None) -> Dict[str, Any]:
        """
        Analyze WITHOUT tools - used for introductions/greetings.
        
        This method runs the LLM without binding tools, preventing the agent
        from calling tools even if it wants to. This implements the "Tool Holster" pattern.
        
        Args:
            question: The question to analyze
            context: Relevant context from knowledge base
            supervisor_instruction: Optional instruction from supervisor
            
        Returns:
            Analysis result dictionary
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # Build system prompt with supervisor instruction
        system_prompt = self._get_system_prompt(supervisor_instruction=supervisor_instruction)
        user_prompt = self._build_user_prompt(question, context)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Call LLM WITHOUT binding tools
        response = self.llm.invoke(messages)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Emit streaming event if callback is set
        if self.streaming_callback and answer:
            self.streaming_callback("agent_response", answer, {"agent": "guardian"})
        
        return {
            'answer': answer,
            'specialist_type': self.specialist_type,
            'question': question
        }

    @trace_agent("guardian")
    def analyze(self, question: str, context: str, supervisor_instruction: str = None, use_tools: bool = True) -> Dict[str, Any]:
        """
        Perform Guardian analysis on a question with provided context.

        If tools are available, uses agent loop with tool calling.
        Otherwise falls back to standard analysis.

        Args:
            question: The question to analyze
            context: Relevant context from knowledge base
            supervisor_instruction: Optional instruction from supervisor (read from AgentState)

        Returns:
            Analysis result dictionary
        """

        # Extract account info from question
        account_info = self._extract_account_info(question)
        
        # Inject account info into context for the LLM
        enhanced_context = f"""
{context}

---

ACCOUNT INFORMATION (for tool calls):
- Default account_id: {account_info['account_id']} (Tricoast Media LLC)
- Advertiser filter: {account_info['advertiser_filter'] if account_info['advertiser_filter'] else 'None (all advertisers)'}

When calling analyze_portfolio_pacing, use these defaults unless the user specifies otherwise.
        """.strip()
        
        # If tools are available AND use_tools is True, use agent loop with tool calling
        # If use_tools is False, run without tools (Tool Holster pattern)
        if self.tools and use_tools:
            try:
                from langchain_core.messages import SystemMessage, HumanMessage
                from ...utils.agent_loop import execute_agent_loop

                logger.info(f"Guardian agent has {len(self.tools)} tools available")
                
                # Build messages
                system_prompt = self._get_system_prompt(supervisor_instruction=supervisor_instruction)
                user_prompt = self._build_user_prompt(question, enhanced_context)

                
                # Inject account defaults into system prompt
                system_prompt_with_defaults = f"""
{system_prompt}

IMPORTANT: When calling analyze_portfolio_pacing tool, use these default values:
- account_id: "{account_info['account_id']}" (Tricoast Media LLC)
- advertiser_filter: {f'"{account_info["advertiser_filter"]}"' if account_info['advertiser_filter'] else 'None'}

Only override these if the user explicitly specifies a different account or advertiser.
                """.strip()
                
                messages = [
                    SystemMessage(content=system_prompt_with_defaults),
                    HumanMessage(content=user_prompt)
                ]
                
                # Bind tools to LLM
                llm_with_tools = self.llm.bind_tools(self.tools)
                
                # Execute agent loop - enable tool call visibility
                # Note: stream_response=False because we'll emit agent_response event ourselves
                # Character-by-character streaming (stream_text) is for orchestrator, not agents
                result = execute_agent_loop(
                    llm_with_tools=llm_with_tools,
                    messages=messages,
                    tools=self.tools,
                    job_name="guardian_analysis",
                    max_iterations=5,
                    streaming_callback=self._emit_streaming_event if self.streaming_callback else None,  # Show tool calls
                    stream_response=False  # Don't stream character-by-character (that's for orchestrator)
                )
                
                # Get the final formatted response from LLM
                final_response = result.get('response', '')
                
                # Emit agent_response event ONCE with the full response
                # This will be displayed in a colored box by the CLI
                # Only emit if it's not JSON (orchestrator will synthesize JSON responses)
                if self.streaming_callback and final_response:
                    try:
                        # Check if it's JSON - if so, don't emit (orchestrator will synthesize)
                        json.loads(final_response.strip())
                        # It's JSON, don't emit via streaming callback
                        # The orchestrator will synthesize it
                    except (json.JSONDecodeError, ValueError):
                        # It's formatted text, emit it as agent_response event
                        # The CLI will display it in a colored streaming box
                        self.streaming_callback("agent_response", final_response, {"agent": "guardian"})
                
                return {
                    'answer': final_response,
                    'specialist_type': self.specialist_type,
                    'question': question,
                    'tool_calls': result.get('tool_calls', [])
                }
            except Exception as e:
                # 🔍 TRAP LOGGING: Full stack trace for guardian agent errors
                print("=" * 80)
                print("🔍 FULL STACK TRACE - GUARDIAN AGENT ERROR:")
                print("=" * 80)
                traceback.print_exc()  # FORCE PRINT TO CONSOLE
                print("=" * 80)
                
                logger.warning(f"Tool-based analysis failed, falling back to standard: {e}", exc_info=True)
                # Fall back to standard analysis
                return super().analyze(question, context)
        else:
            # No tools available, use standard analysis
            return super().analyze(question, context)
    
    def __call__(self, state: Any) -> str:
        """
        Execute Guardian analysis (required by BaseAgent interface).
        
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
        
        result = self.analyze(question, context)
        return result.get('answer', str(result))
