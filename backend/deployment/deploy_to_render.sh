#!/bin/bash

# Deploy Simply Backend to Render.com
# This script creates a web service in the existing "simply" project

echo "🚀 Deploying Simply Backend to Render.com..."

# Project and environment IDs (from render CLI output)
PROJECT_ID="prj-d1ek4rumcj7s73ef5cvg"
ENVIRONMENT_ID="evm-d1ek4rumcj7s73ef5d00"
REDIS_ID="red-d1eklkh5pdvs73c6s43g"

echo "📦 Project: simply ($PROJECT_ID)"
echo "🔴 Redis: simply-redis ($REDIS_ID)"

# Note: This script provides the deployment configuration
# You'll need to create the web service manually through the Render dashboard
# or use the Render API directly

echo "
🔧 Manual Deployment Steps:

1. Go to Render Dashboard: https://dashboard.render.com/projects/$PROJECT_ID

2. Click 'New +' → 'Web Service'

3. Connect GitHub repository: https://github.com/khaliddawar/simply

4. Configure the service:
   - Name: simply-backend
   - Runtime: Docker
   - Branch: master
   - Build Command: (leave empty - using Dockerfile)
   - Start Command: (leave empty - using Dockerfile CMD)
   - Plan: Starter ($7/month)
   - Region: Oregon (US West)

5. Set Environment Variables:
   SERVICE_TYPE=backend
   PYTHONPATH=/app
   LOG_LEVEL=INFO
   
   # Add your API keys from .env file:
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
   ANTHROPIC_API_KEY=your_anthropic_key
   OPENAI_API_KEY=your_openai_key
   PERPLEXITY_API_KEY=your_perplexity_key
   POSTMARK_API_KEY=your_postmark_key
   POSTMARK_FROM_EMAIL=your_from_email
   
   # Redis connection (automatically set):
   REDIS_URL=rediss://red-d1eklkh5pdvs73c6s43g:password@oregon-keyvalue.render.com:6379

6. Advanced Settings:
   - Health Check Path: /health
   - Auto-Deploy: Yes

7. Click 'Create Web Service'

8. Wait for deployment to complete

✅ Your backend will be available at: https://simply-backend.onrender.com
"

echo "🔗 Useful links:"
echo "   Dashboard: https://dashboard.render.com/projects/$PROJECT_ID"
echo "   Redis: https://dashboard.render.com/r/$REDIS_ID"
echo ""
echo "📝 After deployment, update your Chrome extension API endpoint to:"
echo "   https://simply-backend.onrender.com" 