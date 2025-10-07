import os
import sys
import json
import logging
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bpt-check")

def check_environment_variables():
    """Check if all required environment variables are set"""
    logger.info("Checking environment variables...")
    
    # OpenAI Configuration
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        if len(openai_api_key) > 10:
            logger.info("✅ OPENAI_API_KEY: Configured")
        else:
            logger.warning("❌ OPENAI_API_KEY: Invalid (too short)")
    else:
        logger.warning("❌ OPENAI_API_KEY: Not configured")
    
    # Supabase Configuration
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        logger.info("✅ Supabase: Configured")
    else:
        logger.warning("❌ Supabase: Not fully configured")
    
    # Email Configuration
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL")
    admin_email = os.getenv("ADMIN_EMAIL")
    
    if all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email, admin_email]):
        logger.info("✅ Email: Fully configured")
    elif any([smtp_server, smtp_port, smtp_username, smtp_password, sender_email, admin_email]):
        logger.warning("⚠️ Email: Partially configured")
        missing = []
        if not smtp_server: missing.append("SMTP_SERVER")
        if not smtp_port: missing.append("SMTP_PORT")
        if not smtp_username: missing.append("SMTP_USERNAME")
        if not smtp_password: missing.append("SMTP_PASSWORD")
        if not sender_email: missing.append("SENDER_EMAIL")
        if not admin_email: missing.append("ADMIN_EMAIL")
        logger.warning(f"  Missing: {', '.join(missing)}")
    else:
        logger.warning("❌ Email: Not configured")
    
    # Slack Configuration
    slack_app_token = os.getenv("SLACK_APP_TOKEN")
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    if slack_app_token and slack_bot_token:
        logger.info("✅ Slack: Configured")
    else:
        logger.warning("❌ Slack: Not fully configured")
    
    # Fireflies Configuration
    fireflies_webhook_secret = os.getenv("FIREFLIES_WEBHOOK_SECRET")
    if fireflies_webhook_secret:
        logger.info("✅ Fireflies webhook secret: Configured")
    else:
        logger.warning("❌ Fireflies webhook secret: Not configured")

def check_file_storage():
    """Check if file storage is properly configured"""
    logger.info("Checking file storage...")
    
    data_dir = Path("data")
    expected_subdirs = ["transcripts", "chunks", "embeddings", "trades"]
    
    if not data_dir.exists():
        logger.warning("❌ Data directory not found, creating it...")
        data_dir.mkdir(exist_ok=True)
        for subdir in expected_subdirs:
            (data_dir / subdir).mkdir(exist_ok=True)
        logger.info("✅ Created data directory structure")
    else:
        logger.info("✅ Data directory exists")
        
        # Check subdirectories
        missing_dirs = []
        for subdir in expected_subdirs:
            if not (data_dir / subdir).exists():
                missing_dirs.append(subdir)
                (data_dir / subdir).mkdir(exist_ok=True)
        
        if missing_dirs:
            logger.warning(f"⚠️ Created missing subdirectories: {', '.join(missing_dirs)}")
        else:
            logger.info("✅ All expected subdirectories exist")
    
    # Check if any data has been stored
    has_data = False
    for subdir in expected_subdirs:
        if any((data_dir / subdir).iterdir()):
            has_data = True
            break
    
    if has_data:
        logger.info("✅ Data has been stored in the file system")
    else:
        logger.warning("⚠️ No data found in storage directories")

def check_server_status():
    """Check if the server is running"""
    logger.info("Checking server status...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            logger.info("✅ Server is running on port 8000")
            
            # Check status from health endpoint
            try:
                status = response.json()
                if "status" in status and status["status"] == "ok":
                    logger.info("✅ Server health check passed")
                    
                    # Check individual services if reported
                    if "services" in status:
                        services = status["services"]
                        for service, service_status in services.items():
                            status_symbol = "✅" if service_status.get("status") == "ok" else "❌"
                            logger.info(f"{status_symbol} {service}: {service_status.get('status', 'unknown')}")
                else:
                    logger.warning("⚠️ Server health check did not return 'ok' status")
            except json.JSONDecodeError:
                logger.warning("⚠️ Server health check did not return valid JSON")
        else:
            logger.warning(f"⚠️ Server returned status code {response.status_code}")
    except requests.RequestException:
        logger.warning("❌ Server is not running on port 8000")
    
    # Check if the server is running on other common ports
    for port in [8001, 8002]:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            logger.info(f"✅ Server is also running on port {port}")
        except requests.RequestException:
            pass

def check_transcript_file():
    """Check if test_transcript.txt exists and is valid"""
    logger.info("Checking test transcript file...")
    
    # Check in the new config directory location
    transcript_path = Path("config/test_transcript.txt")
    if not transcript_path.exists():
        # Also check the old location for backward compatibility
        old_transcript_path = Path("test_transcript.txt")
        if old_transcript_path.exists():
            logger.info(f"✅ test_transcript.txt found in root directory ({old_transcript_path.stat().st_size} bytes)")
            logger.info("   Consider moving it to config/ directory for better organization")
            return
        else:
            logger.warning("❌ test_transcript.txt not found in config/ or root directory")
            return
    
    # Check file size
    file_size = transcript_path.stat().st_size
    if file_size < 100:
        logger.warning(f"⚠️ test_transcript.txt is very small ({file_size} bytes)")
    else:
        logger.info(f"✅ test_transcript.txt exists in config/ ({file_size} bytes)")

def check_ngrok():
    """Check if ngrok is running and forwarding properly"""
    logger.info("Checking ngrok status...")
    
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        if response.status_code == 200:
            tunnels = response.json().get("tunnels", [])
            if tunnels:
                for tunnel in tunnels:
                    logger.info(f"✅ Ngrok tunnel: {tunnel['public_url']} -> {tunnel['config']['addr']}")
            else:
                logger.warning("❌ No active ngrok tunnels found")
        else:
            logger.warning(f"⚠️ Ngrok API returned status code {response.status_code}")
    except requests.RequestException:
        logger.warning("❌ Ngrok is not running (API not available on port 4040)")

if __name__ == "__main__":
    logger.info("=== BPT Service Check ===")
    check_environment_variables()
    logger.info("")
    check_file_storage()
    logger.info("")
    check_server_status()
    logger.info("")
    check_transcript_file()
    logger.info("")
    check_ngrok()
    logger.info("")
    logger.info("=== Check Complete ===")
    
    # Try to add a health endpoint if user wants to verify
    if "--add-health" in sys.argv:
        try:
            with open("app/routes/health_routes.py", "w") as f:
                f.write('''
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
''')
            logger.info("✅ Added health endpoint at /health")
            logger.info("   Restart the server to apply changes")
        except Exception as e:
            logger.error(f"❌ Failed to add health endpoint: {str(e)}") 