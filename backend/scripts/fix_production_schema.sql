-- Fix Production Database Schema Issues
-- This script adds missing columns and tables to fix webhook processing errors

-- Add missing columns to transcripts table
ALTER TABLE transcripts 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS summary TEXT;

-- Add missing columns to semantic_chunks table if they don't exist
ALTER TABLE semantic_chunks 
ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50);

-- Create missing subscribers table
CREATE TABLE IF NOT EXISTS subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    active BOOLEAN DEFAULT true,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create missing trades table (referenced in some parts of the code)
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL, -- 'buy', 'sell', 'hold'
    price DECIMAL(10,2),
    quantity INTEGER,
    confidence DECIMAL(3,2), -- 0.00 to 1.00
    reasoning TEXT,
    timestamp_mentioned TEXT,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create missing transcript_chunks table (used by some legacy code paths)
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536), -- OpenAI embeddings
    position INTEGER DEFAULT 0,
    is_first BOOLEAN DEFAULT false,
    is_last BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(transcript_id, chunk_index)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcripts_metadata ON transcripts USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_transcripts_summary ON transcripts(summary);
CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);
CREATE INDEX IF NOT EXISTS idx_subscribers_active ON subscribers(active);
CREATE INDEX IF NOT EXISTS idx_trades_transcript_id ON trades(transcript_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_transcript_id ON transcript_chunks(transcript_id);

-- Enable RLS on new tables for security
ALTER TABLE subscribers ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_chunks ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access
CREATE POLICY IF NOT EXISTS "Allow service role full access" 
ON subscribers FOR ALL TO service_role USING (true);

CREATE POLICY IF NOT EXISTS "Allow service role full access" 
ON trades FOR ALL TO service_role USING (true);

CREATE POLICY IF NOT EXISTS "Allow service role full access" 
ON transcript_chunks FOR ALL TO service_role USING (true);

-- Create policies for public read access
CREATE POLICY IF NOT EXISTS "Allow public read access" 
ON subscribers FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Allow public read access" 
ON trades FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Allow public read access" 
ON transcript_chunks FOR SELECT USING (true);

-- Insert some default subscribers if none exist
INSERT INTO subscribers (email, name, active) 
SELECT 'admin@example.com', 'Admin User', true
WHERE NOT EXISTS (SELECT 1 FROM subscribers LIMIT 1);

-- Add comments for documentation
COMMENT ON COLUMN transcripts.metadata IS 'JSON metadata for additional transcript information';
COMMENT ON COLUMN transcripts.summary IS 'AI-generated summary of the transcript';
COMMENT ON TABLE subscribers IS 'Email subscribers for transcript notifications';
COMMENT ON TABLE trades IS 'Extracted trading ideas and recommendations from transcripts';
COMMENT ON TABLE transcript_chunks IS 'Legacy chunk storage for backward compatibility';

-- Update any existing transcripts to have default metadata if null
UPDATE transcripts 
SET metadata = '{}' 
WHERE metadata IS NULL;

-- Verify the changes
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('transcripts', 'subscribers', 'trades', 'transcript_chunks', 'semantic_chunks')
    AND table_schema = 'public'
ORDER BY table_name, ordinal_position; 