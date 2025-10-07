"""
Session Manager Utility for BPT Trading Assistant

Handles Streamlit session state management, chat history persistence,
and export functionality for the web interface.
"""

import streamlit as st
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class SessionManager:
    """Manages session state and chat history for the Streamlit interface."""
    
    def __init__(self):
        """Initialize the session manager."""
        self.session_key_prefix = "bpt_"
    
    def initialize_session_state(self):
        """Initialize Streamlit session state with default values."""
        
        # Chat messages list
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Session start time
        if "session_start" not in st.session_state:
            st.session_state.session_start = time.time()
        
        # Session metadata
        if "session_metadata" not in st.session_state:
            st.session_state.session_metadata = {
                "created_at": datetime.now().isoformat(),
                "user_agent": "streamlit_web",
                "session_id": self._generate_session_id()
            }
        
        # Transcript context tracking
        if "active_transcript" not in st.session_state:
            st.session_state.active_transcript = {
                "transcript_id": None,
                "name": None,
                "created_at": None,
                "last_modified": None,
                "metadata": {},
                "is_active": False
            }
        
        # Available transcripts cache
        if "transcripts_cache" not in st.session_state:
            st.session_state.transcripts_cache = {
                "transcripts": [],
                "last_updated": 0,
                "cache_duration": 300  # 5 minutes cache
            }
        
        # Error tracking
        if "errors" not in st.session_state:
            st.session_state.errors = []
        
        # User preferences
        if "user_preferences" not in st.session_state:
            st.session_state.user_preferences = {
                "theme": "light",
                "show_timestamps": True,
                "auto_scroll": True,
                "response_streaming": True
            }
        
        # API status cache
        if "api_status_cache" not in st.session_state:
            st.session_state.api_status_cache = {
                "last_check": 0,
                "status": None,
                "cache_duration": 60  # 1 minute cache
            }
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"streamlit_{int(time.time())}_{hash(time.time()) % 10000}"
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a message to the chat history.
        
        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional metadata for the message
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": time.strftime("%H:%M:%S"),
            "datetime": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        st.session_state.messages.append(message)
        
        # Limit message history to prevent memory issues
        max_messages = 1000
        if len(st.session_state.messages) > max_messages:
            st.session_state.messages = st.session_state.messages[-max_messages:]
    
    def get_messages(self, role_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get chat messages, optionally filtered by role.
        
        Args:
            role_filter: Optional role to filter by ("user" or "assistant")
        
        Returns:
            List of message dictionaries
        """
        messages = st.session_state.messages
        
        if role_filter:
            messages = [msg for msg in messages if msg["role"] == role_filter]
        
        return messages
    
    def clear_messages(self) -> None:
        """Clear all chat messages."""
        st.session_state.messages = []
        st.session_state.session_start = time.time()
        
        # Reset error tracking
        if "errors" in st.session_state:
            st.session_state.errors = []
    
    def get_session_duration(self) -> str:
        """
        Get formatted session duration.
        
        Returns:
            Formatted duration string
        """
        duration_seconds = time.time() - st.session_state.session_start
        
        if duration_seconds < 60:
            return f"{int(duration_seconds)}s"
        elif duration_seconds < 3600:
            minutes = int(duration_seconds / 60)
            seconds = int(duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(duration_seconds / 3600)
            minutes = int((duration_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive session statistics.
        
        Returns:
            Dict containing session statistics
        """
        messages = st.session_state.messages
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "session_duration": self.get_session_duration(),
            "session_duration_seconds": time.time() - st.session_state.session_start,
            "messages_per_minute": len(messages) / max((time.time() - st.session_state.session_start) / 60, 1),
            "session_start": datetime.fromtimestamp(st.session_state.session_start).isoformat(),
            "current_time": datetime.now().isoformat(),
            "errors_count": len(st.session_state.get("errors", [])),
            "session_id": st.session_state.session_metadata.get("session_id", "unknown")
        }
    
    def export_to_markdown(self) -> str:
        """
        Export chat history to markdown format.
        
        Returns:
            Markdown formatted chat history
        """
        stats = self.get_session_stats()
        
        markdown_content = f"""# BPT Trading Assistant - Chat Export

**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Session Duration:** {stats['session_duration']}  
**Total Messages:** {stats['total_messages']}  
**Session ID:** {stats['session_id']}

---

## 📊 Session Statistics

| Metric | Value |
|--------|-------|
| User Messages | {stats['user_messages']} |
| Assistant Responses | {stats['assistant_messages']} |
| Session Duration | {stats['session_duration']} |
| Messages per Minute | {stats['messages_per_minute']:.1f} |
| Errors | {stats['errors_count']} |

---

## 💬 Chat History

"""
        
        for i, message in enumerate(st.session_state.messages, 1):
            role_emoji = "👤" if message["role"] == "user" else "🤖"
            role_title = message["role"].title()
            timestamp = message.get("timestamp", "")
            datetime_str = message.get("datetime", "")
            
            markdown_content += f"""### {role_emoji} {role_title} Message #{i}

**Time:** {timestamp}  
**DateTime:** {datetime_str}

{message['content']}

---

"""
        
        # Add error log if there are errors
        if st.session_state.get("errors"):
            markdown_content += f"""
## ⚠️ Error Log

"""
            for error in st.session_state.errors:
                markdown_content += f"""**{error.get('timestamp', 'Unknown')}:**  
Question: {error.get('question', 'N/A')}  
Error: {error.get('error', 'Unknown error')}

"""
        
        markdown_content += f"""
---

        *Generated by TubeVibe Trading Assistant - Streamlit Web Interface*  
*Export time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return markdown_content
    
    def export_to_json(self) -> str:
        """
        Export chat history to JSON format.
        
        Returns:
            JSON formatted chat history
        """
        export_data = {
            "export_metadata": {
                "export_time": datetime.now().isoformat(),
                "export_timestamp": time.time(),
                "format_version": "1.0",
                "source": "bpt_streamlit_web"
            },
            "session_info": st.session_state.session_metadata,
            "session_stats": self.get_session_stats(),
            "user_preferences": st.session_state.user_preferences,
            "chat_history": st.session_state.messages,
            "error_log": st.session_state.get("errors", [])
        }
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def import_from_json(self, json_content: str) -> bool:
        """
        Import chat history from JSON format.
        
        Args:
            json_content: JSON string containing chat history
        
        Returns:
            True if import successful, False otherwise
        """
        try:
            data = json.loads(json_content)
            
            # Validate format
            if "chat_history" not in data:
                return False
            
            # Import messages
            imported_messages = data["chat_history"]
            if isinstance(imported_messages, list):
                st.session_state.messages = imported_messages
                
                # Import preferences if available
                if "user_preferences" in data:
                    st.session_state.user_preferences.update(data["user_preferences"])
                
                # Import session info if available
                if "session_info" in data:
                    st.session_state.session_metadata.update(data["session_info"])
                
                return True
        
        except (json.JSONDecodeError, KeyError, TypeError):
            return False
        
        return False
    
    def log_error(self, error: str, question: str = "", context: str = "") -> None:
        """
        Log an error to the session error tracking.
        
        Args:
            error: Error message
            question: Question that caused the error
            context: Additional context
        """
        error_entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "error": error,
            "question": question,
            "context": context
        }
        
        st.session_state.errors.append(error_entry)
        
        # Limit error log size
        max_errors = 50
        if len(st.session_state.errors) > max_errors:
            st.session_state.errors = st.session_state.errors[-max_errors:]
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference value.
        
        Args:
            key: Preference key
            default: Default value if key not found
        
        Returns:
            Preference value or default
        """
        return st.session_state.user_preferences.get(key, default)
    
    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference value.
        
        Args:
            key: Preference key
            value: Preference value
        """
        st.session_state.user_preferences[key] = value
    
    def cache_api_status(self, status: Dict[str, Any]) -> None:
        """
        Cache API status for performance.
        
        Args:
            status: API status dict
        """
        st.session_state.api_status_cache = {
            "last_check": time.time(),
            "status": status,
            "cache_duration": 60
        }
    
    def get_cached_api_status(self) -> Optional[Dict[str, Any]]:
        """
        Get cached API status if still valid.
        
        Returns:
            Cached status dict or None if expired
        """
        cache = st.session_state.api_status_cache
        
        if time.time() - cache["last_check"] < cache["cache_duration"]:
            return cache["status"]
        
        return None
    
    # Transcript Context Management Methods
    
    def set_active_transcript(self, transcript_id: str, name: str, created_at: str = None, 
                            last_modified: str = None, metadata: Dict = None) -> None:
        """
        Set the active transcript context.
        
        Args:
            transcript_id: Unique identifier for the transcript
            name: Display name for the transcript
            created_at: Creation timestamp (ISO format)
            last_modified: Last modification timestamp (ISO format)
            metadata: Additional transcript metadata
        """
        st.session_state.active_transcript = {
            "transcript_id": transcript_id,
            "name": name,
            "created_at": created_at or datetime.now().isoformat(),
            "last_modified": last_modified or datetime.now().isoformat(),
            "metadata": metadata or {},
            "is_active": True,
            "context_updated_at": datetime.now().isoformat()
        }
        
        # Log the context change
        self.log_error(f"Transcript context changed to: {name} (ID: {transcript_id})", 
                      context="transcript_context_change")
    
    def get_active_transcript(self) -> Dict[str, Any]:
        """
        Get the current active transcript context.
        
        Returns:
            Dict containing active transcript information
        """
        return st.session_state.active_transcript.copy()
    
    def clear_transcript_context(self) -> None:
        """Clear the active transcript context."""
        st.session_state.active_transcript = {
            "transcript_id": None,
            "name": None,
            "created_at": None,
            "last_modified": None,
            "metadata": {},
            "is_active": False
        }
        
        # Clear related chat messages when context changes
        self.clear_messages()
    
    def has_active_transcript(self) -> bool:
        """
        Check if there's an active transcript context.
        
        Returns:
            True if there's an active transcript, False otherwise
        """
        return st.session_state.active_transcript.get("is_active", False) and \
               st.session_state.active_transcript.get("transcript_id") is not None
    
    def get_transcript_display_name(self) -> str:
        """
        Get a formatted display name for the active transcript.
        
        Returns:
            Formatted display name or default message
        """
        if not self.has_active_transcript():
            return "No transcript selected"
        
        transcript = st.session_state.active_transcript
        name = transcript.get("name", "Unknown Transcript")
        created_at = transcript.get("created_at")
        
        if created_at:
            try:
                # Parse and format the creation date
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                formatted_date = created_date.strftime("%Y-%m-%d %H:%M")
                return f"{name} ({formatted_date})"
            except:
                return name
        
        return name
    
    def get_transcript_recency_indicator(self) -> str:
        """
        Get a human-readable recency indicator for the active transcript.
        
        Returns:
            Recency indicator string (e.g., "2 hours ago", "Yesterday")
        """
        if not self.has_active_transcript():
            return ""
        
        created_at = st.session_state.active_transcript.get("created_at")
        if not created_at:
            return ""
        
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now()
            
            # Calculate time difference
            diff = now - created_date
            
            if diff.days == 0:
                if diff.seconds < 3600:  # Less than 1 hour
                    minutes = diff.seconds // 60
                    return f"{minutes} minutes ago" if minutes > 1 else "Just now"
                else:  # Less than 24 hours
                    hours = diff.seconds // 3600
                    return f"{hours} hours ago" if hours > 1 else "1 hour ago"
            elif diff.days == 1:
                return "Yesterday"
            elif diff.days < 7:
                return f"{diff.days} days ago"
            else:
                return created_date.strftime("%Y-%m-%d")
        except:
            return ""
    
    def cache_transcripts(self, transcripts: List[Dict]) -> None:
        """
        Cache the list of available transcripts.
        
        Args:
            transcripts: List of transcript dictionaries
        """
        st.session_state.transcripts_cache = {
            "transcripts": transcripts,
            "last_updated": time.time(),
            "cache_duration": 300  # 5 minutes
        }
    
    def get_cached_transcripts(self) -> Optional[List[Dict]]:
        """
        Get cached transcripts if still valid.
        
        Returns:
            List of transcript dicts or None if expired
        """
        cache = st.session_state.transcripts_cache
        
        if time.time() - cache["last_updated"] < cache["cache_duration"]:
            return cache["transcripts"]
        
        return None 