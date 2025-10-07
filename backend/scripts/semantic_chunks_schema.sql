-- Semantic Chunks Database Schema (Domain-Agnostic)
-- This script creates a completely new schema for semantic chunks with rich metadata
-- Run this to replace the old financial-specific schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables to start fresh (BE CAREFUL - THIS DELETES ALL DATA)
DROP TABLE IF EXISTS transcript_chunks CASCADE;
DROP TABLE IF EXISTS transcripts CASCADE;
DROP TABLE IF EXISTS semantic_chunks CASCADE;

-- Create transcripts table (unchanged - metadata only)
CREATE TABLE transcripts (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT UNIQUE NOT NULL,
    title TEXT,
    meeting_id TEXT,
    date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    word_count INTEGER,
    duration_seconds INTEGER,
    source TEXT DEFAULT 'unknown',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create semantic_chunks table with rich metadata
CREATE TABLE semantic_chunks (
    -- Primary identification
    id VARCHAR(32) PRIMARY KEY,  -- Hash-based unique ID from semantic chunker
    transcript_id TEXT REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    
    -- Core content
    text TEXT NOT NULL,
    
    -- Rich metadata (domain-agnostic)
    entities JSONB NOT NULL DEFAULT '[]',  -- Array of entity objects [{text, label, start, end, confidence}]
    sentiment VARCHAR(50),                 -- Configurable sentiment from domain config
    language VARCHAR(10) DEFAULT 'en',    -- Language code
    metadata JSONB NOT NULL DEFAULT '{}', -- Flexible metadata field
    
    -- NLP analysis results
    sentence_count INTEGER DEFAULT 1,
    entity_types TEXT[] DEFAULT '{}',     -- Array of detected entity type strings
    
    -- Position tracking
    start_position INTEGER DEFAULT 0,
    end_position INTEGER DEFAULT 0,
    
    -- Vector embeddings
    embedding vector(1536),  -- OpenAI text-embedding-3-large default
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(transcript_id, chunk_index)
);

-- Create indexes for efficient querying
CREATE INDEX idx_semantic_chunks_transcript_id ON semantic_chunks(transcript_id);
CREATE INDEX idx_semantic_chunks_sentiment ON semantic_chunks(sentiment);
CREATE INDEX idx_semantic_chunks_language ON semantic_chunks(language);

-- GIN index on entities JSONB for fast entity-based queries
CREATE INDEX idx_semantic_chunks_entities_gin ON semantic_chunks USING GIN (entities);

-- GIN index on entity_types array for fast entity type filtering
CREATE INDEX idx_semantic_chunks_entity_types_gin ON semantic_chunks USING GIN (entity_types);

-- Vector index for similarity search (create after data is loaded)
-- CREATE INDEX semantic_chunks_embedding_idx ON semantic_chunks 
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create functions for vector similarity search
CREATE OR REPLACE FUNCTION match_semantic_chunks(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.1,
    match_count INT DEFAULT 10
) RETURNS TABLE (
    id VARCHAR,
    transcript_id TEXT,
    chunk_index INTEGER,
    text TEXT,
    entities JSONB,
    sentiment VARCHAR,
    language VARCHAR,
    metadata JSONB,
    entity_types TEXT[],
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
SELECT
    sc.id,
    sc.transcript_id,
    sc.chunk_index,
    sc.text,
    sc.entities,
    sc.sentiment,
    sc.language,
    sc.metadata,
    sc.entity_types,
    1 - (sc.embedding <=> query_embedding) as similarity
FROM
    semantic_chunks sc
WHERE
    sc.embedding IS NOT NULL AND
    1 - (sc.embedding <=> query_embedding) > match_threshold
ORDER BY
    sc.embedding <=> query_embedding
LIMIT match_count;
$$;

-- Create function for searching within a specific transcript
CREATE OR REPLACE FUNCTION match_transcript_semantic_chunks(
    query_embedding vector(1536),
    transcript_id_param TEXT,
    match_threshold FLOAT DEFAULT 0.1,
    match_count INT DEFAULT 10
) RETURNS TABLE (
    id VARCHAR,
    transcript_id TEXT,
    chunk_index INTEGER,
    text TEXT,
    entities JSONB,
    sentiment VARCHAR,
    language VARCHAR,
    metadata JSONB,
    entity_types TEXT[],
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
SELECT
    sc.id,
    sc.transcript_id,
    sc.chunk_index,
    sc.text,
    sc.entities,
    sc.sentiment,
    sc.language,
    sc.metadata,
    sc.entity_types,
    1 - (sc.embedding <=> query_embedding) as similarity
FROM
    semantic_chunks sc
WHERE
    sc.embedding IS NOT NULL AND
    sc.transcript_id = transcript_id_param AND
    1 - (sc.embedding <=> query_embedding) > match_threshold
ORDER BY
    sc.embedding <=> query_embedding
LIMIT match_count;
$$;

-- Create function for entity-based filtering
CREATE OR REPLACE FUNCTION match_chunks_by_entities(
    query_embedding vector(1536),
    entity_types_filter TEXT[],
    match_threshold FLOAT DEFAULT 0.1,
    match_count INT DEFAULT 10
) RETURNS TABLE (
    id VARCHAR,
    transcript_id TEXT,
    chunk_index INTEGER,
    text TEXT,
    entities JSONB,
    sentiment VARCHAR,
    language VARCHAR,
    metadata JSONB,
    entity_types TEXT[],
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
SELECT
    sc.id,
    sc.transcript_id,
    sc.chunk_index,
    sc.text,
    sc.entities,
    sc.sentiment,
    sc.language,
    sc.metadata,
    sc.entity_types,
    1 - (sc.embedding <=> query_embedding) as similarity
FROM
    semantic_chunks sc
WHERE
    sc.embedding IS NOT NULL AND
    sc.entity_types && entity_types_filter AND  -- Array overlap operator
    1 - (sc.embedding <=> query_embedding) > match_threshold
ORDER BY
    sc.embedding <=> query_embedding
LIMIT match_count;
$$;

-- Create function for sentiment filtering
CREATE OR REPLACE FUNCTION match_chunks_by_sentiment(
    query_embedding vector(1536),
    sentiment_filter VARCHAR,
    match_threshold FLOAT DEFAULT 0.1,
    match_count INT DEFAULT 10
) RETURNS TABLE (
    id VARCHAR,
    transcript_id TEXT,
    chunk_index INTEGER,
    text TEXT,
    entities JSONB,
    sentiment VARCHAR,
    language VARCHAR,
    metadata JSONB,
    entity_types TEXT[],
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
SELECT
    sc.id,
    sc.transcript_id,
    sc.chunk_index,
    sc.text,
    sc.entities,
    sc.sentiment,
    sc.language,
    sc.metadata,
    sc.entity_types,
    1 - (sc.embedding <=> query_embedding) as similarity
FROM
    semantic_chunks sc
WHERE
    sc.embedding IS NOT NULL AND
    sc.sentiment = sentiment_filter AND
    1 - (sc.embedding <=> query_embedding) > match_threshold
ORDER BY
    sc.embedding <=> query_embedding
LIMIT match_count;
$$;

-- Grant permissions (adjust as needed for your security model)
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_chunks ENABLE ROW LEVEL SECURITY;

-- Create policies for read access
CREATE POLICY "Allow public read access" 
ON transcripts FOR SELECT USING (true);

CREATE POLICY "Allow public read access" 
ON semantic_chunks FOR SELECT USING (true);

-- Create policies for service role
CREATE POLICY "Allow service role full access" 
ON transcripts FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access" 
ON semantic_chunks FOR ALL TO service_role USING (true);

-- Create a view for easy querying with transcript metadata
CREATE VIEW semantic_chunks_with_transcript AS
SELECT 
    sc.*,
    t.title as transcript_title,
    t.date as transcript_date,
    t.source as transcript_source
FROM semantic_chunks sc
JOIN transcripts t ON sc.transcript_id = t.transcript_id;

-- Sample queries for testing (commented out)
/*
-- Example entity-based query:
SELECT id, text, entities, sentiment 
FROM semantic_chunks 
WHERE entities @> '[{"label": "MONEY"}]';

-- Example sentiment filtering:
SELECT id, text, sentiment, entity_types 
FROM semantic_chunks 
WHERE sentiment = 'bullish' 
AND entity_types && ARRAY['MONEY', 'PERCENT'];

-- Example complex metadata query:
SELECT id, text, metadata->'source' as source
FROM semantic_chunks 
WHERE metadata->>'confidence' > '0.8';
*/ 