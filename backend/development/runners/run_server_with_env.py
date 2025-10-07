import os
import sys
import subprocess
import asyncio
import json
from app.services.supabase_client import SupabaseService
from app.services.embedding_service import EmbeddingService

# Load environment variables from env.txt
env_vars = {}
with open('env.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env_vars[key] = value

# Set environment variables
for key, value in env_vars.items():
    os.environ[key] = value

# Override specific settings for debugging
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['DEBUG'] = 'true'
os.environ['USE_MOCK_SUPABASE'] = 'false'
os.environ['USE_MOCK_EMBEDDINGS'] = 'false'
os.environ['USE_MOCK_QA'] = 'false'

# Print environment variables for verification
print("Environment variables set:")
print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL', 'Not set')}")
print(f"SUPABASE_KEY: {'Set (hidden)' if os.environ.get('SUPABASE_KEY') else 'Not set'}")
print(f"OPENAI_API_KEY: {'Set (hidden)' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
print(f"LOG_LEVEL: {os.environ.get('LOG_LEVEL', 'Not set')}")

async def check_and_load_transcript():
    print("\nChecking for existing transcripts in Supabase...")
    supabase = SupabaseService()
    embedding_service = EmbeddingService()
    
    # Check if Supabase is connected
    if not supabase.is_connected():
        print("Error: Supabase not connected, cannot load transcripts")
        return
        
    # Check for existing transcripts
    transcripts = await supabase.get_transcripts()
    if transcripts.get("success", False) and len(transcripts.get("data", [])) > 0:
        print(f"Found {len(transcripts['data'])} existing transcripts")
        return
        
    print("No transcripts found. Loading a sample transcript...")
    
    # Load a sample transcript
    try:
        # Load transcript from file
        with open('dummy_transcript.txt', 'r') as f:
            transcript_text = f.read()
            
        # Create a transcript record
        transcript_id = "sample-transcript-001"
        title = "Sample Trading Meeting"
        date = "2023-07-15"
        
        transcript_result = await supabase.add_transcript(
            transcript_id=transcript_id,
            title=title,
            date=date,
            text=transcript_text
        )
        
        if not transcript_result.get("success", False):
            print(f"Error creating transcript: {transcript_result.get('error', 'Unknown error')}")
            return
            
        print(f"Created transcript: {transcript_id}")
        
        # Generate embedding for the transcript text
        chunks = []
        chunk_size = 1000
        overlap = 200
        
        # Split text into chunks
        for i in range(0, len(transcript_text), chunk_size - overlap):
            chunk_text = transcript_text[i:i + chunk_size]
            if len(chunk_text) < 100:  # Skip very short chunks
                continue
                
            chunk = {
                "transcript_id": transcript_id,
                "chunk_index": len(chunks) + 1,
                "text": chunk_text,
                "position": i,
                "embedding": []  # Will be populated below
            }
            chunks.append(chunk)
        
        print(f"Created {len(chunks)} chunks from transcript")
        
        # Generate embeddings for each chunk
        for chunk in chunks:
            embedding = await embedding_service.get_embedding(chunk["text"])
            if embedding:
                chunk["embedding"] = embedding
                # Insert chunk with embedding into Supabase
                chunk_result = await supabase.add_chunk(
                    transcript_id=chunk["transcript_id"],
                    chunk_index=chunk["chunk_index"],
                    text=chunk["text"],
                    position=chunk["position"],
                    embedding=chunk["embedding"]
                )
                
                if not chunk_result.get("success", False):
                    print(f"Error adding chunk {chunk['chunk_index']}: {chunk_result.get('error', 'Unknown error')}")
                else:
                    print(f"Added chunk {chunk['chunk_index']} with embedding")
            else:
                print(f"Failed to generate embedding for chunk {chunk['chunk_index']}")
                
        print(f"Successfully loaded transcript '{title}' with {len(chunks)} chunks")
    except Exception as e:
        print(f"Error loading sample transcript: {str(e)}")

# Run async setup operations
asyncio.run(check_and_load_transcript())

# Run the uvicorn server
cmd = [sys.executable, "-m", "uvicorn", "simple_fastapi:app", "--reload", "--port", "8000", "--log-level", "debug"]
subprocess.run(cmd)