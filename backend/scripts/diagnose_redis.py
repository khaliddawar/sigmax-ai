#!/usr/bin/env python3
"""
Redis Connection Diagnostic Script
Helps diagnose Redis connection issues with Render.com

Usage:
    python scripts/diagnose_redis.py
"""

import os
import sys
import socket
import logging
from pathlib import Path
from urllib.parse import urlparse

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_dns_resolution():
    """Test DNS resolution for Redis host"""
    redis_url = os.getenv('REDIS_URL', '')
    
    if not redis_url:
        logger.error("❌ REDIS_URL not found in environment variables")
        return False
    
    logger.info(f"🔗 Testing DNS resolution for: {redis_url}")
    
    try:
        # Parse the Redis URL
        parsed = urlparse(redis_url)
        hostname = parsed.hostname
        port = parsed.port or 6379
        
        logger.info(f"📍 Hostname: {hostname}")
        logger.info(f"📍 Port: {port}")
        
        # Test DNS resolution
        logger.info("🔍 Testing DNS resolution...")
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"✅ DNS resolved to: {ip_address}")
        
        # Test port connectivity
        logger.info(f"🔌 Testing port connectivity to {hostname}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            logger.info(f"✅ Port {port} is reachable!")
            return True
        else:
            logger.error(f"❌ Port {port} is not reachable (error code: {result})")
            logger.error("💡 This might be due to:")
            logger.error("   1. Redis service not fully deployed")
            logger.error("   2. Firewall/Access Control restrictions")
            logger.error("   3. External access not enabled")
            return False
            
    except socket.gaierror as e:
        logger.error(f"❌ DNS resolution failed: {e}")
        logger.error("💡 Possible causes:")
        logger.error("   1. Incorrect hostname in REDIS_URL")
        logger.error("   2. Redis service not fully deployed")
        logger.error("   3. Network connectivity issues")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def check_environment_config():
    """Check Redis environment configuration"""
    logger.info("🔧 Checking environment configuration...")
    
    redis_vars = [
        'REDIS_URL',
        'REDIS_HOST', 
        'REDIS_PORT',
        'REDIS_PASSWORD',
        'REDIS_DB'
    ]
    
    for var in redis_vars:
        value = os.getenv(var, 'NOT SET')
        if var == 'REDIS_PASSWORD' and value:
            value = '*' * len(value)  # Hide password
        logger.info(f"   {var}: {value}")

def get_public_ip():
    """Get our public IP address"""
    try:
        import requests
        response = requests.get('https://api.ipify.org', timeout=5)
        public_ip = response.text.strip()
        logger.info(f"🌐 Your public IP address: {public_ip}")
        logger.info("💡 You may need to add this IP to Render.com Redis Access Control")
        return public_ip
    except Exception as e:
        logger.warning(f"⚠️  Could not determine public IP: {e}")
        return None

def main():
    """Main diagnostic function"""
    logger.info("🚀 Starting Redis Connection Diagnostics")
    logger.info("=" * 60)
    
    # Check environment configuration
    check_environment_config()
    logger.info("=" * 60)
    
    # Get public IP
    get_public_ip()
    logger.info("=" * 60)
    
    # Test DNS and connectivity
    success = test_dns_resolution()
    logger.info("=" * 60)
    
    if success:
        logger.info("🎉 Network connectivity looks good!")
        logger.info("📋 Next step: Try Redis connection test again")
        logger.info("   python scripts/test_redis_connection.py")
    else:
        logger.error("❌ Network connectivity issues detected")
        logger.info("🔧 Troubleshooting steps:")
        logger.info("   1. Check Redis service status in Render.com dashboard")
        logger.info("   2. Verify the service shows 'Live' status")
        logger.info("   3. Check if Access Control is restricting external connections")
        logger.info("   4. Add your public IP to Access Control if needed")
        logger.info("   5. Wait a few minutes for DNS propagation")

if __name__ == "__main__":
    main() 