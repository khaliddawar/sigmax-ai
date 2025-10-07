#!/usr/bin/env python3
"""
Database setup script for BPT system
Creates necessary tables and loads test data
"""
import os
import sys
import asyncio
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.supabase_client import SupabaseService

async def setup_database():
    """Set up the database with necessary tables and test data"""
    print("🚀 Setting up BPT database...")
    
    supabase_service = SupabaseService()
    
    try:
        # Create tables using SQL
        print("📋 Creating database tables...")
        
        # Create transcripts table
        transcripts_sql = """
        CREATE TABLE IF NOT EXISTS transcripts (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Create semantic_chunks table (the one actually used by the system)
        semantic_chunks_sql = """
        CREATE TABLE IF NOT EXISTS semantic_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            transcript_id TEXT REFERENCES transcripts(id),
            text TEXT NOT NULL,
            embedding VECTOR(1536),
            sentence_count INTEGER,
            language TEXT,
            entities JSONB,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Create chunks table (for compatibility)
        chunks_sql = """
        CREATE TABLE IF NOT EXISTS chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            transcript_id TEXT REFERENCES transcripts(id),
            content TEXT NOT NULL,
            embedding VECTOR(1536),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Create vector search functions
        vector_functions_sql = """
        -- Function to search semantic chunks
        CREATE OR REPLACE FUNCTION match_semantic_chunks(
            query_embedding VECTOR(1536),
            transcript_id_filter TEXT DEFAULT NULL,
            match_threshold FLOAT DEFAULT 0.3,
            match_count INT DEFAULT 5
        )
        RETURNS TABLE (
            id UUID,
            transcript_id TEXT,
            text TEXT,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                semantic_chunks.id,
                semantic_chunks.transcript_id,
                semantic_chunks.text,
                1 - (semantic_chunks.embedding <=> query_embedding) AS similarity
            FROM semantic_chunks
            WHERE 
                (transcript_id_filter IS NULL OR semantic_chunks.transcript_id = transcript_id_filter)
                AND semantic_chunks.embedding IS NOT NULL
                AND 1 - (semantic_chunks.embedding <=> query_embedding) > match_threshold
            ORDER BY semantic_chunks.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        
        -- Function to search regular chunks (for compatibility)
        CREATE OR REPLACE FUNCTION match_chunks(
            query_embedding VECTOR(1536),
            transcript_id_filter TEXT DEFAULT NULL,
            match_threshold FLOAT DEFAULT 0.3,
            match_count INT DEFAULT 5
        )
        RETURNS TABLE (
            id UUID,
            transcript_id TEXT,
            content TEXT,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                chunks.id,
                chunks.transcript_id,
                chunks.content,
                1 - (chunks.embedding <=> query_embedding) AS similarity
            FROM chunks
            WHERE 
                (transcript_id_filter IS NULL OR chunks.transcript_id = transcript_id_filter)
                AND chunks.embedding IS NOT NULL
                AND 1 - (chunks.embedding <=> query_embedding) > match_threshold
            ORDER BY chunks.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """
        
        # Execute SQL commands
        try:
            supabase_service.client.postgrest.rpc('exec_sql', {'sql': transcripts_sql}).execute()
            print("✅ Created transcripts table")
        except Exception as e:
            print(f"⚠️ Transcripts table: {str(e)}")
        
        try:
            supabase_service.client.postgrest.rpc('exec_sql', {'sql': semantic_chunks_sql}).execute()
            print("✅ Created semantic_chunks table")
        except Exception as e:
            print(f"⚠️ Semantic chunks table: {str(e)}")
        
        try:
            supabase_service.client.postgrest.rpc('exec_sql', {'sql': chunks_sql}).execute()
            print("✅ Created chunks table")
        except Exception as e:
            print(f"⚠️ Chunks table: {str(e)}")
        
        try:
            supabase_service.client.postgrest.rpc('exec_sql', {'sql': vector_functions_sql}).execute()
            print("✅ Created vector search functions")
        except Exception as e:
            print(f"⚠️ Vector functions: {str(e)}")
        
        # Load test transcript data
        print("📄 Loading test transcript...")
        
        # Check if test transcript exists in data folder
        transcript_file = project_root / "data" / "transcripts" / "test_transcript_1748089980.json"
        if transcript_file.exists():
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
            
            # Insert transcript
            transcript_record = {
                'id': 'test_transcript_1748089980',
                'title': transcript_data.get('title', 'Test Transcript'),
                'content': transcript_data.get('content', ''),
                'metadata': transcript_data.get('metadata', {})
            }
            
            # Upsert transcript
            result = supabase_service.client.table('transcripts').upsert(transcript_record).execute()
            if result.data:
                print("✅ Loaded test transcript")
            else:
                print("❌ Failed to load test transcript")
        else:
            print("⚠️ Test transcript file not found, creating minimal record")
            minimal_transcript = {
                'id': 'test_transcript_1748089980',
                'title': 'Patrick Market Analysis',
                'content': 'Test transcript content',
                'metadata': {'speaker': 'Patrick Ceresna'}
            }
            result = supabase_service.client.table('transcripts').upsert(minimal_transcript).execute()
            if result.data:
                print("✅ Created minimal test transcript")
        
        print("✨ Database setup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False

async def load_test_chunks():
    """Load test chunks from data folder if they exist"""
    print("📦 Loading test chunks...")
    
    chunks_dir = project_root / "data" / "chunks" / "test_transcript_1748089980"
    if not chunks_dir.exists():
        print("⚠️ No test chunks found in data folder")
        return False
    
    supabase_service = SupabaseService()
    
    try:
        chunk_files = list(chunks_dir.glob("*.json"))
        print(f"Found {len(chunk_files)} chunk files")
        
        chunks_loaded = 0
        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            # Insert into chunks table (for compatibility)
            chunk_record = {
                'transcript_id': 'test_transcript_1748089980',
                'content': chunk_data.get('content', ''),
                'metadata': chunk_data.get('metadata', {})
            }
            
            result = supabase_service.client.table('chunks').insert(chunk_record).execute()
            if result.data:
                chunks_loaded += 1
        
        print(f"✅ Loaded {chunks_loaded} chunks")
        return chunks_loaded > 0
        
    except Exception as e:
        print(f"❌ Failed to load chunks: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(setup_database())
    asyncio.run(load_test_chunks()) 