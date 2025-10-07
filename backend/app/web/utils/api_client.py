"""
API Client Utility for BPT Trading Assistant

Handles communication with the BPT backend API for question answering,
health checks, transcript processing, and other backend services.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional, List
import streamlit as st

class BPTAPIClient:
    """Client for interacting with the BPT backend API."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the BPT API. If None, will try to determine from environment.
        """
        self.base_url = base_url or self._get_base_url()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "BPT-Streamlit-Client/1.0"
        })
        
        # Set timeout for all requests
        self.timeout = 30
    
    def _get_base_url(self) -> str:
        """Determine the API base URL from environment or default."""
        # Try different possible configurations
        bpt_api_url = os.getenv("BPT_API_URL")
        api_url_env = os.getenv("API_URL")
        
        # Also check Railway's built-in service URL as fallback
        railway_backend_url = os.getenv("RAILWAY_SERVICE_BPT_URL")
        if railway_backend_url and not railway_backend_url.startswith('http'):
            railway_backend_url = f"https://{railway_backend_url}"
        
        api_url = (
            bpt_api_url or 
            api_url_env or 
            railway_backend_url or
            "http://localhost:8002"  # Updated to match our server configuration
        )
        
        # Debug logging to help troubleshoot URL configuration
        print(f"[API_CLIENT] Environment variables:")
        print(f"  BPT_API_URL: {bpt_api_url}")
        print(f"  API_URL: {api_url_env}")
        print(f"  RAILWAY_SERVICE_BPT_URL: {railway_backend_url}")
        print(f"  Selected API URL: {api_url}")
        
        # Ensure it doesn't end with a slash
        return api_url.rstrip('/')
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the API is healthy and accessible.
        
        Returns:
            Dict containing health status and any additional info
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "healthy": True,
                    "status": data.get("status", "healthy"),
                    "health": data,  # Include full health data
                    "timestamp": time.time()
                }
            else:
                return {
                    "success": False,
                    "healthy": False,
                    "error": f"HTTP {response.status_code}",
                    "timestamp": time.time()
                }
        
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "healthy": False,
                "error": "Request timeout - API may be slow or unresponsive",
                "timestamp": time.time()
            }
        
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "healthy": False,
                "error": f"Cannot connect to API at {self.base_url}",
                "timestamp": time.time()
            }
        
        except Exception as e:
            return {
                "success": False,
                "healthy": False,
                "error": f"Unexpected error: {str(e)}",
                "timestamp": time.time()
            }
    
    def ask_question(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ask a question to the BPT system.
        
        Args:
            question: The question to ask
            session_id: Optional session ID for context
        
        Returns:
            Dict containing the answer and metadata
        """
        try:
            payload = {
                "question": question.strip(),
                "session_id": session_id,
                "timestamp": time.time(),
                "source": "streamlit_web"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/qa",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "answer": data.get("answer", ""),
                    "confidence": data.get("confidence"),
                    "sources": data.get("sources", []),
                    "processing_time": data.get("processing_time"),
                    "session_id": data.get("session_id"),
                    "timestamp": time.time()
                }
            
            elif response.status_code == 400:
                error_data = response.json()
                return {
                    "success": False,
                    "error": error_data.get("detail", "Bad request"),
                    "error_type": "validation",
                    "timestamp": time.time()
                }
            
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "No relevant information found for your question",
                    "error_type": "not_found",
                    "timestamp": time.time()
                }
            
            elif response.status_code == 500:
                return {
                    "success": False,
                    "error": "Internal server error - please try again later",
                    "error_type": "server_error",
                    "timestamp": time.time()
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unexpected response code: {response.status_code}",
                    "error_type": "http_error",
                    "timestamp": time.time()
                }
        
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout - the query is taking too long",
                "error_type": "timeout",
                "timestamp": time.time()
            }
        
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Cannot connect to the BPT API",
                "error_type": "connection",
                "timestamp": time.time()
            }
        
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid response format from API",
                "error_type": "json_error",
                "timestamp": time.time()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown",
                "timestamp": time.time()
            }
    
    def process_transcript(self, content: str, filename: str = "uploaded_transcript.txt") -> Dict[str, Any]:
        """
        Process an uploaded transcript file.
        
        Args:
            content: The transcript content
            filename: Original filename
        
        Returns:
            Dict containing processing results
        """
        try:
            payload = {
                "content": content,
                "filename": filename,
                "source": "streamlit_upload",
                "timestamp": time.time()
            }
            
            response = self.session.post(
                f"{self.base_url}/api/qa/process-transcript",
                json=payload,
                timeout=60  # Longer timeout for processing
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "session_id": data.get("session_id"),
                    "stats": data.get("stats", {}),
                    "processing_time": data.get("processing_time"),
                    "timestamp": time.time()
                }
            
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                return {
                    "success": False,
                    "error": error_data.get("detail", f"HTTP {response.status_code}"),
                    "timestamp": time.time()
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Processing error: {str(e)}",
                "timestamp": time.time()
            }
    
    def get_recent_sessions(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent transcript sessions.
        
        Args:
            limit: Maximum number of sessions to return
        
        Returns:
            Dict containing session list
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/qa/sessions",
                params={"limit": limit},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", True),
                    "sessions": data.get("sessions", []),
                    "total": data.get("total", 0),
                    "timestamp": time.time()
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Failed to fetch sessions: HTTP {response.status_code}",
                    "timestamp": time.time()
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching sessions: {str(e)}",
                "timestamp": time.time()
            }
    
    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """
        Get details for a specific session.
        
        Args:
            session_id: The session ID
        
        Returns:
            Dict containing session details
        """
        try:
            response = self.session.get(
                f"{self.base_url}/transcripts/{session_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "session": data,
                    "timestamp": time.time()
                }
            
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "Session not found",
                    "timestamp": time.time()
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Failed to fetch session: HTTP {response.status_code}",
                    "timestamp": time.time()
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching session: {str(e)}",
                "timestamp": time.time()
            }

    def get_transcript_content(self, transcript_id: str, include_chunks: bool = True) -> Dict[str, Any]:
        """
        Get content of a specific transcript.
        
        Args:
            transcript_id: ID of the transcript to retrieve
            include_chunks: Whether to include chunk details
        
        Returns:
            Dict containing transcript content and metadata
        """
        try:
            params = {"include_chunks": include_chunks} if not include_chunks else {}
            
            response = self.session.get(
                f"{self.base_url}/transcripts/{transcript_id}",
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "transcript": data,
                    "timestamp": time.time()
                }
            
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "Transcript not found",
                    "error_type": "not_found",
                    "timestamp": time.time()
                }
            
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: Failed to get transcript",
                    "error_type": "http_error",
                    "timestamp": time.time()
                }
        
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "error_type": "timeout",
                "timestamp": time.time()
            }
        
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Cannot connect to API",
                "error_type": "connection",
                "timestamp": time.time()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown",
                "timestamp": time.time()
            }

    def delete_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """
        Delete a transcript and all its related data.
        
        This method sends a DELETE request to remove:
        - The transcript record
        - All transcript chunks
        - All semantic chunks
        - Key points analysis
        - Transcript sharing permissions
        
        This action cannot be undone.
        
        Args:
            transcript_id: ID of the transcript to delete
        
        Returns:
            Dict containing deletion results and metadata
        """
        try:
            response = self.session.delete(
                f"{self.base_url}/transcripts/{transcript_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "transcript_id": transcript_id,
                    "deleted_items": data.get("deleted_items", {}),
                    "total_deleted": data.get("total_deleted", 0),
                    "processing_time": data.get("processing_time", 0),
                    "timestamp": time.time()
                }
            
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "Transcript not found",
                    "error_type": "not_found",
                    "timestamp": time.time()
                }
            
            elif response.status_code == 400:
                error_data = response.json()
                return {
                    "success": False,
                    "error": error_data.get("detail", "Bad request"),
                    "error_type": "validation",
                    "timestamp": time.time()
                }
            
            elif response.status_code == 500:
                error_data = response.json()
                return {
                    "success": False,
                    "error": error_data.get("detail", "Internal server error during deletion"),
                    "error_type": "server_error",
                    "timestamp": time.time()
                }
            
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: Failed to delete transcript",
                    "error_type": "http_error",
                    "timestamp": time.time()
                }
        
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout - deletion may take longer than expected",
                "error_type": "timeout",
                "timestamp": time.time()
            }
        
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Cannot connect to API",
                "error_type": "connection",
                "timestamp": time.time()
            }
        
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid response format from API",
                "error_type": "json_error",
                "timestamp": time.time()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown",
                "timestamp": time.time()
            }

# Cache the API client instance to avoid recreation
@st.cache_resource
def get_api_client() -> BPTAPIClient:
    """Get a cached instance of the API client."""
    return BPTAPIClient()

# Helper function for error handling in Streamlit
def handle_api_error(response: Dict[str, Any], context: str = "operation"):
    """
    Handle API errors gracefully in Streamlit interface.
    
    Args:
        response: API response dict
        context: Context description for the error
    """
    if not response.get("success", False):
        error = response.get("error", "Unknown error")
        error_type = response.get("error_type", "unknown")
        
        if error_type == "connection":
            st.error(f"🔌 Connection Error: {error}")
            st.info("💡 Make sure the BPT API server is running and accessible")
        
        elif error_type == "timeout":
            st.error(f"⏰ Timeout Error: {error}")
            st.info("💡 The request is taking longer than expected. Try again or simplify your question.")
        
        elif error_type == "not_found":
            st.warning(f"🔍 No Results: {error}")
            st.info("💡 Try rephrasing your question or asking about recent trading sessions.")
        
        elif error_type == "validation":
            st.error(f"⚠️ Input Error: {error}")
            st.info("💡 Please check your input and try again.")
        
        else:
            st.error(f"❌ Error during {context}: {error}")
            
        return False
    
    return True 