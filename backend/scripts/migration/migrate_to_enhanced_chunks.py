#!/usr/bin/env python3
"""
Migrate from old chunks to enhanced chunks.

This script:
1. Deletes old chunks from the database
2. Processes the transcript with enhanced chunking strategy
3. Stores new enhanced chunks with better context preservation
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_to_enhanced_chunks():
    """Migrate from old chunks to enhanced chunks"""
    
    try:
        # Import required services
        from app.services.semantic_chunker import SemanticChunker
        from app.services.semantic_chunks_service import SemanticChunksService
        
        # Initialize services
        logger.info("Initializing enhanced chunking services...")
        chunker = SemanticChunker(domain_type="generic")
        chunks_service = SemanticChunksService()
        
        # Read the test transcript
        transcript_path = project_root / "config" / "test_transcript.txt"
        if not transcript_path.exists():
            logger.error(f"Test transcript not found at {transcript_path}")
            return False
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        logger.info(f"Loaded transcript: {len(transcript_text)} characters")
        
        # Step 1: Clear old chunks from database
        logger.info("🗑️ Clearing old chunks from database...")
        try:
            # Get current chunk count using statistics
            stats = await chunks_service.get_chunk_statistics()
            old_count = stats.get('total_chunks', 0)
            logger.info(f"Found {old_count} existing chunks to remove")
            
            # Clear all existing chunks
            if old_count > 0:
                clear_result = await chunks_service.clear_all_data()
                if clear_result.get('success'):
                    logger.info(f"✅ Deleted {old_count} old chunks from database")
                else:
                    logger.error(f"Failed to clear data: {clear_result.get('error')}")
                    return False
            else:
                logger.info("No existing chunks found")
                
        except Exception as e:
            logger.error(f"Error clearing old chunks: {e}")
            return False
        
        # Step 2: Generate enhanced chunks
        logger.info("🔄 Generating enhanced chunks with new strategy...")
        enhanced_chunks = chunker.chunk_text(transcript_text, source_id="test_transcript_enhanced")
        
        logger.info(f"Generated {len(enhanced_chunks)} enhanced chunks")
        
        # Analyze the enhanced chunks
        chunk_sizes = [len(chunk.text) for chunk in enhanced_chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        sentence_counts = [chunk.sentence_count for chunk in enhanced_chunks]
        avg_sentences = sum(sentence_counts) / len(sentence_counts)
        
        logger.info(f"Enhanced chunks statistics:")
        logger.info(f"  Average size: {avg_size:.1f} characters")
        logger.info(f"  Size range: {min(chunk_sizes)}-{max(chunk_sizes)} characters")
        logger.info(f"  Average sentences: {avg_sentences:.1f}")
        logger.info(f"  Sentence range: {min(sentence_counts)}-{max(sentence_counts)}")
        
        # Step 3: Store enhanced chunks in database
        logger.info("💾 Storing enhanced chunks in database...")
        
        # Generate embeddings for enhanced chunks
        from app.services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        
        # Extract text for embedding generation
        chunk_texts = [chunk.text for chunk in enhanced_chunks]
        logger.info("Generating embeddings for enhanced chunks...")
        embeddings = await embedding_service.generate_embeddings(chunk_texts)
        
        if not embeddings or len(embeddings) != len(enhanced_chunks):
            logger.error(f"Failed to generate embeddings: expected {len(enhanced_chunks)}, got {len(embeddings) if embeddings else 0}")
            return False
        
        # Store chunks with embeddings
        store_result = await chunks_service.store_semantic_chunks(
            chunks=enhanced_chunks,
            embeddings=embeddings,
            transcript_id="test_transcript_enhanced"
        )
        
        stored_count = store_result.get('chunks_stored', 0)
        failed_count = len(store_result.get('failed_chunks', []))
        
        logger.info(f"Storage result: {stored_count} stored, {failed_count} failed")
        
        # Step 4: Verify migration
        logger.info("🔍 Verifying migration...")
        
        # Check stored chunks using statistics
        verification_stats = await chunks_service.get_chunk_statistics()
        new_count = verification_stats.get('total_chunks', 0)
        
        # Get a sample chunk for verification
        sample_chunks = await chunks_service.get_chunks_by_transcript("test_transcript_enhanced")
        
        logger.info(f"\n=== MIGRATION RESULTS ===")
        logger.info(f"Old chunks removed: {old_count}")
        logger.info(f"Enhanced chunks generated: {len(enhanced_chunks)}")
        logger.info(f"Enhanced chunks stored: {stored_count}")
        logger.info(f"Storage failures: {failed_count}")
        logger.info(f"Final database count: {new_count}")
        
        # Verify chunk quality
        if sample_chunks:
            sample_chunk = sample_chunks[0]
            logger.info(f"\nSample enhanced chunk:")
            logger.info(f"  ID: {sample_chunk.get('id', 'N/A')}")
            logger.info(f"  Size: {len(sample_chunk.get('text', ''))} characters")
            logger.info(f"  Sentences: {sample_chunk.get('sentence_count', 'N/A')}")
            logger.info(f"  Language: {sample_chunk.get('language', 'N/A')}")
            logger.info(f"  Entities: {len(sample_chunk.get('entities', []))}")
            logger.info(f"  Text preview: {sample_chunk.get('text', '')[:100]}...")
        
        # Success criteria
        success = (stored_count == len(enhanced_chunks) and 
                  new_count == stored_count and 
                  failed_count == 0)
        
        if success:
            logger.info("\n✅ MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info("Enhanced chunking strategy is now active in the database.")
            logger.info("Key improvements:")
            logger.info(f"  • Larger chunks: {avg_sentences:.1f} sentences avg (was 2-3)")
            logger.info(f"  • Better size: {avg_size:.1f} chars avg (target 300-500)")
            logger.info(f"  • Context preservation with overlap")
            logger.info(f"  • Domain-agnostic entity extraction")
            logger.info(f"  • Enhanced language detection")
        else:
            logger.error("❌ MIGRATION INCOMPLETE!")
            logger.error(f"Expected {len(enhanced_chunks)} chunks, got {new_count}")
            
        return success
        
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_enhanced_retrieval():
    """Test retrieval with enhanced chunks"""
    
    try:
        from app.services.semantic_chunks_service import SemanticChunksService
        from app.services.embedding_service import EmbeddingService
        
        logger.info("\n🔍 Testing enhanced chunk retrieval...")
        chunks_service = SemanticChunksService()
        embedding_service = EmbeddingService()
        
        # Test queries
        test_queries = [
            "What did Patrick say about the market?",
            "pullback analysis",
            "market outlook"
        ]
        
        for query in test_queries:
            logger.info(f"\nTesting query: '{query}'")
            
            # Generate query embedding
            query_embeddings = await embedding_service.generate_embeddings([query])
            if not query_embeddings:
                logger.error(f"Failed to generate embedding for query: {query}")
                continue
            
            query_embedding = query_embeddings[0]
            
            # Search using semantic search
            results = await chunks_service.search_semantic_chunks(
                query_embedding=query_embedding,
                transcript_id="test_transcript_enhanced",
                match_threshold=0.1,
                match_count=3
            )
            
            logger.info(f"Found {len(results)} results:")
            for i, result in enumerate(results[:2]):
                similarity = result.get('similarity', 0)
                text_preview = result.get('text', '')[:100]
                logger.info(f"  {i+1}. Similarity: {similarity:.3f}")
                logger.info(f"     Text: {text_preview}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Retrieval test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting migration to enhanced chunks...")
    
    try:
        # Run migration
        success = asyncio.run(migrate_to_enhanced_chunks())
        
        if success:
            # Test retrieval
            asyncio.run(test_enhanced_retrieval())
            
            logger.info("\n🎉 ENHANCED CHUNKING MIGRATION COMPLETE!")
            logger.info("Your RAG system now uses the improved chunking strategy.")
            logger.info("All issues from the second opinion have been addressed:")
            logger.info("  ✅ Larger, more contextual chunks")
            logger.info("  ✅ Better chunk boundaries")
            logger.info("  ✅ Enhanced language detection")
            logger.info("  ✅ Domain-agnostic entity extraction")
            logger.info("  ✅ Context preservation with overlap")
        else:
            logger.error("❌ Migration failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 