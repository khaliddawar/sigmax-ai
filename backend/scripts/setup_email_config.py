#!/usr/bin/env python3
"""
Setup email configuration for BPT project
This script configures the necessary SMTP settings for Railway deployment
"""

import os
import subprocess
import sys

def setup_email_config():
    """Configure email settings for Railway deployment"""
    
    print("🔧 Setting up email configuration for BPT...")
    
    # Email configuration settings
    email_configs = {
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SENDER_EMAIL": "bptcompanion@gmail.com",
        # Note: SMTP_USERNAME and SMTP_PASSWORD need to be set manually
        # for security reasons
    }
    
    print("\n📧 Setting basic SMTP configuration...")
    
    try:
        # Set each configuration variable
        for key, value in email_configs.items():
            cmd = f"railway variables --set {key}={value} --service BPT"
            print(f"Setting {key}...")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {key} set successfully")
            else:
                print(f"❌ Failed to set {key}: {result.stderr}")
                return False
        
        print("\n🔑 Manual steps required:")
        print("1. Set SMTP_USERNAME (Gmail email address):")
        print("   railway variables --set SMTP_USERNAME=your_email@gmail.com --service BPT")
        print("\n2. Set SMTP_PASSWORD (Gmail app password):")
        print("   railway variables --set SMTP_PASSWORD=your_app_password --service BPT")
        print("\n📝 To create a Gmail app password:")
        print("   1. Go to https://myaccount.google.com/security")
        print("   2. Enable 2-Factor Authentication if not already enabled")
        print("   3. Go to 'App passwords' and generate a new password")
        print("   4. Use that 16-character password (not your regular Gmail password)")
        
        print("\n✅ Basic email configuration completed!")
        print("⚠️  Don't forget to set SMTP_USERNAME and SMTP_PASSWORD manually for security")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up email configuration: {str(e)}")
        return False

def test_email_config():
    """Test if email configuration is complete"""
    print("\n🧪 Testing email configuration...")
    
    required_vars = ["SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SENDER_EMAIL"]
    
    try:
        # Get current variables
        result = subprocess.run("railway variables --service BPT", shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ Failed to get Railway variables")
            return False
        
        # Check which variables are set
        variables_output = result.stdout
        set_vars = []
        missing_vars = []
        
        for var in required_vars:
            if var in variables_output:
                set_vars.append(var)
            else:
                missing_vars.append(var)
        
        print(f"✅ Set variables: {', '.join(set_vars)}")
        if missing_vars:
            print(f"❌ Missing variables: {', '.join(missing_vars)}")
            return False
        else:
            print("✅ All email configuration variables are set!")
            return True
            
    except Exception as e:
        print(f"❌ Error testing configuration: {str(e)}")
        return False

def main():
    """Main function"""
    print("BPT Email Configuration Setup")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_email_config()
    else:
        setup_email_config()
        print("\n" + "=" * 40)
        print("Run 'python scripts/setup_email_config.py test' to verify configuration")

if __name__ == "__main__":
    main() 