"""
Setup SignalScope Database in Supabase
"""
import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test Supabase connection"""
    print("\n" + "="*50)
    print("Testing Supabase Connection...")
    print("="*50)
    
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("❌ Supabase credentials not found in .env")
            return None
        
        print(f"📍 Connecting to: {url}")
        
        # Create Supabase client
        supabase: Client = create_client(url, key)
        
        # Test connection by trying to query (will fail if tables don't exist yet)
        try:
            result = supabase.table("messages").select("id").limit(1).execute()
            print("✅ Supabase connection successful!")
            print("✅ Tables already exist")
        except Exception as e:
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                print("✅ Supabase connection successful!")
                print("⚠️  Tables don't exist yet (this is expected)")
            else:
                print(f"⚠️  Connection works but got error: {e}")
        
        return supabase
        
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return None

def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n" + "="*50)
    print("Testing OpenAI API Connection...")
    print("="*50)
    
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key or api_key.startswith("sk-proj-your"):
            print("❌ OpenAI API key not found or is still placeholder")
            return False
        
        print(f"🔑 API Key found: {api_key[:20]}...")
        
        # Set API key
        openai.api_key = api_key
        
        # Test with a simple completion
        client = openai.Client(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello SignalScope!' in 3 words"}],
            max_tokens=10
        )
        
        print(f"✅ OpenAI API working!")
        print(f"📝 Test response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        if "api_key" in str(e).lower():
            print("💡 Make sure your API key is valid and has credits")
        return False

def test_redis_connection():
    """Test Redis connection"""
    print("\n" + "="*50)
    print("Testing Redis Connection...")
    print("="*50)
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        
        # Get queue status
        streams = [
            "signalscope:messages:realtime",
            "signalscope:messages:standard",
            "signalscope:messages:archive"
        ]
        
        total_messages = 0
        for stream in streams:
            length = r.xlen(stream)
            total_messages += length
            if length > 0:
                print(f"  {stream.split(':')[-1]}: {length} messages")
        
        print(f"✅ Redis connected! Total messages in queues: {total_messages}")
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Make sure Redis is running")
        return False

def create_tables_instructions():
    """Show instructions for creating tables"""
    print("\n" + "="*50)
    print("📋 Instructions to Create Database Tables")
    print("="*50)
    print("""
To create the tables in Supabase:

1. Go to your Supabase Dashboard:
   https://supabase.com/dashboard/project/nnydhrkavnhohmourjzb/sql/new
   
2. Copy the entire content of:
   database/create_tables.sql
   
3. Paste it in the SQL editor

4. Click "Run" to execute

5. You should see "SignalScope database tables created successfully!"

The script will create:
✅ messages - Store captured messages
✅ message_batches - Track processing batches  
✅ reports - Store AI-generated reports
✅ report_subscriptions - User subscriptions
✅ ticker_stats - Ticker statistics
✅ processing_jobs - Background job tracking
✅ system_metrics - Performance metrics

After creating tables, run this script again to verify.
""")

def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("   SignalScope Backend Setup & Connection Test")
    print("="*60)
    
    # Test connections
    results = {
        "Redis": test_redis_connection(),
        "Supabase": test_supabase_connection() is not None,
        "OpenAI": test_openai_connection()
    }
    
    # Summary
    print("\n" + "="*50)
    print("Summary")
    print("="*50)
    
    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {service}: {'Connected' if status else 'Not Connected'}")
    
    # Next steps
    if not results["Supabase"]:
        create_tables_instructions()
    elif all(results.values()):
        print("\n🎉 All services are connected and ready!")
        print("\nYour backend is fully operational. You can now:")
        print("1. Send messages from Chrome Extension")
        print("2. Process batches with LLM")
        print("3. Generate AI-powered reports")
        print("4. Store data persistently")
    else:
        print("\n⚠️  Some services need configuration")
        if not results["Redis"]:
            print("- Start Redis: docker run -d -p 6379:6379 redis:7-alpine")
        if not results["OpenAI"]:
            print("- Add valid OpenAI API key to .env file")

if __name__ == "__main__":
    main()