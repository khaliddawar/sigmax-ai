import os
import asyncio
import sys
from app.services.embedding_service import EmbeddingService
from app.services.supabase_client import SupabaseService
from app.services.retrieval_qa_service import RetrievalQAService

# Load environment variables from env.txt
env_vars = {}
try:
    with open('env.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key] = value
                os.environ[key] = value
except Exception as e:
    print(f"Error loading env.txt: {e}")

# Override specific settings for debugging
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['DEBUG'] = 'true'
os.environ['USE_MOCK_SUPABASE'] = 'false'
os.environ['USE_MOCK_EMBEDDINGS'] = 'false'
os.environ['USE_MOCK_QA'] = 'false'

async def check_services():
    print("Checking environment variables:")
    print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL', 'Not set')}")
    print(f"SUPABASE_KEY: {'Set (hidden)' if os.environ.get('SUPABASE_KEY') else 'Not set'}")
    print(f"OPENAI_API_KEY: {'Set (hidden)' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
    
    print("\nInitializing services:")
    supabase = SupabaseService()
    embedding = EmbeddingService()
    qa = RetrievalQAService(embedding, supabase)
    
    print(f"Supabase connected: {supabase.is_connected()}")
    print(f"Using mock embeddings: {embedding.use_mock}")
    print(f"Using mock QA responses: {qa.use_mock}")
    
    print("\nTesting Supabase connection:")
    conn_result = supabase.check_connection()
    print(f"Connection result: {conn_result}")
    
    print("\nChecking PGVector setup:")
    pgvector_result = await supabase.check_pgvector()
    print(f"PGVector result: {pgvector_result}")
    
    if not embedding.use_mock:
        print("\nTesting embedding generation:")
        test_text = "This is a test sentence for embedding generation."
        embedding_result = await embedding.get_embedding(test_text)
        print(f"Generated embedding of length: {len(embedding_result) if embedding_result else 'Failed'}")
    
    return {
        "supabase_connected": supabase.is_connected(),
        "using_mock_embeddings": embedding.use_mock,
        "using_mock_qa": qa.use_mock,
        "pgvector_setup": pgvector_result.get("success", False) if pgvector_result else False
    }

if __name__ == "__main__":
    results = asyncio.run(check_services())
    
    print("\nSummary:")
    if results["supabase_connected"] and not results["using_mock_embeddings"] and results["pgvector_setup"]:
        print("✅ All services are properly configured for vector search")
    else:
        print("❌ Vector search is not available due to these issues:")
        if not results["supabase_connected"]:
            print("  - Supabase connection failed")
        if results["using_mock_embeddings"]:
            print("  - Using mock embeddings (OpenAI API key missing or invalid)")
        if not results["pgvector_setup"]:
            print("  - PGVector extension not properly set up in Supabase")
    
    if results["using_mock_qa"]:
        print("  - QA service is using mock responses") 