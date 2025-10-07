#!/usr/bin/env python3
"""
Migration script to update existing user plan_limits to new structure:
- Free users: 10 videos total (instead of 1 per week)
- Premium users: unlimited per month (instead of unlimited weekly)
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.supabase_client import get_supabase_client

NEW_PLAN_LIMITS = {
    "free": {
        "total_videos": 10,           # 10 videos total (lifetime)
        "monthly_videos": -1,         # Not applicable for free
        "daily_requests": 100,
        "monthly_tokens": 50000,
        "concurrent_jobs": 2,
        "email_summaries": True,
        "max_video_duration": 3600,   # 1 hour
        "priority_processing": False
    },
    "premium": {
        "total_videos": -1,           # Not applicable (unlimited)
        "monthly_videos": -1,         # Unlimited per month
        "daily_requests": 1000,
        "monthly_tokens": 500000,
        "concurrent_jobs": 10,
        "email_summaries": True,
        "max_video_duration": 7200,   # 2 hours
        "priority_processing": True
    },
    "enterprise": {
        "total_videos": -1,           # Not applicable (unlimited)
        "monthly_videos": -1,         # Unlimited per month
        "daily_requests": 5000,
        "monthly_tokens": 1000000,
        "concurrent_jobs": 20,
        "email_summaries": True,
        "max_video_duration": 14400,  # 4 hours
        "priority_processing": True,
        "custom_integrations": True
    }
}

def migrate_user_plan_limits():
    """Update all users to new plan limits structure"""
    try:
        supabase = get_supabase_client()
        
        # Get all users
        response = supabase.table("user_profiles").select("id, user_id, email, plan_type, plan_limits").execute()
        
        if not response.data:
            print("No users found to migrate")
            return
        
        print(f"Found {len(response.data)} users to migrate")
        
        updated_count = 0
        for user in response.data:
            user_id = user["user_id"]
            plan_type = user.get("plan_type", "free")
            current_limits = user.get("plan_limits", {})
            
            # Get new limits for the user's plan
            new_limits = NEW_PLAN_LIMITS.get(plan_type, NEW_PLAN_LIMITS["free"])
            
            # Check if update is needed
            if current_limits != new_limits:
                print(f"Updating user {user['email']} ({plan_type}) plan limits...")
                
                # Update the user's plan limits
                update_result = supabase.table("user_profiles").update({
                    "plan_limits": new_limits,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("user_id", user_id).execute()
                
                if update_result.data:
                    print(f"  ✅ Updated {user['email']}")
                    updated_count += 1
                else:
                    print(f"  ❌ Failed to update {user['email']}")
            else:
                print(f"  ⏭️  No update needed for {user['email']}")
        
        print(f"\n🎉 Migration completed! Updated {updated_count} users.")
        
        # Show summary of current plan distribution
        plan_counts = {}
        for user in response.data:
            plan_type = user.get("plan_type", "free")
            plan_counts[plan_type] = plan_counts.get(plan_type, 0) + 1
        
        print("\n📊 Plan Distribution:")
        for plan, count in plan_counts.items():
            print(f"  {plan}: {count} users")
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False
    
    return True

def verify_migration():
    """Verify that the migration was successful"""
    try:
        supabase = get_supabase_client()
        
        # Check a few users to verify
        response = supabase.table("user_profiles").select("email, plan_type, plan_limits").limit(5).execute()
        
        print("\n🔍 Verification - Sample users:")
        for user in response.data:
            plan_type = user.get("plan_type", "free")
            plan_limits = user.get("plan_limits", {})
            expected_limits = NEW_PLAN_LIMITS.get(plan_type, NEW_PLAN_LIMITS["free"])
            
            status = "✅" if plan_limits == expected_limits else "❌"
            print(f"  {status} {user['email']} ({plan_type})")
            
            if plan_type == "free":
                total_videos = plan_limits.get("total_videos", "MISSING")
                print(f"      total_videos: {total_videos}")
            else:
                monthly_videos = plan_limits.get("monthly_videos", "MISSING")
                print(f"      monthly_videos: {monthly_videos}")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    print("🚀 Starting plan limits migration...")
    print("=" * 50)
    
    # Show what will change
    print("📋 New Plan Structure:")
    print("  Free Plan: 10 videos total (instead of 1 per week)")
    print("  Premium Plan: unlimited per month (instead of unlimited weekly)")
    print("  Enterprise Plan: unlimited per month")
    print()
    
    # Confirm before proceeding
    confirm = input("Proceed with migration? (y/N): ").lower().strip()
    if confirm != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run migration
    success = migrate_user_plan_limits()
    
    if success:
        # Verify results
        verify_migration()
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
