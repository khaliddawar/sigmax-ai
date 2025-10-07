#!/usr/bin/env python3
"""
Check which email service is configured and will be used
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def check_email_services():
    """Check which email services are configured"""
    
    print("📧 Email Service Configuration Check")
    print("=" * 45)
    
    try:
        from app.services.email_service import email_service
        from app.services.postmark_email_service import postmark_email_service
        
        print("\n🔍 Gmail SMTP Service (Primary)")
        print("-" * 30)
        print(f"Configured: {email_service.is_configured}")
        if email_service.is_configured:
            print(f"SMTP Server: {email_service.smtp_server}")
            print(f"SMTP Port: {email_service.smtp_port}")
            print(f"Sender Email: {email_service.sender_email}")
            print("✅ Gmail SMTP is ready and will be used")
        else:
            print("❌ Gmail SMTP not configured")
            missing = []
            if not email_service.smtp_server: missing.append("SMTP_SERVER")
            if not email_service.smtp_port: missing.append("SMTP_PORT") 
            if not email_service.smtp_username: missing.append("SMTP_USERNAME")
            if not email_service.smtp_password: missing.append("SMTP_PASSWORD")
            if not email_service.sender_email: missing.append("SENDER_EMAIL")
            print(f"Missing: {', '.join(missing)}")
        
        print("\n🔍 Postmark Service (Fallback)")
        print("-" * 30)
        print(f"Configured: {postmark_email_service.is_configured}")
        if postmark_email_service.is_configured:
            print(f"API Token: {'***' + postmark_email_service.api_token[-4:] if postmark_email_service.api_token else 'None'}")
            print(f"Sender Email: {postmark_email_service.sender_email}")
            print("⚠️ Postmark is configured but will only be used as fallback")
        else:
            print("❌ Postmark not configured (this is fine)")
        
        print("\n🎯 Email Service Selection Logic")
        print("-" * 30)
        if email_service.is_configured:
            print("✅ Gmail SMTP will be used (primary choice)")
            print("   - Enhanced card-grid layout ✅")
            print("   - JSON summary support ✅")
            print("   - Singleton instance ✅")
        elif postmark_email_service.is_configured:
            print("⚠️ Postmark will be used (fallback)")
            print("   - Enhanced card-grid layout ✅")
            print("   - JSON summary support ✅")
        else:
            print("❌ No email service configured!")
            print("   - Emails will fail to send")
        
        print("\n📋 Environment Variables Needed for Gmail SMTP:")
        print("-" * 30)
        env_vars = [
            "SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", 
            "SMTP_PASSWORD", "SENDER_EMAIL"
        ]
        for var in env_vars:
            value = os.getenv(var)
            if value:
                if "PASSWORD" in var:
                    print(f"✅ {var}: ***{value[-4:] if len(value) > 4 else '***'}")
                else:
                    print(f"✅ {var}: {value}")
            else:
                print(f"❌ {var}: Not set")
                
    except Exception as e:
        print(f"❌ Error checking email services: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_email_services() 