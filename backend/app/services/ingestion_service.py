import time
import logging
import asyncio
import re
from datetime import datetime, timezone
import traceback
from typing import Dict, Any, List, Optional
import uuid
import os
import json
import aiohttp

from .transcript_processor import TranscriptProcessor
from .embedding_service import EmbeddingService
from .supabase_client import SupabaseService
from .file_storage import FileStorageService
from .summary_service_v2 import SummaryServiceRouter
from .trade_service import extract_trades, TradeExtractionService
from .email_router import email_router
from .retrieval_qa_service import RetrievalQAService
from .semantic_chunker import SemanticChunker
from .semantic_chunks_service import SemanticChunksService

logger = logging.getLogger("bpt-ingestion-service")

class IngestionService:
    """
    Service for orchestrating the complete ingestion pipeline
    from transcript processing to email delivery
    """
    
    def __init__(self):
        """Initialize the ingestion service with dependencies"""
        self.transcript_processor = TranscriptProcessor()
        self.embedding_service = EmbeddingService()
        self.supabase_service = SupabaseService()
        self.file_storage_service = FileStorageService()
        self.email_service = email_router
        
        # Initialize the QA service using embedding and storage services
        self.qa_service = RetrievalQAService(self.embedding_service, self.supabase_service)
        
        # Initialize trade extraction service
        self.trade_extraction = TradeExtractionService()
        
        # 🔄 Use router instead of direct service (backward compatible)
        self.summary_service = SummaryServiceRouter()
        
        # Initialize semantic chunking services
        self.semantic_chunker = SemanticChunker()
        self.semantic_chunks_service = SemanticChunksService()
        
        logger.info("Ingestion service initialized")
    
    def _derive_duration_from_transcript(self, transcript_text: str) -> int:
        """
        Derive transcript duration from timestamps in the text.
        
        Enhanced to support multiple formats:
        1. Fireflies JSON format: {"startTime": "MM:SS", "endTime": "MM:SS"}
        2. Traditional formats: MM:SS, HH:MM:SS, [MM:SS], XmYs, Xs
        
        Returns duration in seconds.
        """
        try:
            # First, try to parse as Fireflies JSON format
            if transcript_text.strip().startswith('[') and transcript_text.strip().endswith(']'):
                try:
                    import json
                    transcript_data = json.loads(transcript_text)
                    if isinstance(transcript_data, list) and len(transcript_data) > 0:
                        # Extract all timestamps from Fireflies JSON
                        timestamps = []
                        for entry in transcript_data:
                            if isinstance(entry, dict):
                                start_time = entry.get('startTime', '')
                                end_time = entry.get('endTime', '')
                                if start_time:
                                    timestamps.append(start_time)
                                if end_time:
                                    timestamps.append(end_time)
                        
                        if timestamps:
                            # Convert timestamps to seconds and find max
                            max_seconds = 0
                            for timestamp in timestamps:
                                seconds = self._parse_timestamp_to_seconds(timestamp)
                                if seconds > max_seconds:
                                    max_seconds = seconds
                            
                            if max_seconds > 0:
                                logger.info(f"Derived duration from Fireflies JSON: {max_seconds} seconds ({max_seconds//60}:{max_seconds%60:02d})")
                                return max_seconds
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.debug(f"Failed to parse as Fireflies JSON: {e}")
                    # Fall through to traditional timestamp detection
            
            # Traditional timestamp detection patterns
            patterns = [
                r'\b(\d{1,2}):(\d{2}):(\d{2})\b',  # HH:MM:SS
                r'\b(\d{1,2}):(\d{2})\b',          # MM:SS
                r'\[(\d{1,2}):(\d{2})\]',          # [MM:SS]
                r'\b(\d+)m(\d+)s\b',               # XmYs
                r'\b(\d+)s\b'                      # Xs
            ]
            
            all_timestamps = []
            
            for pattern in patterns:
                matches = re.findall(pattern, transcript_text)
                for match in matches:
                    if len(match) == 3:  # HH:MM:SS
                        hours, minutes, seconds = map(int, match)
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                    elif len(match) == 2:
                        if 'm' in pattern:  # XmYs format
                            minutes, seconds = map(int, match)
                            total_seconds = minutes * 60 + seconds
                        else:  # MM:SS format
                            minutes, seconds = map(int, match)
                            total_seconds = minutes * 60 + seconds
                    else:  # Xs format
                        total_seconds = int(match[0])
                    
                    all_timestamps.append(total_seconds)
            
            if all_timestamps:
                max_duration = max(all_timestamps)
                logger.info(f"Derived duration from traditional timestamps: {max_duration} seconds ({max_duration//60}:{max_duration%60:02d})")
                return max_duration
            
            # If no timestamps found, check environment variable
            allow_no_timestamps = os.getenv('ALLOW_NO_TIMESTAMPS', 'false').lower() == 'true'
            if allow_no_timestamps:
                default_duration = int(os.getenv('DEFAULT_TRANSCRIPT_DURATION', '600'))  # 10 minutes
                logger.warning(f"No timestamps found, using default duration: {default_duration} seconds ({default_duration//60}:{default_duration%60:02d})")
                return default_duration
            
            # Provide detailed error with transcript sample for debugging
            sample = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
            raise ValueError(
                f"No valid timestamps found in transcript. Cannot determine duration for validation.\n"
                f"Expected formats: MM:SS, HH:MM:SS, [MM:SS], XmYs, Xs, or Fireflies JSON with startTime/endTime\n"
                f"Transcript sample: {sample}\n"
                f"Set ALLOW_NO_TIMESTAMPS=true to use default duration."
            )
            
        except Exception as e:
            logger.error(f"Error deriving duration from transcript: {str(e)}")
            raise

    def _parse_timestamp_to_seconds(self, timestamp: str) -> int:
        """
        Parse a timestamp string to seconds.
        Supports MM:SS and HH:MM:SS formats.
        """
        try:
            parts = timestamp.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                return 0
        except (ValueError, AttributeError):
            return 0
    
    async def start_ingestion_pipeline(self, 
                                     transcript_id: str, 
                                     transcript_url: str, 
                                     meeting_title: Optional[str] = None, 
                                     meeting_date: Optional[str] = None,
                                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start the complete ingestion pipeline
        
        Args:
            transcript_id: Unique identifier for the transcript
            transcript_url: URL to download the transcript from
            meeting_title: Title of the meeting (optional)
            meeting_date: Date of the meeting (optional)
            metadata: Additional metadata for the transcript (optional)
            
        Returns:
            Dictionary with success status and details
        """
        start_time = time.time()
        pipeline_id = str(uuid.uuid4())
        logger.info(f"Starting ingestion pipeline {pipeline_id} for transcript {transcript_id}")
        
        try:
            # Initialize tracking for steps
            steps_completed = []
            step_times = {}
            
            # Step 1: Download and process transcript
            logger.info("Step 1: Downloading and processing transcript...")
            step_start = time.time()
            
            transcript_data = await self._download_transcript(transcript_url)
            if not transcript_data["success"]:
                return transcript_data
                
            transcript_text = transcript_data["text"]
            
            # Process the transcript into chunks
            processed_data = self.transcript_processor.process_transcript(transcript_text)
            
            if not processed_data.get("success", False):
                logger.error(f"Failed to process transcript: {processed_data.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Failed to process transcript: {processed_data.get('error', 'Unknown error')}"
                }
                
            transcript_chunks = processed_data["chunks"]
            
            # Add transcript_id and metadata to each chunk
            for i, chunk in enumerate(transcript_chunks):
                chunk.update({
                    "transcript_id": transcript_id,
                    "chunk_index": i,
                    "position": i,
                    "is_first": i == 0,
                    "is_last": i == len(transcript_chunks) - 1,
                    "metadata": metadata or {}
                })
            
            # Create transcript metadata
            transcript_metadata = {
                "title": meeting_title or "Untitled Meeting",
                "date": meeting_date or datetime.now().isoformat(),
                "word_count": len(transcript_text.split()),
                "chunk_count": len(transcript_chunks),
                "source": metadata.get("source") if metadata else "fireflies_webhook",
                **(metadata or {})
            }
            
            step_times["download_process"] = time.time() - step_start
            steps_completed.append("download_process")
            logger.info(f"Transcript processed into {len(transcript_chunks)} chunks")
            
            # Step 2: Generate embeddings for chunks
            logger.info("Step 2: Generating embeddings...")
            step_start = time.time()
            
            # Extract text from chunks for embedding
            chunk_texts = [chunk["text"] for chunk in transcript_chunks]
            
            # Generate embeddings
            embeddings_result = await self.embedding_service.get_embeddings(chunk_texts)
            
            if not embeddings_result:
                logger.warning("Failed to generate embeddings, continuing without them")
                chunk_embeddings = None
            else:
                chunk_embeddings = embeddings_result
                logger.info(f"Generated {len(chunk_embeddings)} embeddings")
                
            step_times["generate_embeddings"] = time.time() - step_start
            steps_completed.append("generate_embeddings")
            
            # Step 3: Store transcript and chunks in database
            logger.info("Step 3: Storing transcript and chunks in database...")
            step_start = time.time()
            
            # Create a session ID if not provided
            meeting_id = metadata.get("meeting_id") if metadata else None
            if not meeting_id:
                meeting_id = f"meet_{uuid.uuid4().hex[:10]}"
                
            # Ensure we have a title
            if not meeting_title:
                meeting_title = transcript_metadata.get("title", "Untitled Meeting")
                
            # Ensure we have a date and correct timestamp if needed
            if not meeting_date:
                meeting_date = transcript_metadata.get("date", datetime.now().isoformat())
            else:
                # Fix timestamp handling - convert Unix timestamp to ISO format if needed
                try:
                    # Check if it's a Unix timestamp (string of digits)
                    if isinstance(meeting_date, str) and meeting_date.isdigit():
                        # Convert from milliseconds to seconds if needed
                        timestamp = int(meeting_date)
                        if timestamp > 1e10:  # Likely milliseconds
                            timestamp = timestamp / 1000
                        
                        # Validate timestamp is reasonable (between 1970 and 2050 to be safer)
                        min_timestamp = 0  # 1970-01-01
                        max_timestamp = 2524608000  # 2050-01-01 (safer than 2100)
                        
                        if timestamp < min_timestamp or timestamp > max_timestamp:
                            logger.warning(f"Invalid timestamp {timestamp} (outside 1970-2050 range), using current time")
                            meeting_date = datetime.now(timezone.utc).isoformat()
                        else:
                            # Convert to datetime and then ISO format with better error handling
                            try:
                                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                                meeting_date = dt.isoformat()
                                logger.info(f"Converted timestamp {timestamp} to date: {meeting_date}")
                            except (ValueError, OSError) as e:
                                logger.warning(f"Failed to convert timestamp {timestamp}: {e}, using current time")
                                meeting_date = datetime.now(timezone.utc).isoformat()
                    elif isinstance(meeting_date, str):
                        # Try to parse as ISO string directly
                        try:
                            parsed_dt = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
                            # Ensure it's in UTC and properly formatted
                            if parsed_dt.tzinfo is None:
                                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                            meeting_date = parsed_dt.isoformat()
                            logger.info(f"Parsed ISO date: {meeting_date}")
                        except ValueError as e:
                            logger.warning(f"Could not parse ISO date '{meeting_date}': {e}, using current time")
                            meeting_date = datetime.now(timezone.utc).isoformat()
                    else:
                        logger.warning(f"Unexpected date format: {type(meeting_date)}, using current time")
                        meeting_date = datetime.now(timezone.utc).isoformat()
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"Could not parse date '{meeting_date}': {e}, using current time")
                    meeting_date = datetime.now(timezone.utc).isoformat()
                
            # Update transcript metadata with corrected date
            transcript_metadata["date"] = meeting_date
            
            # Determine which storage service to use
            storage_service = self.supabase_service if self.supabase_service.is_connected() else self.file_storage_service
            storage_type = "Supabase" if self.supabase_service.is_connected() else "File storage"
            
            logger.info(f"Using {storage_type} for transcript storage")
            
            # Create transcript record with user_id if available
            user_id = metadata.get("user_id") if metadata else None
            transcript_record_data = {
                    "meeting_id": meeting_id,
                    "title": meeting_title,
                    "date": meeting_date,
                    **transcript_metadata
                }
            
            # Add user_id if available (for YouTube extension authenticated users)
            if user_id:
                transcript_record_data["user_id"] = user_id
                logger.info(f"Creating transcript record for authenticated user: {user_id}")
            
            transcript_result = await storage_service.create_transcript_record(
                transcript_id, 
                transcript_record_data
            )
            
            if transcript_result["success"]:
                if transcript_result.get("already_exists"):
                    logger.info(f"Transcript {transcript_id} already exists, continuing with processing")
                else:
                    logger.info(f"Created new transcript record {transcript_id}")
                    
                # Store chunks with embeddings (only if transcript was newly created)
                if not transcript_result.get("already_exists"):
                    chunks_result = await storage_service.store_transcript_chunks(
                        transcript_id,
                        transcript_chunks,
                        chunk_embeddings
                    )
                    logger.info(f"Stored transcript and {chunks_result.get('count', 0)} chunks in {storage_type.lower()}")
                else:
                    logger.info(f"Skipping chunk storage for existing transcript {transcript_id}")
            else:
                logger.error(f"Failed to store transcript: {transcript_result.get('error')}")
                # Continue processing even if transcript creation failed (might be a duplicate)
                logger.warning("Continuing with summary generation despite transcript creation failure")
                
            step_times["store_transcript"] = time.time() - step_start
            steps_completed.append("store_transcript")
            
            # Step 4: Generate summary
            logger.info("Step 4: Generating summary...")
            step_start = time.time()
            
            # 💡 FIX: Derive duration from transcript content itself
            derived_duration = self._derive_duration_from_transcript(transcript_text)
            
            # Enhanced summary generation - NO FALLBACKS, fail explicitly
            summary_result = await self.summary_service.generate_summary(
                transcript_id=transcript_id,
                transcript_text=transcript_text,
                duration_seconds=derived_duration
            )
            
            # Extract HTML summary from the result dictionary - NO FALLBACKS
            if isinstance(summary_result, dict) and "summary_html" in summary_result:
                summary_html = summary_result["summary_html"]
                logger.info(f"Generated enhanced summary: {len(summary_html)} chars")
                
                # Log additional summary statistics if available
                if "segments_processed" in summary_result:
                    logger.info(f"Enhanced summary processed {summary_result['segments_processed']} segments")
                if "enhancement_level" in summary_result:
                    logger.info(f"Enhancement level: {summary_result['enhancement_level']}")
                if "processing_metadata" in summary_result:
                    method = summary_result["processing_metadata"].get("method", "unknown")
                    logger.info(f"Summary method used: {method}")
            else:
                # NO FALLBACK - fail explicitly to expose the real issue
                raise ValueError(f"Summary service returned invalid format: {type(summary_result)}. Expected dict with 'summary_html' key.")
            
            # Store summary in database
            update_result = await storage_service.update_transcript_record(
                transcript_id,
                {"summary": summary_html}
            )
            
            if update_result["success"]:
                logger.info(f"Summary stored in {storage_type.lower()}")
            else:
                logger.error(f"Failed to store summary: {update_result.get('error')}")
                    
            step_times["generate_summary"] = time.time() - step_start
            steps_completed.append("generate_summary")
            
            # Step 5: Extract trades
            logger.info("Step 5: Extracting trades...")
            step_start = time.time()
            
            trades = await self.trade_extraction.extract_trades(transcript_text)
            
            logger.info(f"Extracted {len(trades)} trades")
            
            # Store trades in database
            if trades:
                for trade in trades:
                    trade_result = await storage_service.create_trade_record(
                        transcript_id,
                        trade
                    )
                    
                    if not trade_result["success"]:
                        logger.error(f"Failed to store trade: {trade_result.get('error')}")
                        
            step_times["extract_trades"] = time.time() - step_start
            steps_completed.append("extract_trades")
            
            # Step 6: Send email to subscribers
            logger.info("Step 6: Sending emails to subscribers...")
            step_start = time.time()
            
            # Get subscribers from storage service
            subscribers_result = await storage_service.get_subscribers()
            subscribers = subscribers_result.get("subscribers", []) if subscribers_result["success"] else []
                    
            # If no subscribers in database, check environment variables
            if not subscribers:
                from os import getenv
                admin_email = getenv("ADMIN_EMAIL")
                if admin_email:
                    subscribers = [{"email": admin_email}]
                    
            # Extract action items from summary result (if available)
            action_items = []
            if isinstance(summary_result, dict):
                action_items = summary_result.get("action_items", [])
                logger.info(f"Found {len(action_items)} action items in summary")
            
            # Determine email recipient – prefer the authenticated user when available
            user_id = metadata.get("user_id") if metadata else None
            user_email = metadata.get("user_email") if metadata else None
            email_recipients = []
            
            # If the pipeline has information about the authenticated user, always email them first.
            # We no longer gate this on a specific `source` value – this prevents regressions when the
            # caller forgets to set the correct string (e.g. "youtube" vs "youtube_extension").
            if user_id:
                if user_email:
                    # Use email from metadata (more efficient)
                    email_recipients = [{"email": user_email, "name": ""}]
                    logger.info(f"Sending summary to authenticated user: {user_email}")
                else:
                    # Fallback: Get user's email from the database
                    try:
                        from app.services.supabase_client import get_supabase_client
                        supabase = get_supabase_client()
                        
                        user_response = supabase.table("user_profiles").select("email, full_name").eq("user_id", user_id).execute()
                        
                        if user_response.data:
                            db_user_email = user_response.data[0]["email"]
                            user_name = user_response.data[0].get("full_name", "")
                            email_recipients = [{"email": db_user_email, "name": user_name}]
                            logger.info(f"Sending summary to authenticated user: {db_user_email}")
                        else:
                            logger.warning(f"User profile not found for user_id: {user_id}")
                            # Fall back to subscribers if user not found
                            email_recipients = []
                            
                    except Exception as e:
                        logger.error(f"Error getting user email for {user_id}: {e}")
                        # Fall back to subscribers on error
                        email_recipients = []
            
            # If no authenticated user email found, fall back to subscribers list
            if not email_recipients:
                logger.info("Falling back to subscribers list...")
                email_recipients = subscribers
            
            # Send emails to determined recipients
            email_results = []
            logger.info(f"Sending emails to {len(email_recipients)} recipients")
            
            for recipient in email_recipients:
                email_result = await self.email_service.send_quicksheet_email(
                    recipient["email"],
                    {"title": meeting_title, "date": meeting_date},
                    summary_html,
                    trades,
                    action_items,
                    transcript_id=transcript_id,
                    metadata=metadata  # Pass the fresh metadata from the pipeline
                )
                
                email_results.append(email_result)
                logger.info(f"Email sent to {recipient['email']}: {email_result.get('success', False)}")
                
            logger.info(f"Sent {len(email_results)} emails")
                
            step_times["send_emails"] = time.time() - step_start
            steps_completed.append("send_emails")
            
            # Finalize and return result
            end_time = time.time()
            total_time = end_time - start_time
            
            logger.info(f"Ingestion pipeline completed in {total_time:.2f} seconds")
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "transcript_id": transcript_id,
                "meeting_id": meeting_id,
                "storage_type": storage_type,
                "steps_completed": steps_completed,
                "step_times": step_times,
                "total_time": total_time,
                "summary_length": len(summary_html),
                "summary_html": summary_html,
                "trades_count": len(trades),
                "emails_sent": len(email_results)
            }
            
        except Exception as e:
            logger.error(f"Error in ingestion pipeline: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "pipeline_id": pipeline_id
            }
    
    async def _download_transcript(self, transcript_url: str) -> Dict[str, Any]:
        """
        Download transcript from URL
        
        Args:
            transcript_url: URL to download the transcript from
            
        Returns:
            Dictionary with success status and transcript text
        """
        try:
            logger.info(f"Downloading transcript from {transcript_url}")
            
            # Handle local URLs for testing
            if transcript_url.startswith("http://localhost") or transcript_url.startswith("file://"):
                if transcript_url.startswith("file://"):
                    file_path = transcript_url[7:]  # Remove file:// prefix
                else:
                    # Extract path from URL for localhost testing
                    from urllib.parse import urlparse
                    parsed_url = urlparse(transcript_url)
                    file_path = parsed_url.path.lstrip('/')
                
                # Check if file exists
                if not os.path.exists(file_path):
                    logger.error(f"Transcript file not found: {file_path}")
                    return {
                        "success": False,
                        "error": f"Transcript file not found: {file_path}"
                    }
                
                # Read transcript from local file
                with open(file_path, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
                    logger.info(f"Successfully read transcript from local file ({len(transcript_text)} chars)")
                    return {
                        "success": True,
                        "text": transcript_text
                    }
            
            # Download from remote URL
            async with aiohttp.ClientSession() as session:
                async with session.get(transcript_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download transcript: HTTP {response.status}")
                        return {
                            "success": False,
                            "error": f"Failed to download transcript: HTTP {response.status}"
                        }
                    
                    transcript_text = await response.text()
                    logger.info(f"Successfully downloaded transcript ({len(transcript_text)} chars)")
                    return {
                        "success": True,
                        "text": transcript_text
                    }
                
        except Exception as e:
            logger.error(f"Error downloading transcript: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def _send_summary_email(self, transcript_id: str, title: str, summary: str, trades: List[Dict[str, Any]]) -> bool:
        """
        Send summary email
        
        Args:
            transcript_id: ID of the transcript
            title: Title of the meeting
            summary: Generated summary
            trades: Extracted trades
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Get subscribers
            subscribers_result = await self.file_storage_service.get_subscribers()
            if not subscribers_result.get("success") or not subscribers_result.get("subscribers"):
                logger.warning("No subscribers found for summary email")
                return False
            
            subscribers = [sub["email"] for sub in subscribers_result.get("subscribers", [])]
            
            # Format trades for email
            trades_text = ""
            if trades:
                trades_text = "\n\n## Extracted Trades\n\n"
                for i, trade in enumerate(trades, 1):
                    trades_text += f"### Trade {i}\n"
                    trades_text += f"- Symbol: {trade.get('symbol', 'N/A')}\n"
                    trades_text += f"- Action: {trade.get('action', 'N/A')}\n"
                    trades_text += f"- Price: {trade.get('price', 'N/A')}\n"
                    trades_text += f"- Quantity: {trade.get('quantity', 'N/A')}\n"
                    trades_text += f"- Confidence: {trade.get('confidence', 'N/A')}\n\n"
            
            # Create email content
            subject = f"Meeting Summary: {title}"
            body = f"""# Meeting Summary: {title}

## Summary
{summary}

{trades_text}

This summary was automatically generated from the transcript.
"""
            
            # Send email
            sent = await self.email_service.send_email(subscribers, subject, body)
            if sent:
                logger.info(f"Summary email sent for transcript {transcript_id}")
                return True
            else:
                logger.error(f"Failed to send summary email for transcript {transcript_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending summary email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def process_transcript(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a transcript from a webhook
        
        Args:
            webhook_data: Webhook data containing transcript information
            
        Returns:
            Dictionary with processing results
        """
        try:
            transcript_id = webhook_data.get("transcript_id")
            if not transcript_id:
                logger.error("No transcript ID provided in webhook data")
                return {"success": False, "error": "No transcript ID provided"}
            
            logger.info(f"Processing transcript: {transcript_id}")
            logger.debug(f"Webhook data: {webhook_data}")
            
            # 1. Download transcript
            transcript_url = webhook_data.get("transcript_url")
            if not transcript_url:
                logger.error("No transcript URL provided in webhook data")
                return {"success": False, "error": "No transcript URL provided"}
            
            logger.info(f"Downloading transcript from URL: {transcript_url}")
            download_result = await self._download_transcript(transcript_url)
            if not download_result:
                logger.error(f"Failed to download transcript from URL: {transcript_url}")
                return {"success": False, "error": "Failed to download transcript"}
            
            transcript_text = download_result.get("text", "")
            if not transcript_text:
                logger.error("Downloaded transcript is empty")
                return {"success": False, "error": "Downloaded transcript is empty"}
            
            logger.info(f"Successfully downloaded transcript: {len(transcript_text)} characters")
            
            # 2. Create transcript record
            logger.info(f"Creating transcript record for {transcript_id}")
            metadata = {
                "title": webhook_data.get("title", "Untitled Meeting"),
                "meeting_id": webhook_data.get("meeting_id", ""),
                "recording_url": webhook_data.get("recording_url", ""),
                "audio_url": webhook_data.get("audio_url", ""),
                "summary": webhook_data.get("summary", ""),
                "metadata": webhook_data.get("metadata", {}),
                "transcript_text": transcript_text
            }
            
            storage_service = self.file_storage_service if self.file_storage_service.is_connected() else self.file_storage
            
            record_result = await storage_service.create_transcript_record(transcript_id, metadata)
            if not record_result.get("success"):
                logger.error(f"Failed to create transcript record: {record_result.get('error')}")
                return {"success": False, "error": f"Failed to create transcript record: {record_result.get('error')}"}
            
            logger.info(f"Transcript record created successfully: {transcript_id}")
            
            # 3. Process transcript into chunks
            logger.info(f"Processing transcript into chunks")
            chunks = self.transcript_processor.process_transcript(transcript_text)
            if not chunks:
                logger.error("Failed to process transcript into chunks")
                return {"success": False, "error": "Failed to process transcript into chunks"}
            
            logger.info(f"Created {len(chunks)} chunks from transcript")
            
            # 4. Generate embeddings for chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            texts = [chunk["text"] for chunk in chunks]
            
            try:
                embeddings = await self.embedding_service.generate_embeddings(texts)
                logger.info(f"Generated {len(embeddings)} embeddings")
            except Exception as e:
                logger.error(f"Error generating embeddings: {str(e)}")
                embeddings = None
            
            # 5. Store chunks and embeddings
            logger.info(f"Storing chunks and embeddings")
            store_result = await storage_service.store_transcript_chunks(transcript_id, chunks, embeddings)
            if not store_result.get("success"):
                logger.error(f"Failed to store chunks: {store_result.get('error')}")
                return {"success": False, "error": f"Failed to store chunks: {store_result.get('error')}"}
            
            logger.info(f"Successfully stored {len(chunks)} chunks")
            
            # 6. Extract trades
            logger.info(f"Extracting trades from transcript")
            trades = await extract_trades(chunks)
            
            logger.info(f"Extracted {len(trades)} trades")
            
            # Store trades
            if trades:
                logger.info(f"Storing {len(trades)} trades")
                for trade in trades:
                    trade_result = await storage_service.create_trade_record(transcript_id, trade)
                    if not trade_result.get("success"):
                        logger.warning(f"Failed to store trade: {trade_result.get('error')}")
            
            # 7. Generate summary
            logger.info(f"Generating transcript summary")
            try:
                # 💡 FIX: Derive duration from transcript content itself
                derived_duration = self._derive_duration_from_transcript(transcript_text)
                
                # 🔄 Enhanced summary generation (with fallback protection)
                summary_result = await self.summary_service.generate_summary(
                    transcript_id=transcript_id,
                    transcript_text=transcript_text,
                    duration_seconds=derived_duration
                )
                
                # Extract the HTML summary from the enhanced result
                if summary_result.get("success") and summary_result.get("summary_html"):
                    summary_html = summary_result["summary_html"]
                    logger.info(f"Generated enhanced summary: {len(summary_html)} characters, {summary_result.get('segments_processed', 0)} segments processed")
                    
                    # Log processing method used
                    if "processing_metadata" in summary_result:
                        method = summary_result["processing_metadata"].get("method", "unknown")
                        logger.info(f"Summary method used: {method}")
                else:
                    # Fallback to a simple summary if enhanced fails
                    summary_html = "Enhanced summary generation failed"
                    logger.warning(f"Enhanced summary failed: {summary_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error generating summary: {str(e)}")
                summary_html = webhook_data.get("summary", "No summary available")
                logger.info(f"Using provided summary fallback: {len(summary_html)} characters")
            
            # 8. Update transcript record with summary
            logger.info(f"Updating transcript record with summary")
            update_result = await storage_service.update_transcript_record(transcript_id, {
                "detailed_summary": summary_html,
                "processing_complete": True,
                "processed_at": datetime.now().isoformat()
            })
            
            if not update_result.get("success"):
                logger.warning(f"Failed to update transcript record: {update_result.get('error')}")
            
            # 9. Send email with summary
            try:
                logger.info(f"Sending summary email for {transcript_id}")
                email_result = await self.email_service.send_session_summary_email(
                    transcript_id,
                    webhook_data.get("title", "Meeting Summary"),
                    summary_html,
                    trades
                )
                
                if email_result.get("success"):
                    logger.info(f"Summary email sent successfully")
                else:
                    logger.warning(f"Failed to send summary email: {email_result.get('error')}")
            except Exception as e:
                logger.error(f"Error sending summary email: {str(e)}")
            
            logger.info(f"Transcript processing complete: {transcript_id}")
            
            return {
                "success": True,
                "transcript_id": transcript_id,
                "chunks": len(chunks),
                "trades": len(trades),
                "summary": True if summary_html else False
            }
            
        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    async def process_transcript_direct(
        self,
        transcript_text: str,
        video_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a transcript with direct text (for YouTube queue service)
        
        Args:
            transcript_text: The actual transcript text content
            video_id: Video ID (for YouTube processing)
            title: Title of the video/meeting
            metadata: Additional metadata including user info
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Generate a unique transcript ID
            if video_id:
                transcript_id = f"yt_{video_id}_{str(uuid.uuid4())[:8]}"
            else:
                transcript_id = f"transcript_{str(uuid.uuid4())[:8]}"
            
            logger.info(f"Processing transcript {transcript_id} for queue service")
            
            # Use the existing pipeline with text
            result = await self.start_ingestion_pipeline_with_text(
                transcript_id=transcript_id,
                transcript_text=transcript_text,
                meeting_title=title,
                meeting_date=datetime.now().isoformat(),
                metadata=metadata
            )
            
            logger.info(f"Queue processing completed for transcript {transcript_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in queue process_transcript: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    async def start_ingestion_pipeline_with_text(
        self,
        transcript_id: str,
        transcript_text: str,
        meeting_title: Optional[str] = None,
        meeting_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start the complete ingestion pipeline with direct transcript text
        (bypasses the download step)
        
        Args:
            transcript_id: Unique identifier for the transcript
            transcript_text: The actual transcript text content
            meeting_title: Title of the meeting (optional)
            meeting_date: Date of the meeting (optional)
            metadata: Additional metadata for the transcript (optional)
            
        Returns:
            Dictionary with success status and details
        """
        start_time = time.time()
        pipeline_id = str(uuid.uuid4())
        logger.info(f"Starting ingestion pipeline {pipeline_id} for transcript {transcript_id} with direct text")
        
        # 🆕 PREMIUM/FREE PIPELINE SPLIT: Determine user tier and pipeline steps
        from app.services.pipeline_utils import (
            is_premium_user, 
            log_pipeline_decision, 
            get_pipeline_steps_for_user,
            validate_pipeline_metadata,
            log_cost_savings
        )
        
        # Validate and normalize metadata
        normalized_metadata = validate_pipeline_metadata(metadata)
        user_plan = normalized_metadata.get("user_plan", "free")
        is_premium = is_premium_user(normalized_metadata)
        pipeline_steps = get_pipeline_steps_for_user(normalized_metadata)
        
        # Log the routing decision for monitoring
        log_pipeline_decision(transcript_id, is_premium, user_plan, normalized_metadata)
        
        try:
            # Initialize tracking for steps
            steps_completed = []
            step_times = {}
            skipped_operations = []  # Track what we skip for cost monitoring
            
            # Step 1: Process transcript (skip download since we have text)
            logger.info("Step 1: Processing transcript text...")
            step_start = time.time()
            
            if not transcript_text or not transcript_text.strip():
                logger.error("Empty transcript text provided")
                return {
                    "success": False,
                    "error": "Empty transcript text provided"
                }
            
            # Process the transcript into chunks
            processed_data = self.transcript_processor.process_transcript(transcript_text)
            
            if not processed_data.get("success", False):
                logger.error(f"Failed to process transcript: {processed_data.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Failed to process transcript: {processed_data.get('error', 'Unknown error')}"
                }
                
            transcript_chunks = processed_data["chunks"]
            
            # Add transcript_id and metadata to each chunk
            for i, chunk in enumerate(transcript_chunks):
                chunk.update({
                    "transcript_id": transcript_id,
                    "chunk_index": i,
                    "position": i,
                    "is_first": i == 0,
                    "is_last": i == len(transcript_chunks) - 1,
                    "metadata": metadata or {}
                })
            
            # Create transcript metadata
            transcript_metadata = {
                "title": meeting_title or "Untitled Meeting",
                "date": meeting_date or datetime.now().isoformat(),
                "word_count": len(transcript_text.split()),
                "chunk_count": len(transcript_chunks),
                "source": metadata.get("source") if metadata else "fireflies_webhook",
                **(metadata or {})
            }
            
            step_times["process_text"] = time.time() - step_start
            steps_completed.append("process_text")
            logger.info(f"Transcript processed into {len(transcript_chunks)} chunks")
            
            # Step 2: Generate embeddings for chunks (PREMIUM ONLY)
            if pipeline_steps['generate_embeddings']:
                logger.info("Step 2: Generating embeddings (Premium user)...")
                step_start = time.time()
                
                # Extract text from chunks for embedding
                chunk_texts = [chunk["text"] for chunk in transcript_chunks]
                
                # Generate embeddings
                embeddings_result = await self.embedding_service.get_embeddings(chunk_texts)
                
                if not embeddings_result:
                    logger.warning("Failed to generate embeddings, continuing without them")
                    chunk_embeddings = None
                else:
                    chunk_embeddings = embeddings_result
                    logger.info(f"Generated {len(chunk_embeddings)} embeddings")
                    
                step_times["generate_embeddings"] = time.time() - step_start
                steps_completed.append("generate_embeddings")
            else:
                logger.info("⏩ Step 2: Skipping embeddings generation (Free user)")
                chunk_embeddings = None
                skipped_operations.append("embeddings_generation")
            
            # Step 3: Store transcript and chunks in database
            logger.info("Step 3: Storing transcript and chunks in database...")
            step_start = time.time()
            
            # Create a session ID if not provided
            meeting_id = metadata.get("meeting_id") if metadata else None
            if not meeting_id:
                meeting_id = f"meet_{uuid.uuid4().hex[:10]}"
                
            # Ensure we have a title
            if not meeting_title:
                meeting_title = transcript_metadata.get("title", "Untitled Meeting")
                
            # Ensure we have a date
            if not meeting_date:
                meeting_date = transcript_metadata.get("date", datetime.now().isoformat())
                
            # Determine which storage service to use
            storage_service = self.supabase_service if self.supabase_service.is_connected() else self.file_storage_service
            storage_type = "Supabase" if self.supabase_service.is_connected() else "File storage"
            
            logger.info(f"Using {storage_type} for transcript storage")
            
            # Create transcript record with user_id if available
            user_id = metadata.get("user_id") if metadata else None
            transcript_record_data = {
                    "meeting_id": meeting_id,
                    "title": meeting_title,
                    "date": meeting_date,
                    **transcript_metadata
                }
            
            # Add user_id if available (for YouTube extension authenticated users)
            if user_id:
                transcript_record_data["user_id"] = user_id
                logger.info(f"Creating transcript record for authenticated user: {user_id}")
            
            transcript_result = await storage_service.create_transcript_record(
                transcript_id, 
                transcript_record_data
            )
            
            if transcript_result["success"]:
                if transcript_result.get("already_exists"):
                    logger.info(f"Transcript {transcript_id} already exists, continuing with processing")
                else:
                    logger.info(f"Created new transcript record {transcript_id}")
                    
                # Store chunks with embeddings (only if transcript was newly created)
                if not transcript_result.get("already_exists"):
                    chunks_result = await storage_service.store_transcript_chunks(
                        transcript_id,
                        transcript_chunks,
                        chunk_embeddings
                    )
                    logger.info(f"Stored transcript and {chunks_result.get('count', 0)} chunks in {storage_type.lower()}")
                else:
                    logger.info(f"Skipping chunk storage for existing transcript {transcript_id}")
            else:
                logger.error(f"Failed to store transcript: {transcript_result.get('error')}")
                # Continue processing even if transcript creation failed (might be a duplicate)
                logger.warning("Continuing with summary generation despite transcript creation failure")
                
            step_times["store_transcript"] = time.time() - step_start
            steps_completed.append("store_transcript")
            
            # Step 3.5: Generate and store semantic chunks (PREMIUM ONLY)
            if pipeline_steps['semantic_chunking']:
                logger.info("Step 3.5: Generating and storing semantic chunks (Premium user)...")
                step_start = time.time()
                
                try:
                    # Generate semantic chunks using the semantic chunker
                    semantic_chunks = self.semantic_chunker.chunk_text(transcript_text, source_id=transcript_id)
                    
                    if semantic_chunks:
                        logger.info(f"Generated {len(semantic_chunks)} semantic chunks")
                        
                        # Extract text from semantic chunks for embedding
                        semantic_chunk_texts = [chunk.text for chunk in semantic_chunks]
                        
                        # Generate embeddings for semantic chunks
                        semantic_embeddings_result = await self.embedding_service.get_embeddings(semantic_chunk_texts)
                        
                        if semantic_embeddings_result and len(semantic_embeddings_result) == len(semantic_chunks):
                            logger.info(f"Generated {len(semantic_embeddings_result)} semantic embeddings")
                            
                            # Store semantic chunks in the semantic_chunks table
                            semantic_store_result = await self.semantic_chunks_service.store_semantic_chunks(
                                chunks=semantic_chunks,
                                embeddings=semantic_embeddings_result,
                                transcript_id=transcript_id
                            )
                            
                            if semantic_store_result.get("success"):
                                chunks_stored = semantic_store_result.get("chunks_stored", 0)
                                logger.info(f"Successfully stored {chunks_stored} semantic chunks")
                            else:
                                logger.warning(f"Failed to store semantic chunks: {semantic_store_result.get('error')}")
                        else:
                            logger.warning("Failed to generate embeddings for semantic chunks, skipping semantic chunk storage")
                    else:
                        logger.warning("No semantic chunks generated, skipping semantic chunk storage")
                        
                except Exception as e:
                    logger.warning(f"Error processing semantic chunks: {e}, continuing with regular pipeline")
                    
                step_times["store_semantic_chunks"] = time.time() - step_start
                steps_completed.append("store_semantic_chunks")
            else:
                logger.info("⏩ Step 3.5: Skipping semantic chunking (Free user)")
                skipped_operations.extend(["semantic_chunking", "semantic_embeddings"])
            
            # Step 4: Generate summary
            logger.info("Step 4: Generating summary...")
            step_start = time.time()
            
            # 💡 FIX: Derive duration from transcript content itself
            derived_duration = self._derive_duration_from_transcript(transcript_text)
            
            # Enhanced summary generation - NO FALLBACKS, fail explicitly
            summary_result = await self.summary_service.generate_summary(
                transcript_id=transcript_id,
                transcript_text=transcript_text,
                duration_seconds=derived_duration
            )
            
            # Extract HTML summary from the result dictionary - NO FALLBACKS
            if isinstance(summary_result, dict) and "summary_html" in summary_result:
                summary_html = summary_result["summary_html"]
                logger.info(f"Generated enhanced summary: {len(summary_html)} chars")
                
                # Log additional summary statistics if available
                if "segments_processed" in summary_result:
                    logger.info(f"Enhanced summary processed {summary_result['segments_processed']} segments")
                if "enhancement_level" in summary_result:
                    logger.info(f"Enhancement level: {summary_result['enhancement_level']}")
                if "processing_metadata" in summary_result:
                    method = summary_result["processing_metadata"].get("method", "unknown")
                    logger.info(f"Summary method used: {method}")
            else:
                # NO FALLBACK - fail explicitly to expose the real issue
                raise ValueError(f"Summary service returned invalid format: {type(summary_result)}. Expected dict with 'summary_html' key.")
            
            # Store summary in database
            update_result = await storage_service.update_transcript_record(
                transcript_id,
                {"summary": summary_html}
            )
            
            if update_result["success"]:
                logger.info(f"Summary stored in {storage_type.lower()}")
            else:
                logger.error(f"Failed to store summary: {update_result.get('error')}")
                    
            step_times["generate_summary"] = time.time() - step_start
            steps_completed.append("generate_summary")
            
            # Step 5: Extract trades
            logger.info("Step 5: Extracting trades...")
            step_start = time.time()
            
            trades = await self.trade_extraction.extract_trades(transcript_text)
            
            logger.info(f"Extracted {len(trades)} trades")
            
            # Store trades in database
            if trades:
                for trade in trades:
                    trade_result = await storage_service.create_trade_record(
                        transcript_id,
                        trade
                    )
                    
                    if not trade_result["success"]:
                        logger.error(f"Failed to store trade: {trade_result.get('error')}")
                        
            step_times["extract_trades"] = time.time() - step_start
            steps_completed.append("extract_trades")
            
            # Step 6: Send email to subscribers
            logger.info("Step 6: Sending emails to subscribers...")
            step_start = time.time()
            
            # Get subscribers from storage service
            subscribers_result = await storage_service.get_subscribers()
            subscribers = subscribers_result.get("subscribers", []) if subscribers_result["success"] else []
                    
            # If no subscribers in database, check environment variables
            if not subscribers:
                from os import getenv
                admin_email = getenv("ADMIN_EMAIL")
                if admin_email:
                    subscribers = [{"email": admin_email}]
                    
            # Extract action items from summary result (if available)
            action_items = []
            if isinstance(summary_result, dict):
                action_items = summary_result.get("action_items", [])
                logger.info(f"Found {len(action_items)} action items in summary")
            
            # Determine email recipient – prefer the authenticated user when available
            user_id = metadata.get("user_id") if metadata else None
            user_email = metadata.get("user_email") if metadata else None
            email_recipients = []
            
            # If the pipeline has information about the authenticated user, always email them first.
            # We no longer gate this on a specific `source` value – this prevents regressions when the
            # caller forgets to set the correct string (e.g. "youtube" vs "youtube_extension").
            if user_id:
                if user_email:
                    # Use email from metadata (more efficient)
                    email_recipients = [{"email": user_email, "name": ""}]
                    logger.info(f"Sending summary to authenticated user: {user_email}")
                else:
                    # Fallback: Get user's email from the database
                    try:
                        from app.services.supabase_client import get_supabase_client
                        supabase = get_supabase_client()
                        
                        user_response = supabase.table("user_profiles").select("email, full_name").eq("user_id", user_id).execute()
                        
                        if user_response.data:
                            db_user_email = user_response.data[0]["email"]
                            user_name = user_response.data[0].get("full_name", "")
                            email_recipients = [{"email": db_user_email, "name": user_name}]
                            logger.info(f"Sending summary to authenticated user: {db_user_email}")
                        else:
                            logger.warning(f"User profile not found for user_id: {user_id}")
                            # Fall back to subscribers if user not found
                            email_recipients = []
                            
                    except Exception as e:
                        logger.error(f"Error getting user email for {user_id}: {e}")
                        # Fall back to subscribers on error
                        email_recipients = []
            
            # If no authenticated user email found, fall back to subscribers list
            if not email_recipients:
                logger.info("Falling back to subscribers list...")
                email_recipients = subscribers
            
            # Send emails to determined recipients
            email_results = []
            logger.info(f"Sending emails to {len(email_recipients)} recipients")
            
            for recipient in email_recipients:
                email_result = await self.email_service.send_quicksheet_email(
                    recipient["email"],
                    {"title": meeting_title, "date": meeting_date},
                    summary_html,
                    trades,
                    action_items,
                    transcript_id=transcript_id,
                    metadata=metadata  # Pass the fresh metadata from the pipeline
                )
                
                email_results.append(email_result)
                logger.info(f"Email sent to {recipient['email']}: {email_result.get('success', False)}")
                
            logger.info(f"Sent {len(email_results)} emails")
                
            step_times["send_emails"] = time.time() - step_start
            steps_completed.append("send_emails")
            
            # Log cost savings for monitoring
            log_cost_savings(transcript_id, user_plan, skipped_operations)
            
            # Finalize and return result
            end_time = time.time()
            total_time = end_time - start_time
            
            logger.info(f"Ingestion pipeline (with text) completed in {total_time:.2f} seconds")
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "transcript_id": transcript_id,
                "meeting_id": meeting_id,
                "storage_type": storage_type,
                "steps_completed": steps_completed,
                "step_times": step_times,
                "total_time": total_time,
                "summary_length": len(summary_html),
                "summary_html": summary_html,
                "trades_count": len(trades),
                "emails_sent": len(email_results),
                "transcript_length": len(transcript_text),
                # 🆕 Pipeline split information
                "pipeline_info": {
                    "user_plan": user_plan,
                    "premium_features": is_premium,
                    "skipped_operations": skipped_operations,
                    "cost_savings_enabled": len(skipped_operations) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in ingestion pipeline (with text): {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "pipeline_id": pipeline_id
            }

# Standalone function for background tasks
async def start_ingestion_pipeline(
    transcript_id: str, 
    transcript_url: str, 
    meeting_title: Optional[str] = None, 
    meeting_date: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Standalone function to start the ingestion pipeline
    
    Args:
        transcript_id: Unique identifier for the transcript
        transcript_url: URL to download the transcript from
        meeting_title: Title of the meeting (optional)
        meeting_date: Date of the meeting (optional)
        metadata: Additional metadata for the transcript (optional)
        
    Returns:
        Dictionary with success status and details
    """
    service = IngestionService()
    return await service.start_ingestion_pipeline(
        transcript_id, 
        transcript_url, 
        meeting_title, 
        meeting_date,
        metadata
    ) 