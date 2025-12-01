"""
Generic agent loop utilities for tool-calling agents.

Provides reusable agent loop execution for any agent that needs LLM invocation
with tool calling, conversation management, and response formatting.

Used by:
- KnowledgeCuratorAgent (current)
- Future Stage 2 agents (MilestoneSynthesizerAgent, etc.)
- Future Stage 3 agents (SceneOrchestrator, BeatGenerator)
- Dual-mode agents (for validation/proposals)
"""

import json
import logging
import traceback
from typing import Any, Optional, List, Dict
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)


def _safe_extract_content(result) -> str:
    """
    Safely extract content from LLM result, handling both string and list formats.
    
    Gemini (and other LLMs) can return content as:
    - A string: "Hello world"
    - A list: [] (empty for tool calls) or [{"type": "text", "text": "Hello"}]
    
    Args:
        result: LLM result object with .content attribute
        
    Returns:
        String content, or empty string if content is list/empty
    """
    if not hasattr(result, 'content'):
        return ""
    
    content = result.content
    
    if isinstance(content, str):
        return content.strip() if content else ""
    elif isinstance(content, list):
        # Extract text from list of content blocks (Gemini format)
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                # Handle Gemini's content block format: {"type": "text", "text": "..."}
                if block.get("type") == "text" and "text" in block:
                    text_parts.append(str(block["text"]))
                elif "text" in block:
                    # Fallback: just look for "text" key
                    text_parts.append(str(block["text"]))
            elif isinstance(block, str):
                text_parts.append(block)
        return " ".join(text_parts).strip()
    else:
        # Fallback: convert to string
        return str(content) if content else ""


