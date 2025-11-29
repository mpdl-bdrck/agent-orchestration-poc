"""Markdown parser for knowledge base ingestion."""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

try:
    import frontmatter
    FRONTMATTER_AVAILABLE = True
except ImportError:
    FRONTMATTER_AVAILABLE = False
    logging.warning("python-frontmatter not available, frontmatter parsing disabled")

logger = logging.getLogger(__name__)


def parse_markdown(file_path: str) -> Dict[str, any]:
    """
    Parse a Markdown file and extract content and metadata.
    
    Args:
        file_path: Path to the Markdown file
        
    Returns:
        Dictionary with 'content', 'frontmatter', 'title', and 'path' keys
    """
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    # Extract frontmatter if available
    frontmatter_data = {}
    content = raw_content
    
    if FRONTMATTER_AVAILABLE:
        try:
            post = frontmatter.loads(raw_content)
            frontmatter_data = post.metadata if hasattr(post, 'metadata') else {}
            content = post.content if hasattr(post, 'content') else raw_content
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter from {file_path}: {e}")
            # Continue without frontmatter
    
    # Extract title from first heading or filename
    title = _extract_title(content, file_path_obj)
    
    return {
        'content': content,
        'frontmatter': frontmatter_data,
        'title': title,
        'path': str(file_path),
        'filename': file_path_obj.name,
        'file_stem': file_path_obj.stem
    }


def _extract_title(content: str, file_path: Path) -> str:
    """
    Extract title from Markdown content or filename.
    
    Tries:
    1. First H1 heading (# Title)
    2. First H2 heading (## Title)
    3. Filename (without extension)
    """
    # Try to find first H1
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    
    # Try to find first H2
    h2_match = re.search(r'^##\s+(.+)$', content, re.MULTILINE)
    if h2_match:
        return h2_match.group(1).strip()
    
    # Fallback to filename
    return file_path.stem.replace('_', ' ').replace('-', ' ').title()


def split_into_sections(content: str) -> list[Dict[str, str]]:
    """
    Split Markdown content into sections based on headings.
    
    Args:
        content: Markdown content
        
    Returns:
        List of sections with 'heading', 'level', and 'content' keys
    """
    sections = []
    current_section = {'heading': 'Introduction', 'level': 0, 'content': ''}
    
    lines = content.split('\n')
    
    for line in lines:
        # Check for heading
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            # Save previous section if it has content
            if current_section['content'].strip():
                sections.append(current_section.copy())
            
            # Start new section
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            current_section = {
                'heading': heading,
                'level': level,
                'content': ''
            }
        else:
            current_section['content'] += line + '\n'
    
    # Add final section
    if current_section['content'].strip():
        sections.append(current_section)
    
    return sections

