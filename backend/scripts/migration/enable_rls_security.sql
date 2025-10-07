-- Enable Row Level Security (RLS) for all user data tables
-- This ensures users can only access their own data

-- Enable RLS on user_profiles table
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only read/update their own profile
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Enable RLS on transcripts table
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own transcripts
CREATE POLICY "Users can view own transcripts" ON transcripts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own transcripts" ON transcripts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own transcripts" ON transcripts
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own transcripts" ON transcripts
    FOR DELETE USING (auth.uid() = user_id);

-- Enable RLS on semantic_chunks table
ALTER TABLE semantic_chunks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access chunks from their own transcripts
CREATE POLICY "Users can view own semantic chunks" ON semantic_chunks
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM transcripts 
            WHERE transcripts.id = semantic_chunks.transcript_id 
            AND transcripts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own semantic chunks" ON semantic_chunks
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM transcripts 
            WHERE transcripts.id = semantic_chunks.transcript_id 
            AND transcripts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update own semantic chunks" ON semantic_chunks
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM transcripts 
            WHERE transcripts.id = semantic_chunks.transcript_id 
            AND transcripts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own semantic chunks" ON semantic_chunks
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM transcripts 
            WHERE transcripts.id = semantic_chunks.transcript_id 
            AND transcripts.user_id = auth.uid()
        )
    );

-- Enable RLS on enhanced_chunks table (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'enhanced_chunks') THEN
        ALTER TABLE enhanced_chunks ENABLE ROW LEVEL SECURITY;
        
        -- Policy: Users can only access chunks from their own transcripts
        CREATE POLICY "Users can view own enhanced chunks" ON enhanced_chunks
            FOR SELECT USING (
                EXISTS (
                    SELECT 1 FROM transcripts 
                    WHERE transcripts.id = enhanced_chunks.transcript_id 
                    AND transcripts.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can insert own enhanced chunks" ON enhanced_chunks
            FOR INSERT WITH CHECK (
                EXISTS (
                    SELECT 1 FROM transcripts 
                    WHERE transcripts.id = enhanced_chunks.transcript_id 
                    AND transcripts.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can update own enhanced chunks" ON enhanced_chunks
            FOR UPDATE USING (
                EXISTS (
                    SELECT 1 FROM transcripts 
                    WHERE transcripts.id = enhanced_chunks.transcript_id 
                    AND transcripts.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can delete own enhanced chunks" ON enhanced_chunks
            FOR DELETE USING (
                EXISTS (
                    SELECT 1 FROM transcripts 
                    WHERE transcripts.id = enhanced_chunks.transcript_id 
                    AND transcripts.user_id = auth.uid()
                )
            );
    END IF;
END $$;

-- Enable RLS on usage_ledger table (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'usage_ledger') THEN
        ALTER TABLE usage_ledger ENABLE ROW LEVEL SECURITY;
        
        -- Policy: Users can only view their own usage records
        CREATE POLICY "Users can view own usage" ON usage_ledger
            FOR SELECT USING (auth.uid() = user_id);

        CREATE POLICY "System can insert usage records" ON usage_ledger
            FOR INSERT WITH CHECK (true); -- Allow system to insert usage records

        -- No update/delete policies for usage_ledger (immutable audit log)
    END IF;
END $$;

-- Enable RLS on trades table (if exists for financial data)
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trades') THEN
        ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
        
        -- Policy: Users can only access their own trades
        CREATE POLICY "Users can view own trades" ON trades
            FOR SELECT USING (auth.uid() = user_id);

        CREATE POLICY "Users can insert own trades" ON trades
            FOR INSERT WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can update own trades" ON trades
            FOR UPDATE USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete own trades" ON trades
            FOR DELETE USING (auth.uid() = user_id);
    END IF;
END $$;

-- Create security functions for common checks
CREATE OR REPLACE FUNCTION auth.user_owns_transcript(transcript_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM transcripts 
        WHERE id = transcript_id 
        AND user_id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to check if user has quota remaining
CREATE OR REPLACE FUNCTION auth.user_has_quota(user_id UUID, token_count INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    user_limits JSONB;
    monthly_usage INTEGER;
    daily_usage INTEGER;
BEGIN
    -- Get user limits
    SELECT plan_limits INTO user_limits 
    FROM user_profiles 
    WHERE id = user_id;
    
    -- Default limits if not set
    IF user_limits IS NULL THEN
        user_limits := '{"monthly_tokens": 50000, "daily_requests": 100}'::jsonb;
    END IF;
    
    -- Check monthly token usage
    SELECT COALESCE(SUM(tokens_used), 0) INTO monthly_usage
    FROM usage_ledger 
    WHERE user_id = user_id 
    AND created_at >= date_trunc('month', NOW());
    
    -- Check daily request count
    SELECT COUNT(*) INTO daily_usage
    FROM usage_ledger 
    WHERE user_id = user_id 
    AND created_at >= date_trunc('day', NOW());
    
    -- Check if adding this request would exceed limits
    RETURN (monthly_usage + token_count) <= (user_limits->>'monthly_tokens')::INTEGER
        AND daily_usage < (user_limits->>'daily_requests')::INTEGER;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create audit trigger for transcript access
CREATE OR REPLACE FUNCTION audit_transcript_access()
RETURNS TRIGGER AS $$
BEGIN
    -- Log transcript access for security monitoring
    INSERT INTO usage_ledger (user_id, operation, metadata, created_at)
    VALUES (
        auth.uid(),
        TG_OP,
        jsonb_build_object(
            'transcript_id', COALESCE(NEW.id, OLD.id),
            'table_name', TG_TABLE_NAME
        ),
        NOW()
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit trigger to transcripts table
DROP TRIGGER IF EXISTS audit_transcript_access_trigger ON transcripts;
CREATE TRIGGER audit_transcript_access_trigger
    AFTER INSERT OR UPDATE OR DELETE ON transcripts
    FOR EACH ROW EXECUTE FUNCTION audit_transcript_access();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT EXECUTE ON FUNCTION auth.user_owns_transcript TO authenticated;
GRANT EXECUTE ON FUNCTION auth.user_has_quota TO authenticated;

-- Create indexes for RLS performance
CREATE INDEX IF NOT EXISTS idx_transcripts_user_id ON transcripts(user_id);
CREATE INDEX IF NOT EXISTS idx_semantic_chunks_transcript_id ON semantic_chunks(transcript_id);
CREATE INDEX IF NOT EXISTS idx_usage_ledger_user_id_date ON usage_ledger(user_id, created_at);

-- Security validation: Test RLS policies
DO $$
DECLARE
    test_result BOOLEAN;
BEGIN
    -- Verify RLS is enabled on critical tables
    SELECT COUNT(*) = 4 INTO test_result
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
    AND c.relname IN ('user_profiles', 'transcripts', 'semantic_chunks', 'usage_ledger')
    AND c.relrowsecurity = true;
    
    IF NOT test_result THEN
        RAISE EXCEPTION 'RLS validation failed: Not all critical tables have RLS enabled';
    END IF;
    
    RAISE NOTICE 'RLS Security Setup Complete: All policies and functions created successfully';
END $$; 