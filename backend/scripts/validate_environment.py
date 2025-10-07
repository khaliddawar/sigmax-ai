#!/usr/bin/env python3
"""
Environment Validation Script for Simply Authentication & Payment System

This script validates that all required environment variables are properly configured
for the Simply Chrome extension with authentication and payment features.
"""

import os
import sys
import re
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv


class EnvironmentValidator:
    """Validates environment configuration for Simply system"""
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize validator and load environment variables"""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.successes: List[str] = []
        
    def validate_all(self) -> Dict[str, any]:
        """Run all validation checks"""
        print("🔍 Validating Simply Environment Configuration...")
        print("=" * 60)
        
        # Core validations
        self._validate_supabase()
        self._validate_authentication()
        self._validate_payment_system()
        self._validate_email_service()
        self._validate_ai_services()
        self._validate_security()
        self._validate_cors()
        
        # Optional validations
        self._validate_redis()
        self._validate_environment_type()
        
        return self._generate_report()
    
    def _validate_supabase(self) -> None:
        """Validate Supabase configuration"""
        print("📊 Checking Supabase Configuration...")
        
        url = os.getenv("SUPABASE_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url:
            self.issues.append("SUPABASE_URL is required")
        elif not url.startswith("https://") or not url.endswith(".supabase.co"):
            self.issues.append("SUPABASE_URL format invalid (should be https://xxx.supabase.co)")
        else:
            self.successes.append("SUPABASE_URL configured correctly")
            
        if not anon_key:
            self.issues.append("SUPABASE_ANON_KEY (or SUPABASE_KEY) is required")
        elif not self._is_valid_jwt(anon_key):
            self.issues.append("SUPABASE_ANON_KEY appears to be invalid JWT")
        else:
            self.successes.append("SUPABASE_ANON_KEY configured correctly")
            
        if not service_key:
            self.issues.append("SUPABASE_SERVICE_ROLE_KEY is required for backend operations")
        elif not self._is_valid_jwt(service_key):
            self.issues.append("SUPABASE_SERVICE_ROLE_KEY appears to be invalid JWT")
        else:
            self.successes.append("SUPABASE_SERVICE_ROLE_KEY configured correctly")
    
    def _validate_authentication(self) -> None:
        """Validate authentication configuration"""
        print("🔐 Checking Authentication Configuration...")
        
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        jwt_expiration = os.getenv("JWT_EXPIRATION_HOURS", "24")
        
        if not jwt_secret:
            self.issues.append("JWT_SECRET_KEY is required for authentication")
        elif len(jwt_secret) < 32:
            self.issues.append("JWT_SECRET_KEY should be at least 32 characters long")
        elif jwt_secret in ["your-super-secure-jwt-secret-key-here", "dev-jwt-secret-key-change-in-production"]:
            self.issues.append("JWT_SECRET_KEY is using default/example value - change in production")
        else:
            self.successes.append("JWT_SECRET_KEY configured correctly")
            
        if jwt_algorithm not in ["HS256", "HS384", "HS512"]:
            self.warnings.append(f"JWT_ALGORITHM '{jwt_algorithm}' is unusual, typically use HS256")
        else:
            self.successes.append(f"JWT_ALGORITHM set to {jwt_algorithm}")
            
        try:
            expiration_hours = int(jwt_expiration)
            if expiration_hours < 1 or expiration_hours > 168:  # 1 hour to 1 week
                self.warnings.append(f"JWT_EXPIRATION_HOURS ({expiration_hours}) seems unusual")
            else:
                self.successes.append(f"JWT_EXPIRATION_HOURS set to {expiration_hours} hours")
        except ValueError:
            self.issues.append("JWT_EXPIRATION_HOURS must be a valid number")
    
    def _validate_payment_system(self) -> None:
        """Validate Paddle payment system configuration"""
        print("💳 Checking Payment System Configuration...")
        
        vendor_id = os.getenv("PADDLE_VENDOR_ID")
        api_key = os.getenv("PADDLE_API_KEY")
        environment = os.getenv("PADDLE_ENVIRONMENT", "sandbox")
        
        if not vendor_id:
            self.warnings.append("PADDLE_VENDOR_ID not set - payment features will be disabled")
        elif not vendor_id.isdigit():
            self.issues.append("PADDLE_VENDOR_ID should be numeric")
        else:
            self.successes.append("PADDLE_VENDOR_ID configured")
            
        if not api_key:
            self.warnings.append("PADDLE_API_KEY not set - payment features will be disabled")
        elif api_key.startswith("your_"):
            self.issues.append("PADDLE_API_KEY is using placeholder value")
        else:
            self.successes.append("PADDLE_API_KEY configured")
            
        if environment not in ["sandbox", "production"]:
            self.issues.append("PADDLE_ENVIRONMENT must be 'sandbox' or 'production'")
        else:
            self.successes.append(f"PADDLE_ENVIRONMENT set to {environment}")
            
        # Check product IDs
        premium_id = os.getenv("PADDLE_PRODUCT_ID_PREMIUM")
        enterprise_id = os.getenv("PADDLE_PRODUCT_ID_ENTERPRISE")
        
        if not premium_id:
            self.warnings.append("PADDLE_PRODUCT_ID_PREMIUM not set")
        elif not premium_id.isdigit():
            self.issues.append("PADDLE_PRODUCT_ID_PREMIUM should be numeric")
        else:
            self.successes.append("PADDLE_PRODUCT_ID_PREMIUM configured")
            
        if not enterprise_id:
            self.warnings.append("PADDLE_PRODUCT_ID_ENTERPRISE not set")
        elif not enterprise_id.isdigit():
            self.issues.append("PADDLE_PRODUCT_ID_ENTERPRISE should be numeric")
        else:
            self.successes.append("PADDLE_PRODUCT_ID_ENTERPRISE configured")
    
    def _validate_email_service(self) -> None:
        """Validate email service configuration"""
        print("📧 Checking Email Service Configuration...")
        
        # Check SMTP configuration
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("SENDER_EMAIL")
        
        # Check Postmark configuration
        postmark_token = os.getenv("POSTMARK_API_TOKEN")
        postmark_sender = os.getenv("POSTMARK_SENDER_EMAIL")
        
        has_smtp = all([smtp_server, smtp_username, smtp_password, sender_email])
        has_postmark = all([postmark_token, postmark_sender])
        
        if not has_smtp and not has_postmark:
            self.issues.append("Either SMTP or Postmark email configuration is required")
        elif has_smtp and has_postmark:
            self.warnings.append("Both SMTP and Postmark configured - Postmark will be preferred")
        
        if has_smtp:
            if not self._is_valid_email(sender_email):
                self.issues.append("SENDER_EMAIL is not a valid email address")
            else:
                self.successes.append("SMTP email service configured")
                
        if has_postmark:
            if not self._is_valid_email(postmark_sender):
                self.issues.append("POSTMARK_SENDER_EMAIL is not a valid email address")
            else:
                self.successes.append("Postmark email service configured")
    
    def _validate_ai_services(self) -> None:
        """Validate AI service configuration"""
        print("🤖 Checking AI Services Configuration...")
        
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        
        if not openai_key:
            self.issues.append("OPENAI_API_KEY is required for core functionality")
        elif openai_key.startswith("your_") or "your_openai_api_key_here" in openai_key:
            self.issues.append("OPENAI_API_KEY is using placeholder value")
        elif not openai_key.startswith("sk-"):
            self.issues.append("OPENAI_API_KEY format appears invalid (should start with 'sk-')")
        else:
            self.successes.append("OPENAI_API_KEY configured correctly")
            
        if anthropic_key:
            if not anthropic_key.startswith("sk-ant-"):
                self.warnings.append("ANTHROPIC_API_KEY format appears invalid (should start with 'sk-ant-')")
            else:
                self.successes.append("ANTHROPIC_API_KEY configured")
        else:
            self.warnings.append("ANTHROPIC_API_KEY not set - Claude features disabled")
            
        if perplexity_key:
            if not perplexity_key.startswith("pplx-"):
                self.warnings.append("PERPLEXITY_API_KEY format appears invalid (should start with 'pplx-')")
            else:
                self.successes.append("PERPLEXITY_API_KEY configured")
        else:
            self.warnings.append("PERPLEXITY_API_KEY not set - research features disabled")
    
    def _validate_security(self) -> None:
        """Validate security configuration"""
        print("🛡️ Checking Security Configuration...")
        
        environment = os.getenv("ENVIRONMENT", "development")
        debug = os.getenv("DEBUG", "false").lower()
        
        if environment == "production":
            if debug == "true":
                self.issues.append("DEBUG should be 'false' in production environment")
            else:
                self.successes.append("DEBUG properly disabled for production")
                
            # Check for development values in production
            jwt_secret = os.getenv("JWT_SECRET_KEY", "")
            if "dev" in jwt_secret.lower():
                self.issues.append("JWT_SECRET_KEY contains 'dev' - use production secret")
        else:
            self.successes.append(f"Environment set to {environment}")
    
    def _validate_cors(self) -> None:
        """Validate CORS configuration"""
        print("🌐 Checking CORS Configuration...")
        
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
        chrome_extension_id = os.getenv("CHROME_EXTENSION_ID")
        
        if not allowed_origins:
            self.warnings.append("ALLOWED_ORIGINS not set - may cause CORS issues")
        elif "chrome-extension://" not in allowed_origins:
            self.warnings.append("ALLOWED_ORIGINS should include chrome-extension:// for extension")
        else:
            self.successes.append("ALLOWED_ORIGINS configured for extension")
            
        if not chrome_extension_id:
            self.warnings.append("CHROME_EXTENSION_ID not set")
        elif chrome_extension_id == "your_chrome_extension_id":
            self.issues.append("CHROME_EXTENSION_ID is using placeholder value")
        else:
            self.successes.append("CHROME_EXTENSION_ID configured")
    
    def _validate_redis(self) -> None:
        """Validate Redis configuration (optional)"""
        print("🔴 Checking Redis Configuration...")
        
        redis_url = os.getenv("REDIS_URL")
        
        if not redis_url:
            self.warnings.append("REDIS_URL not set - job queues will use in-memory storage")
        elif not redis_url.startswith(("redis://", "rediss://")):
            self.issues.append("REDIS_URL format invalid (should start with redis:// or rediss://)")
        else:
            self.successes.append("REDIS_URL configured")
    
    def _validate_environment_type(self) -> None:
        """Validate environment type consistency"""
        print("🏗️ Checking Environment Type...")
        
        environment = os.getenv("ENVIRONMENT", "development")
        paddle_env = os.getenv("PADDLE_ENVIRONMENT", "sandbox")
        
        if environment == "production" and paddle_env == "sandbox":
            self.warnings.append("Production environment using Paddle sandbox - verify this is intentional")
        elif environment == "development" and paddle_env == "production":
            self.warnings.append("Development environment using Paddle production - this may be dangerous")
        else:
            self.successes.append(f"Environment consistency: {environment} / Paddle: {paddle_env}")
    
    def _is_valid_jwt(self, token: str) -> bool:
        """Check if string looks like a valid JWT"""
        parts = token.split('.')
        return len(parts) == 3 and all(len(part) > 0 for part in parts)
    
    def _is_valid_email(self, email: str) -> bool:
        """Check if string is a valid email address"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _generate_report(self) -> Dict[str, any]:
        """Generate validation report"""
        print("\n" + "=" * 60)
        print("📋 VALIDATION REPORT")
        print("=" * 60)
        
        # Print successes
        if self.successes:
            print(f"\n✅ SUCCESSES ({len(self.successes)}):")
            for success in self.successes:
                print(f"   ✓ {success}")
        
        # Print warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   ⚠ {warning}")
        
        # Print issues
        if self.issues:
            print(f"\n❌ ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   ✗ {issue}")
        
        # Overall status
        is_valid = len(self.issues) == 0
        
        print(f"\n{'='*60}")
        if is_valid:
            if self.warnings:
                print("🟡 CONFIGURATION VALID WITH WARNINGS")
                print("   Your configuration will work but has some recommendations.")
            else:
                print("🟢 CONFIGURATION FULLY VALID")
                print("   All required settings are properly configured!")
        else:
            print("🔴 CONFIGURATION HAS ISSUES")
            print("   Please fix the issues above before deploying.")
        
        print(f"{'='*60}\n")
        
        return {
            "valid": is_valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "successes": self.successes,
            "summary": {
                "total_checks": len(self.issues) + len(self.warnings) + len(self.successes),
                "issues_count": len(self.issues),
                "warnings_count": len(self.warnings),
                "successes_count": len(self.successes)
            }
        }


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Simply environment configuration")
    parser.add_argument("--env-file", help="Path to .env file (default: .env)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()
    
    try:
        validator = EnvironmentValidator(args.env_file)
        result = validator.validate_all()
        
        if args.json:
            import json
            print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        sys.exit(0 if result["valid"] else 1)
        
    except Exception as e:
        print(f"❌ Validation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 