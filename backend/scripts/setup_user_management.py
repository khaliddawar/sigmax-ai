import os
import sys
import argparse
import asyncio
from pathlib import Path

# Add the app directory to path to allow importing modules
script_dir = Path(__file__).parent
root_dir = script_dir.parent
sys.path.append(str(root_dir))

# Import services
from app.services.supabase_client import SupabaseService

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("user-management-setup")

async def check_user_management_setup():
    """Check if user management tables are set up"""
    logger.info("Checking if user management tables are set up...")
    
    # Initialize Supabase client
    supabase_service = SupabaseService()
    
    if not supabase_service.is_connected():
        logger.error("Supabase client not connected. Check your credentials.")
        return False
    
    try:
        # Check if user_profiles table exists
        result = supabase_service.client.table("user_profiles").select("count(*)", count="exact").limit(1).execute()
        logger.info("User management tables are already set up.")
        return True
    except Exception as e:
        logger.info("User management tables are not set up.")
        return False

async def setup_user_management():
    """Set up user management tables"""
    logger.info("Setting up user management tables...")
    
    # Initialize Supabase client
    supabase_service = SupabaseService()
    
    if not supabase_service.is_connected():
        logger.error("Supabase client not connected. Check your credentials.")
        return False
    
    try:
        # Read SQL script
        sql_path = Path(__file__).parent / "setup_user_management.sql"
        with open(sql_path, "r") as f:
            sql = f.read()
        
        # Split into individual statements
        # This simple approach assumes statements are separated by semicolons
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
        
        # Execute each statement
        for i, stmt in enumerate(statements):
            try:
                result = supabase_service.client.rpc("exec_sql", {"sql": stmt}).execute()
                logger.info(f"Executed statement {i+1}/{len(statements)}")
            except Exception as e:
                logger.error(f"Error executing statement {i+1}: {str(e)}")
                logger.error(f"Statement: {stmt}")
                # Continue with next statement
                continue
        
        logger.info("User management tables setup completed.")
        return True
    except Exception as e:
        logger.error(f"Error setting up user management tables: {str(e)}")
        return False

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Set up user management tables")
    parser.add_argument("action", choices=["check", "setup"], help="Action to perform")
    args = parser.parse_args()
    
    if args.action == "check":
        result = await check_user_management_setup()
        if result:
            logger.info("User management tables are already set up.")
        else:
            logger.info("User management tables are not set up.")
    elif args.action == "setup":
        # Check if already set up
        already_setup = await check_user_management_setup()
        if already_setup:
            logger.info("User management tables are already set up.")
            return
        
        # Set up tables
        result = await setup_user_management()
        if result:
            logger.info("User management tables have been set up successfully.")
        else:
            logger.error("Failed to set up user management tables.")

if __name__ == "__main__":
    asyncio.run(main()) 