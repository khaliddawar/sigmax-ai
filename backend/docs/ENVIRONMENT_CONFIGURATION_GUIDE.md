# Environment Configuration Guide - Simply Authentication & Payment System

This guide provides comprehensive instructions for configuring environment variables and API keys required for the Simply Chrome extension with authentication and payment features.

## 🎯 Overview

The Simply system requires proper configuration of:
- **Authentication System** (Supabase Auth)
- **Payment Processing** (Paddle)
- **Email Delivery** (SMTP/Postmark)
- **AI Services** (OpenAI, Anthropic)
- **Database** (Supabase)
- **Security** (JWT tokens)

## 📋 Required Environment Variables

### 1. **Supabase Configuration** (CRITICAL)

```bash
# Supabase Database & Auth
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**How to get these values:**
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to Settings → API
4. Copy the values from the "Project API keys" section

### 2. **Authentication & Security** (CRITICAL)

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Password security
BCRYPT_ROUNDS=12
```

**How to generate JWT secret:**
```bash
# Option 1: OpenSSL
openssl rand -base64 32

# Option 2: Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 3: Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

### 3. **Payment System** (Paddle)

```bash
# Paddle Configuration
PADDLE_VENDOR_ID=your_paddle_vendor_id
PADDLE_API_KEY=your_paddle_api_key
PADDLE_PUBLIC_KEY=your_paddle_public_key
PADDLE_WEBHOOK_SECRET=your_paddle_webhook_secret
PADDLE_ENVIRONMENT=sandbox  # or 'production'

# Product IDs for different plans
PADDLE_PRODUCT_ID_PREMIUM=12345
PADDLE_PRODUCT_ID_ENTERPRISE=12346
```

**How to get Paddle credentials:**
1. Sign up at [Paddle.com](https://paddle.com)
2. Go to Developer Tools → Authentication
3. Create API keys for your environment
4. Set up webhook endpoints in Paddle dashboard
5. Configure product catalog with pricing

### 4. **Email Service Configuration**

```bash
# Option A: SMTP (Gmail/Outlook)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com

# Option B: Postmark (Recommended for production)
POSTMARK_API_TOKEN=your_postmark_server_token
POSTMARK_SENDER_EMAIL=noreply@yourdomain.com
POSTMARK_SENDER_NAME=Simply
```

**Gmail App Password Setup:**
1. Enable 2-factor authentication on your Google account
2. Go to Google Account settings
3. Security → 2-Step Verification → App passwords
4. Generate an app password for "Mail"
5. Use this password (not your regular password)

### 5. **AI Services**

```bash
# OpenAI (Required)
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL_NAME=gpt-4o-mini

# Anthropic (Optional)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Perplexity (Optional - for research features)
PERPLEXITY_API_KEY=pplx-...
```

### 6. **Redis Configuration** (For production scaling)

```bash
# Redis for job queues and caching
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 7. **Application Configuration**

```bash
# Environment
ENVIRONMENT=production  # or 'development'
DEBUG=false
LOG_LEVEL=INFO

# CORS & Security
ALLOWED_ORIGINS=https://yourdomain.com,chrome-extension://your-extension-id
CHROME_EXTENSION_ID=your_chrome_extension_id

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

## 🏗️ Environment Setup by Deployment Type

### Development Environment

Create `.env` file in project root:

```bash
# === DEVELOPMENT CONFIGURATION ===
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# === SUPABASE (Development Project) ===
SUPABASE_URL=https://your-dev-project.supabase.co
SUPABASE_ANON_KEY=your_dev_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_dev_service_role_key

# === AUTHENTICATION ===
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# === PADDLE (Sandbox) ===
PADDLE_VENDOR_ID=your_sandbox_vendor_id
PADDLE_API_KEY=your_sandbox_api_key
PADDLE_ENVIRONMENT=sandbox

# === EMAIL (Development) ===
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-dev-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-dev-email@gmail.com

