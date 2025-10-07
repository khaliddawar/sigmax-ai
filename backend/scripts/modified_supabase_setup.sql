-- Supabase pgvector Setup Script (Modified to handle existing functions)
-- This script creates all necessary tables and functions for pgvector integration
-- Run this after enabling the pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing functions if they exist to avoid return type conflicts
DROP FUNCTION IF EXISTS match_chunks(vector, float, int);
DROP FUNCTION IF EXISTS match_transcript_chunks(vector, text, float, int);

-- Create transcripts table for storing metadata
CREATE TABLE IF NOT EXISTS transcripts (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT UNIQUE NOT NULL,
    title TEXT,
    meeting_id TEXT,
    date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    word_count INTEGER,
    duration_seconds INTEGER,
    source TEXT DEFAULT 'fireflies',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create transcript_chunks table with vector embeddings
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1536),  -- This is for OpenAI embeddings (ada-002)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(transcript_id, chunk_index)
);

-- Create transcript_analyses table for key points and summaries
CREATE TABLE IF NOT EXISTS transcript_analyses (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL,  -- e.g., 'key_points', 'summary', 'action_items'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(transcript_id, analysis_type)
);

-- Create trade_ideas table for extracted trading ideas
CREATE TABLE IF NOT EXISTS trade_ideas (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    tickers TEXT[] DEFAULT '{}',
    strategy TEXT,
    time_frame TEXT,
    risk_level TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create a function for vector similarity search
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_threshold FLOAT,
    match_count INT
) RETURNS TABLE (
    id INTEGER,
    transcript_id TEXT,
    chunk_index INTEGER,
    text TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
SELECT
    tc.id,
    tc.transcript_id,
    tc.chunk_index,
    tc.text,
    tc.metadata,
    1 - (tc.embedding <=> query_embedding) as similarity
FROM
    transcript_chunks tc
WHERE
    tc.embedding IS NOT NULL AND
    1 - (tc.embedding <=> query_embedding) > match_threshold
ORDER BY
    tc.embedding <=> query_embedding
LIMIT match_count;
$$;

-- Create a function for searching within a specific transcript
CREATE OR REPLACE FUNCTION match_transcript_chunks(
    query_embedding vector(1536),
    transcript_id_param TEXT,
    match_threshold FLOAT,
    match_count INT
) RETURNS TABLE (
    id INTEGER,
    transcript_id TEXT,
    chunk_index INTEGER,
    text TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
SELECT
    tc.id,
    tc.transcript_id,
    tc.chunk_index,
    tc.text,
    tc.metadata,
    1 - (tc.embedding <=> query_embedding) as similarity
FROM
    transcript_chunks tc
WHERE
    tc.embedding IS NOT NULL AND
    tc.transcript_id = transcript_id_param AND
    1 - (tc.embedding <=> query_embedding) > match_threshold
ORDER BY
    tc.embedding <=> query_embedding
LIMIT match_count;
$$;

-- Instead of creating the index immediately which requires 61MB of memory,
-- we'll provide instructions for creating it separately when more memory is available
-- or after reducing the parameters

/* 
-- NOTE: RUN THIS SEPARATELY AFTER INCREASING MEMORY OR ADJUSTING PARAMETERS
-- To run this, either:
-- 1. Set maintenance_work_mem to at least 64MB:
--    SET maintenance_work_mem = '64MB';
-- 2. OR reduce the number of lists for less memory usage:
--    CREATE INDEX transcript_chunks_embedding_idx ON transcript_chunks 
--    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
--
-- Recommended index creation (with temporarily increased memory):
SET maintenance_work_mem = '64MB';
CREATE INDEX transcript_chunks_embedding_idx ON transcript_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
*/

-- Grant permissions
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_ideas ENABLE ROW LEVEL SECURITY;

-- Create policies for each table
CREATE POLICY "Allow public read access" 
ON transcripts FOR SELECT USING (true);

CREATE POLICY "Allow public read access" 
ON transcript_chunks FOR SELECT USING (true);

CREATE POLICY "Allow public read access" 
ON transcript_analyses FOR SELECT USING (true);

CREATE POLICY "Allow public read access" 
ON trade_ideas FOR SELECT USING (true);

-- Create policies for service role
CREATE POLICY "Allow service role full access" 
ON transcripts FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access" 
ON transcript_chunks FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access" 
ON transcript_analyses FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access" 
ON trade_ideas FOR ALL TO service_role USING (true);

-- Create users_feedback table to track user feedback on responses
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    question_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating INTEGER,  -- User rating (e.g., 1-5)
    feedback TEXT,   -- Descriptive feedback
    transcript_id TEXT REFERENCES transcripts(transcript_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create chat_sessions table to track user conversations
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create chat_messages table to store conversation history
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL,  -- 'user', 'assistant' or 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
); 