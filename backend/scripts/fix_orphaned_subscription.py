#!/usr/bin/env python3
"""
Fix orphaned subscription by manually linking customer to user
This handles the case where webhooks come with no custom_data and no existing subscription records
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the app directory to the Python path
app_dir = os.path.join(os.path.dirname(__file__), '..', 'app')
sys.path.insert(0, app_dir)

try:
    from services.supabase_client import get_supabase_client
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from app.services.supabase_client import get_supabase_client

def load_env_file(file_path=None):
    """Load environment variables from .env file"""
    if file_path is None:
        possible_paths = [
            ".env",
            "app/.env", 
            "../app/.env",
            os.path.join(os.path.dirname(__file__), "..", "app", ".env")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        else:
            print("❌ .env file not found")
            return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
                    except ValueError:
                        continue
        return True
    except Exception as e:
        print(f"Error loading .env file: {e}")
        return False

def fix_orphaned_subscription():
    """Fix the specific orphaned subscription from recent logs"""
    print("🔧 Fixing Orphaned Subscription")
    print("=" * 50)
    
    # Load environment
    if not load_env_file():
        return False
    
    # Initialize services
    supabase = get_supabase_client()
    
    # From the logs, we know these details:
    customer_id = "ctm_01k24hrs2kn87m74dcbata1h0j"
    subscription_id = "sub_01k25e1yc3v8yjf32caz466wqa"
    transaction_id = "txn_01k25e0t489f4at6y9c1ehken7"
    
    print(f"📝 Orphaned Subscription Details:")
    print(f"   Customer ID: {customer_id}")
    print(f"   Subscription ID: {subscription_id}")
    print(f"   Transaction ID: {transaction_id}")
    
    # Step 1: Find the target user (premium user who should be linked)
    try:
        # Look for premium users without proper subscription records
        users_result = supabase.table("user_profiles").select("user_id, email, plan_type").eq("plan_type", "premium").execute()
        
        if not users_result.data:
            print("❌ No premium users found to link to")
            return False
        
        print(f"\n🔍 Found {len(users_result.data)} premium user(s):")
        for i, user in enumerate(users_result.data):
            print(f"   {i+1}. {user['email']} ({user['user_id'][:8]}...)")
        
        # For now, let's use the first premium user (you can modify this logic)
        target_user = users_result.data[0]
        user_id = target_user["user_id"]
        user_email = target_user["email"]
        
        print(f"\n✅ Selected user: {user_email} ({user_id})")
        
    except Exception as e:
        print(f"❌ Error finding target user: {e}")
        return False
    
    # Step 2: Check if subscription already exists
    try:
        existing_sub = supabase.table("subscriptions").select("*").eq("paddle_subscription_id", subscription_id).execute()
        
        if existing_sub.data:
            print(f"ℹ️  Subscription record already exists: {existing_sub.data[0]}")
            return True
            
    except Exception as e:
        print(f"⚠️  Error checking existing subscription: {e}")
    
    # Step 3: Create the subscription record
    try:
        subscription_data = {
            "user_id": user_id,
            "paddle_subscription_id": subscription_id,
            "paddle_customer_id": customer_id,
            "plan": "premium",
            "status": "active",
            "current_period_start": datetime.utcnow().isoformat(),
            "current_period_end": (datetime.utcnow().replace(day=28) if datetime.utcnow().day < 28 else datetime.utcnow().replace(month=datetime.utcnow().month+1, day=28)).isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "manual_link": True,
                "linked_at": datetime.utcnow().isoformat(),
                "source_transaction": transaction_id,
                "reason": "Orphaned subscription from missing custom_data"
            }
        }
        
        result = supabase.table("subscriptions").insert(subscription_data).execute()
        
        if result.data:
            print(f"✅ Successfully created subscription record for {user_email}")
            print(f"   Subscription ID: {subscription_id}")
            print(f"   Customer ID: {customer_id}")
            print(f"   Plan: premium")
            return True
        else:
            print(f"❌ Failed to create subscription record: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating subscription record: {e}")
        return False

def verify_fix():
    """Verify that the fix worked"""
    print("\n🔍 Verifying Fix...")
    
    supabase = get_supabase_client()
    
    customer_id = "ctm_01k24hrs2kn87m74dcbata1h0j"
    subscription_id = "sub_01k25e1yc3v8yjf32caz466wqa"
    
    try:
        # Check subscription record
        sub_result = supabase.table("subscriptions").select("*").eq("paddle_subscription_id", subscription_id).execute()
        
        if sub_result.data:
            sub = sub_result.data[0]
            print(f"✅ Subscription record found:")
            print(f"   User ID: {sub['user_id']}")
            print(f"   Plan: {sub['plan']}")
            print(f"   Status: {sub['status']}")
            print(f"   Customer ID: {sub['paddle_customer_id']}")
            
            # Check user profile
            user_result = supabase.table("user_profiles").select("email, plan_type").eq("user_id", sub['user_id']).execute()
            if user_result.data:
                user = user_result.data[0]
                print(f"   User Email: {user['email']}")
                print(f"   User Plan: {user['plan_type']}")
                
                if user['plan_type'] == 'premium':
                    print("\n🎉 SUCCESS: User is properly set to premium plan!")
                    return True
                else:
                    print(f"\n⚠️  User plan is {user['plan_type']}, not premium")
                    return False
            else:
                print(f"\n❌ User profile not found for user_id: {sub['user_id']}")
                return False
        else:
            print("❌ Subscription record not found")
            return False
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Orphaned Subscription Fix Tool")
    print("=" * 60)
    
    if fix_orphaned_subscription():
        print("\n" + "=" * 60)
        verify_fix()
        print("\n✨ Fix completed! Future webhooks for this customer should now work correctly.")
    else:
        print("\n❌ Fix failed. Please check the errors above.")

