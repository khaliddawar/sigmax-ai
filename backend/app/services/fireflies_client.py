"""
Fireflies.ai GraphQL API Client

This service handles communication with the Fireflies.ai GraphQL API
to fetch transcript data when webhooks are received.
"""

import os
import httpx
import logging
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger("bpt-fireflies-client")

class FirefliesClient:
    """
    Client for interacting with Fireflies.ai GraphQL API
    """
    
    def __init__(self):
        self.api_key = os.getenv("FIREFLIES_API_KEY")
        self.base_url = "https://api.fireflies.ai/graphql"
        self.timeout = 30.0
        
        if not self.api_key:
            logger.warning("No FIREFLIES_API_KEY found in environment variables")
            
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_transcript_by_meeting_id(self, meeting_id: str) -> Dict[str, Any]:
        """
        Fetch transcript data from Fireflies using the meeting ID
        
        Args:
            meeting_id: The meeting/transcript ID from Fireflies
            
        Returns:
            Dict with success status and transcript data
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "No Fireflies API key configured"
                }
            
            # GraphQL query to fetch transcript data
            query = """
            query GetTranscript($transcriptId: String!) {
                transcript(id: $transcriptId) {
                    id
                    title
                    date
                    duration
                    organizer_email
                    participants
                    transcript_url
                    sentences {
                        raw_text
                        speaker_name
                        start_time
                        end_time
                    }
                    speakers {
                        id
                        name
                    }
                    summary {
                        keywords
                        action_items
                        outline
                        shorthand_bullet
                        overview
                        bullet_gist
                    }
                    meeting_info {
                        fred_joined
                        silent_meeting
                        summary_status
                    }
                }
            }
            """
            
            payload = {
                "query": query,
                "variables": {
                    "transcriptId": meeting_id
                }
            }
            
            logger.info(f"Fetching transcript data for meeting ID: {meeting_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    return {
                        "success": False,
                        "error": f"GraphQL errors: {data['errors']}"
                    }
                
                # Extract transcript data
                transcript_data = data.get("data", {}).get("transcript")
                
                if not transcript_data:
                    logger.error(f"No transcript data found for meeting ID: {meeting_id}")
                    return {
                        "success": False,
                        "error": "No transcript data found"
                    }
                
                # Log the structure for debugging
                logger.info(f"Transcript data keys: {list(transcript_data.keys()) if transcript_data else 'None'}")
                
                # Process the sentence data to create full transcript text with better null handling
                sentences = transcript_data.get("sentences") or []
                transcript_text = ""
                
                # Ensure sentences is a list and not None
                if not isinstance(sentences, list):
                    logger.warning(f"Sentences field is not a list: {type(sentences)}, value: {sentences}")
                    sentences = []
                
                if sentences:
                    try:
                        # Sort by start_time and combine into full text
                        sorted_sentences = sorted(sentences, key=lambda x: x.get("start_time", 0) if x else 0)
                        
                        current_speaker = None
                        for sentence in sorted_sentences:
                            if not sentence:  # Skip None/null sentences
                                continue
                                
                            speaker_name = sentence.get("speaker_name", "Unknown")
                            text = sentence.get("raw_text", "").strip()
                            
                            if text:
                                # Add speaker label if changed
                                if speaker_name != current_speaker:
                                    if transcript_text:
                                        transcript_text += "\n\n"
                                    transcript_text += f"{speaker_name}: "
                                    current_speaker = speaker_name
                                else:
                                    transcript_text += " "
                                
                                transcript_text += text
                    except Exception as e:
                        logger.error(f"Error processing sentences: {str(e)}")
                        sentences = []  # Reset to empty list on error
                
                # Handle speakers with better null checking
                speakers_data = transcript_data.get("speakers") or []
                if not isinstance(speakers_data, list):
                    logger.warning(f"Speakers field is not a list: {type(speakers_data)}, value: {speakers_data}")
                    speakers_data = []
                
                # Handle participants with better null checking  
                participants_data = transcript_data.get("participants") or []
                if not isinstance(participants_data, list):
                    logger.warning(f"Participants field is not a list: {type(participants_data)}, value: {participants_data}")
                    participants_data = []
                
                # Return processed data
                processed_data = {
                    "transcript_id": transcript_data.get("id"),
                    "title": transcript_data.get("title"),
                    "transcript_text": transcript_text,
                    "date": transcript_data.get("date"),
                    "duration": transcript_data.get("duration"),
                    "organizer_email": transcript_data.get("organizer_email"),
                    "participants": participants_data,
                    "speakers": [
                        {
                            "id": speaker.get("id") if speaker else None,
                            "name": speaker.get("name") if speaker else None
                        } 
                        for speaker in speakers_data if speaker is not None
                    ],
                    "summary": transcript_data.get("summary") or {},
                    "meeting_info": transcript_data.get("meeting_info") or {},
                    "sentence_count": len(sentences) if isinstance(sentences, list) else 0,
                    "transcript_url": transcript_data.get("transcript_url")
                }
                
                logger.info(f"Successfully fetched transcript data for {meeting_id}: {len(transcript_text)} characters, {len(sentences)} sentences")
                
                return {
                    "success": True,
                    "data": processed_data
                }
                
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching transcript data for meeting ID: {meeting_id}")
            return {
                "success": False,
                "error": "Request timeout"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching transcript data: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error fetching transcript data: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Fireflies API
        
        Returns:
            Dict with success status and connection info
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "No API key configured"
                }
            
            # Simple query to test connection
            query = """
            query TestConnection {
                user {
                    user_id
                    email
                }
            }
            """
            
            payload = {
                "query": query
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data:
                    return {
                        "success": False,
                        "error": f"GraphQL errors: {data['errors']}"
                    }
                
                user_data = data.get("data", {}).get("user")
                
                return {
                    "success": True,
                    "data": {
                        "user": user_data,
                        "api_url": self.base_url
                    }
                }
                
        except Exception as e:
            logger.error(f"Error testing Fireflies connection: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_recent_transcripts(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent transcripts from Fireflies
        
        Args:
            limit: Number of transcripts to fetch
            
        Returns:
            Dict with success status and transcripts list
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "No API key configured"
                }
            
            query = """
            query GetRecentTranscripts($limit: Int!) {
                transcripts(limit: $limit) {
                    id
                    title
                    date
                    duration
                    organizer_email
                }
            }
            """
            
            payload = {
                "query": query,
                "variables": {
                    "limit": limit
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data:
                    return {
                        "success": False,
                        "error": f"GraphQL errors: {data['errors']}"
                    }
                
                transcripts = data.get("data", {}).get("transcripts", [])
                
                return {
                    "success": True,
                    "data": transcripts
                }
                
        except Exception as e:
            logger.error(f"Error fetching recent transcripts: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 