"""Metadata extractor for knowledge base files."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def extract_metadata(file_path: str, base_path: str = None) -> Dict[str, any]:
    """
    Extract metadata from file path and folder structure.
    
    Args:
        file_path: Full path to the file
        base_path: Base path of knowledge base (for relative path calculation)
        
    Returns:
        Dictionary with metadata including category, tags, source_file, etc.
    """
    file_path_obj = Path(file_path)
    
    # Get relative path from base
    if base_path:
        try:
            rel_path = Path(file_path).relative_to(Path(base_path))
            path_parts = rel_path.parts[:-1]  # Exclude filename
        except ValueError:
            # File not under base_path
            path_parts = file_path_obj.parts[:-1]
    else:
        path_parts = file_path_obj.parts[:-1]
    
    # Extract category from first folder level
    category = path_parts[0] if path_parts else 'uncategorized'
    
    # Generate tags from folder structure
    tags = list(path_parts) if path_parts else []
    
    # Extract additional metadata from filename
    filename_metadata = _extract_filename_metadata(file_path_obj.stem)
    
    metadata = {
        'category': category,
        'tags': tags,
        'source_file': str(file_path),
        'filename': file_path_obj.name,
        'file_stem': file_path_obj.stem,
        'folder_path': '/'.join(path_parts) if path_parts else '',
        **filename_metadata
    }
    
    return metadata


def _extract_filename_metadata(filename_stem: str) -> Dict[str, any]:
    """
    Extract metadata from filename patterns.
    
    Common patterns:
    - date_prefix: 2024-01-15_document.md
    - numbered: 01_introduction.md
    - versioned: document_v2.md
    """
    metadata = {}
    
    # Check for date prefix (YYYY-MM-DD or YYYY_MM_DD)
    date_match = re.match(r'^(\d{4}[-_]\d{2}[-_]\d{2})[-_]?(.+)$', filename_stem)
    if date_match:
        metadata['date'] = date_match.group(1).replace('_', '-')
        metadata['title_part'] = date_match.group(2)
    
    # Check for numbered prefix (01_, 02_, etc.)
    numbered_match = re.match(r'^(\d+)[-_]?(.+)$', filename_stem)
    if numbered_match and not metadata.get('date'):
        metadata['order'] = int(numbered_match.group(1))
        metadata['title_part'] = numbered_match.group(2)
    
    # Check for version suffix (_v2, -v2, etc.)
    version_match = re.search(r'[-_]v(\d+)$', filename_stem)
    if version_match:
        metadata['version'] = int(version_match.group(1))
    
    return metadata


def generate_chunk_metadata(
    chunk_index: int,
    file_metadata: Dict[str, any],
    section_heading: Optional[str] = None
) -> Dict[str, any]:
    """
    Generate metadata for a specific chunk.
    
    Args:
        chunk_index: Index of chunk within file
        file_metadata: Metadata from file
        section_heading: Optional section heading
        
    Returns:
        Chunk-specific metadata
    """
    chunk_metadata = {
        'chunk_index': chunk_index,
        'source_file': file_metadata['source_file'],
        'category': file_metadata['category'],
        'tags': file_metadata['tags'],
    }
    
    if section_heading:
        chunk_metadata['section_heading'] = section_heading
    
    # Copy relevant file metadata
    if 'date' in file_metadata:
        chunk_metadata['date'] = file_metadata['date']
    if 'version' in file_metadata:
        chunk_metadata['version'] = file_metadata['version']
    
    return chunk_metadata

