"""
Script to apply paddle_customer_id migration to Supabase
"""
import os
import sys
from pathlib import Path
from supabase import create_client, Client

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def load_env_file(env_path: str = "app/.env"):
    """Load environment variables from .env file"""
    if not os.path.exists(env_path):
        print(f"❌ .env file not found at {env_path}")
        return False
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")
    return True

def apply_migration():
    """Apply the paddle_customer_id migration"""
    # Load environment variables
    if not load_env_file():
        return False
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
        
        # Read the migration SQL
        migration_path = Path(__file__).parent / "migration" / "add_paddle_customer_id.sql"
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        print("📝 Applying migration...")
        
        # Execute the SQL statements one by one
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for statement in statements:
            if statement:
                print(f"   Executing: {statement[:50]}...")
                try:
                    # Use RPC to execute raw SQL
                    result = supabase.rpc("exec_sql", {"query": statement}).execute()
                    print(f"   ✅ Success")
                except Exception as e:
                    # Some statements might fail if already applied, that's ok
                    if "already exists" in str(e).lower():
                        print(f"   ⚠️  Already exists (skipping)")
                    else:
                        print(f"   ❌ Error: {e}")
        
        print("\n✅ Migration completed!")
        
        # Verify the column exists
        print("\n🔍 Verifying migration...")
        try:
            # Try to query with the new column
            result = supabase.table("subscriptions").select("paddle_customer_id").limit(1).execute()
            print("✅ paddle_customer_id column is accessible")
            return True
        except Exception as e:
            if "column" in str(e).lower():
                print(f"⚠️  Column might not be accessible via API yet: {e}")
                print("   You may need to run the migration directly in Supabase SQL editor")
            else:
                print(f"❌ Verification error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Paddle Customer ID Migration Script")
    print("=" * 50)
    
    if apply_migration():
        print("\n✅ All done! The paddle_customer_id column has been added.")
        print("\n📌 Next steps:")
        print("1. Deploy the updated code to Render")
        print("2. Monitor webhook processing")
        print("3. The column will be populated as new webhooks arrive")
    else:
        print("\n⚠️  Migration may need to be run manually in Supabase")
        print("\n📌 Manual steps:")
        print("1. Go to Supabase SQL editor")
        print("2. Run the contents of scripts/migration/add_paddle_customer_id.sql")
        print("3. Verify the column was added successfully")
