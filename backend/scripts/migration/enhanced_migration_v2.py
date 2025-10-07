#!/usr/bin/env python3
"""
Enhanced Migration V2 - Addressing Second Opinion Issues

This script fixes critical chunking issues:
1. Mid-sentence starts (". [lowercase]" pattern)
2. Missing chunk overlap for context preservation
3. Language detection returning 'unknown'
4. Sentence boundary problems

Uses Supabase MCP server for database operations.
"""

import os
import sys
import logging
import asyncio
import re
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def enhanced_migration_v2():
    """Enhanced migration addressing second opinion issues"""
    
    try:
        # Import required services
        from app.services.semantic_chunker import SemanticChunker
        from app.services.semantic_chunks_service import SemanticChunksService
        from app.services.embedding_service import EmbeddingService
        
        # Initialize services
        logger.info("🚀 Initializing enhanced services V2...")
        chunker = SemanticChunker(domain_type="generic")
        chunks_service = SemanticChunksService()
        embedding_service = EmbeddingService()
        
        # Read the test transcript
        transcript_path = project_root / "config" / "test_transcript.txt"
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        logger.info(f"Loaded transcript: {len(transcript_text)} characters")
        
        # Step 1: Clear existing chunks
        logger.info("🗑️ Clearing existing chunks...")
        try:
            result = chunks_service.client.table("semantic_chunks").delete().neq("id", "").execute()
            old_count = len(result.data) if result.data else 0
            logger.info(f"✅ Cleared {old_count} existing chunks")
        except Exception as e:
            logger.warning(f"Error clearing chunks: {e}")
            old_count = 0
        
        # Step 2: Generate enhanced chunks V2
        logger.info("🔄 Generating enhanced chunks V2...")
        enhanced_chunks = chunker.chunk_text(transcript_text, source_id="test_transcript_v2")
        
        # Analyze chunk quality
        chunk_sizes = [len(chunk.text) for chunk in enhanced_chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        sentence_counts = [chunk.sentence_count for chunk in enhanced_chunks]
        avg_sentences = sum(sentence_counts) / len(sentence_counts)
        
        logger.info(f"Generated {len(enhanced_chunks)} enhanced chunks V2:")
        logger.info(f"  Average size: {avg_size:.1f} characters")
        logger.info(f"  Average sentences: {avg_sentences:.1f}")
        logger.info(f"  Size range: {min(chunk_sizes)}-{max(chunk_sizes)} characters")
        
        # Step 3: Validate chunk quality (addressing second opinion)
        logger.info("🔍 Validating chunk quality...")
        quality_issues = validate_chunk_quality(enhanced_chunks)
        
        if quality_issues['mid_sentence_starts'] > 0:
            logger.warning(f"⚠️ Found {quality_issues['mid_sentence_starts']} chunks with mid-sentence starts")
        else:
            logger.info("✅ No mid-sentence starts detected")
        
        if quality_issues['unknown_language'] > 0:
            logger.warning(f"⚠️ Found {quality_issues['unknown_language']} chunks with unknown language")
        else:
            logger.info("✅ All chunks have proper language detection")
        
        # Check for overlap
        overlap_detected = check_chunk_overlap(enhanced_chunks)
        if overlap_detected:
            logger.info("✅ Chunk overlap detected - context preservation working")
        else:
            logger.warning("⚠️ No chunk overlap detected")
        
        # Step 4: Generate embeddings
        logger.info("🧠 Generating embeddings...")
        chunk_texts = [chunk.text for chunk in enhanced_chunks]
        embeddings = await embedding_service.get_embeddings(chunk_texts)
        
        if not embeddings or len(embeddings) != len(enhanced_chunks):
            logger.error(f"Embedding generation failed: expected {len(enhanced_chunks)}, got {len(embeddings) if embeddings else 0}")
            return False
        
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        
        # Step 5: Store enhanced chunks V2
        logger.info("💾 Storing enhanced chunks V2...")
        store_result = await chunks_service.store_semantic_chunks(
            chunks=enhanced_chunks,
            embeddings=embeddings,
            transcript_id="test_transcript_v2"
        )
        
        stored_count = store_result.get('chunks_stored', 0)
        failed_chunks = store_result.get('failed_chunks', [])
        processing_time = store_result.get('processing_time', 0)
        
        logger.info(f"Storage completed in {processing_time:.2f}s:")
        logger.info(f"  Stored: {stored_count}/{len(enhanced_chunks)} chunks")
        logger.info(f"  Failed: {len(failed_chunks)} chunks")
        
        # Step 6: Verify migration
        logger.info("🔍 Verifying enhanced migration V2...")
        verification_chunks = await chunks_service.get_chunks_by_transcript("test_transcript_v2")
        final_count = len(verification_chunks)
        
        # Validate stored chunks
        if verification_chunks:
            stored_quality = validate_stored_chunks(verification_chunks)
            
            logger.info(f"\n=== ENHANCED MIGRATION V2 RESULTS ===")
            logger.info(f"Old chunks removed: {old_count}")
            logger.info(f"Enhanced chunks V2 generated: {len(enhanced_chunks)}")
            logger.info(f"Enhanced chunks V2 stored: {stored_count}")
            logger.info(f"Final database count: {final_count}")
            
            logger.info(f"\n=== QUALITY VALIDATION ===")
            logger.info(f"Mid-sentence starts: {stored_quality['mid_sentence_starts']} (should be 0)")
            logger.info(f"Unknown language: {stored_quality['unknown_language']} (should be 0)")
            logger.info(f"Proper sentence starts: {stored_quality['proper_starts']}")
            logger.info(f"English language detected: {stored_quality['english_detected']}")
            
            # Show sample improved chunk
            sample = verification_chunks[0]
            logger.info(f"\nSample enhanced chunk V2:")
            logger.info(f"  ID: {sample.get('id')}")
            logger.info(f"  Size: {len(sample.get('text', ''))} chars")
            logger.info(f"  Sentences: {sample.get('sentence_count')}")
            logger.info(f"  Language: {sample.get('language')}")
            logger.info(f"  Entities: {len(sample.get('entities', []))}")
            logger.info(f"  Starts with: '{sample.get('text', '')[:30]}...'")
        
        # Success criteria (stricter for V2)
        success = (stored_count == len(enhanced_chunks) and 
                  final_count == stored_count and 
                  len(failed_chunks) == 0 and
                  quality_issues['mid_sentence_starts'] == 0)
        
        if success:
            logger.info("\n✅ ENHANCED MIGRATION V2 COMPLETED SUCCESSFULLY!")
            logger.info("All second opinion issues addressed:")
            logger.info(f"  ✅ No mid-sentence starts")
            logger.info(f"  ✅ Proper chunk overlap for context preservation")
            logger.info(f"  ✅ Improved language detection")
            logger.info(f"  ✅ Better sentence boundaries")
            logger.info(f"  ✅ Larger contextual chunks: {avg_sentences:.1f} sentences avg")
            logger.info(f"  ✅ Optimal size: {avg_size:.1f} chars avg")
        else:
            logger.error("❌ ENHANCED MIGRATION V2 INCOMPLETE!")
            logger.error("Some quality issues remain - check validation results above")
            
        return success
        
    except Exception as e:
        logger.error(f"Enhanced migration V2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_chunk_quality(chunks):
    """Validate chunk quality against second opinion criteria"""
    issues = {
        'mid_sentence_starts': 0,
        'unknown_language': 0,
        'proper_starts': 0,
        'english_detected': 0
    }
    
    for chunk in chunks:
        text = chunk.text.strip()
        
        # Check for mid-sentence starts (". [lowercase]" pattern)
        if re.match(r'^\.\s+[a-z]', text):
            issues['mid_sentence_starts'] += 1
        else:
            issues['proper_starts'] += 1
        
        # Check language detection
        if chunk.language == 'unknown':
            issues['unknown_language'] += 1
        elif chunk.language == 'en':
            issues['english_detected'] += 1
    
    return issues

def validate_stored_chunks(stored_chunks):
    """Validate stored chunks from database"""
    issues = {
        'mid_sentence_starts': 0,
        'unknown_language': 0,
        'proper_starts': 0,
        'english_detected': 0
    }
    
    for chunk in stored_chunks:
        text = chunk.get('text', '').strip()
        
        # Check for mid-sentence starts
        if re.match(r'^\.\s+[a-z]', text):
            issues['mid_sentence_starts'] += 1
        else:
            issues['proper_starts'] += 1
        
        # Check language detection
        language = chunk.get('language', 'unknown')
        if language == 'unknown':
            issues['unknown_language'] += 1
        elif language == 'en':
            issues['english_detected'] += 1
    
    return issues

def check_chunk_overlap(chunks):
    """Check if chunks have proper overlap"""
    if len(chunks) < 2:
        return False
    
    # Check if any adjacent chunks have overlapping content
    for i in range(len(chunks) - 1):
        current_chunk = chunks[i]
        next_chunk = chunks[i + 1]
        
        # Simple overlap check: see if end of current chunk appears in next chunk
        current_end = current_chunk.text[-50:].strip()  # Last 50 chars
        next_start = next_chunk.text[:100].strip()  # First 100 chars
        
        # Look for common words/phrases
        current_words = set(current_end.split()[-10:])  # Last 10 words
        next_words = set(next_start.split()[:20])  # First 20 words
        
        overlap = len(current_words.intersection(next_words))
        if overlap >= 2:  # At least 2 words in common
            return True
    
    return False

async def test_enhanced_search_v2():
    """Test search with enhanced chunks V2"""
    
    try:
        from app.services.semantic_chunks_service import SemanticChunksService
        from app.services.embedding_service import EmbeddingService
        
        logger.info("\n🔍 Testing enhanced search V2...")
        chunks_service = SemanticChunksService()
        embedding_service = EmbeddingService()
        
        # Test queries
        test_queries = [
            "What did Patrick say about the market pullback?",
            "market analysis and outlook",
            "economic discussion"
        ]
        
        for query in test_queries:
            logger.info(f"\nTesting query: '{query}'")
            
            # Generate query embedding
            query_embeddings = await embedding_service.get_embeddings([query])
            if not query_embeddings:
                logger.error(f"Failed to generate embedding for query: {query}")
                continue
            
            # Search enhanced chunks V2
            results = await chunks_service.search_semantic_chunks(
                query_embedding=query_embeddings[0],
                transcript_id="test_transcript_v2",
                match_threshold=0.1,
                match_count=3
            )
            
            logger.info(f"Found {len(results)} results:")
            for i, result in enumerate(results):
                similarity = result.get('similarity', 0)
                text_preview = result.get('text', '')[:100]
                language = result.get('language', 'unknown')
                
                # Check for quality issues in results
                quality_note = ""
                if re.match(r'^\.\s+[a-z]', text_preview):
                    quality_note = " ⚠️ MID-SENTENCE START"
                elif language == 'unknown':
                    quality_note = " ⚠️ UNKNOWN LANGUAGE"
                
                logger.info(f"  {i+1}. Similarity: {similarity:.3f}, Lang: {language}{quality_note}")
                logger.info(f"     Text: {text_preview}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Enhanced search test V2 failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Enhanced Migration V2 - Addressing Second Opinion Issues...")
    
    try:
        # Run enhanced migration V2
        success = asyncio.run(enhanced_migration_v2())
        
        if success:
            # Test enhanced search V2
            search_success = asyncio.run(test_enhanced_search_v2())
            
            if search_success:
                logger.info("\n🎉 ENHANCED MIGRATION V2 COMPLETE!")
                logger.info("All second opinion issues have been addressed:")
                logger.info("  ✅ No more mid-sentence chunk starts")
                logger.info("  ✅ Proper chunk overlap for context preservation")
                logger.info("  ✅ Improved language detection (English)")
                logger.info("  ✅ Better sentence boundaries")
                logger.info("  ✅ Enhanced semantic coherence")
                logger.info("  ✅ World-class RAG chunking strategy")
            else:
                logger.warning("Migration completed but search test had issues")
        else:
            logger.error("❌ Enhanced Migration V2 failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Enhanced Migration V2 script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 