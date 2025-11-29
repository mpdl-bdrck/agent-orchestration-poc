"""
Guardian Agent - Portfolio Oversight Specialist

The Guardian Agent provides system-wide monitoring, anomaly detection, and portfolio
health assessment using the campaign-portfolio-pacing tool.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..base_specialist import BaseSpecialistAgent
from ...utils.observability import trace_agent
from ...utils.tool_instructions import build_toolkit_reference

logger = logging.getLogger(__name__)


class PortfolioPacingInput(BaseModel):
    """Input schema for portfolio pacing analysis."""
    account_id: str = Field(default="17", description="Account ID to analyze (default: 17 for Tricoast Media LLC)")
    advertiser_filter: Optional[str] = Field(default=None, description="Optional advertiser name filter (e.g., 'Lilly' for Eli Lilly)")
    campaign_start: Optional[str] = Field(default=None, description="Campaign start date (YYYY-MM-DD) for pacing calculations")
    campaign_end: Optional[str] = Field(default=None, description="Campaign end date (YYYY-MM-DD) for pacing calculations")
    campaign_budget: Optional[float] = Field(default=None, description="Total campaign budget for pacing calculations")


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
        
        # Load tools
        self.tools = self._load_tools()
        self.streaming_callback = None  # Callback for streaming events
        self._toolkit_reference = None  # Cache for toolkit reference
    
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
        """Load Guardian-specific tools."""
        try:
            return [
                StructuredTool.from_function(
                    func=self._analyze_portfolio_pacing,
                    name="analyze_portfolio_pacing",
                    description="""Connects to the live database to fetch current pacing metrics and portfolio insights.
                    
                    CRITICAL USAGE RULES:
                    - STRICTLY RESERVED for queries asking for *numbers*, *data*, *status*, or *health* metrics
                    - DO NOT USE if the user is just asking who you are or what you do
                    - DO NOT USE for introductions, greetings, or general conversation
                    - DO NOT USE for role explanations or "who are you?" questions
                    - If the input is ambiguous, err on the side of NOT calling this tool
                    - This tool is computationally expensive - only use when live data is explicitly required
                    
                    This tool provides comprehensive portfolio oversight including:
                    - Campaign Portfolio Timeline (start/end dates, days passed/left)
                    - Budget Status (portfolio budget, spent, should have spent, remaining)
                    - Daily Pacing (target/actual/required daily rates, pacing status, budget projection)
                    - Daily Trend (spend and impressions over time)
                    
                    Default values:
                    - account_id: "17" (Tricoast Media LLC)
                    - advertiser_filter: None (all advertisers) or "Lilly" if user mentions Eli Lilly
                    
                    Always use account_id="17" unless user specifies a different account.
                    If user mentions "Eli Lilly" or "Lilly", use advertiser_filter="Lilly".
                    
                    Returns JSON with detailed portfolio insights matching dashboard format.""",
                    args_schema=PortfolioPacingInput
                )
            ]
        except Exception as e:
            logger.warning(f"Could not load portfolio pacing tool: {e}")
            return []

    def _analyze_portfolio_pacing(
        self,
        account_id: str,
        advertiser_filter: Optional[str] = None,
        campaign_start: Optional[str] = None,
        campaign_end: Optional[str] = None,
        campaign_budget: Optional[float] = None
    ) -> str:
        """Wrapper for portfolio pacing analysis tool with hardcoded defaults."""
        try:
            from ...tools.portfolio_pacing_tool import analyze_portfolio_pacing
            
            # Hardcode values for Eli Lilly portfolio
            # Account 17 = Tricoast Media LLC
            # Half of current budget: $466,004.06 / 2 ≈ $233,000
            hardcoded_account_id = "17"
            hardcoded_advertiser = "Lilly"
            hardcoded_campaign_start = "2025-11-01"
            hardcoded_campaign_end = "2025-11-30"
            hardcoded_campaign_budget = 233000.0  # Half of $466,004.06 (rounded)
            
            return analyze_portfolio_pacing(
                account_id=hardcoded_account_id,
                advertiser_filter=hardcoded_advertiser,
                campaign_start=hardcoded_campaign_start,
                campaign_end=hardcoded_campaign_end,
                campaign_budget=hardcoded_campaign_budget
            )
        except Exception as e:
            logger.error(f"Portfolio pacing analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return json.dumps({
                "status": "error",
                "error": str(e),
                "message": "Portfolio analysis failed"
            })

    @trace_agent("guardian")
    def analyze(self, question: str, context: str, supervisor_instruction: str = None) -> Dict[str, Any]:
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
        
        # If tools are available, use agent loop with tool calling
        if self.tools:
            try:
                from langchain_core.messages import SystemMessage, HumanMessage
                from ...utils.agent_loop import execute_agent_loop

                logger.info(f"Guardian agent has {len(self.tools)} tools available")
                self._emit_streaming_event("status", f"Using {len(self.tools)} tool(s) for analysis")
                
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
                
                # Execute agent loop - don't stream tool results, only final response
                result = execute_agent_loop(
                    llm_with_tools=llm_with_tools,
                    messages=messages,
                    tools=self.tools,
                    job_name="guardian_analysis",
                    max_iterations=5,
                    streaming_callback=None,  # Don't stream tool results, only final response
                    stream_response=True  # Enable streaming
                )
                
                # Get the final formatted response from LLM
                final_response = result.get('response', '')
                
                # Emit the final formatted response (not raw tool output)
                # Only emit if it's not JSON (orchestrator will synthesize JSON responses)
                if self.streaming_callback and final_response:
                    try:
                        # Check if it's JSON - if so, don't emit (orchestrator will synthesize)
                        json.loads(final_response.strip())
                        # It's JSON, don't emit via streaming callback
                        # The orchestrator will synthesize it
                    except (json.JSONDecodeError, ValueError):
                        # It's formatted text, emit it for streaming display in colored box
                        # The handler will stream it character by character
                        self.streaming_callback("agent_response", final_response, {"agent": "guardian"})
                
                return {
                    'answer': final_response,
                    'specialist_type': self.specialist_type,
                    'question': question,
                    'tool_calls': result.get('tool_calls', [])
                }
            except Exception as e:
                logger.warning(f"Tool-based analysis failed, falling back to standard: {e}")
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
