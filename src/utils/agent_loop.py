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
from typing import Any, Optional, List, Dict
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool


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

        # Check if LLM has content (final response)
        has_content = hasattr(result, 'content') and result.content and result.content.strip()

        # Check if LLM wants to use tools
        has_tool_calls = hasattr(result, 'tool_calls') and result.tool_calls

        # If we have content and no tool calls, this is the final response
        if has_content and not has_tool_calls:
            response_text = result.content
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
                        tool_result = tool_func.invoke(tool_args)
                        tool_calls.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": tool_result
                        })

                        # Add tool result message for next iteration
                        messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call_id))
                    except Exception as e:
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
                if hasattr(final_result, 'content') and final_result.content:
                    result = final_result
                    break
            except Exception:
                pass
            break

    # If we hit max iterations, try to get a final response anyway
    if iteration >= max_iterations and (not hasattr(result, 'content') or not result.content):
        try:
            final_result = llm_with_tools.invoke(messages)
            if hasattr(final_result, 'content') and final_result.content:
                result = final_result
        except Exception:
            pass

    # Format final response (if not already set from streaming)
    if not response_text:
        if result is None:
            response_text = "I apologize, but I didn't receive a response. Please try rephrasing your query."
        elif hasattr(result, 'content'):
            response_text = result.content if result.content else "I apologize, but I received an empty response. Please try rephrasing your query."
        else:
            response_text = str(result) if result else "I apologize, but I received an empty response. Please try rephrasing your query."

    # Ensure we have a non-empty response
    if not response_text or response_text.strip() == "":
        response_text = "I apologize, but I didn't receive a meaningful response. Please try rephrasing your query or check if the database contains the requested information."

    # Parse tool results data for conversation history
    tool_results_data = _parse_tool_results_for_history(tool_calls)

    return {
        "response": response_text,
        "tool_calls": tool_calls,
        "tool_results_data": tool_results_data
    }


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

    # Ensure job_name is always included in tool args
    if not isinstance(tool_args, dict):
        tool_args = {}
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

