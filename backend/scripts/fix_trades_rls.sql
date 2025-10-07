-- Fix RLS policies for trades table to allow anonymous inserts
-- This allows the application to insert trades using the anonymous key

-- Add INSERT policy for anonymous role on trades table
CREATE POLICY IF NOT EXISTS "Allow anonymous insert access" 
ON trades FOR INSERT TO anon WITH CHECK (true);

-- Add INSERT policy for anonymous role on subscribers table (if needed)
CREATE POLICY IF NOT EXISTS "Allow anonymous insert access" 
ON subscribers FOR INSERT TO anon WITH CHECK (true);

-- Add INSERT policy for anonymous role on transcript_chunks table (if needed)
CREATE POLICY IF NOT EXISTS "Allow anonymous insert access" 
ON transcript_chunks FOR INSERT TO anon WITH CHECK (true);

-- Verify policies
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename IN ('trades', 'subscribers', 'transcript_chunks')
ORDER BY tablename, policyname; 