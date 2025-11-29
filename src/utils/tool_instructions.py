"""
Tool Instructions Utilities

Provides utilities for:
1. Building toolkit references from tool schemas (for system prompts)
2. Loading execution instructions from markdown files (for runtime injection)
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)


def build_toolkit_reference(tools: List[StructuredTool]) -> str:
    """
    Build toolkit reference for system prompt from available tools.
    
    Generates a reference document with:
    - Tool name and purpose
    - Input schema (from Pydantic model)
    - Output schema description
    - General use cases
    
    Args:
        tools: List of StructuredTool instances
        
    Returns:
        Formatted toolkit reference string
    """
    if not tools:
        return ""
    
    toolkit_parts = ["## AVAILABLE TOOLS\n"]
    
    for tool in tools:
        tool_name = tool.name
        tool_description = tool.description or "Tool for analysis"
        
        # Extract purpose (first sentence)
        purpose = tool_description.split('.')[0] if '.' in tool_description else tool_description.split('\n')[0]
        
        # Extract input schema from args_schema
        input_schema_parts = []
        if hasattr(tool, 'args_schema') and tool.args_schema:
            args_schema = tool.args_schema
            if hasattr(args_schema, 'model_fields'):
                for field_name, field_info in args_schema.model_fields.items():
                    # Get field type
                    field_type = str(field_info.annotation)
                    # Simplify type name
                    if 'Optional' in field_type:
                        field_type = field_type.replace('Optional[', '').replace(']', '') + ' (optional)'
                    elif 'Union' in field_type:
                        field_type = field_type.split(',')[0].replace('Union[', '').replace(']', '')
                    
                    # Get default value
                    default = field_info.default
                    if default == ...:
                        default_str = "required"
                    elif default is None:
                        default_str = "None (optional)"
                    else:
                        default_str = f'"{default}"'
                    
                    # Get description
                    description = field_info.description or ""
                    
                    input_schema_parts.append(
                        f"- **{field_name}** ({field_type}, default: {default_str}): {description}"
                    )
        
        # Build tool entry
        toolkit_parts.append(f"### {tool_name}")
        toolkit_parts.append(f"**Purpose**: {purpose}")
        toolkit_parts.append("")
        toolkit_parts.append("**Input Schema**:")
        if input_schema_parts:
            toolkit_parts.extend(input_schema_parts)
        else:
            toolkit_parts.append("- No parameters required")
        toolkit_parts.append("")
        toolkit_parts.append("**Output Schema**:")
        toolkit_parts.append("Returns JSON with analysis results and insights.")
        toolkit_parts.append("")
        toolkit_parts.append("**Use When**:")
        # Extract use cases from description
        if "Use this tool when" in tool_description:
            use_cases_section = tool_description.split("Use this tool when")[1].split("Returns")[0].strip()
            toolkit_parts.append(use_cases_section)
        else:
            toolkit_parts.append("- Analysis requests related to this tool's domain")
        toolkit_parts.append("")
    
    return "\n".join(toolkit_parts)


def load_execution_instructions(
    tool_name: str,
    question: str,
    tool_args: Dict[str, Any],
    conversation_history: Optional[List[Dict]] = None,
    project_root: Optional[Path] = None
) -> Optional[str]:
    """
    Load and process execution instructions from markdown file.
    
    Looks for execution instructions in:
    1. tools/{tool_name}/execution_instructions.md
    2. src/tools/{tool_name}/execution_instructions.md
    3. tools/campaign-portfolio-pacing/execution_instructions.md (for portfolio pacing)
    
    Args:
        tool_name: Name of the tool
        question: Current user question
        tool_args: Arguments being passed to the tool
        conversation_history: Recent conversation history
        project_root: Root directory of the project (auto-detected if None)
        
    Returns:
        Processed execution instructions string, or None if not found
    """
    if project_root is None:
        # Auto-detect project root (go up from src/utils)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
    
    # Map tool names to possible file paths
    tool_path_mappings = {
        'analyze_portfolio_pacing': [
            project_root / 'tools' / 'campaign-portfolio-pacing' / 'execution_instructions.md',
            project_root / 'src' / 'tools' / 'portfolio_pacing_tool' / 'execution_instructions.md',
        ],
        # Add more mappings as needed
    }
    
    # Try tool-specific paths first
    possible_paths = tool_path_mappings.get(tool_name, [])
    
    # Add generic paths
    possible_paths.extend([
        project_root / 'tools' / tool_name / 'execution_instructions.md',
        project_root / 'src' / 'tools' / tool_name / 'execution_instructions.md',
    ])
    
    for path in possible_paths:
        if path.exists():
            try:
                content = path.read_text()
                
                # Process template variables
                content = content.replace("{question}", question)
                content = content.replace("{tool_name}", tool_name)
                
                # Replace tool args
                for arg_name, arg_value in tool_args.items():
                    content = content.replace(f"{{{arg_name}}}", str(arg_value))
                
                # Extract relevant sections based on question keywords
                question_lower = question.lower()
                relevant_sections = []
                
                # Parse markdown sections (simple approach)
                lines = content.split('\n')
                current_section = []
                in_relevant_section = False
                
                for line in lines:
                    # Check if this is a section header
                    if line.startswith('###'):
                        # Check if section is relevant to question
                        section_lower = line.lower()
                        keywords_in_section = ['trend', 'risk', 'calculate', 'average', 'pacing', 'budget']
                        if any(kw in question_lower and kw in section_lower for kw in keywords_in_section):
                            in_relevant_section = True
                            if current_section:
                                relevant_sections.extend(current_section)
                            current_section = [line]
                        else:
                            in_relevant_section = False
                            if current_section:
                                relevant_sections.extend(current_section)
                            current_section = []
                    elif in_relevant_section or not line.startswith('#'):
                        current_section.append(line)
                
                # Add remaining section
                if current_section:
                    relevant_sections.extend(current_section)
                
                # If we found relevant sections, use them; otherwise use full content
                if relevant_sections:
                    return '\n'.join(relevant_sections)
                else:
                    return content
                    
            except Exception as e:
                logger.debug(f"Failed to load execution instructions from {path}: {e}")
                continue
    
    return None

