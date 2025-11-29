"""
Database models for Eternal Ink Suite
PostgreSQL integration with static models validated by YAML schema
"""

from sqlalchemy import Column, Integer, String, Text, JSON, TIMESTAMP, ForeignKey, Float, UniqueConstraint, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector

Base = declarative_base()

# ===========================================
# DATABASE MODELS - STATIC WITH SCHEMA VALIDATION
# ===========================================

class Character(Base):
    """Story Bible-compliant character entities table"""
    __tablename__ = 'characters'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String(255), nullable=False, unique=True)
    canonical_name = Column(String(255), nullable=False)  # Story Bible: primary identifier
    
    # Story Bible fields
    aliases = Column(JSONB, default={})  # Structured dict: alias → who uses it
    introduction_beat = Column(Integer, ForeignKey('beats.beat_number'), nullable=True)
    introduction_text = Column(Text)
    knowledge_states = Column(JSONB, default={})  # Beat-by-beat knowledge tracking summary (beat_number → {knows, suspects, ignorant_of})
    locked_attributes = Column(JSONB, default={})  # Attributes that MUST NOT be contradicted

    # Character-specific fields (legacy fields removed - not in Story Bible format)

    # Enrichment data (preserved from existing schema)
    big_five_profile = Column(String(255))
    big_five_scores = Column(String(255))
    jungian_archetype = Column(String(255))
    enneagram_type = Column(String(255))
    psychological_analysis = Column(Text)
    voice_profile = Column(JSONB)  # Consolidated voice data: dialogue_style + voice_style (ElevenLabs prompts and characteristics)
    visual_description = Column(Text)  # Clean visual description for image generation (markdown text without citations)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    introduction_beat_rel = relationship("Beat", foreign_keys=[introduction_beat], backref="characters_introduced")
    knowledge_states_rel = relationship("CharacterKnowledgeState", back_populates="character", cascade="all, delete-orphan")
    # Note: knowledge_states JSONB column is NOT a relationship - use knowledge_states_rel for relationship access


