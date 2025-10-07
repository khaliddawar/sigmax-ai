#!/usr/bin/env python3
import sys
import os
import asyncio
import json

sys.path.insert(0, '.')

from app.services.transcript_processor import TranscriptProcessor
from app.services.embedding_service import EmbeddingService

async def main():
    # Read transcript
    with open('config/test_transcript.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process into chunks
    processor = TranscriptProcessor()
    result = processor.process_transcript(content)
    chunks = result['chunks']
    
    print(f'✅ Created {len(chunks)} chunks')
    
    # Generate embeddings
    embedding_service = EmbeddingService()
    chunk_texts = [chunk['text'] for chunk in chunks]
    embeddings = await embedding_service.get_embeddings(chunk_texts)
    
    if embeddings:
        print(f'✅ Generated {len(embeddings)} embeddings, each with {len(embeddings[0])} dimensions')
        
        # Prepare chunk data with embeddings
        chunk_data = []
        transcript_id = 'trading_analysis_manual_test'
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_record = {
                'transcript_id': transcript_id,
                'chunk_index': i + 1,
                'text': chunk['text'],
                'position': i,
                'is_first': i == 0,
                'is_last': i == len(chunks) - 1,
                'embedding': embedding,
                'metadata': '{}'
            }
            chunk_data.append(chunk_record)
        
        # Save to JSON for review
        with open('chunks_with_embeddings.json', 'w') as f:
            json.dump(chunk_data, f, indent=2)
        
        print(f'💾 Saved chunk data to chunks_with_embeddings.json')
        print(f'📊 Sample chunk:')
        print(f'   Text: {chunk_data[0]["text"][:100]}...')
        print(f'   Embedding dimensions: {len(chunk_data[0]["embedding"])}')
        
    else:
        print('❌ No embeddings generated')

if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main()) 