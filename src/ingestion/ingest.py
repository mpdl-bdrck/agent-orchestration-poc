"""Main ingestion script for knowledge base."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from .chunk_generator import ChunkGenerator
from ..core.search.semantic_search import store_knowledge_chunks
from ..core.database.session import init_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_markdown_files(kb_path: str) -> List[str]:
    """Find all Markdown files in knowledge base directory."""
    kb_path_obj = Path(kb_path)
    
    if not kb_path_obj.exists():
        raise FileNotFoundError(f"Knowledge base path not found: {kb_path}")
    
    markdown_files = []
    for md_file in kb_path_obj.rglob('*.md'):
        markdown_files.append(str(md_file))
    
    logger.info(f"Found {len(markdown_files)} Markdown files")
    return sorted(markdown_files)


def ingest_knowledge_base(
    kb_path: str,
    context_id: str = None,
    dry_run: bool = False,
    chunk_by_sections: bool = True,
    append_mode: bool = False
) -> dict:
    """
    Ingest knowledge base from Markdown files.
    
    Args:
        kb_path: Path to knowledge base directory
        context_id: Knowledge base context identifier
        dry_run: If True, don't write to database
        chunk_by_sections: If True, chunk by sections; if False, by size
        append_mode: If True, append chunks; if False, replace
        
    Returns:
        Dictionary with ingestion statistics
    """
    logger.info(f"Starting ingestion of knowledge base: {kb_path}")
    
    if dry_run:
        logger.info("DRY RUN MODE - No database writes will be performed")
    
    # Initialize database
    if not dry_run:
        init_database(context_id)
        logger.info(f"Database initialized for context: {context_id or 'default'}")
    
    # Find all Markdown files
    markdown_files = find_markdown_files(kb_path)
    
    if not markdown_files:
        logger.warning("No Markdown files found in knowledge base")
        return {
            'files_processed': 0,
            'chunks_generated': 0,
            'success': False,
            'error': 'No Markdown files found'
        }
    
    # Initialize chunk generator
    chunk_generator = ChunkGenerator()
    
    # Process files
    all_chunks = []
    all_embeddings = []
    files_processed = 0
    files_failed = 0
    
    for file_path in markdown_files:
        try:
            logger.info(f"Processing: {file_path}")
            chunks = chunk_generator.process_file(
                file_path=file_path,
                base_path=kb_path,
                chunk_by_sections=chunk_by_sections
            )
            
            if chunks:
                all_chunks.extend(chunks)
                all_embeddings.extend([chunk['chunk_embedding'] for chunk in chunks])
                files_processed += 1
                logger.info(f"  Generated {len(chunks)} chunks")
            else:
                logger.warning(f"  No chunks generated from {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            files_failed += 1
            continue
    
    logger.info(f"Processed {files_processed} files, {files_failed} failed")
    logger.info(f"Total chunks generated: {len(all_chunks)}")
    
    # Store chunks in database
    if not dry_run and all_chunks:
        try:
            success = store_knowledge_chunks(
                chunks=all_chunks,
                embeddings=all_embeddings,
                append_mode=append_mode,
                context_id=context_id
            )
            
            if success:
                logger.info(f"Successfully stored {len(all_chunks)} chunks in database")
            else:
                logger.error("Failed to store chunks in database")
                return {
                    'files_processed': files_processed,
                    'chunks_generated': len(all_chunks),
                    'chunks_stored': 0,
                    'success': False,
                    'error': 'Failed to store chunks'
                }
        except Exception as e:
            logger.error(f"Error storing chunks: {e}")
            return {
                'files_processed': files_processed,
                'chunks_generated': len(all_chunks),
                'chunks_stored': 0,
                'success': False,
                'error': str(e)
            }
    
    return {
        'files_processed': files_processed,
        'files_failed': files_failed,
        'chunks_generated': len(all_chunks),
        'chunks_stored': len(all_chunks) if not dry_run else 0,
        'success': True
    }


def main():
    """CLI entry point for ingestion."""
    parser = argparse.ArgumentParser(
        description='Ingest Markdown knowledge base into vector database'
    )
    parser.add_argument(
        '--kb-path',
        type=str,
        required=True,
        help='Path to knowledge base directory (Markdown files)'
    )
    parser.add_argument(
        '--context-id',
        type=str,
        default=None,
        help='Knowledge base context identifier (for multi-context databases)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - process files but do not write to database'
    )
    parser.add_argument(
        '--chunk-by-size',
        action='store_true',
        help='Chunk by fixed size instead of by sections'
    )
    parser.add_argument(
        '--append',
        action='store_true',
        help='Append chunks instead of replacing existing chunks'
    )
    
    args = parser.parse_args()
    
    try:
        result = ingest_knowledge_base(
            kb_path=args.kb_path,
            context_id=args.context_id,
            dry_run=args.dry_run,
            chunk_by_sections=not args.chunk_by_size,
            append_mode=args.append
        )
        
        if result['success']:
            print(f"\n✅ Ingestion complete!")
            print(f"   Files processed: {result['files_processed']}")
            print(f"   Chunks generated: {result['chunks_generated']}")
            if not args.dry_run:
                print(f"   Chunks stored: {result['chunks_stored']}")
            sys.exit(0)
        else:
            print(f"\n❌ Ingestion failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.exception("Ingestion failed with exception")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

