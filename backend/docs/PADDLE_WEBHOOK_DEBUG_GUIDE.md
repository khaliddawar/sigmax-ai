# 🔧 Paddle Webhook Debug Guide

## 🎯 Root Cause Analysis from Render Logs

### **Primary Issue: Supabase Client Not Initialized**
The webhooks are failing with `'NoneType' object has no attribute 'get'` because `self.supabase` is `None` in the PaddleService webhook handlers.

### **Evidence from Logs:**
✅ **Working Components:**
- Webhooks reach `/payments/notifications` endpoint
- Signature verification passes
- JSON payload parsing succeeds
- Event routing works correctly

❌ **Failing Component:**
- Database operations fail because `self.supabase` is `None`

### **Secondary Issue: Missing user_id in Webhooks**
From the logs, `custom_data` is `null` in subscription webhooks, meaning `user_id` is not being passed from checkout to webhook.

## 🔧 Fixes Applied

### 1. Enhanced Supabase Client Initialization
```python
# Added robust initialization with multiple fallbacks
self.supabase = None
try:
    self.supabase = get_supabase_client()
    if not self.supabase:
        # Fallback to new SupabaseService instance
        supabase_service = SupabaseService()
        if supabase_service.initialized:
            self.supabase = supabase_service.client
except Exception as e:
    # Emergency fallback with direct service creation
    logger.error(f"Error during initialization: {e}")
    supabase_service = SupabaseService()
    if supabase_service.initialized:
        self.supabase = supabase_service.client
```

### 2. Emergency Client Reinitialization in Webhook Handlers
Added emergency reinitialization in all webhook handlers:
```python
if not self.supabase:
    logger.error("CRITICAL: Supabase client not initialized")
    try:
        from app.services.supabase_client import SupabaseService
        supabase_service = SupabaseService()
        if supabase_service.initialized:
            self.supabase = supabase_service.client
            logger.info("✅ Emergency reinitialization successful")
        else:
            return {"success": False, "error": "Database connection not available"}
    except Exception as e:
        logger.error(f"❌ Emergency reinitialization failed: {e}")
        return {"success": False, "error": "Database connection not available"}
```

### 3. Enhanced Custom Data Handling
```python
# Improved checkout data with redundant user_id
checkout_data = {
    "custom_data": {
        "user_id": user_id,
        "plan": request.plan.value,
        "checkout_user_id": user_id  # Redundant backup
    }
}

# Enhanced webhook parsing
custom_data = data.get("custom_data") or {}
user_id = custom_data.get("user_id") or custom_data.get("checkout_user_id")
```

### 4. Better Error Logging
Added detailed logging to track:
- Supabase client status during initialization
- Custom data structure in webhooks
- Emergency reinitialization attempts
- Database operation results

## 🧪 Testing Your Fixes

### Manual Test Script
Use the provided `test_paddle_webhook.py` script:

```bash
# Test against your deployed app
python test_paddle_webhook.py --endpoint https://your-app.render.com/api/payments/notifications

# Test locally
python test_paddle_webhook.py --local --user-id your_test_user_id
```

### Check Render Logs
After deploying fixes, monitor logs for:

✅ **Success Indicators:**
```
✅ Supabase client successfully initialized in PaddleService
Processing Paddle webhook: subscription.created
Successfully processed notification: subscription.created
✅ Successfully updated user {user_id} plan to premium
```

❌ **Still Failing:**
```
CRITICAL: Supabase client not initialized
❌ Emergency Supabase client reinitialization failed
'NoneType' object has no attribute 'get'
```

## 🔍 Debugging Steps

### 1. Check Environment Variables
Ensure these are set in Render:
```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
PADDLE_API_KEY=your_paddle_api_key
PADDLE_NOTIFICATION_SECRET=your_notification_secret
```

### 2. Verify Database Tables
Ensure these tables exist in Supabase:
- `user_profiles` (with `user_id`, `plan`, `plan_type` columns)
- `subscriptions` (with proper schema)
- `payments` (with proper schema)

### 3. Test Supabase Connection
Add this test endpoint temporarily:
```python
@router.get("/test-db")
async def test_database():
    try:
        from app.services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table("user_profiles").select("*").limit(1).execute()
            return {"success": True, "data": result.data}
        else:
            return {"success": False, "error": "Supabase client is None"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 4. Monitor Webhook Payloads
Check if `custom_data` is now being passed correctly in logs:
```
🔍 FULL PADDLE WEBHOOK PAYLOAD: {
  "data": {
    "custom_data": {
      "user_id": "actual_user_id",
      "plan": "premium"
    }
  }
}
```

## 🚀 Deploy and Verify

1. **Deploy the fixes** to Render
2. **Create a test subscription** in Paddle sandbox
3. **Monitor logs** for successful webhook processing
4. **Verify user plan update** in Supabase database
5. **Test actual payment flow** end-to-end

## 📊 Success Metrics

Your webhook integration is working correctly when you see:

1. ✅ Webhooks return HTTP 200 status
2. ✅ Subscription records created in database
3. ✅ User plans updated from "free" to "premium"
4. ✅ Payment records created for transactions
5. ✅ No 'NoneType' errors in logs

## 🔗 Additional Resources

- [Paddle Webhook Documentation](https://developer.paddle.com/webhooks)
- [Paddle Signature Verification](https://developer.paddle.com/webhooks/signature-verification)
- [Supabase Python Client](https://supabase.com/docs/reference/python)

---
**Last Updated:** August 2025  
**Version:** 1.0.0
