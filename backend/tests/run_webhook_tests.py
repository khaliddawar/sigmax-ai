#!/usr/bin/env python3
"""
Webhook Test Runner

Runs all webhook integration tests in the correct order.

Usage:
    python run_webhook_tests.py
    python run_webhook_tests.py --full  # Run complete integration tests
    python run_webhook_tests.py --handlers-only  # Test only webhook handlers
    python run_webhook_tests.py --check-env  # Check environment setup only
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 CHECKING ENVIRONMENT SETUP")
    print("=" * 35)
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'PADDLE_API_KEY'
    ]
    
    optional_vars = [
        'SUPABASE_SERVICE_KEY',
        'PADDLE_NOTIFICATION_SECRET',
        'PADDLE_ENVIRONMENT'
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            print(f"✅ {var} is set")
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
        else:
            print(f"✅ {var} is set")
    
    if missing_required:
        print(f"\n❌ MISSING REQUIRED VARIABLES:")
        for var in missing_required:
            print(f"   - {var}")
        print("\n🔧 Set these variables in your .env file or environment")
        return False
    
    if missing_optional:
        print(f"\n⚠️  MISSING OPTIONAL VARIABLES:")
        for var in missing_optional:
            print(f"   - {var}")
        print("\n💡 These are recommended but not required for basic testing")
    
    print(f"\n✅ Environment check passed!")
    return True

async def run_handlers_only_test():
    """Run webhook handlers only test"""
    print("\n🧪 RUNNING WEBHOOK HANDLERS TEST")
    print("=" * 40)
    
    try:
        from test_webhook_handlers_only import WebhookHandlerTester
        
        tester = WebhookHandlerTester()
        success = await tester.run_test_suite()
        
        return success
        
    except ImportError as e:
        print(f"❌ Could not import test module: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def run_full_integration_test():
    """Run full webhook to database integration test"""
    print("\n🧪 RUNNING FULL INTEGRATION TEST")
    print("=" * 38)
    
    try:
        from test_webhook_db_integration import WebhookDatabaseTester
        
        tester = WebhookDatabaseTester()
        success = await tester.run_tests(cleanup=True)
        
        return success
        
    except ImportError as e:
        print(f"❌ Could not import test module: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported"""
    print("\n🔍 CHECKING MODULE IMPORTS")
    print("=" * 30)
    
    modules_to_test = [
        'app.services.paddle_service',
        'app.services.supabase_client',
        'app.models.payment'
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import {len(failed_imports)} modules")
        print("🔧 Make sure you're running from the project root directory")
        return False
    
    print(f"\n✅ All modules imported successfully!")
    return True

async def main():
    parser = argparse.ArgumentParser(description="Run Paddle webhook integration tests")
    parser.add_argument("--full", action="store_true", help="Run full integration tests")
    parser.add_argument("--handlers-only", action="store_true", help="Test only webhook handlers")
    parser.add_argument("--check-env", action="store_true", help="Check environment setup only")
    
    args = parser.parse_args()
    
    print("🚀 PADDLE WEBHOOK TEST SUITE")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Always check environment first
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        return 1
    
    if args.check_env:
        print("\n✅ Environment check completed successfully!")
        return 0
    
    # Test imports
    if not test_imports():
        print("\n❌ Module import check failed.")
        return 1
    
    success = True
    
    try:
        if args.handlers_only:
            # Run only webhook handlers test
            success = await run_handlers_only_test()
            
        elif args.full:
            # Run full integration test
            success = await run_full_integration_test()
            
        else:
            # Run both tests by default
            print("\n🎯 Running both tests (handlers + full integration)")
            
            # First run handlers only test
            handlers_success = await run_handlers_only_test()
            
            if handlers_success:
                # If handlers work, run full integration
                full_success = await run_full_integration_test()
                success = handlers_success and full_success
            else:
                success = False
                print("\n⚠️  Skipping full integration test due to handler failures")
        
        # Final results
        print(f"\n🏁 FINAL RESULTS")
        print("=" * 20)
        if success:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Your webhook integration is ready for deployment")
        else:
            print("❌ SOME TESTS FAILED")
            print("🔧 Please review the error messages above")
            print("💡 Fix the issues before pushing to GitHub")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n👋 Tests cancelled by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