def execute_agent_loop(
    llm_with_tools,
    messages: list[BaseMessage],
    tools: list[StructuredTool],
    job_name: str,
    max_iterations: int = 5,
    streaming_callback: callable = None,
    stream_response: bool = False
) -> dict[str, Any]:
    """
    Execute agent loop with tool calling.

    Generic implementation for any agent that needs to:
    - Invoke LLM with tools
    - Execute tool calls
    - Handle tool results
    - Format final response

    Args:
        llm_with_tools: LLM instance with tools bound (via bind_tools())
        messages: List of LangChain messages (should include system prompt and user query)
        tools: List of StructuredTool instances available to the agent
        job_name: Job name to inject into tool args (if not already present)
        max_iterations: Maximum number of tool-calling iterations

    Returns:
        Dict with:
        - 'response': Final text response from LLM
        - 'tool_calls': List of tool call results
        - 'tool_results_data': Parsed tool results for conversation history (optional)

    Example:
        llm_with_tools = llm.bind_tools(tools)
        messages = [SystemMessage(...), HumanMessage(...)]
        result = execute_agent_loop(llm_with_tools, messages, tools, "my_job")
    """
    tool_calls = []
    iteration = 0
    result = None
    response_text = ""

    while iteration < max_iterations:
        result = llm_with_tools.invoke(messages)

        # SAFE CONTENT CHECK - Handle both string and list content
        content_str = _safe_extract_content(result)
        has_content = bool(content_str)

        # Check if LLM wants to use tools
        has_tool_calls = hasattr(result, 'tool_calls') and result.tool_calls

        # If we have content and no tool calls, this is the final response
        if has_content and not has_tool_calls:
            response_text = content_str
            # Stream the response if enabled
            if stream_response and streaming_callback and response_text:
                try:
                    # Stream character by character for immediate feedback
                    for char in response_text:
                        streaming_callback("stream_text", char, None)
                except Exception:
                    pass
            break

        # If we have tool calls, execute them
        if has_tool_calls:
            # Emit reasoning if present (LLM might provide reasoning before tool calls)
            if has_content and streaming_callback:
                try:
                    # Emit reasoning before tool execution for debugging/transparency
                    streaming_callback("reasoning", content_str, None)
                except Exception:
                    pass  # Don't fail if callback errors
            
            # Add assistant message with tool calls
            messages.append(result)

            # Execute each tool call
            for tool_call in result.tool_calls:
                tool_name, tool_args, tool_call_id = _extract_tool_call_info(tool_call, job_name)

                # Emit streaming event for tool call
                if streaming_callback:
                    try:
                        streaming_callback("tool_call", tool_name, {'tool': tool_name, 'args': tool_args})
                    except Exception:
                        pass  # Don't fail if callback errors

                # Find and execute the tool
                tool_func = next((t for t in tools if t.name == tool_name), None)
                if tool_func:
                    # Load execution instructions from markdown file (if available)
                    try:
                        from .tool_instructions import load_execution_instructions
                        
                        # Extract current question from messages
                        current_question = ""
                        for msg in reversed(messages):
                            if isinstance(msg, HumanMessage):
                                current_question = msg.content
                                break
                        
                        execution_instructions = load_execution_instructions(
                            tool_name=tool_name,
                            question=current_question,
                            tool_args=tool_args,
                            conversation_history=None
                        )
                        
                        # Inject instructions BEFORE tool execution
                        if execution_instructions:
                            instructions_msg = HumanMessage(
                                content=f"TOOL EXECUTION GUIDANCE for {tool_name}:\n\n{execution_instructions}\n\nUse this guidance when interpreting the tool results."
                            )
                            messages.append(instructions_msg)
                            logger.debug(f"Injected execution instructions for {tool_name}")
                    except Exception as e:
                        logger.debug(f"Failed to load execution instructions: {e}")
                    
                    try:
                        # 1. Normalization (Recursive fix confirmed working)
                        logger.info(f"[{job_name}] 🔧 Raw Args: {tool_args}")
                        normalized_args = _normalize_tool_args(tool_args)
                        logger.info(f"[{job_name}] ✅ Normalized: {normalized_args}")
                        
                        # 2. Filter unsupported args (like job_name) - SKIP SIGNATURE INSPECTION
                        # Signature inspection might trigger Pydantic validation, so we'll be more aggressive
                        # Just remove job_name if it exists - the function will reject it if it doesn't accept it
                        if 'job_name' in normalized_args:
                            # Try to remove job_name, but don't inspect signature (might trigger validation)
                            # We'll let the function call fail if job_name isn't accepted
                            logger.info(f"[{job_name}] Removing job_name from args (will be filtered by function if not accepted)")
                            normalized_args_no_job = {k: v for k, v in normalized_args.items() if k != 'job_name'}
                            normalized_args = normalized_args_no_job
                        
                        # 3. AGGRESSIVE BYPASS EXECUTION - Try ALL methods before giving up
                        tool_result = None
                        bypass_success = False
                        last_error = None
                        
                        # Attempt 1: Standard .func (Direct)
                        if not bypass_success:
                            if hasattr(tool_func, 'func'):
                                try:
                                    logger.info(f"[{job_name}] 🚀 Attempting bypass via .func")
                                    tool_result = tool_func.func(**normalized_args)
                                    bypass_success = True
                                    logger.info(f"[{job_name}] ✅✅✅ SUCCESS! Bypassed validation via .func")
                                except Exception as e:
                                    last_error = e
                                    logger.warning(f"[{job_name}] ❌ .func failed: {e}")
                            else:
                                logger.info(f"[{job_name}] No .func attribute found")
                        
                        # Attempt 2: Private ._func (Hidden attribute)
                        if not bypass_success:
                            if hasattr(tool_func, '_func'):
                                try:
                                    logger.info(f"[{job_name}] 🚀 Attempting bypass via ._func")
                                    tool_result = tool_func._func(**normalized_args)
                                    bypass_success = True
                                    logger.info(f"[{job_name}] ✅✅✅ SUCCESS! Bypassed validation via ._func")
                                except Exception as e:
                                    last_error = e
                                    logger.warning(f"[{job_name}] ❌ ._func failed: {e}")
                            else:
                                logger.info(f"[{job_name}] No ._func attribute found")
                        
                        # Attempt 3: Try to get function from tool attributes
                        if not bypass_success:
                            # Some LangChain versions store it differently
                            for attr_name in ['_run', 'run', 'function', '_function']:
                                if hasattr(tool_func, attr_name):
                                    attr = getattr(tool_func, attr_name)
                                    if callable(attr):
                                        try:
                                            logger.info(f"[{job_name}] 🚀 Attempting bypass via .{attr_name}")
                                            tool_result = attr(**normalized_args)
                                            bypass_success = True
                                            logger.info(f"[{job_name}] ✅✅✅ SUCCESS! Bypassed validation via .{attr_name}")
                                            break
                                        except Exception as e:
                                            last_error = e
                                            logger.warning(f"[{job_name}] ❌ .{attr_name} failed: {e}")
                        
                        # Attempt 4: Fallback to invoke (The Crash Zone) - ONLY IF ALL BYPASSES FAILED
                        if not bypass_success:
                            logger.error(f"[{job_name}] ⚠️⚠️⚠️ ALL BYPASS ATTEMPTS FAILED! Falling back to invoke(). CRASH RISK HIGH!")
                            logger.error(f"[{job_name}] Tool type: {type(tool_func)}")
                            logger.error(f"[{job_name}] Tool dir: {[x for x in dir(tool_func) if not x.startswith('__')][:10]}")
                            logger.error(f"[{job_name}] Has .func: {hasattr(tool_func, 'func')}")
                            logger.error(f"[{job_name}] Has ._func: {hasattr(tool_func, '_func')}")
                            logger.error(f"[{job_name}] Last error: {last_error}")
                            logger.error(f"[{job_name}] Normalized args: {normalized_args}")
                            # This will likely crash, but at least we'll have full diagnostics
                            tool_result = tool_func.invoke(normalized_args)
                        
                        # Parse JSON result if tool returns JSON with CSV data
                        csv_data = None
                        csv_filename = None
                        result_text = str(tool_result)
                        
                        try:
                            import json
                            parsed = json.loads(result_text)
                            if isinstance(parsed, dict) and "csv" in parsed:
                                # Tool returned JSON with CSV data
                                csv_data = parsed.get("csv")
                                csv_filename = parsed.get("filename")
                                result_text = parsed.get("text", result_text)  # Use text from JSON
                                
                                # Include advertiser_name and account_name in the result so LLM can use them
                                advertiser_name = parsed.get("advertiser_name")
                                account_name = parsed.get("account_name")
                                if advertiser_name or account_name:
                                    metadata_section = "\n\n---\n"
                                    if advertiser_name:
                                        metadata_section += f"Advertiser: {advertiser_name}\n"
                                    if account_name:
                                        metadata_section += f"Account: {account_name}\n"
                                    result_text = result_text + metadata_section
                                
                                logger.info(f"[{job_name}] ✅ Parsed JSON result with CSV data for {tool_name}: filename={csv_filename}, csv_len={len(csv_data) if csv_data else 0}")
                                
                                # CRITICAL: Store CSV in multiple locations for Chainlit access
                                # 1. Module-level dict (for direct access)
                                if not hasattr(execute_agent_loop, '_csv_storage'):
                                    execute_agent_loop._csv_storage = {}
                                
                                storage_key = f"{job_name}_{tool_name}"
                                execute_agent_loop._csv_storage[storage_key] = {
                                    "csv": csv_data,
                                    "filename": csv_filename,
                                    "timestamp": __import__('time').time()
                                }
                                logger.info(f"[{job_name}] Stored CSV in agent_loop._csv_storage[{storage_key}]")
                                
                                # ALSO store in a file-based cache (most reliable - survives module reloads)
                                try:
                                    import json
                                    import os
                                    import tempfile
                                    cache_dir = os.path.join(tempfile.gettempdir(), "chainlit_csv_cache")
                                    os.makedirs(cache_dir, exist_ok=True)
                                    cache_file = os.path.join(cache_dir, f"{storage_key}.json")
                                    with open(cache_file, 'w') as f:
                                        json.dump({
                                            "csv": csv_data,
                                            "filename": csv_filename,
                                            "node_name": job_name.split("_")[0] if "_" in job_name else job_name
                                        }, f)
                                    logger.info(f"[{job_name}] ✅ ALSO stored CSV in file cache: {cache_file}")
                                except Exception as e:
                                    logger.debug(f"[{job_name}] Could not store CSV in file cache: {e}")
                                
                                # 2. ALSO store in global app.py storage (bypasses import issues)
                                try:
                                    import sys
                                    # Try multiple module names (app.py might be loaded as 'app' or '__main__')
                                    app_module = None
                                    for module_name in ['app', '__main__']:
                                        if module_name in sys.modules:
                                            try:
                                                candidate = sys.modules[module_name]
                                                if hasattr(candidate, '_GLOBAL_CSV_STORAGE'):
                                                    app_module = candidate
                                                    logger.info(f"[{job_name}] Found app module: {module_name}")
                                                    break
                                            except Exception:
                                                continue
                                    
                                    # Also try to find it by checking all modules for _GLOBAL_CSV_STORAGE
                                    if not app_module:
                                        for mod_name, mod in sys.modules.items():
                                            if mod is None:
                                                continue
                                            try:
                                                if hasattr(mod, '_GLOBAL_CSV_STORAGE'):
                                                    # CRITICAL: Check if _GLOBAL_CSV_STORAGE is actually a dict
                                                    # Some modules (like torch.ops) have this attribute but it's not a dict
                                                    storage = getattr(mod, '_GLOBAL_CSV_STORAGE')
                                                    if isinstance(storage, dict):
                                                        app_module = mod
                                                        logger.info(f"[{job_name}] Found app module via search: {mod_name}")
                                                        break
                                            except Exception:
                                                continue
                                    
                                    if app_module:
                                        try:
                                            app_module._GLOBAL_CSV_STORAGE[storage_key] = {
                                                "csv": csv_data,
                                                "filename": csv_filename,
                                                "node_name": job_name.split("_")[0] if "_" in job_name else job_name
                                            }
                                            logger.info(f"[{job_name}] ✅ ALSO stored CSV in app._GLOBAL_CSV_STORAGE[{storage_key}]")
                                        except AttributeError as ae:
                                            logger.warning(f"[{job_name}] ⚠️ _GLOBAL_CSV_STORAGE attribute error: {ae}")
                                        except Exception as e:
                                            logger.warning(f"[{job_name}] ⚠️ Error storing in _GLOBAL_CSV_STORAGE: {e}")
                                    else:
                                        logger.warning(f"[{job_name}] ⚠️ Could not find app module in sys.modules (searched all modules)")
                                except Exception as e:
                                    logger.warning(f"[{job_name}] ⚠️ Could not store CSV in global storage: {e}")
                                
                                # 3. ALSO store in Chainlit session via streaming callback (if available)
                                # This bypasses import issues after Chainlit reloads
                                if streaming_callback:
                                    try:
                                        # Try to access Chainlit session via callback context
                                        # Store CSV data in callback metadata for later retrieval
                                        streaming_callback("csv_data", csv_data, {
                                            "csv": csv_data,
                                            "filename": csv_filename,
                                            "storage_key": storage_key,
                                            "node_name": job_name.split("_")[0] if "_" in job_name else job_name
                                        })
                                    except Exception as e:
                                        logger.debug(f"Could not store CSV via callback: {e}")
                        except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
                            # Not JSON or doesn't contain CSV - use result as-is
                            pass
                        
                        tool_calls.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result_text,  # Text result for LLM processing
                            "csv": csv_data,  # CSV data for file download (if available)
                            "csv_filename": csv_filename  # Filename for CSV (if available)
                        })

                        # Emit tool result for visibility
                        if streaming_callback:
                            try:
                                streaming_callback("tool_result", result_text, {
                                    "tool": tool_name,
                                    "result": result_text,
                                    "csv": csv_data,
                                    "csv_filename": csv_filename
                                })
                            except Exception:
                                pass  # Don't fail if callback errors

                        # Add tool result message for next iteration (use text result for LLM)
                        messages.append(ToolMessage(content=result_text, tool_call_id=tool_call_id))
                    except Exception as e:
                        # 🔍 TRAP LOGGING: Full stack trace dump
                        print("=" * 80)
                        print("🔍 FULL STACK TRACE - TOOL EXECUTION ERROR:")
                        print("=" * 80)
                        traceback.print_exc()  # FORCE PRINT TO CONSOLE
                        print("=" * 80)
                        
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        tool_calls.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "error": str(e)
                        })
                        messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "error": error_msg
                    })
                    messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))

            iteration += 1
            continue  # Loop again to get LLM response with tool results
        elif has_content:
            # We have content but no tool calls - this is the final response
            break
        else:
            # No tool calls and no content - try to get a response
            try:
                messages.append(HumanMessage(content="Please provide your answer based on the tool results above."))
                final_result = llm_with_tools.invoke(messages)
                if _safe_extract_content(final_result):
                    result = final_result
                    break
            except Exception:
                pass
            break

    # If we hit max iterations, try to get a final response anyway
    if iteration >= max_iterations and not _safe_extract_content(result):
        try:
            final_result = llm_with_tools.invoke(messages)
            if _safe_extract_content(final_result):
                result = final_result
        except Exception:
            pass

    # Format final response (if not already set from streaming)
    if not response_text:
        if result is None:
            response_text = "I apologize, but I didn't receive a response. Please try rephrasing your query."
        else:
            content_str = _safe_extract_content(result)
            response_text = content_str if content_str else "I apologize, but I received an empty response. Please try rephrasing your query."

    # Ensure we have a non-empty response
    # If we have tool results but no final response, use the last tool result
    if not response_text or response_text.strip() == "":
        if tool_calls and len(tool_calls) > 0:
            # Use the last successful tool result as the response
            last_tool_call = tool_calls[-1]
            if 'result' in last_tool_call and last_tool_call['result']:
                response_text = str(last_tool_call['result'])
            elif 'error' not in last_tool_call:
                response_text = "I apologize, but I didn't receive a meaningful response. Please try rephrasing your query or check if the database contains the requested information."
            else:
                response_text = "I apologize, but I didn't receive a meaningful response. Please try rephrasing your query or check if the database contains the requested information."
        else:
            response_text = "I apologize, but I didn't receive a meaningful response. Please try rephrasing your query or check if the database contains the requested information."

    # Parse tool results data for conversation history
    tool_results_data = _parse_tool_results_for_history(tool_calls)

    return {
        "response": response_text,
        "tool_calls": tool_calls,
        "tool_results_data": tool_results_data
    }


