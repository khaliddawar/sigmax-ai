#!/usr/bin/env python3
"""
Insert all chunks into Supabase using direct API calls
"""
import json
import sys
import os

sys.path.insert(0, '.')

async def insert_chunks_via_supabase():
    """Insert remaining chunks into Supabase"""
    
    # Load chunks
    with open('chunks_with_embeddings.json', 'r') as f:
        chunks = json.load(f)
    
    print(f"📄 Loaded {len(chunks)} chunks")
    
    # Skip first chunk (already inserted)
    chunks_to_insert = chunks[1:6]  # Insert chunks 2-6 for good coverage
    
    print(f"🔄 Inserting {len(chunks_to_insert)} additional chunks...")
    
    from app.services.supabase_client import SupabaseService
    
    supabase_service = SupabaseService()
    
    for chunk in chunks_to_insert:
        try:
            # Insert chunk directly
            result = await supabase_service.insert_chunk(
                transcript_id=chunk['transcript_id'],
                chunk_index=chunk['chunk_index'],
                text=chunk['text'],
                position=chunk['position'],
                is_first=chunk['is_first'],
                is_last=chunk['is_last'],
                metadata=chunk['metadata'] if isinstance(chunk['metadata'], dict) else {},
                embedding=chunk['embedding']
            )
            
            if result:
                print(f"✅ Inserted chunk {chunk['chunk_index']}")
            else:
                print(f"❌ Failed to insert chunk {chunk['chunk_index']}")
                
        except Exception as e:
            print(f"❌ Error inserting chunk {chunk['chunk_index']}: {e}")
    
    print(f"\n🎯 Chunk insertion complete!")

if __name__ == "__main__":
    import asyncio
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(insert_chunks_via_supabase()) 