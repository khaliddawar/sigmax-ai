"""
Sidebar Component for BPT Trading Assistant

Provides minimal sidebar functionality with essential tools only.
"""

import streamlit as st
import time
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

def render_sidebar(api_client, session_manager=None):
    """
    Render a minimalist sidebar with essential tools only.
    
    Args:
        api_client: BPTAPIClient instance for API communication
        session_manager: SessionManager instance for transcript context
    """
    
    # Add enhanced CSS styling for the sidebar to match main interface
    st.markdown("""
    <style>
    /* Sidebar specific enhancements */
    .css-1d391kg {
        background: linear-gradient(135deg, rgba(248, 250, 252, 0.95) 0%, rgba(241, 245, 249, 0.95) 100%);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(226, 232, 240, 0.6);
    }
    
    /* Sidebar headers */
    .css-1d391kg h4 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.1rem;
        color: #374151;
        margin-bottom: 1rem;
        padding: 0.5rem 0;
        border-bottom: 2px solid rgba(59, 130, 246, 0.2);
    }
    
    .css-1d391kg h5 {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.95rem;
        color: #4b5563;
        margin-bottom: 0.75rem;
        margin-top: 1rem;
    }
    
    /* Sidebar buttons */
    .css-1d391kg .stButton > button {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 13px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
        color: #374151;
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(5px);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        width: 100%;
        margin-bottom: 0.5rem;
    }
    
    .css-1d391kg .stButton > button:hover {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-color: #3b82f6;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
    }
    
    /* Sidebar selectboxes */
    .css-1d391kg .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
        backdrop-filter: blur(5px);
    }
    
    /* Sidebar text inputs */
    .css-1d391kg .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        backdrop-filter: blur(5px);
    }
    
    .css-1d391kg .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }
    
    /* File uploader */
    .css-1d391kg .stFileUploader > div {
        background: rgba(255, 255, 255, 0.9);
        border: 2px dashed rgba(156, 163, 175, 0.6);
        border-radius: 8px;
        backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    
    .css-1d391kg .stFileUploader > div:hover {
        border-color: #3b82f6;
        background: rgba(255, 255, 255, 0.95);
    }
    
    /* Status indicators */
    .css-1d391kg .stSuccess {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(22, 163, 74, 0.1) 100%);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 8px;
        backdrop-filter: blur(5px);
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }
    
    .css-1d391kg .stError {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 8px;
        backdrop-filter: blur(5px);
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }
    
    .css-1d391kg .stWarning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 8px;
        backdrop-filter: blur(5px);
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }
    
    .css-1d391kg .stInfo {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 8px;
        backdrop-filter: blur(5px);
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }
    
    /* Captions */
    .css-1d391kg .stCaption {
        font-family: 'Inter', sans-serif;
        color: #6b7280;
        font-size: 12px;
        font-weight: 400;
    }
    
    /* Checkboxes */
    .css-1d391kg .stCheckbox {
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        color: #374151;
    }
    
    /* Download button */
    .css-1d391kg .stDownloadButton > button {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
    }
    
    .css-1d391kg .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
    }
    
    /* Columns in sidebar */
    .css-1d391kg .stColumns {
        gap: 0.5rem;
    }
    
    /* Separators */
    .css-1d391kg hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(226, 232, 240, 0.8) 50%, transparent 100%);
        margin: 1.5rem 0;
    }
    
    /* Expanders in sidebar */
    .css-1d391kg .streamlit-expanderHeader {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 14px;
        background: rgba(255, 255, 255, 0.8);
        border-radius: 8px;
        border: 1px solid rgba(226, 232, 240, 0.6);
        backdrop-filter: blur(5px);
    }
    
    .css-1d391kg .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 0 0 8px 8px;
        backdrop-filter: blur(10px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Transcript context management (if session_manager provided)
    if session_manager:
        render_transcript_management(api_client, session_manager)
    
    # Vector Database Status
    render_vector_db_status(api_client)
    
    # Testing tools (only show when explicitly opened)
    if st.session_state.get('show_testing_tools', False):
        render_testing_tools(api_client)
    
    # Session management
    render_session_tools()

def render_vector_db_status(api_client):
    """Show vector database and API status."""
    
    st.markdown("#### 🔧 System Status")
    
    # Check API health
    try:
        health = api_client.health_check()
        if health.get("success"):
            st.success("✅ API Connected")
            
            # Show service status details
            health_data = health.get("health", {})
            if health_data.get("supabase"):
                st.success("✅ Vector Database")
            else:
                st.warning("⚠️ Vector Database Issue")
                
            if health_data.get("embedding"):
                st.success("✅ AI Embeddings")
            else:
                st.warning("⚠️ Embeddings Issue")
        else:
            st.error("❌ API Disconnected")
            st.caption("Vector search unavailable")
    except:
        st.error("❌ API Disconnected")
        st.caption("Check if backend is running")
    
    st.markdown("---")

def render_testing_tools(api_client):
    """Render testing tools section (simplified)."""
    
    st.markdown("#### 🧪 Testing Tools")
    
    # Show recent sessions
    if st.button("📋 Show Recent Sessions"):
        try:
            sessions = api_client.get_recent_sessions(limit=5)
            if sessions.get("success") and sessions.get("sessions"):
                st.write("**Recent Sessions:**")
                for session in sessions["sessions"]:
                    st.write(f"• `{session.get('id', 'unknown')}`")
            else:
                st.info("No recent sessions found")
        except:
            st.warning("Could not fetch sessions")
    
    # API testing
    if st.button("🔍 Test API Connection"):
        try:
            health = api_client.health_check()
            if health.get("success"):
                st.success("✅ API is working correctly")
                st.json(health.get("health", {}))
            else:
                st.error(f"❌ API issue: {health.get('error')}")
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")

def render_session_tools():
    """Render session management tools."""
    
    st.markdown("#### ⚙️ Settings")
    
    # Toggle testing tools
    current_testing = st.session_state.get('show_testing_tools', False)
    if st.button("🧪 Toggle Testing Tools"):
        st.session_state.show_testing_tools = not current_testing
        st.rerun()
    
    # Show current session info
    if "session_id" in st.session_state:
        st.caption(f"Session: {st.session_state.session_id}")
    
    # Export chat option
    if st.session_state.get("messages"):
        st.markdown("#### 📤 Export")
        
        if st.button("💾 Download Chat"):
            chat_content = ""
            for msg in st.session_state.messages:
                role = msg["role"].title()
                content = msg["content"]
                chat_content += f"**{role}:** {content}\n\n"
            
            st.download_button(
                label="📄 Download as Markdown",
                data=chat_content,
                file_name=f"bpt_chat_{time.strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
    
    # Clear chat option
    if st.session_state.get("messages"):
        st.markdown("#### 🗑️ Cleanup")
        if st.button("🔄 Clear Chat", help="Start a new conversation"):
            st.session_state.messages = []
            st.rerun()

def _detect_transcript_type(transcript_name: str) -> str:
    """
    Detect transcript type from the name by looking for keywords.
    
    Args:
        transcript_name: Name/title of the transcript
        
    Returns:
        Transcript type: 'trade', 'macro', or 'general'
    """
    name_lower = transcript_name.lower()
    
    # Trade-related keywords
    trade_keywords = ['trade', 'trading', 'position', 'entry', 'exit', 'where is the trade', 'setup', 'levels']
    
    # Macro-related keywords  
    macro_keywords = ['macro', 'outlook', 'economic', 'market outlook', 'forecast', 'analysis', 'global', 'economy']
    
    # Check for trade keywords first
    for keyword in trade_keywords:
        if keyword in name_lower:
            return 'trade'
    
    # Then check for macro keywords
    for keyword in macro_keywords:
        if keyword in name_lower:
            return 'macro'
    
    # Default to general if no specific type detected
    return 'general'

def _get_transcript_recency_category(created_at: str) -> str:
    """
    Categorize transcript by recency for visual indicators.
    
    Args:
        created_at: ISO timestamp string
        
    Returns:
        Category string: 'new', 'recent', 'old'
    """
    try:
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        now = datetime.now(created_date.tzinfo)
        age = now - created_date
        
        if age < timedelta(hours=1):
            return 'new'
        elif age < timedelta(days=7):
            return 'recent'
        else:
            return 'old'
    except:
        return 'old'

def _format_transcript_display_name(transcript: Dict[str, Any], show_metadata: bool = True) -> str:
    """
    Format transcript display name with optional metadata.
    
    Args:
        transcript: Transcript data dictionary
        show_metadata: Whether to include metadata in display name
        
    Returns:
        Formatted display name string
    """
    name = transcript.get("name", f"Transcript {transcript.get('id', 'unknown')}")
    
    if not show_metadata:
        return name
    
    created_at = transcript.get("created_at", "")
    if created_at:
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_date = created_date.strftime("%m/%d %H:%M")
            
            # Add recency indicator
            recency = _get_transcript_recency_category(created_at)
            if recency == 'new':
                indicator = "🆕"
            elif recency == 'recent':
                indicator = "📅"
            else:
                indicator = "📄"
            
            return f"{indicator} {name} ({formatted_date})"
        except:
            return f"📄 {name}"
    else:
        return f"📄 {name}"

def _sort_transcripts(transcripts: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
    """
    Sort transcripts by specified criteria.
    
    Args:
        transcripts: List of transcript dictionaries
        sort_by: Sort criteria ('date_desc', 'date_asc', 'name_asc', 'name_desc')
        
    Returns:
        Sorted list of transcripts
    """
    if sort_by == 'date_desc':
        return sorted(transcripts, key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort_by == 'date_asc':
        return sorted(transcripts, key=lambda x: x.get('created_at', ''))
    elif sort_by == 'name_asc':
        return sorted(transcripts, key=lambda x: x.get('name', '').lower())
    elif sort_by == 'name_desc':
        return sorted(transcripts, key=lambda x: x.get('name', '').lower(), reverse=True)
    else:
        return transcripts

def _filter_transcripts(transcripts: List[Dict[str, Any]], search_term: str) -> List[Dict[str, Any]]:
    """
    Filter transcripts by search term.
    
    Args:
        transcripts: List of transcript dictionaries
        search_term: Search term to filter by
        
    Returns:
        Filtered list of transcripts
    """
    if not search_term:
        return transcripts
    
    search_lower = search_term.lower()
    filtered = []
    
    for transcript in transcripts:
        name = transcript.get('name', '').lower()
        transcript_id = str(transcript.get('id', '')).lower()
        
        if search_lower in name or search_lower in transcript_id:
            filtered.append(transcript)
    
    return filtered

def _auto_select_latest_transcript(session_manager, sorted_transcripts: List[Dict[str, Any]]):
    """
    Auto-select the latest transcript if no transcript is currently active.
    
    Args:
        session_manager: SessionManager instance
        sorted_transcripts: List of transcripts sorted by date (newest first)
    """
    # Only auto-select if no transcript is currently active
    current_transcript = session_manager.get_active_transcript()
    
    if not current_transcript.get("is_active") and sorted_transcripts:
        # Auto-select the latest (first) transcript
        latest_transcript = sorted_transcripts[0]
        
        # Add transcript type detection to metadata
        transcript_type = _detect_transcript_type(latest_transcript.get("name", ""))
        latest_transcript["transcript_type"] = transcript_type
        
        session_manager.set_active_transcript(
            transcript_id=latest_transcript.get("id"),
            name=latest_transcript.get("name", "Unknown"),
            created_at=latest_transcript.get("created_at"),
            last_modified=latest_transcript.get("last_modified"),
            metadata=latest_transcript
        )
        _update_recent_selections(latest_transcript.get("id"))
        
        # Show success message
        st.success(f"✅ Auto-selected latest transcript: {latest_transcript.get('name', 'Unknown')}")
        return True
    
    return False

def render_transcript_management(api_client, session_manager):
    """
    Render enhanced transcript management section in sidebar.
    
    Args:
        api_client: BPTAPIClient instance for API communication
        session_manager: SessionManager instance for transcript context
    """
    
    st.markdown("#### 📄 Transcript Management")
    
    # Upload section - always visible
    st.markdown("##### 📤 Upload New Transcript")
    
    uploaded_file = st.file_uploader(
        "Upload Transcript File",
        type=['txt', 'md'],
        help="Upload a transcript file to add to your collection",
        key="transcript_uploader"
    )
    
    if uploaded_file is not None:
        # Read the file content
        content = str(uploaded_file.read(), "utf-8")
        
        # Show file info
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"**File:** {uploaded_file.name}")
        with col2:
            st.caption(f"**Size:** {len(content)} chars")
        
        # Process button
        if st.button("🔄 Process & Add Transcript", help="Process this transcript for vector search", key="process_transcript_btn"):
            with st.spinner("Processing transcript..."):
                try:
                    result = api_client.process_transcript(content, uploaded_file.name)
                    if result.get("success"):
                        st.success("✅ Transcript processed successfully!")
                        st.write(f"Session ID: `{result.get('session_id')}`")
                        # Clear transcript cache to show new transcript
                        if "transcripts_cache" in st.session_state:
                            st.session_state.transcripts_cache["last_updated"] = 0
                        # Auto-refresh the page to show new transcript
                        st.rerun()
                    else:
                        st.error(f"❌ Processing failed: {result.get('error')}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    st.markdown("---")
    
    # Show compact transcript indicator
    import transcript_header
    transcript_header.render_compact_transcript_indicator(session_manager)
    
    # Transcript Selection Section
    st.markdown("##### 📋 Select Transcript")
    
    # Get available transcripts (with caching)
    transcripts = session_manager.get_cached_transcripts()
    
    if transcripts is None:
        # Fetch transcripts from API
        try:
            with st.spinner("Loading transcripts..."):
                response = api_client.get_recent_sessions(limit=100)  # Increased limit
                if response.get("success") and response.get("sessions"):
                    # Map API response format to expected format
                    raw_transcripts = response["sessions"]
                    transcripts = []
                    for transcript in raw_transcripts:
                        # Detect transcript type
                        transcript_type = _detect_transcript_type(transcript.get("title", ""))
                        
                        # Map session_id to id for consistency
                        mapped_transcript = {
                            "id": transcript.get("session_id"),  # Map session_id to id
                            "name": transcript.get("title", f"Transcript {transcript.get('session_id', 'unknown')}"),
                            "created_at": transcript.get("created_at"),
                            "last_modified": transcript.get("created_at"),  # Use created_at as fallback
                            "chunk_count": transcript.get("chunk_count"),
                            "preview": transcript.get("preview"),
                            "processed": transcript.get("processed", True),
                            "transcript_type": transcript_type,  # Add detected type
                            # Keep original data for reference
                            "session_id": transcript.get("session_id"),
                            "title": transcript.get("title")
                        }
                        transcripts.append(mapped_transcript)
                    
                    session_manager.cache_transcripts(transcripts)
                    
                    # Auto-select the latest transcript if none is currently selected
                    if not session_manager.has_active_transcript() and transcripts:
                        # Sort transcripts by created_at to get the latest one
                        latest_transcript = max(transcripts, key=lambda x: x.get('created_at', ''))
                        session_manager.set_active_transcript(
                            transcript_id=latest_transcript.get("id"),
                            name=latest_transcript.get("name", "Unknown"),
                            created_at=latest_transcript.get("created_at"),
                            last_modified=latest_transcript.get("last_modified"),
                            metadata=latest_transcript
                        )
                        # Add to recent selections
                        _update_recent_selections(latest_transcript.get("id"))
                        # Trigger UI refresh to show the selected transcript
                        st.rerun()
                else:
                    transcripts = []
        except Exception as e:
            st.error(f"Failed to load transcripts: {str(e)}")
            transcripts = []
    
    # Show the dropdown section
    st.markdown("##### 📋 Transcript Selector")
    
    if transcripts:
        # Sort transcripts by date (newest first) for auto-selection
        sorted_transcripts = _sort_transcripts(transcripts, 'date_desc')
        
        # Auto-select latest transcript if none is active
        auto_selected = _auto_select_latest_transcript(session_manager, sorted_transcripts)
        
        # Enhanced transcript selector with search and sort
        st.markdown("##### 🔍 Search & Sort")
        
        # Search functionality
        search_term = st.text_input(
            "Search transcripts:",
            placeholder="Type to search by name or ID...",
            help="Search transcripts by name or ID",
            key="transcript_search"
        )
        
        # Sort options
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox(
                "Sort by:",
                options=[
                    ("date_desc", "📅 Newest First"),
                    ("date_asc", "📅 Oldest First"),
                    ("name_asc", "🔤 Name A-Z"),
                    ("name_desc", "🔤 Name Z-A")
                ],
                format_func=lambda x: x[1],
                index=0,
                key="transcript_sort"
            )[0]
        
        with col2:
            show_metadata = st.checkbox(
                "Show details",
                value=True,
                help="Show dates and indicators",
                key="show_transcript_metadata"
            )
        
        # Filter and sort transcripts
        filtered_transcripts = _filter_transcripts(transcripts, search_term)
        sorted_transcripts = _sort_transcripts(filtered_transcripts, sort_by)
        
        # Show results count
        if search_term:
            st.caption(f"Found {len(filtered_transcripts)} of {len(transcripts)} transcripts")
        
        if sorted_transcripts:
            # Recent selections (last 3 used transcripts)
            recent_selections = st.session_state.get('recent_transcript_selections', [])
            if recent_selections:
                st.markdown("##### ⭐ Recent Selections")
                recent_transcripts = []
                for recent_id in recent_selections[:3]:  # Show last 3
                    for transcript in sorted_transcripts:
                        if transcript.get('id') == recent_id:
                            recent_transcripts.append(transcript)
                            break
                
                if recent_transcripts:
                    recent_options = [""] + [
                        _format_transcript_display_name(t, show_metadata) 
                        for t in recent_transcripts
                    ]
                    recent_map = {
                        _format_transcript_display_name(t, show_metadata): t 
                        for t in recent_transcripts
                    }
                    
                    selected_recent = st.selectbox(
                        "Quick select:",
                        options=recent_options,
                        index=0,
                        help="Select from recently used transcripts",
                        key="recent_transcript_selector"
                    )
                    
                    if selected_recent:
                        transcript = recent_map[selected_recent]
                        # Add transcript type to metadata
                        transcript["transcript_type"] = _detect_transcript_type(transcript.get("name", ""))
                        
                        session_manager.set_active_transcript(
                            transcript_id=transcript.get("id"),
                            name=transcript.get("name", "Unknown"),
                            created_at=transcript.get("created_at"),
                            last_modified=transcript.get("last_modified"),
                            metadata=transcript
                        )
                        _update_recent_selections(transcript.get("id"))
                        st.success(f"✅ Selected: {transcript.get('name', 'Unknown')}")
                        st.rerun()
            
            # Main transcript selector
            st.markdown("##### 📋 All Transcripts")
            
            # Create transcript options for selectbox
            transcript_options = ["Select a transcript..."]
            transcript_map = {}
            
            for transcript in sorted_transcripts:
                display_name = _format_transcript_display_name(transcript, show_metadata)
                transcript_options.append(display_name)
                transcript_map[display_name] = transcript
            
            # Get current selection
            current_transcript = session_manager.get_active_transcript()
            current_selection = "Select a transcript..."
            
            if current_transcript.get("is_active"):
                # Try to find current transcript in the list
                current_id = current_transcript.get("transcript_id")
                for transcript in sorted_transcripts:
                    if transcript.get("id") == current_id:
                        current_display = _format_transcript_display_name(transcript, show_metadata)
                        if current_display in transcript_options:
                            current_selection = current_display
                        break
            
            # Transcript selector dropdown
            selected_transcript_name = st.selectbox(
                "Choose transcript:",
                options=transcript_options,
                index=transcript_options.index(current_selection) if current_selection in transcript_options else 0,
                help="Select a transcript to analyze and ask questions about",
                key="main_transcript_selector"
            )
            
            # Handle transcript selection
            if selected_transcript_name != "Select a transcript..." and selected_transcript_name != current_selection:
                selected_transcript = transcript_map.get(selected_transcript_name)
                if selected_transcript:
                    # Add transcript type to metadata
                    selected_transcript["transcript_type"] = _detect_transcript_type(selected_transcript.get("name", ""))
                    
                    # Set the active transcript
                    session_manager.set_active_transcript(
                        transcript_id=selected_transcript.get("id"),
                        name=selected_transcript.get("name", "Unknown"),
                        created_at=selected_transcript.get("created_at"),
                        last_modified=selected_transcript.get("last_modified"),
                        metadata=selected_transcript
                    )
                    _update_recent_selections(selected_transcript.get("id"))
                    st.success(f"✅ Selected: {selected_transcript.get('name', 'Unknown')}")
                    st.rerun()
            
            # Show transcript preview if one is selected
            if current_transcript.get("is_active"):
                # Debug indicator to show transcript status
                st.info(f"📍 **Active Transcript:** {current_transcript.get('name', 'Unknown')} (ID: `{current_transcript.get('transcript_id', 'None')}`)")
                
                with st.expander("📖 Transcript Preview", expanded=False):
                    transcript_id = current_transcript.get("transcript_id")
                    name = current_transcript.get("name", "Unknown")
                    created_at = current_transcript.get("created_at", "")
                    metadata = current_transcript.get("metadata", {})
                    transcript_type = metadata.get("transcript_type", "general")
                    
                    st.write(f"**Name:** {name}")
                    st.write(f"**Type:** {transcript_type.title()}")
                    st.write(f"**ID:** `{transcript_id}`")
                    if created_at:
                        try:
                            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            formatted_date = created_date.strftime("%Y-%m-%d %H:%M:%S")
                            st.write(f"**Created:** {formatted_date}")
                        except:
                            st.write(f"**Created:** {created_at}")
                    
                    # Show metadata directly (no nested expander)
                    if metadata and len(metadata) > 1:  # More than just transcript_type
                        st.markdown("**Additional Metadata:**")
                        for key, value in metadata.items():
                            if key != "transcript_type":
                                st.write(f"• **{key.title()}:** {value}")
            
            else:
                # Show message when no transcript is selected
                st.info("👆 **Select a transcript above** to access transcript management actions like deletion and analysis.")
        
        else:
            if search_term:
                st.info(f"No transcripts found matching '{search_term}'")
            else:
                st.info("No transcripts available")
    
    else:
        st.info("No transcripts available. Upload a transcript to get started.")
    
    # Transcript Management Actions - Separate top-level section
    current_transcript = session_manager.get_active_transcript()
    if current_transcript.get("is_active"):
        st.markdown("---")
        st.markdown("#### 🛠️ Transcript Actions")
        
        transcript_id = current_transcript.get("transcript_id")
        name = current_transcript.get("name", "Unknown")
        
        st.write("**Manage this transcript:**")
        
        # Debug info to help troubleshoot
        if st.checkbox("Show debug info", value=False, key="debug_transcript_actions"):
            st.json({
                "transcript_id": current_transcript.get("transcript_id"),
                "is_active": current_transcript.get("is_active"),
                "name": current_transcript.get("name"),
                "has_transcript_id": bool(current_transcript.get("transcript_id"))
            })
        
        # Delete transcript section with safety controls
        st.markdown("##### 🗑️ Delete Transcript")
        st.warning("⚠️ **This action cannot be undone!** Deleting will remove:")
        st.markdown("""
        - The transcript record
        - All transcript chunks (text segments)
        - All semantic chunks (embeddings/analysis)
        - Any associated analysis data
        """)
        
        # Triple confirmation system for safety
        col1, col2 = st.columns(2)
        
        with col1:
            confirm_delete = st.checkbox(
                f"I want to delete '{name}'",
                key=f"confirm_delete_{transcript_id}",
                help="Check this box to proceed with deletion"
            )
        
        with col2:
            if confirm_delete:
                double_confirm = st.checkbox(
                    "I understand this is permanent",
                    key=f"double_confirm_{transcript_id}",
                    help="Final confirmation that you understand the action"
                )
            else:
                double_confirm = False
        
        # Final delete button with ultimate safety check
        if confirm_delete and double_confirm:
            st.markdown("---")
            st.error("**Final Step:** Type the transcript name to confirm deletion")
            
            confirmation_text = st.text_input(
                f"Type '{name}' to confirm:",
                key=f"final_confirm_{transcript_id}",
                help="This ensures you're deleting the correct transcript"
            )
            
            if confirmation_text == name:
                col_delete, col_cancel = st.columns(2)
                
                with col_delete:
                    if st.button(
                        "🗑️ DELETE TRANSCRIPT",
                        type="primary",
                        key=f"final_delete_{transcript_id}",
                        help="Permanently delete this transcript and all related data"
                    ):
                        # Execute the deletion
                        with st.spinner("Deleting transcript and all related data..."):
                            try:
                                result = api_client.delete_transcript(transcript_id)
                                
                                if result.get("success"):
                                    # Clear the active transcript from session
                                    session_manager.clear_transcript_context()
                                    
                                    # Clear transcript cache to force refresh
                                    if "transcripts_cache" in st.session_state:
                                        st.session_state.transcripts_cache["last_updated"] = 0
                                    
                                    st.success("✅ Transcript deleted successfully!")
                                    st.balloons()
                                    
                                    # Give user a moment to see success message
                                    time.sleep(1)
                                    st.rerun()
                                    
                                else:
                                    error_msg = result.get("error", "Unknown error occurred")
                                    st.error(f"❌ Deletion failed: {error_msg}")
                                    session_manager.log_error(
                                        f"Transcript deletion failed: {error_msg}",
                                        context="transcript_deletion"
                                    )
                                    
                            except Exception as e:
                                st.error(f"❌ Deletion failed: {str(e)}")
                                session_manager.log_error(
                                    f"Transcript deletion exception: {str(e)}",
                                    context="transcript_deletion_exception"
                                )
                
                with col_cancel:
                    if st.button(
                        "Cancel",
                        key=f"cancel_delete_{transcript_id}",
                        help="Cancel the deletion process"
                    ):
                        st.info("Deletion cancelled.")
                        st.rerun()
            elif confirmation_text:
                st.error(f"Text doesn't match. Please type exactly: '{name}'")
        
        # Additional transcript actions can be added here
        st.markdown("---")
        st.markdown("##### 📊 Other Actions")
        st.info("Future transcript management features will appear here.")
    
    st.markdown("---")

def _update_recent_selections(transcript_id: str):
    """
    Update the recent transcript selections list.
    
    Args:
        transcript_id: ID of the selected transcript
    """
    if "recent_transcript_selections" not in st.session_state:
        st.session_state.recent_transcript_selections = []
    
    recent = st.session_state.recent_transcript_selections
    
    # Remove if already in list
    if transcript_id in recent:
        recent.remove(transcript_id)
    
    # Add to front
    recent.insert(0, transcript_id)
    
    # Keep only last 5
    st.session_state.recent_transcript_selections = recent[:5] 