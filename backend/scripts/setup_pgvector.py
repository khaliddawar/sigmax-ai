#!/usr/bin/env python
"""
Supabase pgvector Setup and Test Script

This script helps set up pgvector in Supabase and test the integration.
It provides a simple command-line interface to:
1. Check if pgvector is installed
2. Set up pgvector and create necessary tables
3. Test the integration with sample data

Usage:
  python setup_pgvector.py check
  python setup_pgvector.py setup
  python setup_pgvector.py test
  python setup_pgvector.py all
"""

import os
import sys
import asyncio
import time
import json
import uuid
import traceback
import argparse
from pathlib import Path

# Add app directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables from .env.example
if not os.getenv("SUPABASE_URL"):
    os.environ["SUPABASE_URL"] = "https://npdxxefohebhabtrrybo.supabase.co"
if not os.getenv("SUPABASE_KEY"):
    os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5wZHh4ZWZvaGViaGFidHJyeWJvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEwMjc0NTgsImV4cCI6MjA2NjYwMzQ1OH0.lS0OgFEFcH85EwWk2it9iLZlH7rUyeoAD_H0NoTGSLc"
os.environ["USE_MOCK_SUPABASE"] = "false"
os.environ["USE_MOCK_EMBEDDINGS"] = "true"  # Keep embeddings mock since OpenAI key might not be available

# Import services
from app.services.supabase_client import SupabaseService
from app.services.embedding_service import EmbeddingService

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
ENDC = "\033[0m"
BOLD = "\033[1m"

def print_header(title):
    """Print a formatted header"""
    print(f"\n{BOLD}{BLUE}{'='*20} {title} {'='*20}{ENDC}\n")

def print_result(success, message):
    """Print a formatted result"""
    if success:
        print(f"{GREEN}✓ {message}{ENDC}")
    else:
        print(f"{RED}✗ {message}{ENDC}")

def read_sql_file(filename):
    """Read SQL from a file"""
    file_path = Path(__file__).parent / filename
    if not file_path.exists():
        print(f"{RED}Error: File {filename} not found{ENDC}")
        return None
    
    with open(file_path, "r") as f:
        return f.read()

