# Redis Setup Guide for Render.com

This guide will help you set up a Redis service on Render.com for the Simply YouTube extension project.

## 🎯 Overview

Redis is **CRITICAL** for the YouTube extension's queue system. It handles:
- Background job queuing for YouTube transcript processing
- Celery worker task distribution
- Real-time processing status updates
- Idempotency and duplicate prevention

## 📋 Step-by-Step Setup

### Step 1: Create Redis Service on Render.com

1. **Go to Render.com Dashboard**
   - Navigate to: [https://dashboard.render.com](https://dashboard.render.com)
   - Sign in to your account

2. **Create New Redis Service**
   - Click the **"New +"** button in the top right
   - Select **"Redis"** from the dropdown menu

3. **Configure Redis Service**
   ```
   Name: simply-redis
   Region: Choose same region as your web service (for better performance)
   Plan: Free (for development) or Starter ($7/month for production)
   ```

4. **Create the Service**
   - Click **"Create Redis"**
   - Wait for the service to be provisioned (usually takes 1-2 minutes)

### Step 2: Get Your Redis URL

Once your Redis service is created:

1. **Navigate to your Redis service** in the Render dashboard
2. **Copy the Connection URL** - it will look like:
   ```
   redis://red-xxxxxxxxxxxxx:6379
   ```
   
   Example:
   ```
   redis://red-c9j8k7l6m5n4p3q2r1s0:6379
   ```

### Step 3: Update Environment Configuration

1. **Open your `.env` file** in the project root
2. **Replace the Redis configuration** with your actual Render.com URL:

   ```bash
   # Redis Configuration (CRITICAL for Queue System)
   # Replace with your actual Render.com Redis URL
   REDIS_URL=redis://red-xxxxxxxxxxxxx:6379
   REDIS_HOST=red-xxxxxxxxxxxxx.redis.render.com
   REDIS_PORT=6379
   REDIS_PASSWORD=
   REDIS_DB=0
   ```

   **Important**: Replace `red-xxxxxxxxxxxxx` with your actual Redis service identifier.

### Step 4: Test Your Redis Connection

Run the test script to verify everything is working:

```bash
python scripts/test_redis_connection.py
```

**Expected Output** (when working):
```
🚀 Starting Redis Connection Test
🔗 Testing Redis connection to: redis://red-xxxxxxxxxxxxx:6379
📡 Testing ping...
✅ Redis ping successful!
🔧 Testing basic operations...
✅ SET test:connection = Hello from Simply!
✅ GET test:connection = Hello from Simply!
📊 Getting Redis info...
✅ Redis version: 7.x.x
✅ Connected clients: 1
✅ Used memory: 1.2M
🧹 Cleaned up test key: test:connection
🎉 All Redis tests passed!
```

## 🔧 Integration with Existing Services

### Queue Service Configuration

Your project already has Redis integration configured in:
- `app/services/queue_service.py` - Main queue service
- `workers/celery_worker.py` - Celery worker for background processing
- `app/settings.py` - Redis configuration loading

### Testing the Full Queue System

After Redis is configured, test the complete queue system:

```bash
# 1. Test Redis infrastructure
python scripts/start_redis_queue.py

# 2. Start Celery worker (in separate terminal)
python workers/celery_worker.py

# 3. Start FastAPI server (in separate terminal)
python app/main.py
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused Error**
   ```
   Error 10061 connecting to localhost:6379
   ```
   **Solution**: Make sure you've updated `REDIS_URL` in `.env` with your Render.com URL

2. **Authentication Failed**
   ```
   WRONGPASS invalid username-password pair
   ```
   **Solution**: Check if your Redis service requires a password (some plans do)

3. **Timeout Errors**
   ```
   TimeoutError: [Errno 10060]
   ```
   **Solution**: Check your network connection and Redis service status

### Verification Steps

1. **Check Redis Service Status**
   - Go to Render.com dashboard
   - Verify your Redis service shows "Live" status
   - Check for any error messages

2. **Verify Environment Variables**
   ```bash
   # Check if Redis URL is loaded correctly
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('REDIS_URL:', os.getenv('REDIS_URL'))"
   ```

3. **Test Network Connectivity**
   ```bash
   # Test if you can reach the Redis host
   ping red-xxxxxxxxxxxxx.redis.render.com
   ```

## 📊 Redis Service Plans

| Plan | Price | Memory | Connections | Best For |
|------|-------|--------|-------------|----------|
| Free | $0/month | 25MB | 20 | Development/Testing |
| Starter | $7/month | 256MB | 1000 | Small Production |
| Standard | $25/month | 1GB | 1000 | Production |

**Recommendation**: Start with Free for development, upgrade to Starter for production.

## 🔄 Next Steps After Redis Setup

1. **✅ Redis Connected** - You're here!
2. **Test Queue System** - Run `python scripts/start_redis_queue.py`
3. **Start Celery Worker** - Run `python workers/celery_worker.py`
4. **Test YouTube API** - Create and test the Chrome extension
5. **End-to-End Testing** - Full pipeline testing

## 🔐 Security Notes

- Redis URL contains authentication credentials - keep it secure
- Don't commit Redis URLs to version control
- Use environment variables for all Redis configuration
- Consider enabling TLS for production (available on paid plans)

## 📞 Support

If you encounter issues:
1. Check Render.com status page: [https://status.render.com](https://status.render.com)
2. Review Render.com Redis documentation
3. Test with the provided scripts in this project

---

**⚡ Quick Setup Summary**:
1. Create Redis service on Render.com
2. Copy the Redis URL
3. Update `REDIS_URL` in `.env`
4. Run `python scripts/test_redis_connection.py`
5. Proceed with queue system testing 