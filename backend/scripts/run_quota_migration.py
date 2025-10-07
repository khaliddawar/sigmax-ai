#!/usr/bin/env python3
"""
Script to run the YouTube extension quota migration on production database
"""

import os
import sys
from supabase import create_client, Client

def run_migration():
    """Run the YouTube extension quota migration"""
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required")
        sys.exit(1)
    
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Read the migration SQL file
    migration_file = 'scripts/migration/add_youtube_extension_support.sql'
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print(f"📂 Read migration file: {migration_file}")
        print(f"📝 Migration SQL length: {len(migration_sql)} characters")
        
        # Execute the migration
        print("🚀 Running migration...")
        result = supabase.rpc('exec_sql', {'sql': migration_sql}).execute()
        
        if result.data:
            print("✅ Migration completed successfully!")
            print(f"📊 Result: {result.data}")
        else:
            print("⚠️  Migration completed but no data returned")
            
    except FileNotFoundError:
        print(f"❌ Error: Migration file not found: {migration_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔄 Starting YouTube Extension Quota Migration")
    print("=" * 50)
    run_migration()
    print("=" * 50)
    print("✅ Migration process completed") 