async def check_pgvector():
    """Check if pgvector is installed"""
    print_header("Checking pgvector Extension")
    
    # Print environment variables (masking sensitive values)
    print(f"Environment variables:")
    print(f"  SUPABASE_URL: {'*' * 30 + os.getenv('SUPABASE_URL', '')[-10:] if os.getenv('SUPABASE_URL') else 'Not set'}")
    print(f"  SUPABASE_KEY: {'*' * 30 + os.getenv('SUPABASE_KEY', '')[-10:] if os.getenv('SUPABASE_KEY') else 'Not set'}")
    print(f"  USE_MOCK_SUPABASE: {os.getenv('USE_MOCK_SUPABASE', 'Not set')}")
    print(f"  USE_MOCK_EMBEDDINGS: {os.getenv('USE_MOCK_EMBEDDINGS', 'Not set')}")
    print(f"  OPENAI_API_KEY: {'*' * 10 + 'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    print()
    
    # Initialize services
    supabase_service = SupabaseService()
    
    # Check pgvector
    check_result = await supabase_service.check_pgvector()
    is_enabled = check_result.get("is_enabled", False)
    
    print(f"pgvector check result:")
    print(json.dumps(check_result, indent=2))
    
    print_result(is_enabled, "pgvector extension is installed and enabled")
    if not is_enabled:
        print(f"{YELLOW}You need to set up pgvector first. Run 'python setup_pgvector.py setup'.{ENDC}")
    
    return is_enabled

async def setup_pgvector():
    """Set up pgvector and create necessary tables"""
    print_header("Setting Up pgvector")
    
    # Initialize services
    supabase_service = SupabaseService()
    
    # First check if helper functions are installed
    helper_functions_sql = read_sql_file("install_helper_functions.sql")
    if helper_functions_sql:
        print(f"{YELLOW}To install helper functions, run the following SQL in your Supabase SQL Editor:{ENDC}")
        print(f"```sql\n{helper_functions_sql}\n```")
        input(f"{YELLOW}Press Enter once you've run the SQL above...{ENDC}")
    
    # Setup pgvector
    setup_result = await supabase_service.setup_pgvector()
    setup_success = setup_result.get("success", False)
    
    print(f"pgvector setup result:")
    print(json.dumps(setup_result, indent=2))
    
    print_result(setup_success, "pgvector extension and tables set up successfully")
    
    # If the setup through API failed, provide manual instructions
    if not setup_success:
        supabase_setup_sql = read_sql_file("supabase_setup.sql")
        if supabase_setup_sql:
            print(f"{YELLOW}To manually set up the tables, run the following SQL in your Supabase SQL Editor:{ENDC}")
            print(f"```sql\n{supabase_setup_sql}\n```")
            input(f"{YELLOW}Press Enter once you've run the SQL above...{ENDC}")
    
    return setup_success

async def test_pgvector_integration():
    """Test pgvector integration with sample data"""
    print_header("Testing pgvector Integration")
    
    # Initialize services
    supabase_service = SupabaseService()
    embedding_service = EmbeddingService()
    
    # Generate a unique test transcript ID
    transcript_id = f"test_{uuid.uuid4().hex[:8]}"
    
    print(f"{BLUE}Testing with transcript ID: {transcript_id}{ENDC}")
    
    # 1. Store transcript chunks
    print(f"\n{BOLD}1. Storing transcript and chunks...{ENDC}")
    chunks = []
    for i in range(5):  # Create 5 test chunks
        chunks.append({
            "chunk_index": i,
            "text": f"This is test chunk {i} for transcript {transcript_id}. It contains some sample text for testing vector embeddings.",
            "metadata": {
                "start_time": i * 90,
                "end_time": (i + 1) * 90,
                "speaker": f"Speaker {i % 3 + 1}"
            }
        })
    
    metadata = {
        "title": f"Test Transcript {transcript_id}",
        "meeting_id": f"meeting_{uuid.uuid4().hex[:8]}",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "word_count": 500,
        "duration_seconds": 900,
        "source": "test"
    }
    
    store_result = await supabase_service.store_transcript_chunks(transcript_id, metadata, chunks)
    
    print(f"Store result:")
    print(json.dumps(store_result, indent=2))
    
    store_success = store_result.get("success", False)
    print_result(store_success, f"Stored transcript with {len(chunks)} chunks")
    
    if not store_success:
        return False
    
    # 2. Generate and store embeddings
    print(f"\n{BOLD}2. Generating and storing embeddings...{ENDC}")
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings
    print(f"Generating embeddings...")
    embeddings_result = await embedding_service.get_embeddings(texts)
    
    if isinstance(embeddings_result, list) and len(embeddings_result) == len(texts):
        print_result(True, f"Generated {len(embeddings_result)} embeddings")
    else:
        print_result(False, "Failed to generate embeddings")
        return False
    
    # Store embeddings
    print(f"Storing embeddings...")
    update_result = await supabase_service.store_embeddings(transcript_id, embeddings_result)
    
    print(f"Update result:")
    print(json.dumps(update_result, indent=2))
    
    update_success = update_result.get("success", False)
    print_result(update_success, f"Updated {update_result.get('chunks_updated', 0)} chunks with embeddings")
    
    if not update_success:
        return False
    
    # 3. Test similarity search
    print(f"\n{BOLD}3. Testing similarity search...{ENDC}")
    # Use the first embedding as the query for testing
    query_embedding = embeddings_result[0]
    
    search_result = await supabase_service.search_similar_chunks(
        embedding=query_embedding,
        limit=5,
        similarity_threshold=0.5
    )
    
    print(f"Search result:")
    print(json.dumps(search_result, indent=2))
    
    search_success = search_result.get("success", False)
    print_result(search_success, f"Found {len(search_result.get('data', []))} similar chunks")
    
    # 4. Test create with embeddings (one-shot)
    print(f"\n{BOLD}4. Testing one-shot transcript creation with embeddings...{ENDC}")
    
    # Generate a new unique test transcript ID
    one_shot_transcript_id = f"test_one_shot_{uuid.uuid4().hex[:8]}"
    
    create_result = await supabase_service.create_transcript_with_embeddings(
        transcript_id=one_shot_transcript_id,
        metadata=metadata,
        chunks=chunks,
        embeddings=embeddings_result
    )
    
    print(f"Create result:")
    print(json.dumps(create_result, indent=2))
    
    create_success = create_result.get("success", False)
    print_result(create_success, f"Created transcript with {create_result.get('chunks_stored', 0)} chunks and embeddings")
    
    # Verify that the one-shot created transcript exists
    print(f"Verifying created transcript...")
    verify_result = await supabase_service.get_transcript_chunks(one_shot_transcript_id)
    
    verify_success = verify_result.get("success", False)
    retrieved_chunks = len(verify_result.get("chunks", []))
    print_result(verify_success, f"Retrieved {retrieved_chunks} chunks")
    
    # Test search on the one-shot created transcript
    print(f"Testing search on created transcript...")
    one_shot_search = await supabase_service.search_similar_chunks(
        embedding=query_embedding,
        transcript_id=one_shot_transcript_id,
        limit=3,
        similarity_threshold=0.5
    )
    
    one_shot_search_success = one_shot_search.get("success", False)
    one_shot_results = len(one_shot_search.get("data", []))
    print_result(one_shot_search_success, f"Found {one_shot_results} similar chunks")
    
    # Overall success
    return store_success and update_success and search_success and create_success

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Supabase pgvector Setup and Test Script")
    parser.add_argument("action", choices=["check", "setup", "test", "all"], 
                        help="Action to perform: check, setup, test, or all")
    
    args = parser.parse_args()
    
    try:
        if args.action == "check" or args.action == "all":
            await check_pgvector()
        
        if args.action == "setup" or args.action == "all":
            await setup_pgvector()
        
        if args.action == "test" or args.action == "all":
            await test_pgvector_integration()
        
        print(f"\n{GREEN}{BOLD}Script completed successfully!{ENDC}")
        
    except Exception as e:
        print(f"\n{RED}Error: {str(e)}{ENDC}")
        print(f"{RED}{traceback.format_exc()}{ENDC}")
        return 1
    
    return 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result) 