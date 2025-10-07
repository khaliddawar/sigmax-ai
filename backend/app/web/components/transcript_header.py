"""
Transcript Header Component for BPT Trading Assistant

Displays the active transcript context in the Streamlit UI header,
providing visual indicators for the currently selected transcript.
"""

import streamlit as st
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import session_manager
import api_client


def detect_bpt_session_type_and_date(transcript_name: str, created_at: str, transcript_id: str = None) -> Tuple[str, str, str]:
    """
    Detect BPT session type and extract date from transcript name and content.
    
    Args:
        transcript_name: Name of the transcript
        created_at: Creation timestamp
        transcript_id: Transcript ID for content analysis
    
    Returns:
        Tuple of (session_type, session_date, session_icon)
    """
    session_type = "Trading Session"  # Default
    session_icon = "📈"  # Default
    session_date = ""
    
    # Step 1: Try to detect session type from transcript name
    name_lower = transcript_name.lower()
    
    if "macro outlook" in name_lower or "macro" in name_lower:
        session_type = "Macro Outlook"
        session_icon = "🌍"
    elif "where is the trade" in name_lower or "where's the trade" in name_lower:
        session_type = "Where is the Trade"
        session_icon = "🎯"
    elif "trading session" in name_lower or "trade session" in name_lower:
        session_type = "Where is the Trade"
        session_icon = "🎯"
    # Note: Removed the broad "trade" match to avoid false positives
    
    # Step 2: Extract date from transcript name
    # Look for common date patterns in the name
    date_patterns = [
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # MM/DD/YYYY or MM-DD-YYYY
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',    # YYYY/MM/DD or YYYY-MM-DD
        r'(\d{1,2}\s+\w+\s+\d{4})',         # DD Month YYYY
        r'(\w+\s+\d{1,2},?\s+\d{4})',       # Month DD, YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, transcript_name)
        if match:
            session_date = match.group(1)
            break
    
    # Step 3: If no date found in name, use created_at date
    if not session_date and created_at:
        try:
            # Parse ISO timestamp and format nicely
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            session_date = dt.strftime("%B %d, %Y")
        except:
            session_date = "Recent"
    
    # Step 4: Try to get more specific info from transcript content (optional, cached)
    if transcript_id and session_type == "Trading Session":  # Only if we couldn't detect from name
        try:
            # This would be cached and only run once per transcript
            api_client_instance = api_client.get_api_client()
            content_response = api_client_instance.get_transcript_content(transcript_id, include_chunks=True)
            
            if content_response.get("success") and content_response.get("data"):
                data = content_response["data"]
                
                # Look in first few chunks for session type mentions
                chunks = data.get("chunks", [])
                if chunks:
                    # Combine first 2-3 chunks to look for session type
                    first_content = " ".join([chunk.get("text", "") for chunk in chunks[:3]])
                    content_lower = first_content.lower()
                    
                    if "macro outlook" in content_lower:
                        session_type = "Macro Outlook"
                        session_icon = "🌍"
                    elif "where is the trade" in content_lower or "where's the trade" in content_lower:
                        session_type = "Where is the Trade"
                        session_icon = "🎯"
        except:
            # If content analysis fails, stick with name-based detection
            pass
    
    return session_type, session_date, session_icon


@st.cache_data(ttl=60, show_spinner=False)  # Reduced cache time and hide spinner
def get_cached_session_info(transcript_id: str, transcript_name: str, created_at: str) -> Tuple[str, str, str]:
    """Cached wrapper for session type detection."""
    result = detect_bpt_session_type_and_date(transcript_name, created_at, transcript_id)
    # Debug: Add to help troubleshoot
    print(f"DEBUG: Session detection for '{transcript_name}' -> {result}")
    return result


def clear_session_cache():
    """Clear the session detection cache."""
    get_cached_session_info.clear()


def render_transcript_header(session_mgr) -> None:
    """
    Render the transcript context header.
    
    Args:
        session_mgr: SessionManager instance for accessing transcript context
    """
    
    # Check if there's an active transcript
    if session_mgr.has_active_transcript():
        transcript = session_mgr.get_active_transcript()
        display_name = session_mgr.get_transcript_display_name()
        recency = session_mgr.get_transcript_recency_indicator()
        
        # Get BPT-specific session information
        transcript_id = transcript.get("transcript_id", "")
        transcript_name = transcript.get("name", display_name)
        created_at = transcript.get("created_at", "")
        
        session_type, session_date, session_icon = get_cached_session_info(
            transcript_id, transcript_name, created_at
        )
        
        # Create a styled header container with session information
        st.markdown(f"""
        <div style="
            background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%);
            border: 1px solid #cbd5e1;
            border-radius: 0.75rem;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: all 0.2s ease;
        " onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)'; this.style.transform='translateY(-1px)';" 
           onmouseout="this.style.boxShadow='0 1px 3px rgba(0,0,0,0.1)'; this.style.transform='translateY(0)';">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="
                        background: #10b981;
                        color: white;
                        border-radius: 50%;
                        width: 12px;
                        height: 12px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 8px;
                        animation: pulse 2s infinite;
                    ">●</div>
                    <div>
                        <div style="
                            font-weight: 600;
                            color: #1f2937;
                            font-size: 1.1rem;
                            margin-bottom: 0.5rem;
                        ">{session_icon} {session_type}</div>
                        <div style="
                            display: flex;
                            align-items: center;
                            gap: 1rem;
                            font-size: 0.85rem;
                        ">
                            {'<div style="color: #6b7280;">📅 ' + session_date + '</div>' if session_date else ''}
                        </div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="
                        color: #6b7280;
                        font-size: 0.85rem;
                        font-style: italic;
                    ">{recency}</div>
                    <div style="
                        color: #9ca3af;
                        font-size: 0.75rem;
                        margin-top: 0.25rem;
                    ">📋 Click to change session</div>
                </div>
            </div>
        </div>
        
        <style>
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        </style>
        """, unsafe_allow_html=True)
        
    else:
        # Show a prompt to select a transcript
        st.markdown("""
        <div style="
            background: linear-gradient(90deg, #fef3c7 0%, #fde68a 100%);
            border: 1px solid #f59e0b;
            border-radius: 0.75rem;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="
                    color: #f59e0b;
                    font-size: 1.5rem;
                ">⚠️</div>
                <div>
                    <div style="
                        font-weight: 600;
                        color: #92400e;
                        font-size: 1.1rem;
                        margin-bottom: 0.25rem;
                    ">No Transcript Selected</div>
                    <div style="
                        color: #a16207;
                        font-size: 0.95rem;
                    ">Please select a transcript from the sidebar to start asking questions.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_compact_transcript_indicator(session_mgr) -> None:
    """
    Render a compact transcript indicator for use in smaller spaces.
    
    Args:
        session_mgr: SessionManager instance for accessing transcript context
    """
    
    if session_mgr.has_active_transcript():
        transcript = session_mgr.get_active_transcript()
        display_name = session_mgr.get_transcript_display_name()
        
        # Get BPT-specific session information
        transcript_id = transcript.get("transcript_id", "")
        transcript_name = transcript.get("name", display_name)
        created_at = transcript.get("created_at", "")
        
        session_type, session_date, session_icon = get_cached_session_info(
            transcript_id, transcript_name, created_at
        )
        
        # Truncate long names
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        
        st.markdown(f"""
        <div style="
            background: #ecfdf5;
            border: 1px solid #10b981;
            border-radius: 0.5rem;
            padding: 0.5rem 0.75rem;
            margin-bottom: 0.75rem;
            font-size: 0.9rem;
        ">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                <span style="color: #10b981;">●</span>
                <span style="color: #065f46; font-weight: 500;">{display_name}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem; font-size: 0.8rem;">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 0.25rem;
                    color: #059669;
                    font-weight: 500;
                ">
                    <span>{session_icon}</span>
                    <span>{session_type}</span>
                </div>
                {f'<div style="color: #6b7280;">📅 {session_date}</div>' if session_date else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            background: #fef2f2;
            border: 1px solid #ef4444;
            border-radius: 0.5rem;
            padding: 0.5rem 0.75rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
        ">
            <span style="color: #ef4444;">○</span>
            <span style="color: #991b1b; font-weight: 500;">No transcript selected</span>
        </div>
        """, unsafe_allow_html=True)


def render_transcript_context_actions(session_mgr) -> None:
    """
    Render action buttons for transcript context management.
    
    Args:
        session_mgr: SessionManager instance for managing transcript context
    """
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔄 Refresh", help="Refresh transcript list", use_container_width=True):
            # Clear the transcripts cache to force refresh
            if "transcripts_cache" in st.session_state:
                st.session_state.transcripts_cache["last_updated"] = 0
            st.rerun()
    
    with col2:
        if session_mgr.has_active_transcript():
            if st.button("❌ Clear", help="Clear active transcript", use_container_width=True):
                session_mgr.clear_transcript_context()
                st.rerun()
        else:
            st.button("❌ Clear", disabled=True, help="No transcript to clear", use_container_width=True)
    
    with col3:
        # Show transcript ID for debugging (if active)
        if session_mgr.has_active_transcript():
            transcript_id = session_mgr.get_active_transcript().get("transcript_id", "")
            st.caption(f"ID: {transcript_id}") 