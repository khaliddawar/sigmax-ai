#!/usr/bin/env python
# run_with_ingestion.py - Starts the BPT server with ingestion pipeline enabled

import os
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run-with-ingestion")

def start_server():
    """Start the FastAPI server with ingestion pipeline enabled"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start BPT server with ingestion pipeline")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--file-storage", action="store_true", help="Use file storage instead of Supabase")
    parser.add_argument("--mock", action="store_true", help="Use mock services")
    parser.add_argument("--env", help="Path to .env file")
    args = parser.parse_args()
    
    # Load environment variables
    if args.env:
        load_dotenv(args.env)
        logger.info(f"Loaded environment variables from {args.env}")
    else:
        load_dotenv()
        logger.info("Loaded environment variables from .env")
    
    # Override environment variables based on command line arguments
    if args.file_storage:
        # Clear Supabase URL and key to force file storage
        os.environ["SUPABASE_URL"] = ""
        os.environ["SUPABASE_KEY"] = ""
        logger.info("Using file storage instead of Supabase")
        
        # Check if Supabase credentials are missing
        if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
            logger.info("Missing Supabase variables: SUPABASE_URL, SUPABASE_KEY")
            logger.info("Will use local file storage instead of Supabase")
        
    if args.mock:
        os.environ["USE_MOCK_SUPABASE"] = "true"
        os.environ["USE_MOCK_OPENAI"] = "true"
        os.environ["USE_MOCK_EMAIL"] = "true"
        logger.info("Using mock services")
        
    # Disable webhook signature verification
    os.environ["WEBHOOK_VERIFY_SIGNATURES"] = "false"
    logger.info("Webhook signature verification disabled")
        
    # Check for required environment variables
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        sys.exit(1)
        
    # Check for optional environment variables
    optional_vars = ["SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", 
                    "SMTP_PASSWORD", "SENDER_EMAIL", "ADMIN_EMAIL"]
    missing_optional = [var for var in optional_vars if not os.environ.get(var)]
    
    if missing_optional:
        logger.warning(f"Missing optional environment variables: {', '.join(missing_optional)}")
        logger.warning("Email functionality will not work without SMTP configuration")
        os.environ["USE_MOCK_EMAIL"] = "true"
        logger.info("Email service will run in mock mode")
        
    # Start the server
    logger.info(f"Starting server on http://{args.host}:{args.port}")
    logger.info(f"API documentation will be available at http://localhost:{args.port}/docs")
    logger.info(f"To test the webhook, you can use: python scripts/test_ingestion_pipeline.py")
    
    # Import and run Uvicorn
    import uvicorn
    from app.main import app
    
    uvicorn.run(app, host=args.host, port=args.port)
    
if __name__ == "__main__":
    start_server() 