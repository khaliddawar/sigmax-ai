#!/usr/bin/env python3
"""
Webhook Setup Checker

Quick diagnostic script to check if webhook integration is properly configured.

Usage:
    python check_webhook_setup.py
"""

import os
import sys
from datetime import datetime

def check_env_vars():
    """Check environment variables"""
    print("🔍 Environment Variables")
    print("-" * 25)
    
    env_vars = {
        'SUPABASE_URL': {'required': True, 'description': 'Supabase project URL'},
        'SUPABASE_ANON_KEY': {'required': True, 'description': 'Supabase anonymous key'},
        'SUPABASE_SERVICE_KEY': {'required': False, 'description': 'Supabase service role key'},
        'PADDLE_API_KEY': {'required': True, 'description': 'Paddle API key'},
        'PADDLE_NOTIFICATION_SECRET': {'required': False, 'description': 'Paddle webhook secret'},
        'PADDLE_ENVIRONMENT': {'required': False, 'description': 'Paddle environment (sandbox/production)'},
    }
    
    missing_required = []
    
    for var, config in env_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var} = {display_value}")
        else:
            status = "❌ REQUIRED" if config['required'] else "⚠️  OPTIONAL"
            print(f"{status} {var} - {config['description']}")
            if config['required']:
                missing_required.append(var)
    
    return len(missing_required) == 0

def check_imports():
    """Check if required modules can be imported"""
    print("\n🔍 Module Imports")
    print("-" * 18)
    
    modules = [
        ('app.services.paddle_service', 'PaddleService'),
        ('app.services.supabase_client', 'SupabaseService'),
        ('app.models.payment', 'Payment models'),
    ]
    
    failed = []
    
    for module, description in modules:
        try:
            __import__(module)
            print(f"✅ {description}")
        except Exception as e:
            print(f"❌ {description}: {e}")
            failed.append(module)
    
    return len(failed) == 0

def test_supabase_connection():
    """Test Supabase connection"""
    print("\n🔍 Supabase Connection")
    print("-" * 22)
    
    try:
        from app.services.supabase_client import get_supabase_client, SupabaseService
        
        # Try global client first
        supabase = get_supabase_client()
        if supabase:
            print("✅ Global Supabase client available")
            return True
        
        # Try creating new service
        service = SupabaseService()
        if service.initialized:
            print("✅ SupabaseService can be initialized")
            return True
        else:
            print("❌ SupabaseService failed to initialize")
            return False
            
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def test_paddle_service():
    """Test PaddleService initialization"""
    print("\n🔍 PaddleService Initialization")
    print("-" * 32)
    
    try:
        from app.services.paddle_service import PaddleService
        
        service = PaddleService()
        
        # Check API key
        if service.api_key:
            print("✅ Paddle API key configured")
        else:
            print("⚠️  Paddle API key not set")
        
        # Check Supabase client
        if service.supabase:
            print("✅ PaddleService has Supabase client")
        else:
            print("❌ PaddleService missing Supabase client")
            return False
        
        # Check notification secrets
        if service.notification_secrets:
            print(f"✅ {len(service.notification_secrets)} notification secret(s) configured")
        else:
            print("⚠️  No notification secrets configured")
        
        print(f"✅ PaddleService environment: {service.environment}")
        return True
        
    except Exception as e:
        print(f"❌ PaddleService initialization failed: {e}")
        return False

def check_database_tables():
    """Check if required database tables exist"""
    print("\n🔍 Database Tables")
    print("-" * 19)
    
    try:
        from app.services.supabase_client import get_supabase_client, SupabaseService
        
        supabase = get_supabase_client()
        if not supabase:
            service = SupabaseService()
            if service.initialized:
                supabase = service.client
            else:
                print("❌ Cannot connect to Supabase")
                return False
        
        tables_to_check = ['user_profiles', 'subscriptions', 'payments']
        
        for table in tables_to_check:
            try:
                # Try to query the table (limit 0 to avoid data)
                result = supabase.table(table).select("*").limit(0).execute()
                print(f"✅ {table} table exists")
            except Exception as e:
                print(f"❌ {table} table issue: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database table check failed: {e}")
        return False

def main():
    print("🔧 PADDLE WEBHOOK SETUP CHECKER")
    print("=" * 45)
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    checks = [
        ("Environment Variables", check_env_vars),
        ("Module Imports", check_imports),
        ("Supabase Connection", test_supabase_connection),
        ("PaddleService Initialization", test_paddle_service),
        ("Database Tables", check_database_tables),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            results.append((check_name, False))
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 15)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\nResults: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Your webhook setup looks good.")
        print("✅ You can proceed with testing and deployment.")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("🔧 Run the fixes and try again.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
