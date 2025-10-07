-- Migration script to recreate BPT database schema in new Simply Supabase project
-- Project: npdxxefohebhabtrrybo (simply)
-- Source: hohpifdmvnwasmrmxonh (BPT)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Create transcripts table (main table)
CREATE TABLE IF NOT EXISTS public.transcripts (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT NOT NULL UNIQUE,
    title TEXT,
    meeting_id TEXT,
    date TIMESTAMPTZ DEFAULT NOW(),
    word_count INTEGER,
    duration_seconds INTEGER,
    source TEXT DEFAULT 'fireflies' CHECK (source IN ('fireflies', 'youtube', 'other')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    summary TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    detailed_summary TEXT
);

-- Add comment
COMMENT ON COLUMN public.transcripts.detailed_summary IS 'Full summary content without size restrictions';
COMMENT ON COLUMN public.transcripts.source IS 'Source of the transcript: fireflies, youtube, or other sources';

-- 2. Create transcript_analyses table
CREATE TABLE IF NOT EXISTS public.transcript_analyses (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES public.transcripts(transcript_id),
    analysis_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create trade_ideas table
CREATE TABLE IF NOT EXISTS public.trade_ideas (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES public.transcripts(transcript_id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    tickers TEXT[] DEFAULT '{}',
    strategy TEXT,
    time_frame TEXT,
    risk_level TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create user_feedback table
CREATE TABLE IF NOT EXISTS public.user_feedback (
    id SERIAL PRIMARY KEY,
    question_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating INTEGER,
    feedback TEXT,
    transcript_id TEXT REFERENCES public.transcripts(transcript_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create chat_sessions table
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT,
    context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Create chat_messages table
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT REFERENCES public.chat_sessions(session_id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Create semantic_chunks table (main chunking table)
CREATE TABLE IF NOT EXISTS public.semantic_chunks (
    id VARCHAR PRIMARY KEY,
    transcript_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    entities JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    language VARCHAR DEFAULT 'en',
    embedding vector,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    start_position INTEGER DEFAULT 0,
    end_position INTEGER DEFAULT 0,
    sentence_count INTEGER DEFAULT 1,
    entity_types TEXT[] DEFAULT '{}',
    sentiment VARCHAR
);

-- 8. Create subscribers table
CREATE TABLE IF NOT EXISTS public.subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comment
COMMENT ON TABLE public.subscribers IS 'Email subscribers for transcript notifications';

-- 9. Create trades table
CREATE TABLE IF NOT EXISTS public.trades (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES public.transcripts(transcript_id),
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    price NUMERIC,
    quantity INTEGER,
    confidence NUMERIC,
    reasoning TEXT,
    timestamp_mentioned TEXT,
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Add comment
COMMENT ON TABLE public.trades IS 'Extracted trading ideas and recommendations from transcripts';

-- 10. Create transcript_chunks table (legacy)
CREATE TABLE IF NOT EXISTS public.transcript_chunks (
    id SERIAL PRIMARY KEY,
    transcript_id TEXT REFERENCES public.transcripts(transcript_id),
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector,
    position INTEGER DEFAULT 0,
    is_first BOOLEAN DEFAULT FALSE,
    is_last BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comment
COMMENT ON TABLE public.transcript_chunks IS 'Legacy chunk storage for backward compatibility';

-- 11. Create user_profiles table
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id),
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    plan_type TEXT DEFAULT 'free' CHECK (plan_type IN ('free', 'premium', 'enterprise')),
    plan_limits JSONB DEFAULT '{"daily_requests": 100, "monthly_tokens": 50000, "concurrent_jobs": 2, "email_summaries": true, "max_video_duration": 3600, "priority_processing": false}',
    subscription_status TEXT DEFAULT 'active' CHECK (subscription_status IN ('active', 'cancelled', 'expired')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Create usage_ledger table
CREATE TABLE IF NOT EXISTS public.usage_ledger (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    resource_type TEXT NOT NULL CHECK (resource_type IN ('tokens', 'requests', 'video_processing')),
    amount INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. Create youtube_videos table
CREATE TABLE IF NOT EXISTS public.youtube_videos (
    id SERIAL PRIMARY KEY,
    video_id TEXT NOT NULL UNIQUE,
    transcript_id TEXT REFERENCES public.transcripts(transcript_id),
    channel_name TEXT,
    channel_id TEXT,
    video_url TEXT NOT NULL,
    thumbnail_url TEXT,
    published_at TIMESTAMPTZ,
    view_count BIGINT,
    like_count INTEGER,
    comment_count INTEGER,
    category TEXT,
    tags TEXT[],
    language TEXT DEFAULT 'en',
    auto_generated_captions BOOLEAN DEFAULT FALSE,
    processed_by_user UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS) on all tables
ALTER TABLE public.transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcript_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.semantic_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscribers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcript_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.youtube_videos ENABLE ROW LEVEL SECURITY;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transcripts_transcript_id ON public.transcripts(transcript_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_source ON public.transcripts(source);
CREATE INDEX IF NOT EXISTS idx_transcripts_date ON public.transcripts(date);

CREATE INDEX IF NOT EXISTS idx_semantic_chunks_transcript_id ON public.semantic_chunks(transcript_id);
CREATE INDEX IF NOT EXISTS idx_semantic_chunks_embedding ON public.semantic_chunks USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_trades_transcript_id ON public.trades(transcript_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON public.trades(symbol);

CREATE INDEX IF NOT EXISTS idx_youtube_videos_video_id ON public.youtube_videos(video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_transcript_id ON public.youtube_videos(transcript_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_transcripts_updated_at BEFORE UPDATE ON public.transcripts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscribers_updated_at BEFORE UPDATE ON public.subscribers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_youtube_videos_updated_at BEFORE UPDATE ON public.youtube_videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant necessary permissions (adjust as needed based on your RLS policies)
-- These are basic permissions - you may need to add specific RLS policies

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO service_role;

-- Success message
SELECT 'Database schema migration completed successfully!' as status; 