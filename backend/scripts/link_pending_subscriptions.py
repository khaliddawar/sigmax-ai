#!/usr/bin/env python3
"""
Utility script to link pending subscriptions to users.
This helps resolve cases where customer_id couldn't be mapped to user_id during webhook processing.
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
    # Try alternative import
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from app.services.supabase_client import get_supabase_client


def load_env_file(file_path):
    """Load environment variables from .env file"""
    env_vars = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
    except Exception as e:
        print(f"Error loading .env file: {e}")
    return env_vars


async def find_and_link_pending_subscriptions():
    """Find pending subscriptions and attempt to link them to users"""
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), '..', 'app', '.env')
    env_vars = load_env_file(env_file)
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Get Supabase client
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to initialize Supabase client")
        return
    
    try:
        # Find all pending subscriptions
        print("🔍 Looking for pending subscriptions...")
        pending_result = supabase.table("subscriptions").select("*").eq("status", "pending_user_link").execute()
        
        if not pending_result.data:
            print("✅ No pending subscriptions found")
            return
        
        print(f"📋 Found {len(pending_result.data)} pending subscription(s)")
        
        for subscription in pending_result.data:
            paddle_customer_id = subscription.get("paddle_customer_id")
            paddle_subscription_id = subscription.get("paddle_subscription_id")
            plan_type = subscription.get("plan_type")
            
            print(f"\n🔗 Processing subscription: {paddle_subscription_id}")
            print(f"   Customer ID: {paddle_customer_id}")
            print(f"   Plan: {plan_type}")
            
            # Strategy 1: Look for users who recently made checkouts
            # Get recent user profiles (last 24 hours) and see if any match
            user_id = await find_user_for_subscription(supabase, subscription)
            
            if user_id:
                print(f"✅ Found matching user: {user_id}")
                
                # Update the subscription with the user_id
                update_result = supabase.table("subscriptions").update({
                    "user_id": user_id,
                    "status": "active",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", subscription["id"]).execute()
                
                if update_result.data:
                    print(f"✅ Successfully linked subscription to user {user_id}")
                    
                    # Update user's plan
                    plan_update_result = supabase.table("user_profiles").update({
                        "plan_type": plan_type
                    }).eq("user_id", user_id).execute()
                    
                    if plan_update_result.data:
                        print(f"✅ Updated user {user_id} plan to {plan_type}")
                    else:
                        print(f"⚠️ Failed to update user plan: {plan_update_result}")
                else:
                    print(f"❌ Failed to update subscription: {update_result}")
            else:
                print(f"❌ Could not find matching user for subscription {paddle_subscription_id}")
                print("   Manual intervention required")
        
    except Exception as e:
        print(f"❌ Error processing pending subscriptions: {e}")


async def find_user_for_subscription(supabase, subscription):
    """Try to find a user that matches this subscription"""
    try:
        paddle_customer_id = subscription.get("paddle_customer_id")
        created_at = subscription.get("created_at")
        plan_type = subscription.get("plan_type")
        
        # Strategy 1: Look for recent premium users who don't have an active subscription
        recent_users_result = supabase.table("user_profiles").select("user_id, email, plan_type").eq("plan_type", "free").execute()
        
        if recent_users_result.data:
            print(f"   Found {len(recent_users_result.data)} potential users")
            
            # For now, if there's only one free user and one pending subscription, assume they match
            # This is a heuristic that works for small user bases
            if len(recent_users_result.data) == 1:
                user = recent_users_result.data[0]
                print(f"   🎯 Heuristic match: Only one free user found: {user['email']}")
                return user["user_id"]
        
        # Strategy 2: Look for users with email patterns or timing
        # (This would require more complex logic based on your specific use case)
        
        return None
        
    except Exception as e:
        print(f"Error in user matching: {e}")
        return None


def list_pending_subscriptions():
    """List all pending subscriptions for manual review"""
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), '..', 'app', '.env')
    env_vars = load_env_file(env_file)
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Get Supabase client
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to initialize Supabase client")
        return
    
    try:
        # Get all subscriptions
        all_subs = supabase.table("subscriptions").select("*").execute()
        
        print("📊 All Subscriptions:")
        print("=" * 80)
        
        for sub in all_subs.data:
            print(f"ID: {sub['id']}")
            print(f"User ID: {sub.get('user_id', 'NULL')}")
            print(f"Paddle Sub ID: {sub.get('paddle_subscription_id')}")
            print(f"Paddle Customer ID: {sub.get('paddle_customer_id')}")
            print(f"Plan: {sub.get('plan_type')}")
            print(f"Status: {sub.get('status')}")
            print(f"Created: {sub.get('created_at')}")
            print("-" * 40)
        
        # Get recent user profiles
        users = supabase.table("user_profiles").select("user_id, email, plan_type, created_at").execute()
        
        print("\n📊 Recent Users:")
        print("=" * 80)
        
        for user in users.data:
            print(f"User ID: {user['user_id']}")
            print(f"Email: {user.get('email', 'No email')}")
            print(f"Plan: {user.get('plan_type')}")
            print(f"Created: {user.get('created_at')}")
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error listing data: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_pending_subscriptions()
    else:
        asyncio.run(find_and_link_pending_subscriptions())
