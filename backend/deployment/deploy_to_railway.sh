#!/bin/bash

# BPT Railway Deployment Helper Script
# This script helps you prepare for Railway deployment

echo "🚀 BPT Railway Deployment Helper"
echo "================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    echo "   git remote add origin <your-github-repo-url>"
    echo "   git push -u origin main"
    exit 1
fi

# Check if required files exist
echo "📋 Checking required files..."

required_files=("Dockerfile" "requirements.txt" "railway.json" ".env.railway" "RAILWAY_DEPLOYMENT.md")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    else
        echo "✅ $file exists"
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "❌ Missing required files:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    echo "Please ensure all files are created before deployment."
    exit 1
fi

# Check environment variables template
echo ""
echo "🔧 Environment Variables Checklist"
echo "=================================="
echo "Before deploying to Railway, make sure you have:"
echo ""
echo "✅ Supabase project set up with:"
echo "   - SUPABASE_URL"
echo "   - SUPABASE_ANON_KEY" 
echo "   - SUPABASE_SERVICE_ROLE_KEY"
echo ""
echo "✅ OpenAI API key:"
echo "   - OPENAI_API_KEY"
echo ""
echo "✅ Admin secret (generate a secure random string):"
echo "   - ADMIN_SECRET"
echo ""

# Generate a sample admin secret
admin_secret=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "GENERATE_YOUR_OWN_SECURE_SECRET")
echo "💡 Sample admin secret: $admin_secret"
echo ""

echo "📖 Next Steps:"
echo "=============="
echo "1. Push your code to GitHub if you haven't already"
echo "2. Go to https://railway.app and create a new project"
echo "3. Deploy TWO services from the same repository:"
echo ""
echo "   🔧 Backend Service:"
echo "   - Name: bpt-backend"
echo "   - Environment variables: See .env.railway (leave SERVICE_TYPE empty)"
echo ""
echo "   🖥️  Frontend Service:"
echo "   - Name: bpt-frontend" 
echo "   - Environment variables: SERVICE_TYPE=streamlit, BPT_API_URL=<backend-url>"
echo ""
echo "4. Test both services after deployment"
echo "5. Set up custom domains (optional)"
echo ""
echo "📚 For detailed instructions, see: RAILWAY_DEPLOYMENT.md"
echo ""
echo "🎉 Good luck with your deployment!" 