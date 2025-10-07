#!/usr/bin/env python3
"""
Fix missing embeddings for the test transcript
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
from app.services.embedding_service import EmbeddingService

async def fix_embeddings():
    """Fix missing embeddings for test transcript"""
    print("🔧 Fixing missing embeddings...")
    
    supabase_service = SupabaseService()
    embedding_service = EmbeddingService()
    
    try:
        # Get chunks without embeddings
        response = supabase_service.client.table('chunks').select('*').eq('transcript_id', 'test_transcript_1748089980').is_('embedding', 'null').execute()
        
        chunks_without_embeddings = response.data if response.data else []
        
        if not chunks_without_embeddings:
            print("✅ All chunks already have embeddings!")
            return True
        
        print(f"📊 Found {len(chunks_without_embeddings)} chunks without embeddings")
        
        # Generate embeddings for chunks without them
        for i, chunk in enumerate(chunks_without_embeddings):
            try:
                print(f"🔄 Processing chunk {i+1}/{len(chunks_without_embeddings)}: {chunk['id']}")
                
                # Generate embedding
                embedding = await embedding_service.generate_embedding(chunk['content'])
                
                if embedding:
                    # Update chunk with embedding
                    update_response = supabase_service.client.table('chunks').update({
                        'embedding': embedding
                    }).eq('id', chunk['id']).execute()
                    
                    if update_response.data:
                        print(f"   ✅ Updated chunk {chunk['id']}")
                    else:
                        print(f"   ❌ Failed to update chunk {chunk['id']}")
                else:
                    print(f"   ❌ Failed to generate embedding for chunk {chunk['id']}")
                    
            except Exception as e:
                print(f"   ❌ Error processing chunk {chunk['id']}: {str(e)}")
        
        print("✨ Embedding fix completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing embeddings: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(fix_embeddings()) 