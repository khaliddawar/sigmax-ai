# Production Deployment Checklist - Simply Chrome Extension (No Paddle)

This checklist covers deploying the Simply Chrome extension to production **without Paddle payments**, using Gmail for email delivery.

## 📋 Pre-Deployment Checklist

### 1. ✅ **Environment Configuration**

- [ ] Copy `production-no-paddle.env` to your deployment environment
- [ ] Generate a strong JWT secret: `openssl rand -base64 32`
- [ ] Update `JWT_SECRET_KEY` with the generated secret
- [ ] Verify Supabase credentials are correct
- [ ] Set up Gmail app password for SMTP
- [ ] Update `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SENDER_EMAIL` with your Gmail details

### 2. ✅ **Gmail Email Setup**

**Enable Gmail App Password:**
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Navigate to Security → 2-Step Verification
3. Scroll down to "App passwords"
4. Generate a new app password for "Mail"
5. Use this 16-character password (not your regular Gmail password)

**Update Environment Variables:**
```bash
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SENDER_EMAIL=your-email@gmail.com
```

### 3. ✅ **Backend Deployment (Render.com)**

**Environment Variables to Set in Render Dashboard:**
```bash
# Core Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
SUPABASE_URL=https://npdxxefohebhabtrrybo.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Security
JWT_SECRET_KEY=your-generated-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Email (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SENDER_EMAIL=your-email@gmail.com

# AI Services
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# CORS (Update after extension is published)
ALLOWED_ORIGINS=chrome-extension://your-extension-id
CHROME_EXTENSION_ID=your-extension-id

# Feature Flags
ENABLE_PAYMENTS=false
ENABLE_PADDLE=false
```

### 4. ✅ **Chrome Extension Preparation**

**Update Extension Manifest:**
- [ ] Update `host_permissions` to include your production backend URL
- [ ] Set proper `content_security_policy`
- [ ] Remove any development-only permissions

**Example manifest.json updates:**
```json
{
  "host_permissions": [
    "https://simply-firy.onrender.com/*",
    "https://www.youtube.com/*"
  ],
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self';"
  }
}
```

### 5. ✅ **Extension Configuration**

The extension is already configured to disable payments in production. Verify:

```typescript
// In extension/simply/config.ts
production: {
  features: {
    authentication: true,
    payments: false,  // ✅ Already disabled
    emailDelivery: true,
    analytics: true
  }
}
```

## 🚀 Deployment Steps

### Step 1: Deploy Backend

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "feat: disable Paddle payments for production deployment"
   git push origin master
   ```

2. **Deploy on Render:**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Your service should auto-deploy from GitHub
   - Monitor logs for any errors

3. **Test Backend:**
   ```bash
   curl https://simply-firy.onrender.com/health
   ```

### Step 2: Publish Chrome Extension

1. **Build Extension:**
   ```bash
   cd extension/simply
   npm run build
   ```

2. **Create Extension Package:**
   - Zip the `dist` folder contents
   - **Do not** include the `dist` folder itself, just its contents

3. **Upload to Chrome Web Store:**
   - Go to [Chrome Developer Dashboard](https://chrome.google.com/webstore/devconsole)
   - Upload the zip file
   - Fill in store listing details
   - Submit for review

4. **Get Extension ID:**
   - After upload, note the extension ID (it will look like: `abcdefghijklmnopqrstuvwxyzabcdef`)

### Step 3: Update CORS Configuration

1. **Update Backend Environment:**
   ```bash
   # In Render dashboard, update these variables:
   ALLOWED_ORIGINS=chrome-extension://your-actual-extension-id
   CHROME_EXTENSION_ID=your-actual-extension-id
   ```

2. **Redeploy Backend:**
   - The service will auto-restart with new environment variables

## 🧪 Testing

### Test Authentication Flow

1. **Install Extension** (from Chrome Web Store or load unpacked)
2. **Navigate to YouTube video**
3. **Extract transcript** (should work without authentication)
4. **Try to generate summary** (should prompt for login)
5. **Sign up/Login** with test account
6. **Generate summary** (should work and send email)

### Test Email Delivery

1. **After successful summary generation**
2. **Check your Gmail inbox** for the summary email
3. **Verify email formatting** and content

### Test Weekly Limits

1. **Create free account**
2. **Generate 1 summary** (should work)
3. **Try to generate 2nd summary** (should show limit reached)
4. **Should see upgrade prompt** (but no payment option since disabled)

## 🔍 Monitoring & Troubleshooting

### Check Backend Logs

```bash
# In Render dashboard, go to your service → Logs
# Look for any errors related to:
# - Authentication
# - Email sending
# - Database connections
```

### Common Issues & Solutions

**Authentication Fails:**
- ✅ Check JWT_SECRET_KEY is set correctly
- ✅ Verify Supabase credentials
- ✅ Check CORS settings

**Email Not Sending:**
- ✅ Verify Gmail app password is correct
- ✅ Check SMTP settings
- ✅ Ensure 2FA is enabled on Gmail account

**Extension Can't Connect:**
- ✅ Verify host_permissions in manifest
- ✅ Check CORS settings in backend
- ✅ Ensure extension ID is correct

## 📈 Post-Deployment

### Monitor Usage

1. **Check Supabase dashboard** for user registrations
2. **Monitor backend logs** for any errors
3. **Track email delivery** success rates

### Prepare for Payments (Future)

When ready to add payments:
1. Set up Paddle account
2. Update environment variables
3. Re-enable payment features in config
4. Test payment flow thoroughly

## 🎯 Success Criteria

- [ ] ✅ Backend deployed and responding to health checks
- [ ] ✅ Extension published to Chrome Web Store
- [ ] ✅ Authentication flow works end-to-end
- [ ] ✅ Email summaries are delivered successfully
- [ ] ✅ Weekly limits are enforced for free users
- [ ] ✅ No payment UI is shown (as intended)
- [ ] ✅ Error handling works properly

---

**Ready for Production!** 🚀

Your Simply Chrome extension is now ready for production use with authentication and email delivery, without payment complexity. 