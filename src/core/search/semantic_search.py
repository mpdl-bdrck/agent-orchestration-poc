"""
Standalone semantic search functions for knowledge base queries.

Provides hybrid search capabilities combining keyword and semantic similarity
for querying knowledge base content.
"""

import logging
from typing import Any

from sqlalchemy import text, func

from ..database.session import get_db_session
from ..database.models import KnowledgeChunk

logger = logging.getLogger(__name__)


def search_knowledge_base(
    query_text: str = None,
    query_embedding: list[float] = None,
    chunk_types: list[str] | None = None,
    match_limit: int = 5,
    context_id: str = None  # Knowledge base context identifier
) -> list[dict[str, Any]]:
    """
    Perform hybrid search on knowledge base chunks.

    Combines keyword search (TSVECTOR) with semantic search (pgvector)
    using Reciprocal Rank Fusion (RRF) for optimal results.

    Args:
        query_text: User's natural language query
        query_embedding: Vector embedding of the query
        chunk_types: Optional filter for specific chunk types
        match_limit: Maximum number of results to return
        context_id: Knowledge base context identifier

    Returns:
        List of matching chunks with relevance scores
    """
    # Use context-specific database session if provided
    db_session_context = get_db_session(context_id) if context_id else get_db_session()
    with db_session_context as session:
        try:
            # Ensure match_limit is an integer
            match_limit = int(match_limit) if match_limit is not None else 5

            # Validate query_embedding is provided
            if query_embedding is None:
                logger.error("query_embedding is required for semantic search")
                return []

            # Prepare chunk type filter
            chunk_type_filter = ""
            if chunk_types:
                # Create a comma-separated string for SQL IN clause
                chunk_type_list = ", ".join(f"'{ct}'" for ct in chunk_types)
                chunk_type_filter = f"AND chunk_type IN ({chunk_type_list})"

            # Convert embedding to PostgreSQL vector format
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Hybrid search query using RRF (Reciprocal Rank Fusion)
            # This combines keyword search with semantic search
            sql_query = f"""
            WITH keyword_search AS (
                SELECT
                    id,
                    chunk_type,
                    chunk_title,
                    chunk_content,
                    chunk_metadata,
                    ts_rank_cd(chunk_keywords, websearch_to_tsquery('english', :query_text)) as keyword_score,
                    ROW_NUMBER() OVER (ORDER BY ts_rank_cd(chunk_keywords, websearch_to_tsquery('english', :query_text)) DESC) as keyword_rank
                FROM knowledge_chunks
                WHERE chunk_keywords @@ websearch_to_tsquery('english', :query_text)
                  {chunk_type_filter}
                ORDER BY keyword_score DESC
                LIMIT :limit
            ),
            semantic_search AS (
                SELECT
                    id,
                    chunk_type,
                    chunk_title,
                    chunk_content,
                    chunk_metadata,
                    1 - (chunk_embedding <=> :embedding) as semantic_score,
                    ROW_NUMBER() OVER (ORDER BY chunk_embedding <=> :embedding) as semantic_rank
                FROM knowledge_chunks
                WHERE 1=1
                  {chunk_type_filter}
                ORDER BY chunk_embedding <=> :embedding
                LIMIT :limit
            ),
            combined_results AS (
                SELECT
                    COALESCE(k.id, s.id) as chunk_id,
                    COALESCE(k.chunk_type, s.chunk_type) as chunk_type,
                    COALESCE(k.chunk_title, s.chunk_title) as chunk_title,
                    COALESCE(k.chunk_content, s.chunk_content) as chunk_content,
                    COALESCE(k.chunk_metadata, s.chunk_metadata) as chunk_metadata,
                    COALESCE(k.keyword_score, 0) as keyword_score,
                    COALESCE(s.semantic_score, 0) as semantic_score,
                    COALESCE(k.keyword_rank, 0) as keyword_rank,
                    COALESCE(s.semantic_rank, 0) as semantic_rank
                FROM keyword_search k
                FULL OUTER JOIN semantic_search s ON k.id = s.id
            )
            SELECT
                chunk_id,
                chunk_type,
                chunk_title,
                chunk_content,
                chunk_metadata,
                keyword_score,
                semantic_score,
                -- RRF score: combines keyword and semantic rankings
                (COALESCE(1.0 / (60 + keyword_rank), 0.0) * 0.5 +  -- 50% weight to keyword
                 COALESCE(1.0 / (60 + semantic_rank), 0.0) * 0.5)  -- 50% weight to semantic
                as relevance_score
            FROM combined_results
            ORDER BY relevance_score DESC
            LIMIT :limit
            """

            result = session.execute(text(sql_query), {
                'query_text': query_text,
                'embedding': embedding_str,
                'limit': match_limit * 2  # Get more candidates for better ranking
            }).fetchall()

            # Format results
            chunks = []
            for row in result[:match_limit]:  # Limit final results
                chunks.append({
                    'chunk_id': row[0],
                    'chunk_type': row[1],
                    'chunk_title': row[2],
                    'chunk_content': row[3],
                    'chunk_metadata': row[4] or {},
                    'keyword_score': float(row[5]),
                    'semantic_score': float(row[6]),
                    'relevance_score': float(row[7])
                })

            logger.info(f"Hybrid search returned {len(chunks)} results")
            return chunks

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []


