#!/usr/bin/env python3
"""
BPT Trading Assistant - Web Interface Launcher

Easy startup script for the Streamlit web interface.
Handles configuration and launches the app with appropriate settings.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import streamlit
        print(f"✅ Streamlit {streamlit.__version__} detected")
        return True
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
            print("✅ Streamlit installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install Streamlit")
            return False

def setup_environment():
    """Set up environment variables and configuration."""
    
    # Set default API URL if not configured
    if not os.getenv("BPT_API_URL"):
        os.environ["BPT_API_URL"] = "http://localhost:8000"
        print(f"🔧 Set default API URL: {os.environ['BPT_API_URL']}")
    
    # Add current directory to Python path for imports
    current_dir = Path(__file__).parent.absolute()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
        print(f"🔧 Added to Python path: {current_dir}")

def launch_streamlit(port=8501, host="localhost", dev_mode=False):
    """Launch the Streamlit application."""
    
    app_path = Path(__file__).parent / "app" / "web" / "streamlit_app.py"
    
    if not app_path.exists():
        print(f"❌ Application file not found: {app_path}")
        return False
    
    print(f"🚀 Launching BPT Web Interface...")
    print(f"🌐 URL: http://{host}:{port}")
    print(f"📁 App Path: {app_path}")
    
    # Build streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.port", str(port),
        "--server.address", host,
        "--server.headless", "true" if not dev_mode else "false",
        "--server.fileWatcherType", "auto",
        "--browser.gatherUsageStats", "false"
    ]
    
    if dev_mode:
        cmd.extend([
            "--server.runOnSave", "true",
            "--server.allowRunOnSave", "true"
        ])
    
    try:
        subprocess.run(cmd)
        return True
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        return True
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Launch BPT Trading Assistant Web Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_web_interface.py                    # Launch on default port 8501
  python run_web_interface.py --port 8080       # Launch on custom port
  python run_web_interface.py --dev             # Launch in development mode
  python run_web_interface.py --host 0.0.0.0    # Allow external connections
        """
    )
    
    parser.add_argument(
        "--port", "-p", 
        type=int, 
        default=8501,
        help="Port to run the web interface on (default: 8501)"
    )
    
    parser.add_argument(
        "--host", 
        default="localhost",
        help="Host to bind to (default: localhost, use 0.0.0.0 for external access)"
    )
    
    parser.add_argument(
        "--dev", 
        action="store_true",
        help="Enable development mode with auto-reload"
    )
    
    parser.add_argument(
        "--check-api", 
        action="store_true",
        help="Test API connection before launching"
    )
    
    args = parser.parse_args()
    
    print("🎯 BPT Trading Assistant - Web Interface Launcher")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Check API connection if requested
    if args.check_api:
        print("🔍 Testing API connection...")
        try:
            import requests
            api_url = os.getenv("BPT_API_URL", "http://localhost:8000")
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ API connection successful: {api_url}")
            else:
                print(f"⚠️ API returned status {response.status_code}: {api_url}")
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to API at {api_url}")
            print("💡 Make sure the BPT API server is running")
        except Exception as e:
            print(f"❌ API check failed: {e}")
    
    # Launch application
    success = launch_streamlit(
        port=args.port,
        host=args.host,
        dev_mode=args.dev
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 