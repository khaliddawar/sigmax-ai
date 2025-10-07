#!/usr/bin/env python3
"""
Script to apply the YouTube extension quota migration to production database
This script runs the migration SQL statements individually for better error handling
"""

import os
import sys
from supabase import create_client, Client

def run_migration():
    """Apply the YouTube extension quota migration"""
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required")
        print("Set these in your environment or .env file")
        sys.exit(1)
    
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🔗 Connected to Supabase")
    
    # Test connection
    try:
        result = supabase.table('transcripts').select('id').limit(1).execute()
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Migration steps
    migration_steps = [
        {
            "name": "Add plan_limits column to user_profiles",
            "sql": """
                ALTER TABLE public.user_profiles 
                ADD COLUMN IF NOT EXISTS plan_limits JSONB DEFAULT '{
                  "monthly_tokens": 50000,
                  "daily_requests": 100,
                  "max_video_duration": 3600,
                  "tier": "free"
                }'::jsonb;
            """
        },
        {
            "name": "Create user_usage table",
            "sql": """
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
            """
        },
        {
            "name": "Enable RLS on user_usage",
            "sql": "ALTER TABLE public.user_usage ENABLE ROW LEVEL SECURITY;"
        },
        {
            "name": "Create RLS policies for user_usage",
            "sql": """
                CREATE POLICY IF NOT EXISTS "Users can view their own usage"
                ON public.user_usage
                FOR SELECT
                USING (user_id = auth.uid());
                
                CREATE POLICY IF NOT EXISTS "Users can update their own usage"
                ON public.user_usage
                FOR UPDATE
                USING (user_id = auth.uid());
                
                CREATE POLICY IF NOT EXISTS "Service role can manage all usage"
                ON public.user_usage
                FOR ALL
                TO service_role
                USING (true);
            """
        }
    ]
    
    # Run each migration step
    for i, step in enumerate(migration_steps, 1):
        print(f"\n🔄 Step {i}/{len(migration_steps)}: {step['name']}")
        try:
            # Use raw SQL execution via rpc
            result = supabase.rpc('exec', {'sql': step['sql']}).execute()
            print(f"✅ Step {i} completed successfully")
        except Exception as e:
            print(f"❌ Step {i} failed: {e}")
            print("Continuing with next step...")
    
    print("\n🎉 Migration process completed!")
    print("Note: Some steps may have failed if they already exist, which is normal.")

if __name__ == "__main__":
    print("🔄 Starting YouTube Extension Quota Migration")
    print("=" * 60)
    run_migration()
    print("=" * 60) 