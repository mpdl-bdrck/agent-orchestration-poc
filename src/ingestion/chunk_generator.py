"""Chunk generator for knowledge base ingestion."""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from sentence_transformers import SentenceTransformer

from .markdown_parser import parse_markdown, split_into_sections
from .metadata_extractor import extract_metadata, generate_chunk_metadata

logger = logging.getLogger(__name__)


class ChunkGenerator:
    """Generate chunks from Markdown files with embeddings."""
    
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        max_chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        """
        Initialize chunk generator.
        
        Args:
            embedding_model_name: Name of sentence-transformers model
            max_chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum characters per chunk
        """
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        logger.info(f"Initialized ChunkGenerator with model: {embedding_model_name}")
    
    def process_file(
        self,
        file_path: str,
        base_path: str = None,
        chunk_by_sections: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process a Markdown file and generate chunks.
        
        Args:
            file_path: Path to Markdown file
            base_path: Base path of knowledge base
            chunk_by_sections: If True, chunk by sections; if False, chunk by size
            
        Returns:
            List of chunk dictionaries with content, metadata, and embeddings
        """
        # Parse Markdown
        parsed = parse_markdown(file_path)
        content = parsed['content']
        file_metadata = extract_metadata(file_path, base_path)
        
        # Merge frontmatter into file metadata
        if parsed.get('frontmatter'):
            file_metadata.update(parsed['frontmatter'])
        
        # Generate chunks
        if chunk_by_sections:
            chunks = self._chunk_by_sections(content, file_metadata, parsed.get('title'))
        else:
            chunks = self._chunk_by_size(content, file_metadata, parsed.get('title'))
        
        # Generate embeddings
        chunk_texts = [chunk['chunk_content'] for chunk in chunks]
        embeddings = self.embedding_model.encode(chunk_texts, show_progress_bar=False)
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk['chunk_embedding'] = embeddings[i].tolist()
        
        logger.info(f"Generated {len(chunks)} chunks from {file_path}")
        return chunks
    
    def _chunk_by_sections(
        self,
        content: str,
        file_metadata: Dict[str, Any],
        file_title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Chunk content by Markdown sections."""
        sections = split_into_sections(content)
        chunks = []
        
        for i, section in enumerate(sections):
            section_content = section['content'].strip()
            
            # Skip empty sections
            if len(section_content) < self.min_chunk_size:
                continue
            
            # If section is too large, split it further
            if len(section_content) > self.max_chunk_size:
                sub_chunks = self._split_large_section(
                    content=section_content,
                    section_heading=section['heading'],
                    file_metadata=file_metadata,
                    file_title=file_title,
                    base_index=len(chunks)
                )
                chunks.extend(sub_chunks)
            else:
                # Create chunk from section
                chunk_metadata = generate_chunk_metadata(
                    chunk_index=i,
                    file_metadata=file_metadata,
                    section_heading=section['heading']
                )
                
                chunk = {
                    'chunk_type': 'section',
                    'chunk_title': f"{file_title or file_metadata['filename']}: {section['heading']}",
                    'chunk_content': section_content,
                    'chunk_metadata': chunk_metadata,
                    'sequence_order': i + 1
                }
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_size(
        self,
        content: str,
        file_metadata: Dict[str, Any],
        file_title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Chunk content by fixed size with overlap."""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = start + self.max_chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence endings
                for i in range(end, max(start + self.min_chunk_size, end - 100), -1):
                    if content[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk_content = content[start:end].strip()
            
            if len(chunk_content) >= self.min_chunk_size:
                chunk_metadata = generate_chunk_metadata(
                    chunk_index=chunk_index,
                    file_metadata=file_metadata
                )
                
                chunk = {
                    'chunk_type': 'document',
                    'chunk_title': f"{file_title or file_metadata['filename']} (part {chunk_index + 1})",
                    'chunk_content': chunk_content,
                    'chunk_metadata': chunk_metadata,
                    'sequence_order': chunk_index + 1
                }
                chunks.append(chunk)
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    def _split_large_section(
        self,
        content: str,
        section_heading: str,
        file_metadata: Dict[str, Any] = None,
        file_title: Optional[str] = None,
        base_index: int = 0
    ) -> List[Dict[str, Any]]:
        """Split a large section into smaller chunks."""
        # Simple splitting by paragraphs
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunk_content = '\n\n'.join(current_chunk)
                chunk_metadata = generate_chunk_metadata(
                    chunk_index=base_index + chunk_index,
                    file_metadata=file_metadata or {},
                    section_heading=section_heading
                )
                
                chunks.append({
                    'chunk_type': 'section',
                    'chunk_title': f"{file_title or 'Document'}: {section_heading} (part {chunk_index + 1})",
                    'chunk_content': chunk_content,
                    'chunk_metadata': chunk_metadata,
                    'sequence_order': base_index + chunk_index + 1
                })
                current_chunk = [para]
                current_size = para_size
                chunk_index += 1
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for '\n\n'
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunk_metadata = generate_chunk_metadata(
                chunk_index=base_index + chunk_index,
                file_metadata=file_metadata or {},
                section_heading=section_heading
            )
            
            chunks.append({
                'chunk_type': 'section',
                'chunk_title': f"{file_title or 'Document'}: {section_heading} (part {chunk_index + 1})",
                'chunk_content': chunk_content,
                'chunk_metadata': chunk_metadata,
                'sequence_order': base_index + chunk_index + 1
            })
        
        return chunks

