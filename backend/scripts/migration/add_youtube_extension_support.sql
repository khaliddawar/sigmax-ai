-- Migration: Add YouTube Extension Support
-- This migration adds necessary columns and tables for Chrome extension functionality
-- Date: 2024-01-XX
-- Description: Add plan_limits to user_profiles and ensure transcripts table supports YouTube sources

-- Add plan_limits column to user_profiles for quota management
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS plan_limits JSONB DEFAULT '{
  "monthly_tokens": 50000,
  "daily_requests": 100,
  "max_video_duration": 3600,
  "tier": "free"
}'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN public.user_profiles.plan_limits IS 'JSON object containing user quota limits: monthly_tokens, daily_requests, max_video_duration, tier';

-- Create index on plan_limits for efficient queries
CREATE INDEX IF NOT EXISTS idx_user_profiles_plan_limits_tier 
ON public.user_profiles USING GIN ((plan_limits->>'tier'));

-- Add user_usage table to track actual usage against limits
CREATE TABLE IF NOT EXISTS public.user_usage (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    requests_made INTEGER DEFAULT 0,
    videos_processed INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, period_start, period_end)
);

-- Enable RLS on user_usage
ALTER TABLE public.user_usage ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_usage
CREATE POLICY "Users can view their own usage"
ON public.user_usage
FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "Users can update their own usage"
ON public.user_usage
FOR UPDATE
USING (user_id = auth.uid());

-- Service role can manage all usage records
CREATE POLICY "Service role can manage all usage"
ON public.user_usage
FOR ALL
TO service_role
USING (true);

-- Create function to get current user limits
CREATE OR REPLACE FUNCTION public.get_user_limits(user_uuid UUID)
RETURNS JSONB
LANGUAGE SQL
SECURITY DEFINER
AS $$
SELECT COALESCE(plan_limits, '{
  "monthly_tokens": 50000,
  "daily_requests": 100,
  "max_video_duration": 3600,
  "tier": "free"
}'::jsonb)
FROM public.user_profiles
WHERE id = user_uuid;
$$;

-- Create function to get current period usage
CREATE OR REPLACE FUNCTION public.get_current_usage(user_uuid UUID)
RETURNS JSONB
LANGUAGE SQL
SECURITY DEFINER
AS $$
SELECT COALESCE(
  json_build_object(
    'tokens_used', tokens_used,
    'requests_made', requests_made,
    'videos_processed', videos_processed,
    'period_start', period_start,
    'period_end', period_end
  )::jsonb,
  '{
    "tokens_used": 0,
    "requests_made": 0,
    "videos_processed": 0,
    "period_start": null,
    "period_end": null
  }'::jsonb
)
FROM public.user_usage
WHERE user_id = user_uuid
  AND period_start <= CURRENT_DATE
  AND period_end >= CURRENT_DATE
ORDER BY period_start DESC
LIMIT 1;
$$;

-- Create function to increment usage
CREATE OR REPLACE FUNCTION public.increment_usage(
  user_uuid UUID,
  tokens_consumed INTEGER DEFAULT 0,
  requests_increment INTEGER DEFAULT 1,
  videos_increment INTEGER DEFAULT 0
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  current_month_start DATE;
  current_month_end DATE;
BEGIN
  -- Calculate current month boundaries
  current_month_start := date_trunc('month', CURRENT_DATE)::DATE;
  current_month_end := (date_trunc('month', CURRENT_DATE) + interval '1 month - 1 day')::DATE;
  
  -- Insert or update usage record for current month
  INSERT INTO public.user_usage (
    user_id, 
    period_start, 
    period_end, 
    tokens_used, 
    requests_made, 
    videos_processed,
    updated_at
  )
  VALUES (
    user_uuid,
    current_month_start,
    current_month_end,
    tokens_consumed,
    requests_increment,
    videos_increment,
    NOW()
  )
  ON CONFLICT (user_id, period_start, period_end)
  DO UPDATE SET
    tokens_used = user_usage.tokens_used + tokens_consumed,
    requests_made = user_usage.requests_made + requests_increment,
    videos_processed = user_usage.videos_processed + videos_increment,
    updated_at = NOW();
    
  RETURN TRUE;
END;
$$;

-- Create function to check if user can consume tokens
CREATE OR REPLACE FUNCTION public.can_consume_tokens(
  user_uuid UUID,
  tokens_needed INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_limits JSONB;
  current_usage JSONB;
  monthly_limit INTEGER;
  current_tokens INTEGER;
BEGIN
  -- Get user limits
  SELECT public.get_user_limits(user_uuid) INTO user_limits;
  monthly_limit := (user_limits->>'monthly_tokens')::INTEGER;
  
  -- Get current usage
  SELECT public.get_current_usage(user_uuid) INTO current_usage;
  current_tokens := COALESCE((current_usage->>'tokens_used')::INTEGER, 0);
  
  -- Check if user can consume the requested tokens
  RETURN (current_tokens + tokens_needed) <= monthly_limit;
END;
$$;

-- Ensure transcripts table supports YouTube sources (already has source column with default 'fireflies')
-- Update the source column to allow 'youtube' values
ALTER TABLE public.transcripts 
ALTER COLUMN source SET DEFAULT 'fireflies';

-- Add check constraint to ensure valid source values
DO $$
BEGIN
  -- Drop constraint if it exists
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'transcripts_source_check' 
    AND table_name = 'transcripts'
  ) THEN
    ALTER TABLE public.transcripts DROP CONSTRAINT transcripts_source_check;
  END IF;
  
  -- Add updated constraint
  ALTER TABLE public.transcripts 
  ADD CONSTRAINT transcripts_source_check 
  CHECK (source IN ('fireflies', 'youtube', 'manual', 'api'));
END $$;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcripts_source_date 
ON public.transcripts (source, date);

CREATE INDEX IF NOT EXISTS idx_user_usage_user_period 
ON public.user_usage (user_id, period_start, period_end);

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.user_usage TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_limits(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_current_usage(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.increment_usage(UUID, INTEGER, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.can_consume_tokens(UUID, INTEGER) TO authenticated;

-- Update existing users with default plan limits if they don't have them
UPDATE public.user_profiles 
SET plan_limits = '{
  "monthly_tokens": 50000,
  "daily_requests": 100,
  "max_video_duration": 3600,
  "tier": "free"
}'::jsonb
WHERE plan_limits IS NULL;

-- Add comment to document the migration
COMMENT ON TABLE public.user_usage IS 'Tracks user consumption against their plan limits for quota management';

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'Migration completed successfully: YouTube extension support added';
  RAISE NOTICE 'Added plan_limits to user_profiles';
  RAISE NOTICE 'Created user_usage table for quota tracking';
  RAISE NOTICE 'Added utility functions for quota management';
  RAISE NOTICE 'Updated transcripts table to support YouTube sources';
END $$; 