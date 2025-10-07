#!/usr/bin/env python3
import json
import sys
import os

sys.path.insert(0, '.')

def main():
    # Read the chunks
    with open('chunks_with_embeddings.json', 'r') as f:
        chunks = json.load(f)
    
    print(f"📄 Loaded {len(chunks)} chunks")
    
    # We'll insert chunks 2-5 to have enough data for testing
    chunks_to_insert = chunks[1:5]  # Skip first chunk (already inserted), take next 4
    
    print(f"🔄 Inserting {len(chunks_to_insert)} chunks...")
    
    for i, chunk in enumerate(chunks_to_insert, 2):
        # Convert embedding array to PostgreSQL array format
        embedding_str = '[' + ','.join(map(str, chunk['embedding'])) + ']'
        
        # Escape single quotes in text
        text_escaped = chunk['text'].replace("'", "''")
        
        sql = f"""INSERT INTO transcript_chunks (transcript_id, chunk_index, text, position, is_first, is_last, metadata, embedding) 
VALUES (
    '{chunk['transcript_id']}',
    {chunk['chunk_index']},
    $${text_escaped}$$,
    {chunk['position']},
    {str(chunk['is_first']).lower()},
    {str(chunk['is_last']).lower()},
    '{json.dumps(chunk['metadata'])}',
    '{embedding_str}'::vector
);"""
        
        # Write to individual file for manual execution
        with open(f'chunk_{chunk["chunk_index"]}.sql', 'w') as f:
            f.write(sql)
        
        print(f"✅ Generated SQL for chunk {chunk['chunk_index']}")
    
    print(f"\n🎯 Generated SQL files for chunks 2-5")
    print("Execute these manually in Supabase or use the MCP server")

if __name__ == "__main__":
    main() 