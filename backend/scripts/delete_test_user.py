#!/usr/bin/env python3
"""
Delete test user khalid.noor@outlook.com for webhook testing
"""
import os
import sys
from pathlib import Path
from supabase import create_client, Client

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def load_env_file(env_path: str = None):
    """Load environment variables from .env file"""
    if env_path is None:
        # Try multiple possible locations
        possible_paths = [
            ".env",
            "app/.env", 
            "../app/.env",
            str(Path(__file__).parent.parent / "app" / ".env")
        ]
    else:
        possible_paths = [env_path]
    
    env_vars = {}
    for path in possible_paths:
        if os.path.exists(path):
            print(f"📁 Loading environment from: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                break
            except UnicodeDecodeError:
                print(f"⚠️  Could not read {path} with UTF-8 encoding")
                continue
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    return env_vars

def delete_test_user():
    """Delete the test user and all associated data"""
    try:
        # Load environment variables
        env_vars = load_env_file()
        
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials in environment")
            return False
        
        print(f"🔗 Connecting to Supabase: {supabase_url}")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        target_email = "khalid.noor@outlook.com"
        target_user_id = "afad44d2-1171-4453-b7df-e46a2b4d5b99"
        
        print(f"🎯 Target user: {target_email}")
        print(f"🎯 Target user ID: {target_user_id}")
        print()
        
        # First, verify the user exists
        user_result = supabase.table('user_profiles').select('*').eq('email', target_email).execute()
        if not user_result.data:
            print(f"✅ User {target_email} not found - already deleted or doesn't exist")
            return True
        
        user = user_result.data[0]
        print(f"📋 Found user:")
        print(f"   Email: {user.get('email')}")
        print(f"   User ID: {user.get('user_id')}")
        print(f"   Plan: {user.get('plan_type')}")
        print(f"   Status: {user.get('subscription_status')}")
        print()
        
        # Delete in order to avoid foreign key constraints
        
        # 1. Delete subscriptions first
        print("🗑️  Deleting subscriptions...")
        sub_result = supabase.table('subscriptions').select('*').eq('user_id', target_user_id).execute()
        if sub_result.data:
            for sub in sub_result.data:
                print(f"   Deleting subscription: {sub.get('paddle_subscription_id')}")
            
            delete_subs = supabase.table('subscriptions').delete().eq('user_id', target_user_id).execute()
            print(f"   ✅ Deleted {len(sub_result.data)} subscription(s)")
        else:
            print("   ℹ️  No subscriptions found")
        
        # 2. Delete any payments (if they exist)
        print("🗑️  Checking for payments...")
        try:
            payment_result = supabase.table('payments').select('*').eq('user_id', target_user_id).execute()
            if payment_result.data:
                delete_payments = supabase.table('payments').delete().eq('user_id', target_user_id).execute()
                print(f"   ✅ Deleted {len(payment_result.data)} payment(s)")
            else:
                print("   ℹ️  No payments found")
        except Exception as e:
            print(f"   ℹ️  Payments table not accessible or empty: {e}")
        
        # 3. Delete user profile
        print("🗑️  Deleting user profile...")
        delete_user = supabase.table('user_profiles').delete().eq('user_id', target_user_id).execute()
        print(f"   ✅ Deleted user profile for {target_email}")
        
        # 4. Try to delete from auth.users (this might fail if we don't have permissions)
        print("🗑️  Attempting to delete from auth.users...")
        try:
            # Note: This might not work with service role key depending on RLS policies
            auth_delete = supabase.auth.admin.delete_user(target_user_id)
            print(f"   ✅ Deleted from auth.users")
        except Exception as e:
            print(f"   ⚠️  Could not delete from auth.users: {e}")
            print("   ℹ️  This is usually fine - auth user will be orphaned but harmless")
        
        print()
        print("🎉 User deletion completed!")
        print(f"✅ {target_email} has been removed from the database")
        print("🧪 You can now test the webhook processing again")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        return False

if __name__ == "__main__":
    print("🗑️  Test User Deletion Script")
    print("=" * 50)
    print("⚠️  This will delete khalid.noor@outlook.com and all associated data")
    print()
    
    # Ask for confirmation
    response = input("Are you sure you want to proceed? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        if delete_test_user():
            print("\n✅ User deletion completed successfully!")
        else:
            print("\n❌ User deletion failed - see errors above")
    else:
        print("❌ Deletion cancelled by user")

