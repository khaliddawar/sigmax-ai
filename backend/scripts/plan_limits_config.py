# Plan Limits Configuration
# This defines the limits for each plan type

PLAN_LIMITS = {
    "free": {
        "total_videos": 10,           # 10 videos total (lifetime)
        "monthly_videos": -1,         # Not applicable for free (use total_videos)
        "daily_requests": 100,
        "monthly_tokens": 50000,
        "concurrent_jobs": 2,
        "email_summaries": True,
        "max_video_duration": 3600,   # 1 hour
        "priority_processing": False
    },
    "premium": {
        "total_videos": -1,           # Not applicable (use monthly_videos)
        "monthly_videos": -1,         # Unlimited per month
        "daily_requests": 1000,
        "monthly_tokens": 500000,
        "concurrent_jobs": 10,
        "email_summaries": True,
        "max_video_duration": 7200,   # 2 hours
        "priority_processing": True
    },
    "enterprise": {
        "total_videos": -1,           # Not applicable (use monthly_videos)
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

# Helper functions
def get_plan_limits(plan_type: str) -> dict:
    """Get plan limits for a specific plan type"""
    return PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])

def is_unlimited_plan(plan_type: str) -> bool:
    """Check if plan has unlimited video access"""
    return plan_type in ["premium", "enterprise"]