class Setting(Base):
    """Story Bible-compliant setting/location entities table"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String(255), nullable=False, unique=True)
    canonical_name = Column(String(255), nullable=False)  # Story Bible: primary identifier
    
    # Story Bible fields
    aliases = Column(JSONB, default={})  # Structured dict: alias → who uses it
    locked_features = Column(JSONB, default={})  # Physical attributes that MUST NOT be contradicted
    beats_here = Column(JSONB, default=[])  # Array of beat_numbers where location appears

    # Setting-specific fields
    type = Column(String(255))
    parent_location = Column(String(255))
    associated_characters = Column(JSONB)

    # Enrichment data (preserved from existing schema)
    atmospheric_profile = Column(JSONB, default={})  # Consolidated prose descriptions: sensory_signature, environmental_psychology, genius_loci, atmospheric_integration

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Object(Base):
    """Story Bible-compliant object entities table"""
    __tablename__ = 'objects'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String(255), nullable=False, unique=True)
    canonical_description = Column(Text, nullable=False)  # Story Bible: primary identifier (exact physical description)
    
    # Story Bible fields
    locked_attributes = Column(JSONB, default={})  # Attributes that MUST NOT be contradicted
    location_history = Column(JSONB, default={})  # Beat-by-beat location tracking: beat_number → location mapping
    introduction_beat = Column(Integer, ForeignKey('beats.beat_number'), nullable=True)

    # Object-specific fields (minimal - focus on Story Bible compliance)
    name = Column(String(255))  # Short name for reference

    # Enrichment data (preserved from existing schema)
    object_analysis = Column(JSONB, default={})  # Consolidated prose descriptions: material_culture, semiotic_function, object_ontology, object_integration

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    introduction_beat_rel = relationship("Beat", foreign_keys=[introduction_beat], backref="objects_introduced")


# ===========================================
# STORY BIBLE MODELS (New Schema)
# ===========================================

class StoryMetadata(Base):
    """Story-level metadata table (one per database)"""
    __tablename__ = 'story_metadata'

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    genre = Column(String(255))
    setting_period = Column(String(255))
    narrative_pov = Column(String(255))
    tone_keywords = Column(ARRAY(Text))
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Note: job relationship removed for per-database architecture


class MasterTimeline(Base):
    """Master timeline events table"""
    __tablename__ = 'master_timeline'

    id = Column(Integer, primary_key=True)
    date_time = Column(String(255), nullable=False)
    event = Column(Text, nullable=False)
    characters_present = Column(ARRAY(Integer))  # Array of character IDs
    significance = Column(Text)
    is_fixed = Column(Boolean, default=False)
    sequence_order = Column(Integer, nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('sequence_order', name='master_timeline_seq_unique'),
    )
    
    # Note: job relationship removed for per-database architecture


class ReferencesRegistry(Base):
    """Literary/historical quotes and references registry"""
    __tablename__ = 'references_registry'

    id = Column(Integer, primary_key=True)
    reference_text = Column(Text, nullable=False)
    attributed_source = Column(String(255))
    verification_status = Column(String(50), nullable=False, default='UNVERIFIED')  # VERIFIED/FABRICATED/UNVERIFIED
    used_in_beat = Column(Integer, ForeignKey('beats.beat_number'), nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Note: job relationship removed for per-database architecture
    beat = relationship("Beat", foreign_keys=[used_in_beat])


class Beat(Base):
    """Story Bible-compliant beats table - primary table for beat structure"""
    __tablename__ = 'beats'

    id = Column(Integer, primary_key=True)
    beat_number = Column(Integer, nullable=False, unique=True)  # Sequential beat number (primary identifier)
    beat_purpose = Column(Text)  # Purpose from Story Bible
    format_variation = Column(JSONB)  # Format variation from FormatVariationAnalyzerAgent
    prose = Column(Text)  # Generated prose (from Stage 3)
    
    # Story Bible constraint fields
    characters_present = Column(JSONB, default=[])  # Array of character canonical_names with knowledge states
    required_elements = Column(JSONB, default=[])  # Required elements for this beat
    forbidden_elements = Column(JSONB, default=[])  # Forbidden elements for this beat
    objects_used = Column(JSONB, default=[])  # Objects used in this beat
    location = Column(String(255))  # Location canonical_name
    timeline_position = Column(String(255))  # Timeline position string
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Note: job_id removed, beat_number is now globally unique within database
    # Relationships
    knowledge_states = relationship("CharacterKnowledgeState", back_populates="beat", cascade="all, delete-orphan")
    # Note: characters_introduced and objects_introduced relationships created via backref on Character/Object models
    references = relationship("ReferencesRegistry", back_populates="beat")


class CharacterKnowledgeState(Base):
    """Character knowledge states table - beat-by-beat knowledge tracking"""
    __tablename__ = 'character_knowledge_states'

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    beat_number = Column(Integer, ForeignKey('beats.beat_number'), nullable=False)
    
    # Knowledge state arrays
    knows = Column(JSONB, default=[])  # Array of facts character knows
    suspects = Column(JSONB, default=[])  # Array of facts character suspects
    ignorant_of = Column(JSONB, default=[])  # Array of facts character doesn't know
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('character_id', 'beat_number', name='character_knowledge_states_char_beat_unique'),
    )
    
    # Relationships
    character = relationship("Character", back_populates="knowledge_states_rel")
    beat = relationship("Beat", back_populates="knowledge_states")


class KnowledgeChunk(Base):
    """Knowledge chunks table for semantic search"""
    __tablename__ = 'knowledge_chunks'

    id = Column(Integer, primary_key=True)
    chunk_type = Column(String(50), nullable=False)  # Document type, category, etc.
    chunk_title = Column(String(200), nullable=False)
    chunk_content = Column(Text, nullable=False)
    chunk_embedding = Column(Vector(384), nullable=False)  # all-MiniLM-L6-v2
    chunk_keywords = Column(TSVECTOR, nullable=False)      # For keyword search
    sequence_order = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Metadata stored as JSONB for flexibility (category, tags, source file, etc.)
    chunk_metadata = Column(JSONB)

    # Note: context_id can be stored in chunk_metadata if needed for multi-context databases


class Conversation(Base):
    """Story conversations table for persistent chat history"""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    story_name = Column(String(255), nullable=False, index=True)  # Story identifier
    session_id = Column(String(255), nullable=False, index=True)  # Conversation session identifier
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)  # Message content
    tool_calls = Column(JSONB, default=[])  # Store tool usage information
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Composite index for efficient querying
    __table_args__ = (
        Index('idx_conversations_story_session', 'story_name', 'session_id'),
    )

