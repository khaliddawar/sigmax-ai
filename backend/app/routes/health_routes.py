from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/health")
async def health():
    """Health check endpoint"""
    # Check environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    # Compile service status
    services = {
        "openai": {
            "status": "ok" if openai_api_key else "not_configured"
        },
        "supabase": {
            "status": "ok" if (supabase_url and supabase_key) else "not_configured"
        },
        "email": {
            "status": "ok" if all([
                os.getenv("SMTP_SERVER"),
                os.getenv("SMTP_PORT"),
                os.getenv("SMTP_USERNAME"),
                os.getenv("SMTP_PASSWORD")
            ]) else "not_configured"
        }
    }
    
    return {
        "status": "ok",
        "services": services
    } 