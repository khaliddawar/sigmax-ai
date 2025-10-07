import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import traceback
import uuid
import datetime

logger = logging.getLogger("bpt-file-storage")

class FileStorageService:
    """Service for storing files locally"""
    
    def __init__(self, base_dir: str = "data"):
        """Initialize the file storage service with a base directory"""
        self.base_dir = Path(base_dir)
        
        # Create required directories
        self.transcripts_dir = self.base_dir / "transcripts"
        self.chunks_dir = self.base_dir / "chunks"
        self.embeddings_dir = self.base_dir / "embeddings"
        self.trades_dir = self.base_dir / "trades"
        
        for directory in [self.transcripts_dir, self.chunks_dir, self.embeddings_dir, self.trades_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"File storage initialized at {base_dir}")
        
    def is_connected(self) -> bool:
        """Check if file storage is connected (always true for local storage)"""
        return True
    
    async def save_json(self, filename: str, data: Dict[str, Any]) -> str:
        """
        Save JSON data to a file
        
        Args:
            filename: Name of the file to save
            data: Data to save as JSON
            
        Returns:
            Path to the saved file
        """
        try:
            # Ensure the filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Save to transcripts directory
            file_path = self.transcripts_dir / filename
            
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"JSON data saved to: {file_path}")
            
            return str(file_path)
        except Exception as e:
            logger.error(f"Error saving JSON file {filename}: {str(e)}")
            raise
    
    async def create_transcript_record(self, transcript_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a transcript record
        
        Args:
            transcript_id: ID of the transcript
            metadata: Metadata for the transcript
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Create a record with metadata and timestamp
            record = {
                "id": str(uuid.uuid4()),
                "transcript_id": transcript_id,
                "created_at": datetime.datetime.now().isoformat(),
                **metadata
            }
            
            # Save to file
            file_path = self.transcripts_dir / f"{transcript_id}.json"
            with open(file_path, "w") as f:
                json.dump(record, f, indent=2)
                
            logger.info(f"Created transcript record: {transcript_id}")
            
            return {
                "success": True,
                "data": record
            }
        except Exception as e:
            logger.error(f"Error creating transcript record: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_transcript_record(self, transcript_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a transcript record
        
        Args:
            transcript_id: ID of the transcript
            updates: Updates to apply to the transcript
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Load existing record
            file_path = self.transcripts_dir / f"{transcript_id}.json"
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"Transcript record not found: {transcript_id}"
                }
                
            with open(file_path, "r") as f:
                record = json.load(f)
                
            # Apply updates
            record.update(updates)
            record["updated_at"] = datetime.datetime.now().isoformat()
            
            # Save updated record
            with open(file_path, "w") as f:
                json.dump(record, f, indent=2)
                
            logger.info(f"Updated transcript record: {transcript_id}")
            
            return {
                "success": True,
                "data": record
            }
        except Exception as e:
            logger.error(f"Error updating transcript record: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def store_transcript_chunks(self, transcript_id: str, chunks: List[Dict[str, Any]], embeddings: Optional[List[List[float]]] = None) -> Dict[str, Any]:
        """
        Store transcript chunks with embeddings
        
        Args:
            transcript_id: ID of the transcript
            chunks: List of transcript chunks
            embeddings: List of embeddings for chunks (optional)
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Create directory for transcript chunks
            chunks_dir = self.chunks_dir / transcript_id
            chunks_dir.mkdir(parents=True, exist_ok=True)
            
            # Create directory for embeddings if provided
            if embeddings:
                embeddings_dir = self.embeddings_dir / transcript_id
                embeddings_dir.mkdir(parents=True, exist_ok=True)
            
            # Store each chunk
            for i, chunk in enumerate(chunks):
                # Add chunk ID and save to file
                chunk_id = f"chunk_{i}"
                chunk_with_id = {
                    "id": chunk_id,
                    "transcript_id": transcript_id,
                    "index": i,
                    **chunk
                }
                
                # Save chunk
                chunk_path = chunks_dir / f"{chunk_id}.json"
                with open(chunk_path, "w") as f:
                    json.dump(chunk_with_id, f, indent=2)
                
                # Save embedding if provided
                if embeddings and i < len(embeddings):
                    embedding_path = embeddings_dir / f"{chunk_id}.json"
                    with open(embedding_path, "w") as f:
                        json.dump({
                            "id": chunk_id,
                            "transcript_id": transcript_id,
                            "embedding": embeddings[i]
                        }, f, indent=2)
            
            logger.info(f"Stored {len(chunks)} chunks for transcript: {transcript_id}")
            
            return {
                "success": True,
                "count": len(chunks)
            }
        except Exception as e:
            logger.error(f"Error storing chunks: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_trade_record(self, transcript_id: str, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a trade record
        
        Args:
            transcript_id: ID of the transcript
            trade_data: Trade data
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Create directory for transcript trades
            trades_dir = self.trades_dir / transcript_id
            trades_dir.mkdir(parents=True, exist_ok=True)
            
            # Add trade ID and timestamps
            trade_id = str(uuid.uuid4())
            trade_record = {
                "id": trade_id,
                "transcript_id": transcript_id,
                "created_at": datetime.datetime.now().isoformat(),
                **trade_data
            }
            
            # Save to file
            trade_path = trades_dir / f"{trade_id}.json"
            with open(trade_path, "w") as f:
                json.dump(trade_record, f, indent=2)
                
            logger.info(f"Created trade record for transcript: {transcript_id}")
            
            return {
                "success": True,
                "data": trade_record
            }
        except Exception as e:
            logger.error(f"Error creating trade record: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_subscribers(self) -> Dict[str, Any]:
        """
        Get subscribers from configuration
        
        Returns:
            Dictionary with success status and subscribers
        """
        # For file-based storage, we'll get this from environment variable
        from os import getenv
        admin_email = getenv("ADMIN_EMAIL")
        
        subscribers = []
        if admin_email:
            subscribers.append({"email": admin_email})
        else:
            # Always return at least one subscriber for testing
            subscribers.append({"email": "admin@example.com"})
            
        return {
            "success": True,
            "subscribers": subscribers
        }
    
    async def get_transcript_chunks(self, transcript_id: str) -> Dict[str, Any]:
        """Get all chunks for a transcript"""
        try:
            # Get chunk directory
            chunk_dir = self.chunks_dir / transcript_id
            
            if not chunk_dir.exists():
                return {
                    "success": False,
                    "error": f"No chunks found for transcript {transcript_id}"
                }
                
            # Read all chunk files
            chunks = []
            for chunk_file in sorted(chunk_dir.glob("chunk_*.json")):
                with open(chunk_file, "r") as f:
                    chunks.append(json.load(f))
                    
            logger.info(f"Retrieved {len(chunks)} chunks for transcript {transcript_id}")
            
            return {
                "success": True,
                "chunks": chunks
            }
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_transcript_by_id(self, transcript_id: str) -> Dict[str, Any]:
        """Get a transcript by ID"""
        try:
            # Get transcript file
            file_path = self.transcripts_dir / f"{transcript_id}.json"
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"Transcript {transcript_id} not found"
                }
                
            # Read transcript data
            with open(file_path, "r") as f:
                transcript = json.load(f)
                
            # Get chunks if available
            chunks_result = await self.get_transcript_chunks(transcript_id)
            if chunks_result["success"]:
                transcript["chunks"] = chunks_result["chunks"]
                
            logger.info(f"Retrieved transcript {transcript_id}")
            
            return {
                "success": True,
                "transcript": transcript
            }
        except Exception as e:
            logger.error(f"Error retrieving transcript: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_transcripts(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get all transcripts"""
        try:
            # Get all transcript files
            transcript_files = list(self.transcripts_dir.glob("*.json"))
            
            # Apply pagination
            paginated_files = transcript_files[offset:offset + limit]
            
            # Read transcript data
            transcripts = []
            for file_path in paginated_files:
                with open(file_path, "r") as f:
                    transcript = json.load(f)
                    transcript["id"] = file_path.stem  # Add ID from filename
                    transcripts.append(transcript)
                    
            logger.info(f"Retrieved {len(transcripts)} transcripts")
            
            return {
                "success": True,
                "transcripts": transcripts,
                "total": len(transcript_files),
                "offset": offset,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error retrieving transcripts: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_trades_for_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """Get all trades for a transcript"""
        try:
            # Get trade directory
            trade_dir = self.trades_dir / transcript_id
            
            if not trade_dir.exists():
                return {
                    "success": True,
                    "trades": []  # No trades yet
                }
                
            # Read all trade files
            trades = []
            for trade_file in trade_dir.glob("*.json"):
                with open(trade_file, "r") as f:
                    trades.append(json.load(f))
                    
            logger.info(f"Retrieved {len(trades)} trades for transcript {transcript_id}")
            
            return {
                "success": True,
                "trades": trades
            }
        except Exception as e:
            logger.error(f"Error retrieving trades: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_transcript(self, transcript_id: str) -> bool:
        """Clear a transcript and all related data"""
        try:
            # Remove transcript file
            transcript_path = self.transcripts_dir / f"{transcript_id}.json"
            if transcript_path.exists():
                transcript_path.unlink()
                
            # Remove chunk directory
            chunk_dir = self.chunks_dir / transcript_id
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)
                
            # Remove embedding directory
            embedding_dir = self.embeddings_dir / transcript_id
            if embedding_dir.exists():
                shutil.rmtree(embedding_dir)
                
            # Remove trade directory
            trade_dir = self.trades_dir / transcript_id
            if trade_dir.exists():
                shutil.rmtree(trade_dir)
                
            logger.info(f"Cleared transcript {transcript_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error clearing transcript: {str(e)}")
            return False 
    
    async def get_transcript_by_hash(self, transcript_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get a transcript by its hash for duplicate detection
        
        Args:
            transcript_hash: Hash of the transcript content
            
        Returns:
            Dictionary with transcript data or None if not found
        """
        try:
            import hashlib
            
            # Search through all transcript files for one with matching hash
            for file_path in self.transcripts_dir.glob("*.json"):
                with open(file_path, "r") as f:
                    transcript_data = json.load(f)
                    
                # Check if this transcript has the matching hash
                if transcript_data.get("transcript"):
                    content_hash = hashlib.md5(transcript_data["transcript"].encode()).hexdigest()[:16]
                    if content_hash == transcript_hash:
                        logger.info(f"Found transcript with hash {transcript_hash}")
                        return {
                            "transcript_id": transcript_data.get("transcript_id", file_path.stem),
                            "video_id": transcript_data.get("video_id"),
                            "title": transcript_data.get("title", "Unknown Title"),
                            "transcript": transcript_data.get("transcript"),
                            "metadata": transcript_data.get("metadata", {}),
                            "file_path": str(file_path)
                        }
            
            logger.info(f"No transcript found with hash {transcript_hash}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for transcript by hash: {str(e)}")
            return None