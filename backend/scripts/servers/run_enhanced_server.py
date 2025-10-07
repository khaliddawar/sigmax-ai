#!/usr/bin/env python3
"""
Enhanced Server Startup Script

This script starts the enhanced BPT API server and optionally runs tests.
"""

import subprocess
import sys
import time
import asyncio
import os
from pathlib import Path

def start_server():
    """Start the enhanced API server"""
    print("🚀 Starting Enhanced BPT API Server...")
    print("=" * 50)
    
    # Change to the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Start the server
    try:
        print("Starting server on http://localhost:8000")
        print("Enhanced features:")
        print("  • Semantic chunking with rich metadata")
        print("  • Vector-based similarity search")
        print("  • Domain-agnostic entity extraction")
        print("  • Sentiment analysis")
        print("  • Enhanced Q&A with confidence scoring")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Run the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def run_tests():
    """Run the enhanced API tests"""
    print("🧪 Running Enhanced API Tests...")
    print("=" * 50)
    
    try:
        # Run the test script
        result = subprocess.run([
            sys.executable, "test_enhanced_api.py"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run tests only
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        # Start server
        start_server() 