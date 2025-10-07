import os
import sys
import subprocess
import logging
from pathlib import Path
import uvicorn
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run-with-auth")

def check_env_variables():
    """Check if required environment variables are set"""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Authentication will run in mock mode if variables are not set")
        
        # Ask if user wants to use mock mode
        use_mock = input("Run in mock mode? (y/n): ").lower() == "y"
        if use_mock:
            os.environ["USE_MOCK_SUPABASE"] = "true"
            os.environ["USE_MOCK_USERS"] = "true"
            logger.info("Running in mock mode")
        else:
            logger.error("Cannot start without required environment variables")
            return False
    
    return True

def load_env_file(env_file=".env"):
    """Load environment variables from .env file"""
    env_path = Path(env_file)
    if not env_path.exists():
        logger.warning(f"{env_file} file not found")
        return False
    
    logger.info(f"Loading environment variables from {env_file}")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            key, value = line.split("=", 1)
            os.environ[key] = value
    
    return True

def run_setup():
    """Run setup scripts if needed"""
    
    # Check if pgvector is enabled
    try:
        from app.services.supabase_client import SupabaseService
        supabase = SupabaseService()
        
        if supabase.is_connected():
            logger.info("Checking pgvector status...")
            pgvector_result = supabase.check_pgvector_setup()
            
            if not pgvector_result["enabled"]:
                logger.warning("pgvector extension not enabled. Some functionality may not work.")
                
                # Ask if user wants to enable pgvector
                setup_pgvector = input("Setup pgvector extension? (y/n): ").lower() == "y"
                if setup_pgvector:
                    logger.info("Setting up pgvector extension...")
                    setup_result = supabase.setup_pgvector()
                    if setup_result["success"]:
                        logger.info("pgvector setup successful")
                    else:
                        logger.error(f"pgvector setup failed: {setup_result.get('error')}")
            else:
                logger.info("pgvector extension is enabled")
                
            # Check if user management tables exist
            logger.info("Checking user management tables...")
            try:
                user_table_check = supabase.client.table("user_profiles").select("count(*)", count="exact").limit(1).execute()
                logger.info("User management tables are set up")
            except Exception as e:
                logger.warning("User management tables not set up.")
                
                # Ask if user wants to set up user management
                setup_user_mgmt = input("Setup user management tables? (y/n): ").lower() == "y"
                if setup_user_mgmt:
                    try:
                        # Import setup script
                        sys.path.append(str(Path(__file__).parent / "scripts"))
                        from scripts.setup_user_management import setup_user_management
                        
                        # Run setup
                        logger.info("Setting up user management tables...")
                        import asyncio
                        result = asyncio.run(setup_user_management())
                        
                        if result:
                            logger.info("User management tables setup successful")
                        else:
                            logger.error("User management tables setup failed")
                    except Exception as e:
                        logger.error(f"Error setting up user management tables: {str(e)}")
    except Exception as e:
        logger.error(f"Error checking setup: {str(e)}")

def main():
    """Main function to run the API server"""
    parser = argparse.ArgumentParser(description="Run the API server with authentication")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    parser.add_argument("--mock", action="store_true", help="Use mock mode for authentication")
    parser.add_argument("--skip-setup", action="store_true", help="Skip setup checks")
    args = parser.parse_args()
    
    # Load environment variables
    load_env_file()
    
    # Set mock mode if requested
    if args.mock:
        os.environ["USE_MOCK_SUPABASE"] = "true"
        os.environ["USE_MOCK_USERS"] = "true"
        logger.info("Running in mock mode")
    
    # Check environment variables
    if not check_env_variables():
        return
    
    # Run setup if needed
    if not args.skip_setup:
        run_setup()
    
    # Start the API server
    logger.info(f"Starting API server on {args.host}:{args.port}")
    logger.info("Authentication is enabled")
    
    # Run uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main() 