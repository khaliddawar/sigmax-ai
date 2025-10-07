#!/usr/bin/env python3
"""
Generate embeddings for existing semantic chunks in the database
"""

import os
import asyncio
import logging
from typing import List, Dict, Any

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.services.supabase_client import SupabaseService
from app.services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_embeddings_for_transcript(transcript_id: str):
    """Generate embeddings for all chunks of a specific transcript"""
    
    # Initialize services
    supabase_service = SupabaseService()
    embedding_service = EmbeddingService()
    
    if not supabase_service.is_connected():
        logger.error("Supabase not connected!")
        return False
    
    try:
        # Get all chunks for this transcript that don't have embeddings
        logger.info(f"Getting chunks for transcript: {transcript_id}")
        
        result = supabase_service.client.table("semantic_chunks").select("*").eq("transcript_id", transcript_id).is_("embedding", "null").execute()
        
        if not result.data:
            logger.info("No chunks without embeddings found")
            return True
            
        chunks = result.data
        logger.info(f"Found {len(chunks)} chunks without embeddings")
        
        # Extract texts for embedding generation
        texts = [chunk["text"] for chunk in chunks]
        chunk_ids = [chunk["id"] for chunk in chunks]
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = await embedding_service.get_embeddings(texts)
        
        if not embeddings:
            logger.error("Failed to generate embeddings")
            return False
            
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Update chunks with embeddings
        for i, (chunk_id, embedding) in enumerate(zip(chunk_ids, embeddings)):
            try:
                update_result = supabase_service.client.table("semantic_chunks").update({
                    "embedding": embedding
                }).eq("id", chunk_id).execute()
                
                if update_result.data:
                    logger.info(f"Updated chunk {i+1}/{len(chunk_ids)}: {chunk_id}")
                else:
                    logger.error(f"Failed to update chunk {chunk_id}")
                    
            except Exception as e:
                logger.error(f"Error updating chunk {chunk_id}: {e}")
                
        logger.info("Embedding generation completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        return False

async def main():
    """Main function"""
    transcript_id = "test_transcript_1748089980"
    
    logger.info(f"Starting embedding generation for transcript: {transcript_id}")
    
    success = await generate_embeddings_for_transcript(transcript_id)
    
    if success:
        logger.info("✅ Embeddings generated successfully!")
        logger.info("🎯 You can now test the chat functionality with real vector search!")
    else:
        logger.error("❌ Failed to generate embeddings")

if __name__ == "__main__":
    asyncio.run(main()) 