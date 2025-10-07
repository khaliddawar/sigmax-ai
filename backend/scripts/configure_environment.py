#!/usr/bin/env python3
"""
Environment Configuration Script for Simply Authentication & Payment System

This script helps configure environment variables for different deployment environments:
- Development (local)
- Staging (testing)
- Production (live)
"""

import os
import sys
import secrets
import base64
from pathlib import Path
from typing import Dict, Optional


class EnvironmentConfigurator:
    """Configure environment variables for different environments"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.config = {}
        
    def generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret"""
        return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
    
    def configure_development(self) -> Dict[str, str]:
        """Configure development environment"""
        return {
            # Environment
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            
            # Authentication
            "JWT_SECRET_KEY": self.generate_jwt_secret(),
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_HOURS": "24",
            "BCRYPT_ROUNDS": "12",
            
            # Paddle (Sandbox)
            "PADDLE_ENVIRONMENT": "sandbox",
            
            # Email (Development)
            "SMTP_SERVER": "smtp.gmail.com",
            "SMTP_PORT": "587",
            
            # API Configuration
            "API_HOST": "0.0.0.0",
            "API_PORT": "8000",
            
            # CORS
            "ALLOWED_ORIGINS": "http://localhost:3000,chrome-extension://your-extension-id",
            
            # Redis
            "REDIS_URL": "redis://localhost:6379",
            
            # AI Services
            "OPENAI_MODEL_NAME": "gpt-4o-mini",
            "EMBEDDING_MODEL": "text-embedding-3-large",
            "ANTHROPIC_MODEL": "claude-3-sonnet-20240229",
        }
    
    def configure_staging(self) -> Dict[str, str]:
        """Configure staging environment"""
        return {
            # Environment
            "ENVIRONMENT": "staging",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            
            # Authentication
            "JWT_SECRET_KEY": self.generate_jwt_secret(),
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_HOURS": "24",
            "BCRYPT_ROUNDS": "12",
            
            # Paddle (Sandbox for testing)
            "PADDLE_ENVIRONMENT": "sandbox",
            
            # API Configuration
            "API_HOST": "0.0.0.0",
            "API_PORT": "8000",
            
            # AI Services
            "OPENAI_MODEL_NAME": "gpt-4o-mini",
            "EMBEDDING_MODEL": "text-embedding-3-large",
            "ANTHROPIC_MODEL": "claude-3-sonnet-20240229",
        }
    
    def configure_production(self) -> Dict[str, str]:
        """Configure production environment"""
        return {
            # Environment
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            
            # Authentication
            "JWT_SECRET_KEY": self.generate_jwt_secret(),
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_HOURS": "24",
            "BCRYPT_ROUNDS": "12",
            
            # Paddle (Production)
            "PADDLE_ENVIRONMENT": "production",
            
            # API Configuration
            "API_HOST": "0.0.0.0",
            "API_PORT": "8000",
            
            # AI Services
            "OPENAI_MODEL_NAME": "gpt-4o-mini",
            "EMBEDDING_MODEL": "text-embedding-3-large",
            "ANTHROPIC_MODEL": "claude-3-sonnet-20240229",
        }
    
    def get_template_variables(self) -> Dict[str, str]:
        """Get template variables that need manual configuration"""
        return {
            # Supabase (get from dashboard)
            "SUPABASE_URL": "https://your-project-id.supabase.co",
            "SUPABASE_ANON_KEY": "your_supabase_anon_key",
            "SUPABASE_SERVICE_ROLE_KEY": "your_supabase_service_role_key",
            
            # Paddle (get from Paddle dashboard)
            "PADDLE_VENDOR_ID": "your_paddle_vendor_id",
            "PADDLE_API_KEY": "your_paddle_api_key",
            "PADDLE_PUBLIC_KEY": "your_paddle_public_key",
            "PADDLE_WEBHOOK_SECRET": "your_paddle_webhook_secret",
            "PADDLE_PRODUCT_ID_PREMIUM": "12345",
            "PADDLE_PRODUCT_ID_ENTERPRISE": "12346",
            
            # Email Service
            "SMTP_USERNAME": "your-email@gmail.com",
            "SMTP_PASSWORD": "your-app-password",
            "SENDER_EMAIL": "your-email@gmail.com",
            "POSTMARK_API_TOKEN": "your_postmark_server_token",
            "POSTMARK_SENDER_EMAIL": "noreply@yourdomain.com",
            "POSTMARK_SENDER_NAME": "Simply",
            
            # AI Services
            "OPENAI_API_KEY": "your_openai_api_key",
            "ANTHROPIC_API_KEY": "your_anthropic_api_key",
            "PERPLEXITY_API_KEY": "your_perplexity_api_key",
            
            # Extension
            "CHROME_EXTENSION_ID": "your_chrome_extension_id",
            "FRONTEND_URL": "https://yourdomain.com",
        }
    
    def generate_env_file(self, output_file: str = ".env") -> None:
        """Generate .env file for the specified environment"""
        
        # Get environment-specific config
        if self.environment == "development":
            env_config = self.configure_development()
        elif self.environment == "staging":
            env_config = self.configure_staging()
        elif self.environment == "production":
            env_config = self.configure_production()
        else:
            raise ValueError(f"Unknown environment: {self.environment}")
        
        # Merge with template variables
        template_vars = self.get_template_variables()
        all_vars = {**template_vars, **env_config}
        
        # Generate file content
        content = self._generate_env_content(all_vars)
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Generated {output_file} for {self.environment} environment")
        print(f"📝 Please update the placeholder values with your actual credentials")
    
    def _generate_env_content(self, variables: Dict[str, str]) -> str:
        """Generate .env file content"""
        
        content = f"""# ===================================================================
# Simply Chrome Extension - {self.environment.upper()} Environment Configuration
# Generated by configure_environment.py
# ===================================================================

# === ENVIRONMENT ===
ENVIRONMENT={variables.get('ENVIRONMENT', 'development')}
DEBUG={variables.get('DEBUG', 'false')}
LOG_LEVEL={variables.get('LOG_LEVEL', 'INFO')}

# === SUPABASE CONFIGURATION ===
# Get these from: https://supabase.com/dashboard → Settings → API
SUPABASE_URL={variables.get('SUPABASE_URL')}
SUPABASE_ANON_KEY={variables.get('SUPABASE_ANON_KEY')}
SUPABASE_SERVICE_ROLE_KEY={variables.get('SUPABASE_SERVICE_ROLE_KEY')}

# === AUTHENTICATION & SECURITY ===
JWT_SECRET_KEY={variables.get('JWT_SECRET_KEY')}
JWT_ALGORITHM={variables.get('JWT_ALGORITHM', 'HS256')}
JWT_EXPIRATION_HOURS={variables.get('JWT_EXPIRATION_HOURS', '24')}
BCRYPT_ROUNDS={variables.get('BCRYPT_ROUNDS', '12')}

# === PADDLE PAYMENT SYSTEM ===
# Get these from: https://paddle.com → Developer Tools → Authentication
PADDLE_VENDOR_ID={variables.get('PADDLE_VENDOR_ID')}
PADDLE_API_KEY={variables.get('PADDLE_API_KEY')}
PADDLE_PUBLIC_KEY={variables.get('PADDLE_PUBLIC_KEY')}
PADDLE_WEBHOOK_SECRET={variables.get('PADDLE_WEBHOOK_SECRET')}
PADDLE_ENVIRONMENT={variables.get('PADDLE_ENVIRONMENT', 'sandbox')}
# Product IDs for different subscription plans
PADDLE_PRODUCT_ID_PREMIUM={variables.get('PADDLE_PRODUCT_ID_PREMIUM')}
PADDLE_PRODUCT_ID_ENTERPRISE={variables.get('PADDLE_PRODUCT_ID_ENTERPRISE')}

# === EMAIL CONFIGURATION ===
# Option A: SMTP (Development/Small scale)
SMTP_SERVER={variables.get('SMTP_SERVER', 'smtp.gmail.com')}
SMTP_PORT={variables.get('SMTP_PORT', '587')}
SMTP_USERNAME={variables.get('SMTP_USERNAME')}
SMTP_PASSWORD={variables.get('SMTP_PASSWORD')}
SENDER_EMAIL={variables.get('SENDER_EMAIL')}

# Option B: Postmark (Production recommended)
POSTMARK_API_TOKEN={variables.get('POSTMARK_API_TOKEN')}
POSTMARK_SENDER_EMAIL={variables.get('POSTMARK_SENDER_EMAIL')}
POSTMARK_SENDER_NAME={variables.get('POSTMARK_SENDER_NAME', 'Simply')}

# === AI SERVICES ===
# OpenAI (Required)
OPENAI_API_KEY={variables.get('OPENAI_API_KEY')}
OPENAI_MODEL_NAME={variables.get('OPENAI_MODEL_NAME', 'gpt-4o-mini')}
EMBEDDING_MODEL={variables.get('EMBEDDING_MODEL', 'text-embedding-3-large')}

# Anthropic (Optional)
ANTHROPIC_API_KEY={variables.get('ANTHROPIC_API_KEY')}
ANTHROPIC_MODEL={variables.get('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')}

# Perplexity (Optional - for research features)
PERPLEXITY_API_KEY={variables.get('PERPLEXITY_API_KEY')}

# === REDIS CONFIGURATION ===
# For production scaling and job queues
REDIS_URL={variables.get('REDIS_URL', 'redis://localhost:6379')}
REDIS_HOST={variables.get('REDIS_HOST', 'localhost')}
REDIS_PORT={variables.get('REDIS_PORT', '6379')}
REDIS_PASSWORD={variables.get('REDIS_PASSWORD', '')}
REDIS_DB={variables.get('REDIS_DB', '0')}

# === CORS & SECURITY ===
ALLOWED_ORIGINS={variables.get('ALLOWED_ORIGINS', 'http://localhost:3000')}
CHROME_EXTENSION_ID={variables.get('CHROME_EXTENSION_ID')}
FRONTEND_URL={variables.get('FRONTEND_URL', 'http://localhost:3000')}

# === API CONFIGURATION ===
API_HOST={variables.get('API_HOST', '0.0.0.0')}
API_PORT={variables.get('API_PORT', '8000')}

# === LEGACY SETTINGS (for backward compatibility) ===
QA_MODEL=gpt-4o-mini
"""
        return content
    
    def generate_render_yaml(self) -> None:
        """Generate render.yaml for production deployment"""
        
        yaml_content = """services:
  - type: web
    name: simply-backend
    runtime: docker
    plan: starter
    region: oregon
    branch: master
    dockerfilePath: ./Dockerfile
    envVars:
      # Environment
      - key: ENVIRONMENT
        value: production
      - key: DEBUG
        value: false
      - key: LOG_LEVEL
        value: INFO
        
      # Supabase (from secrets database)
      - key: SUPABASE_URL
        fromDatabase:
          name: simply-secrets
          property: SUPABASE_URL
      - key: SUPABASE_ANON_KEY
        fromDatabase:
          name: simply-secrets
          property: SUPABASE_ANON_KEY
      - key: SUPABASE_SERVICE_ROLE_KEY
        fromDatabase:
          name: simply-secrets
          property: SUPABASE_SERVICE_ROLE_KEY
          
      # Authentication
      - key: JWT_SECRET_KEY
        fromDatabase:
          name: simply-secrets
          property: JWT_SECRET_KEY
      - key: JWT_ALGORITHM
        value: HS256
      - key: JWT_EXPIRATION_HOURS
        value: 24
        
      # Paddle Payment System
      - key: PADDLE_VENDOR_ID
        fromDatabase:
          name: simply-secrets
          property: PADDLE_VENDOR_ID
      - key: PADDLE_API_KEY
        fromDatabase:
          name: simply-secrets
          property: PADDLE_API_KEY
      - key: PADDLE_PUBLIC_KEY
        fromDatabase:
          name: simply-secrets
          property: PADDLE_PUBLIC_KEY
      - key: PADDLE_WEBHOOK_SECRET
        fromDatabase:
          name: simply-secrets
          property: PADDLE_WEBHOOK_SECRET
      - key: PADDLE_ENVIRONMENT
        value: production
      - key: PADDLE_PRODUCT_ID_PREMIUM
        fromDatabase:
          name: simply-secrets
          property: PADDLE_PRODUCT_ID_PREMIUM
      - key: PADDLE_PRODUCT_ID_ENTERPRISE
        fromDatabase:
          name: simply-secrets
          property: PADDLE_PRODUCT_ID_ENTERPRISE
        
      # Email Service
      - key: POSTMARK_API_TOKEN
        fromDatabase:
          name: simply-secrets
          property: POSTMARK_API_TOKEN
      - key: POSTMARK_SENDER_EMAIL
        fromDatabase:
          name: simply-secrets
          property: POSTMARK_SENDER_EMAIL
      - key: POSTMARK_SENDER_NAME
        value: Simply
        
      # AI Services
      - key: OPENAI_API_KEY
        fromDatabase:
          name: simply-secrets
          property: OPENAI_API_KEY
      - key: OPENAI_MODEL_NAME
        value: gpt-4o-mini
      - key: EMBEDDING_MODEL
        value: text-embedding-3-large
      - key: ANTHROPIC_API_KEY
        fromDatabase:
          name: simply-secrets
          property: ANTHROPIC_API_KEY
      - key: ANTHROPIC_MODEL
        value: claude-3-sonnet-20240229
      - key: PERPLEXITY_API_KEY
        fromDatabase:
          name: simply-secrets
          property: PERPLEXITY_API_KEY
        
      # Redis
      - key: REDIS_URL
        fromService:
          type: redis
          name: simply-redis
          property: connectionString
          
      # CORS & Security
      - key: CHROME_EXTENSION_ID
        fromDatabase:
          name: simply-secrets
          property: CHROME_EXTENSION_ID
      - key: FRONTEND_URL
        fromDatabase:
          name: simply-secrets
          property: FRONTEND_URL
      - key: ALLOWED_ORIGINS
        fromDatabase:
          name: simply-secrets
          property: ALLOWED_ORIGINS
          
      # API Configuration
      - key: API_HOST
        value: 0.0.0.0
      - key: API_PORT
        value: 8000

  # Redis service for job queues and caching
  - type: redis
    name: simply-redis
    plan: starter
    region: oregon
    maxmemoryPolicy: allkeys-lru

databases:
  # Secrets database for storing sensitive configuration
  - name: simply-secrets
    databaseName: simply_secrets
    user: simply_admin
"""
        
        with open("render.yaml", 'w') as f:
            f.write(yaml_content)
        
        print("✅ Generated render.yaml for production deployment")
        print("📝 Don't forget to configure the secrets database in Render dashboard")
    
    def print_setup_instructions(self) -> None:
        """Print setup instructions for the environment"""
        
        print(f"\n🚀 SETUP INSTRUCTIONS FOR {self.environment.upper()} ENVIRONMENT")
        print("=" * 60)
        
        if self.environment == "development":
            print("""
1. 📋 Copy the generated .env file to your project root
2. 🔑 Update placeholder values with your actual credentials:
   - Get Supabase keys from https://supabase.com/dashboard
   - Get Paddle keys from https://paddle.com (use sandbox)
   - Set up Gmail app password for SMTP
   - Get OpenAI API key from https://platform.openai.com
3. 🚀 Start the development server:
   python app/main.py
4. 🧪 Test the extension with http://localhost:8000
""")
        
        elif self.environment == "staging":
            print("""
1. 📋 Use the generated .env file as a template
2. 🔑 Configure staging-specific values:
   - Use staging Supabase project
   - Keep Paddle in sandbox mode
   - Use test email addresses
3. 🚀 Deploy to staging environment
4. 🧪 Run full integration tests
""")
        
        elif self.environment == "production":
            print("""
1. 📋 Use render.yaml for Render.com deployment
2. 🔑 Configure production secrets in Render dashboard:
   - Create 'simply-secrets' database
   - Add all sensitive environment variables
3. 🚀 Deploy via GitHub integration
4. 🧪 Monitor logs and test all features
5. 🔐 Enable production security features:
   - Set DEBUG=false
   - Use strong JWT secrets
   - Configure proper CORS origins
""")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configure Simply environment variables")
    parser.add_argument("environment", choices=["development", "staging", "production"],
                       help="Environment to configure")
    parser.add_argument("--output", "-o", default=".env",
                       help="Output file path (default: .env)")
    parser.add_argument("--render-yaml", action="store_true",
                       help="Generate render.yaml for production deployment")
    parser.add_argument("--instructions", action="store_true",
                       help="Show setup instructions")
    
    args = parser.parse_args()
    
    try:
        configurator = EnvironmentConfigurator(args.environment)
        
        # Generate .env file
        configurator.generate_env_file(args.output)
        
        # Generate render.yaml if requested
        if args.render_yaml and args.environment == "production":
            configurator.generate_render_yaml()
        
        # Show instructions if requested
        if args.instructions:
            configurator.print_setup_instructions()
        
        print(f"\n✅ Environment configuration complete for {args.environment}")
        
    except Exception as e:
        print(f"❌ Configuration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 