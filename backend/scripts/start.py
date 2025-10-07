#!/usr/bin/env python3
"""
Python startup script for Railway deployment
This replaces the bash script to ensure better compatibility
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("startup")

def main():
    """Main startup function"""
    logger.info("🚀 BPT Application Starting...")
    
    # Get environment variables
    service_type = os.getenv("SERVICE_TYPE", "").lower()
    port = os.getenv("PORT", "8000")
    
    logger.info(f"Service Type: {service_type or 'default (FastAPI)'}")
    logger.info(f"Port: {port}")
    
    # Ensure Python path includes current directory
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        logger.info(f"Working directory: {current_dir}")
        logger.info(f"Python path: {sys.path[:3]}...")
    
    try:
        if service_type == "frontend":
            # Start Streamlit frontend
            logger.info("Starting Streamlit frontend...")
            
            # Run Streamlit from current working directory (imports now handled in streamlit_app.py)
            cmd = [
                "streamlit", "run", "app/web/streamlit_app.py",
                "--server.port", str(port),
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--server.enableCORS", "false"
            ]
            
            logger.info(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True)
            return result.returncode
            
        else:
            # Default to FastAPI backend - Force deployment 2025-01-06
            logger.info("Starting FastAPI backend...")
            
            # Use app.main:app since app directory structure is maintained
            uvicorn_cmd = [
                "uvicorn", 
                "app.main:app",  # App directory structure maintained
                "--host", "0.0.0.0", 
                "--port", port
            ]
            
            logger.info(f"Executing: {' '.join(uvicorn_cmd)}")
            
            # Execute uvicorn
            result = subprocess.run(uvicorn_cmd, check=True)
            return result.returncode
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to start application: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 