# === AI SERVICES ===
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# === LOCAL SERVICES ===
REDIS_URL=redis://localhost:6379
```

### Production Environment (Render.com)

Configure in Render dashboard or via `render.yaml`:

```yaml
envVars:
  # Environment
  - key: ENVIRONMENT
    value: production
  - key: DEBUG
    value: false
  - key: LOG_LEVEL
    value: INFO
    
  # Supabase (from secrets)
  - key: SUPABASE_URL
    fromDatabase:
      name: simply-secrets
      property: SUPABASE_URL
  - key: SUPABASE_ANON_KEY
    fromDatabase:
      name: simply-secrets
      property: SUPABASE_ANON_KEY
  - key: SUPABASE_SERVICE_ROLE_KEY
    fromDatabase:
      name: simply-secrets
      property: SUPABASE_SERVICE_ROLE_KEY
      
  # Authentication
  - key: JWT_SECRET_KEY
    fromDatabase:
      name: simply-secrets
      property: JWT_SECRET_KEY
      
  # Paddle
  - key: PADDLE_VENDOR_ID
    fromDatabase:
      name: simply-secrets
      property: PADDLE_VENDOR_ID
  - key: PADDLE_API_KEY
    fromDatabase:
      name: simply-secrets
      property: PADDLE_API_KEY
  - key: PADDLE_ENVIRONMENT
    value: production
    
  # Email
  - key: POSTMARK_API_TOKEN
    fromDatabase:
      name: simply-secrets
      property: POSTMARK_API_TOKEN
  - key: POSTMARK_SENDER_EMAIL
    value: noreply@yourdomain.com
    
  # AI Services
  - key: OPENAI_API_KEY
    fromDatabase:
      name: simply-secrets
      property: OPENAI_API_KEY
  - key: ANTHROPIC_API_KEY
    fromDatabase:
      name: simply-secrets
      property: ANTHROPIC_API_KEY
    
  # Redis
  - key: REDIS_URL
    fromService:
      type: redis
      name: simply-redis
      property: connectionString
```

## 🔧 Extension Configuration

### Background Script API Endpoints

Update `extension/simply/background.ts`:

```typescript
// Development
const API_BASE_URL = "http://localhost:8000/api"
const AUTH_BASE_URL = "http://localhost:8000/auth"

// Production
const API_BASE_URL = "https://your-app.onrender.com/api"
const AUTH_BASE_URL = "https://your-app.onrender.com/auth"
```

### Chrome Extension Manifest

Update `extension/simply/manifest.json`:

```json
{
  "host_permissions": [
    "https://your-app.onrender.com/*",
    "https://www.youtube.com/*"
  ],
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self';"
  }
}
```

## 🔐 Security Best Practices

### 1. **Environment Variable Security**

- ✅ **Never commit `.env` files to git**
- ✅ **Use different keys for development/production**
- ✅ **Rotate secrets regularly**
- ✅ **Use secret management services in production**

### 2. **JWT Security**

```bash
# Generate strong JWT secrets (32+ characters)
JWT_SECRET_KEY=$(openssl rand -base64 32)

# Use appropriate expiration times
JWT_EXPIRATION_HOURS=24  # 24 hours for user sessions
```

### 3. **Database Security**

```bash
# Use service role key only for backend operations
# Use anon key for client-side operations with RLS
SUPABASE_SERVICE_ROLE_KEY=service_role_key  # Backend only
SUPABASE_ANON_KEY=anon_key  # Client-side with RLS
```

### 4. **API Key Security**

- ✅ **Restrict API key permissions**
- ✅ **Set usage limits**
- ✅ **Monitor API usage**
- ✅ **Use environment-specific keys**

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] All required environment variables configured
- [ ] Secrets stored securely (not in code)
- [ ] API keys tested and working
- [ ] Database migrations applied
- [ ] Email service configured and tested

### Development Testing

```bash
# Test authentication
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}'

# Test payment integration
curl -X GET http://localhost:8000/payments/plans

# Test email service
curl -X POST http://localhost:8000/api/yt_email_summary \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"video_id":"test","title":"Test Video"}'
```

### Production Deployment

1. **Update API endpoints in extension**
2. **Configure production environment variables**
3. **Test all authentication flows**
4. **Verify payment integration**
5. **Test email delivery**
6. **Monitor error logs**

## 🔍 Troubleshooting

### Common Issues

**Authentication Fails:**
- Check JWT_SECRET_KEY is set
- Verify Supabase credentials
- Check token expiration

**Payment Integration Issues:**
- Verify Paddle API keys
- Check webhook configuration
- Confirm product IDs

**Email Not Sending:**
- Test SMTP credentials
- Check firewall settings
- Verify sender reputation

**CORS Errors:**
- Update ALLOWED_ORIGINS
- Check Chrome extension permissions
- Verify API endpoints

### Environment Validation Script

```python
import os
import sys

def validate_environment():
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'JWT_SECRET_KEY',
        'OPENAI_API_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        sys.exit(1)
    else:
        print("✅ All required environment variables are set")

if __name__ == "__main__":
    validate_environment()
```

## 📞 Support

For additional help:
- Check the logs: `LOG_LEVEL=DEBUG`
- Review API documentation
- Test individual services
- Contact support with specific error messages

---

**Last Updated:** January 2025
**Version:** 1.0.0 