# Backward compatibility alias - will be removed after full migration
def search_story_outline(
    job_id: int = None,
    query_text: str = None,
    query_embedding: list[float] = None,
    chunk_types: list[str] | None = None,
    match_limit: int = 5,
    story_name: str = None
) -> list[dict[str, Any]]:
    """
    Backward compatibility alias for search_knowledge_base.
    
    Maps story_name to context_id for compatibility during migration.
    """
    return search_knowledge_base(
        query_text=query_text,
        query_embedding=query_embedding,
        chunk_types=chunk_types,
        match_limit=match_limit,
        context_id=story_name
    )


def store_knowledge_chunks(
    chunks: list[dict[str, Any]] = None,
    embeddings: list[list[float]] = None,
    append_mode: bool = True,
    context_id: str = None
) -> bool:
    """
    Store knowledge chunks with their embeddings in the database.

    Args:
        chunks: List of chunk dictionaries
        embeddings: Corresponding embeddings for each chunk
        append_mode: If True, accumulate chunks; if False, replace all chunks
        context_id: Knowledge base context identifier

    Returns:
        Success status
    """
    if len(chunks) != len(embeddings):
        logger.error(f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")
        return False

    # Use context-specific database session if provided
    logger.info(f"store_knowledge_chunks called with context_id: {context_id}")
    db_session_context = get_db_session(context_id) if context_id else get_db_session()
    logger.info(f"Using database session for: {'context_' + context_id if context_id else 'global'}")
    with db_session_context as session:
        try:
            # Only clear existing chunks if NOT in append mode
            if not append_mode:
                session.query(KnowledgeChunk).delete()
                logger.info(f"Cleared existing chunks (replace mode)")
            else:
                logger.info(f"Appending chunks (accumulation mode)")

            # Create new chunk records
            added_count = 0
            skipped_count = 0

            for chunk, embedding in zip(chunks, embeddings, strict=True):
                # Handle both chunk objects and dictionaries
                if hasattr(chunk, 'content'):
                    # Chunk object
                    content = chunk.content
                    chunk_type = chunk.chunk_type
                    title = chunk.title
                    sequence_order = chunk.sequence_order
                    metadata = chunk.metadata
                else:
                    # Dictionary - handle both 'content'/'chunk_content' and 'title'/'chunk_title' formats
                    content = chunk.get('content') or chunk.get('chunk_content', '')
                    chunk_type = chunk.get('chunk_type', '')
                    title = chunk.get('title') or chunk.get('chunk_title', '')
                    sequence_order = chunk.get('sequence_order', 0)
                    metadata = chunk.get('metadata') or chunk.get('chunk_metadata', {})

                # Skip empty chunks (no content for semantic search)
                if not content or not content.strip():
                    skipped_count += 1
                    logger.debug(f"Skipping empty chunk: {chunk_type} #{sequence_order} - {title}")
                    continue

                # Check for duplicates if appending
                if append_mode:
                    existing = session.query(KnowledgeChunk).filter_by(
                        chunk_type=chunk_type,
                        sequence_order=sequence_order
                    ).first()
                    if existing:
                        skipped_count += 1
                        logger.debug(f"Skipping duplicate chunk: {chunk_type} #{sequence_order}")
                        continue  # Skip duplicates

                # Create TSVECTOR for keyword search
                keywords = func.to_tsvector('english', content)

                db_chunk = KnowledgeChunk(
                    chunk_type=chunk_type,
                    chunk_title=title,
                    chunk_content=content,
                    chunk_embedding=embedding,  # Pass embedding list directly
                    chunk_keywords=keywords,
                    sequence_order=sequence_order,
                    chunk_metadata=metadata
                )
                session.add(db_chunk)
                added_count += 1

            session.commit()
            logger.info(f"Stored {added_count} chunks (skipped {skipped_count} duplicates) for context: {context_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store knowledge chunks: {e}")
            session.rollback()
            return False


# Backward compatibility alias
def store_outline_chunks(
    job_id: int = None,
    chunks: list[dict[str, Any]] = None,
    embeddings: list[list[float]] = None,
    append_mode: bool = True,
    story_name: str = None
) -> bool:
    """Backward compatibility alias for store_knowledge_chunks."""
    return store_knowledge_chunks(
        chunks=chunks,
        embeddings=embeddings,
        append_mode=append_mode,
        context_id=story_name
    )


def get_knowledge_chunks(context_id: str = None) -> list[dict[str, Any]]:
    """
    Retrieve all knowledge chunks.

    Args:
        context_id: Knowledge base context identifier

    Returns:
        List of chunk dictionaries
    """
    # Use context-specific database session if provided
    db_session_context = get_db_session(context_id) if context_id else get_db_session()
    with db_session_context as session:
        try:
            chunks = session.query(KnowledgeChunk).order_by(
                KnowledgeChunk.chunk_type, KnowledgeChunk.sequence_order
            ).all()

            result = []
            for chunk in chunks:
                result.append({
                    'chunk_id': chunk.id,
                    'chunk_type': chunk.chunk_type,
                    'chunk_title': chunk.chunk_title,
                    'chunk_content': chunk.chunk_content,
                    'chunk_metadata': chunk.chunk_metadata or {},
                    'sequence_order': chunk.sequence_order
                })

            logger.info(f"Retrieved {len(result)} knowledge chunks")
            return result

        except Exception as e:
            logger.error(f"Failed to retrieve knowledge chunks: {e}")
            return []


def validate_knowledge_chunks_exist(context_id: str = None) -> dict[str, Any]:
    """
    Validate that knowledge chunks exist and provide statistics.

    Args:
        context_id: Knowledge base context identifier

    Returns:
        Validation results with statistics
    """
    chunks = get_knowledge_chunks(context_id)

    if not chunks:
        return {
            'exists': False,
            'total_chunks': 0,
            'chunk_types': {},
            'error': 'No knowledge chunks found'
        }

    # Analyze chunk distribution
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk['chunk_type']
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

    return {
        'exists': True,
        'total_chunks': len(chunks),
        'chunk_types': chunk_types,
        'sequence_valid': _validate_sequence_order(chunks)
    }


# Backward compatibility aliases
def get_outline_chunks_for_job(job_id: int = None, story_name: str = None) -> list[dict[str, Any]]:
    """Backward compatibility alias for get_knowledge_chunks."""
    return get_knowledge_chunks(context_id=story_name)


def validate_outline_chunks_exist(job_id: int = None, story_name: str = None) -> dict[str, Any]:
    """Backward compatibility alias for validate_knowledge_chunks_exist."""
    return validate_knowledge_chunks_exist(context_id=story_name)


def _validate_sequence_order(chunks: list[dict[str, Any]]) -> bool:
    """Validate that sequence ordering is correct within each chunk type."""
    type_sequences = {}

    # Group by chunk type
    for chunk in chunks:
        chunk_type = chunk['chunk_type']
        if chunk_type not in type_sequences:
            type_sequences[chunk_type] = []
        type_sequences[chunk_type].append(chunk['sequence_order'])

    # Check each type has consecutive sequences starting from 1
    for chunk_type, sequences in type_sequences.items():
        sequences.sort()
        expected = list(range(1, len(sequences) + 1))
        if sequences != expected:
            logger.warning(f"Invalid sequence for {chunk_type}: {sequences} != {expected}")
            return False

    return True