def _normalize_tool_args(tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Robustly normalizes arguments before Pydantic validation.
    
    Handles deep nesting: [['17']] -> '17'.
    
    LangChain's StructuredTool validates arguments via Pydantic before calling the function.
    When LLM passes lists (e.g., account_id: ["17"] or [['17']]) instead of strings, 
    Pydantic's internal validation calls .strip() on the list, causing: 
    'list' object has no attribute 'strip'
    
    This function normalizes arguments BEFORE Pydantic validation occurs, preventing crashes.
    
    Args:
        tool_args: Dictionary of tool arguments (may contain nested lists)
        
    Returns:
        Normalized dictionary with all lists recursively unwrapped to primitives
    """
    def unwrap(val: Any) -> Any:
        """Recursively unwrap nested lists until we hit a primitive value."""
        if isinstance(val, list):
            return unwrap(val[0]) if len(val) > 0 else None
        return val
    
    normalized = {}
    for key, value in tool_args.items():
        # 1. Unwrap recursively until we hit a primitive
        unwrapped = unwrap(value)
        
        # 2. Handle types safely
        if unwrapped is None:
            normalized[key] = None
        elif isinstance(unwrapped, (str, int, float, bool)):
            normalized[key] = unwrapped
        else:
            # Fallback for complex objects -> string
            normalized[key] = str(unwrapped)
    
    return normalized


def _extract_tool_call_info(tool_call: Any, job_name: str) -> tuple[str, dict[str, Any], str]:
    """
    Extract tool name, args, and call ID from various tool call formats.

    Handles different formats from OpenAI, Anthropic, Gemini, and LangChain.

    Args:
        tool_call: Tool call object (dict or object)
        job_name: Job name to inject into tool args

    Returns:
        Tuple of (tool_name, tool_args, tool_call_id)
    """
    if isinstance(tool_call, dict):
        tool_name = tool_call.get('name', '') or tool_call.get('id', '')
        tool_args = tool_call.get('args', {}) or tool_call.get('parameters', {})
        tool_call_id = tool_call.get('id', tool_name)
    else:
        # Handle LangChain tool call objects
        tool_name = getattr(tool_call, 'name', '') or getattr(tool_call, 'id', '')
        tool_call_id = getattr(tool_call, 'id', None) or tool_name

        # Try different attribute names for args
        tool_args = {}
        if hasattr(tool_call, 'args'):
            tool_args = tool_call.args if isinstance(tool_call.args, dict) else {}
        elif hasattr(tool_call, 'parameters'):
            tool_args = tool_call.parameters if isinstance(tool_call.parameters, dict) else {}
        elif hasattr(tool_call, 'kwargs'):
            tool_args = tool_call.kwargs if isinstance(tool_call.kwargs, dict) else {}
        # If it's a dict-like object, try to convert
        if hasattr(tool_call, '__dict__'):
            tool_args = tool_call.__dict__.get('args', tool_args)

    # Ensure job_name is included in tool args ONLY if the tool accepts it
    # Not all tools need job_name (e.g., echo_tool, canary tools)
    if not isinstance(tool_args, dict):
        tool_args = {}
    
    # Only inject job_name if it's not already present
    # Tools that don't accept job_name will have it filtered out during normalization
    if 'job_name' not in tool_args:
        tool_args['job_name'] = job_name

    return tool_name, tool_args, tool_call_id


def _parse_tool_results_for_history(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """
    Parse tool results for conversation history storage.

    Extracts actual data (entities/entity) from tool results to enable
    follow-up questions without re-querying.

    Args:
        tool_calls: List of tool call results

    Returns:
        List of parsed tool results data or None
    """
    if not tool_calls:
        return None

    results_data = []
    for tc in tool_calls:
        if 'error' not in tc:
            tool_name = tc.get('tool', 'unknown')
            result = tc.get('result', '')
            # Parse JSON result to extract actual data (not just metadata)
            try:
                result_data = json.loads(result) if isinstance(result, str) else result
                # Store the actual entities/entity data for reuse
                if 'entities' in result_data:
                    entities = result_data['entities']
                    # Store entities data (limit to prevent token bloat)
                    if isinstance(entities, list) and len(entities) <= 10:
                        results_data.append({
                            'tool': tool_name,
                            'data': {'entities': entities}
                        })
                    else:
                        # Too many entities, just store summary
                        entity_count = len(entities) if isinstance(entities, list) else 0
                        fields = result_data.get('query_metadata', {}).get('fields_requested', [])
                        results_data.append({
                            'tool': tool_name,
                            'summary': f"Retrieved {entity_count} entities with fields {fields}"
                        })
                elif 'entity' in result_data:
                    # Store single entity data
                    results_data.append({
                        'tool': tool_name,
                        'data': {'entity': result_data['entity']}
                    })
            except Exception:
                pass

    return results_data if results_data else None

