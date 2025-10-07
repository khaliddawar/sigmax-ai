"""
Unified Transcript Handler

This service provides a unified interface for processing stored transcripts
for both Q&A (Streamlit) and email pipeline purposes. It reuses existing
working components without modifying them.
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("bpt-transcript-handler")


class TranscriptHandler:
    """
    Unified handler for processing stored transcripts for different purposes.
    
    This class acts as a coordinator that:
    1. Retrieves transcript text from storage
    2. Routes to appropriate processing pipeline (QA or Email)
    3. Reuses all existing working logic without modification
    """
    
    def __init__(self, supabase_service=None, embedding_service=None, semantic_service=None):
        """
        Initialize the transcript handler with required services.
        
        Args:
            supabase_service: SupabaseService instance for database operations
            embedding_service: EmbeddingService instance for generating embeddings
            semantic_service: SemanticChunksService instance for semantic processing
        """
        self.supabase_service = supabase_service
        self.embedding_service = embedding_service
        self.semantic_service = semantic_service
        
        # Import services only when needed to avoid circular dependencies
        self._ingestion_service = None
        
        logger.info("TranscriptHandler initialized")
    
    def _get_ingestion_service(self):
        """Lazy load the ingestion service to avoid circular imports"""
        if self._ingestion_service is None:
            from app.services.ingestion_service import IngestionService
            self._ingestion_service = IngestionService()
        return self._ingestion_service
    
    async def get_transcript_text(self, transcript_id: str) -> Dict[str, Any]:
        """
        Retrieve full transcript text for a given transcript ID.
        
        This method includes retry logic with exponential backoff to handle
        race conditions where retrieval happens too quickly after storage,
        before database transactions are fully committed.
        
        Args:
            transcript_id: The ID of the transcript to retrieve
            
        Returns:
            Dictionary with success status and transcript text
        """
        if not self.supabase_service:
            return {
                "success": False,
                "error": "SupabaseService not available"
            }
        
        import asyncio
        
        max_retries = 3
        base_delay = 0.5  # Start with 500ms delay
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.supabase_service.get_transcript_text(transcript_id)
                text_length = len(result.get("text", "")) if result.get("success") else 0
                
                # If we got text or this is the final attempt, return the result
                if text_length > 0 or attempt == max_retries:
                    if text_length > 0:
                        logger.info(f"Retrieved transcript text for {transcript_id}: {text_length} characters (attempt {attempt + 1})")
                    else:
                        logger.warning(f"Retrieved transcript text for {transcript_id}: {text_length} characters after {max_retries + 1} attempts")
                    return result
                
                # If no text and we have retries left, wait and try again
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                    logger.info(f"No text retrieved for {transcript_id} on attempt {attempt + 1}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Error retrieving transcript text for {transcript_id} after {max_retries + 1} attempts: {str(e)}")
                    return {
                        "success": False,
                        "error": str(e)
                    }
                else:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Error on attempt {attempt + 1} for {transcript_id}, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        return {
            "success": False,
            "error": f"Max retries exceeded for {transcript_id}"
        }
    
    async def process_for_qa_pipeline(self, transcript_id: str) -> Dict[str, Any]:
        """
        Process a stored transcript for Q&A (Streamlit) pipeline.
        
        This method:
        1. Retrieves the transcript text
        2. Uses the existing /process-transcript logic for semantic chunking
        3. Stores the results in the semantic_chunks table for vector search
        
        Args:
            transcript_id: The ID of the stored transcript
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting Q&A pipeline processing for transcript {transcript_id}")
            start_time = time.time()
            
            # Step 1: Get transcript text
            text_result = await self.get_transcript_text(transcript_id)
            if not text_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to retrieve transcript text: {text_result.get('error')}"
                }
            
            transcript_text = text_result.get("text")
            if not transcript_text:
                return {
                    "success": False,
                    "error": "Empty transcript text retrieved"
                }
            
            logger.info(f"Retrieved transcript text: {len(transcript_text)} characters")
            
            # Step 2: Use existing semantic chunking logic (from /process-transcript endpoint)
            if not self.semantic_service or not self.embedding_service:
                return {
                    "success": False,
                    "error": "Required services (semantic_service, embedding_service) not available"
                }
            
            # Import semantic chunker (reusing existing working code)
            from app.services.semantic_chunker import SemanticChunker
            
            # Create semantic chunks using the same logic as the working Streamlit endpoint
            chunker = SemanticChunker(domain_type="financial")
            semantic_chunks = chunker.chunk_text(transcript_text, source_id=transcript_id)
            
            if not semantic_chunks:
                return {
                    "success": False,
                    "error": "Failed to create semantic chunks"
                }
            
            logger.info(f"Created {len(semantic_chunks)} semantic chunks")
            
            # Step 3: Generate embeddings (reusing existing logic)
            chunk_texts = [chunk.text for chunk in semantic_chunks]
            embeddings = await self.embedding_service.get_embeddings(chunk_texts)
            
            if not embeddings or len(embeddings) != len(semantic_chunks):
                return {
                    "success": False,
                    "error": "Failed to generate embeddings for chunks"
                }
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            # Step 4: Store semantic chunks (reusing existing logic)
            store_result = await self.semantic_service.store_semantic_chunks(
                chunks=semantic_chunks,
                embeddings=embeddings,
                transcript_id=transcript_id
            )
            
            if not store_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to store semantic chunks: {store_result.get('error')}"
                }
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"Q&A pipeline processing completed for {transcript_id} in {processing_time:.2f}s")
            
            return {
                "success": True,
                "transcript_id": transcript_id,
                "pipeline": "qa",
                "chunks_stored": store_result.get("chunks_stored", 0),
                "processing_time": processing_time,
                "character_count": len(transcript_text)
            }
            
        except Exception as e:
            logger.error(f"Error in Q&A pipeline processing for {transcript_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_for_email_pipeline(self, transcript_id: str, 
                                       meeting_title: Optional[str] = None, 
                                       meeting_date: Optional[str] = None,
                                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a stored transcript for email pipeline.
        
        This method:
        1. Retrieves the transcript text
        2. Uses the existing email ingestion pipeline logic
        3. Generates summary and extracts trades
        4. Sends email to subscribers
        
        Args:
            transcript_id: The ID of the stored transcript
            meeting_title: Optional title for the meeting
            meeting_date: Optional date for the meeting
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting email pipeline processing for transcript {transcript_id}")
            start_time = time.time()
            
            # Step 1: Get transcript text
            text_result = await self.get_transcript_text(transcript_id)
            if not text_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to retrieve transcript text: {text_result.get('error')}"
                }
            
            transcript_text = text_result.get("text")
            if not transcript_text:
                return {
                    "success": False,
                    "error": "Empty transcript text retrieved"
                }
            
            logger.info(f"Retrieved transcript text: {len(transcript_text)} characters")
            
            # Step 2: Use existing email pipeline logic (start_ingestion_pipeline_with_text)
            ingestion_service = self._get_ingestion_service()
            
            result = await ingestion_service.start_ingestion_pipeline_with_text(
                transcript_id=transcript_id,
                transcript_text=transcript_text,
                meeting_title=meeting_title or f"Stored Transcript {transcript_id}",
                meeting_date=meeting_date,
                metadata=metadata or {"source": "stored_transcript", "processed_via": "transcript_handler"}
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            if result.get("success"):
                logger.info(f"Email pipeline processing completed for {transcript_id} in {total_time:.2f}s")
                
                # Add our processing info to the result
                result.update({
                    "pipeline": "email",
                    "transcript_handler_time": total_time,
                    "character_count": len(transcript_text)
                })
            else:
                logger.error(f"Email pipeline processing failed for {transcript_id}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in email pipeline processing for {transcript_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_dual_pipeline(self, transcript_id: str,
                                  meeting_title: Optional[str] = None,
                                  meeting_date: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a stored transcript for BOTH Q&A and email pipelines.
        
        This method runs both processing pipelines in sequence, useful for
        webhook-received transcripts that need both vector search capability
        and email notifications.
        
        Args:
            transcript_id: The ID of the stored transcript
            meeting_title: Optional title for the meeting
            meeting_date: Optional date for the meeting
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with results from both pipelines
        """
        try:
            logger.info(f"Starting dual pipeline processing for transcript {transcript_id}")
            start_time = time.time()
            
            # Run Q&A pipeline first (for vector search)
            qa_result = await self.process_for_qa_pipeline(transcript_id)
            
            # Run email pipeline second (for notifications)
            email_result = await self.process_for_email_pipeline(
                transcript_id, meeting_title, meeting_date, metadata
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            success = qa_result.get("success", False) and email_result.get("success", False)
            
            logger.info(f"Dual pipeline processing completed for {transcript_id} in {total_time:.2f}s")
            
            return {
                "success": success,
                "transcript_id": transcript_id,
                "pipeline": "dual",
                "total_time": total_time,
                "qa_result": qa_result,
                "email_result": email_result,
                "qa_success": qa_result.get("success", False),
                "email_success": email_result.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Error in dual pipeline processing for {transcript_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 