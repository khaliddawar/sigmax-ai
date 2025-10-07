#!/usr/bin/env python3
"""
Check specific user status in Supabase database
"""
import os
import sys

# Add the app directory to the Python path
app_dir = os.path.join(os.path.dirname(__file__), '..', 'app')
sys.path.insert(0, app_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(app_dir, '.env'))

from services.supabase_client import get_supabase_client

def check_user_status():
    """Check the specific user mentioned in webhook logs"""
    try:
        supabase = get_supabase_client()
        user_id = 'afad44d2-1171-4453-b7df-e46a2b4d5b99'  # From webhook logs
        
        print('🔍 Checking specific user from webhook logs...')
        print(f'User ID: {user_id}')
        print()
        
        # Check user_profiles
        user_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
        if user_result.data:
            user = user_result.data[0]
            print('📋 User Profile:')
            print(f'   Email: {user.get("email")}')
            print(f'   Plan Type: {user.get("plan_type")}')
            print(f'   Subscription Status: {user.get("subscription_status")}')
            print(f'   Created: {user.get("created_at")}')
            print(f'   Updated: {user.get("updated_at")}')
        else:
            print('❌ User not found in user_profiles table')
        
        print()
        
        # Check subscriptions
        sub_result = supabase.table('subscriptions').select('*').eq('user_id', user_id).execute()
        if sub_result.data:
            print('📋 User Subscriptions:')
            for sub in sub_result.data:
                print(f'   ID: {sub.get("id")}')
                print(f'   Plan: {sub.get("plan")}')
                print(f'   Status: {sub.get("status")}')
                print(f'   Paddle Sub ID: {sub.get("paddle_subscription_id")}')
                print(f'   Paddle Customer ID: {sub.get("paddle_customer_id")}')
                print(f'   Created: {sub.get("created_at")}')
                print('   ---')
        else:
            print('📋 No subscriptions found for this user')
            
        print()
        
        # Also check by email
        email = 'khalid.noor@outlook.com'
        print(f'🔍 Double-checking by email: {email}')
        email_result = supabase.table('user_profiles').select('*').eq('email', email).execute()
        if email_result.data:
            user = email_result.data[0]
            print('📋 User Profile by Email:')
            print(f'   User ID: {user.get("user_id")}')
            print(f'   Email: {user.get("email")}')
            print(f'   Plan Type: {user.get("plan_type")}')
            print(f'   Subscription Status: {user.get("subscription_status")}')
            print(f'   Updated: {user.get("updated_at")}')
        else:
            print('❌ User not found by email')
            
    except Exception as e:
        print(f"❌ Error checking user status: {e}")
        return False
        
    return True

if __name__ == "__main__":
    check_user_status()
