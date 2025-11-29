"""
Guardian Agent - Portfolio Oversight Specialist

The Guardian Agent provides system-wide monitoring, anomaly detection, and portfolio
health assessment using the campaign-portfolio-pacing tool.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator

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
    
    @field_validator('account_id', mode='before')
    @classmethod
    def normalize_account_id(cls, v):
        """Normalize account_id, handling list inputs BEFORE any string operations."""
        # CRITICAL: Handle list FIRST, before Pydantic tries to validate as string
        if isinstance(v, list):
            v = v[0] if len(v) > 0 else "17"
        if v is None:
            return "17"
        # Now safe to convert to string and strip
        return str(v).strip() if isinstance(v, str) else str(v)
    
    @field_validator('advertiser_filter', mode='before')
    @classmethod
    def normalize_advertiser_filter(cls, v):
        """Normalize advertiser_filter, handling list inputs BEFORE any string operations."""
        if isinstance(v, list):
            v = v[0] if len(v) > 0 else None
        if v is None:
            return None
        return str(v).strip() if isinstance(v, str) else str(v)
    
    @field_validator('campaign_start', mode='before')
    @classmethod
    def normalize_campaign_start(cls, v):
        """Normalize campaign_start, handling list inputs BEFORE any string operations."""
        if isinstance(v, list):
            v = v[0] if len(v) > 0 else None
        if v is None:
            return None
        return str(v).strip() if isinstance(v, str) else str(v)
    
    @field_validator('campaign_end', mode='before')
    @classmethod
    def normalize_campaign_end(cls, v):
        """Normalize campaign_end, handling list inputs BEFORE any string operations."""
        if isinstance(v, list):
            v = v[0] if len(v) > 0 else None
        if v is None:
            return None
        return str(v).strip() if isinstance(v, str) else str(v)
    
    @field_validator('campaign_budget', mode='before')
    @classmethod
    def normalize_campaign_budget(cls, v):
        """Normalize campaign_budget, handling list inputs BEFORE any float conversion."""
        if isinstance(v, list):
            v = v[0] if len(v) > 0 else None
        if v is None:
            return None
        try:
            return float(v) if v else None
        except (ValueError, TypeError):
            return None


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
        account_id: str = None,
        advertiser_filter: Optional[str] = None,
        campaign_start: Optional[str] = None,
        campaign_end: Optional[str] = None,
        campaign_budget: Optional[float] = None
    ) -> str:
        """Wrapper for portfolio pacing analysis tool with hardcoded defaults."""
        try:
            from ...tools.portfolio_pacing_tool import analyze_portfolio_pacing
            
            # Defensive coding: handle list inputs from eager LLMs
            def _normalize_string_arg(arg, default=None):
                """Normalize argument to string, handling list inputs."""
                if arg is None:
                    return default
                if isinstance(arg, list):
                    if len(arg) > 0:
                        arg = arg[0]
                    else:
                        return default
                return str(arg).strip() if arg else default
            
            def _normalize_float_arg(arg, default=None):
                """Normalize argument to float, handling list inputs."""
                if arg is None:
                    return default
                if isinstance(arg, list):
                    if len(arg) > 0:
                        arg = arg[0]
                    else:
                        return default
                try:
                    return float(arg) if arg else default
                except (ValueError, TypeError):
                    return default
            
            # Normalize all arguments (defensive - LLM might pass lists)
            account_id = _normalize_string_arg(account_id, "17")
            advertiser_filter = _normalize_string_arg(advertiser_filter, "Lilly")
            campaign_start = _normalize_string_arg(campaign_start, "2025-11-01")
            campaign_end = _normalize_string_arg(campaign_end, "2025-11-30")
            campaign_budget = _normalize_float_arg(campaign_budget, 233000.0)
            
            # Hardcode values for Eli Lilly portfolio
            # Account 17 = Tricoast Media LLC
            # Half of current budget: $466,004.06 / 2 ≈ $233,000
            hardcoded_account_id = account_id if account_id else "17"
            hardcoded_advertiser = advertiser_filter if advertiser_filter else "Lilly"
            hardcoded_campaign_start = campaign_start if campaign_start else "2025-11-01"
            hardcoded_campaign_end = campaign_end if campaign_end else "2025-11-30"
            hardcoded_campaign_budget = campaign_budget if campaign_budget else 233000.0
            
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
            # CRITICAL: Skip tool calling for introductions/greetings based on supervisor instruction
            if supervisor_instruction:
                instruction_lower = supervisor_instruction.lower()
                skip_tools_keywords = ["introduce", "say hi", "greeting", "forbidden", "do not use tools", "text only", "speak text"]
                if any(keyword in instruction_lower for keyword in skip_tools_keywords):
                    logger.info("Supervisor instruction forbids tool usage - skipping tool-based analysis")
                    return super().analyze(question, context)
            
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
                
                # Execute agent loop - enable tool call visibility
                result = execute_agent_loop(
                    llm_with_tools=llm_with_tools,
                    messages=messages,
                    tools=self.tools,
                    job_name="guardian_analysis",
                    max_iterations=5,
                    streaming_callback=self._emit_streaming_event if self.streaming_callback else None,  # Show tool calls
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
