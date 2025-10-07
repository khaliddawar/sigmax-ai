"""
Chat Interface Component for BPT Trading Assistant

Provides a minimalist ChatGPT-style conversation interface with suggested questions below the chat.
"""

import streamlit as st
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

def render_chat_interface(api_client, session_manager):
    """
    Render the minimalist chat interface with suggested questions below.
    
    Args:
        api_client: BPTAPIClient instance for API communication
        session_manager: SessionManager instance for session state management
    """
    
    # Add comprehensive CSS styling for modern UI with BPT brand colors
    st.markdown("""
    <style>
    /* Import Inter font and set global styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap');
    
    /* BPT Brand Colors */
    :root {
        --bpt-primary: #003366;
        --bpt-secondary: #00C2FF;
        --bpt-success: #10b981;
        --bpt-warning: #f59e0b;
        --bpt-error: #ef4444;
        --bpt-neutral-50: #f8fafc;
        --bpt-neutral-100: #f1f5f9;
        --bpt-neutral-200: #e2e8f0;
        --bpt-neutral-300: #cbd5e1;
        --bpt-neutral-400: #94a3b8;
        --bpt-neutral-500: #64748b;
        --bpt-neutral-600: #475569;
        --bpt-neutral-700: #334155;
        --bpt-neutral-800: #1e293b;
        --bpt-neutral-900: #0f172a;
    }
    
    /* Global font override */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
        background: linear-gradient(135deg, var(--bpt-neutral-50) 0%, var(--bpt-neutral-100) 50%, var(--bpt-neutral-200) 100%);
        background-attachment: fixed;
    }
    
    /* Main container enhancements */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 85rem;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        margin: 2rem auto;
        border: 1px solid rgba(255, 255, 255, 0.3);
        width: 95%;
    }
    
    /* Header styling */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: var(--bpt-neutral-800);
        letter-spacing: -0.025em;
    }
    
    /* Chat message containers */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid var(--bpt-neutral-200);
        border-radius: 16px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        backdrop-filter: blur(5px);
        font-family: 'Inter', sans-serif;
        line-height: 1.6;
        font-size: 1.1rem;
        max-width: 90%;
        width: fit-content;
    }
    
    /* User messages (right side) */
    .stChatMessage[data-testid="user-message"] {
        background: linear-gradient(135deg, var(--bpt-primary) 0%, var(--bpt-secondary) 100%);
        color: white;
        margin-left: auto;
        margin-right: 0;
        border: none;
    }
    
    /* Assistant messages (left side) */
    .stChatMessage[data-testid="assistant-message"] {
        background: rgba(255, 255, 255, 0.95);
        color: var(--bpt-neutral-700);
        margin-left: 0;
        margin-right: auto;
        border: 1px solid var(--bpt-neutral-200);
    }
    
    /* Chat input styling */
    .stChatInput > div > div > div {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid var(--bpt-neutral-300);
        border-radius: 24px;
        font-family: 'Inter', sans-serif;
        padding: 1rem 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        backdrop-filter: blur(10px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stChatInput > div > div > div:focus-within {
        border-color: var(--bpt-secondary);
        box-shadow: 0 0 0 3px rgba(0, 194, 255, 0.1), 0 4px 20px rgba(0, 0, 0, 0.12);
        transform: translateY(-1px);
    }
    
    .stChatInput input {
        font-family: 'Inter', sans-serif;
        font-size: 16px;
        color: var(--bpt-neutral-700);
        font-weight: 400;
    }
    
    .stChatInput input::placeholder {
        color: var(--bpt-neutral-400);
        font-weight: 400;
    }
    
    /* Hide unwanted input instruction elements and slider icons */
    [data-testid="InputInstructions"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Hide any other unwanted input decorations */
    .stChatInput .st-emotion-cache-o0516v,
    .stChatInput [data-testid="InputInstructions"],
    .stChatInput .e1gk92lc2 {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Clean up any other potential UI artifacts */
    [data-testid="stChatInput"] [data-testid="InputInstructions"] {
        display: none !important;
    }
    
    /* Remove any floating icons or controls that might appear */
    .stChatInput .st-emotion-cache-* {
        display: none !important;
    }
    
    /* Suggested question buttons */
    .stButton > button {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 14px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, var(--bpt-neutral-50) 100%);
        color: var(--bpt-neutral-700);
        border: 1.5px solid var(--bpt-neutral-300);
        border-radius: 12px;
        padding: 0.875rem 1.25rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(5px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        line-height: 1.5;
        text-align: left;
        white-space: normal;
        height: auto;
        min-height: 3.5rem;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, var(--bpt-primary) 0%, var(--bpt-secondary) 100%);
        color: white;
        border-color: var(--bpt-primary);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 51, 102, 0.3);
    }
    
    .stButton > button:active {
        transform: translateY(0px);
        box-shadow: 0 4px 15px rgba(0, 51, 102, 0.4);
    }
    
    /* Welcome section styling with empty state illustration */
    .welcome-container {
        text-align: center;
        padding: 4rem 2rem 3rem 2rem;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, var(--bpt-neutral-50) 100%);
        border-radius: 20px;
        margin: 2rem 0;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
        min-height: 35vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .welcome-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--bpt-neutral-800);
        margin-bottom: 0.75rem;
        letter-spacing: -0.025em;
        background: linear-gradient(135deg, var(--bpt-primary) 0%, var(--bpt-secondary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .welcome-subtitle {
        color: var(--bpt-neutral-500);
        font-size: 1.25rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    .welcome-description {
        color: var(--bpt-neutral-400);
        font-size: 1rem;
        font-style: italic;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }
    
    /* Empty state illustration */
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1.5rem;
        opacity: 0.7;
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    /* Suggestion questions header */
    .suggestions-header {
        text-align: center;
        color: var(--bpt-neutral-700);
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, var(--bpt-neutral-50) 100%);
        border-radius: 12px;
        backdrop-filter: blur(5px);
        border: 1px solid var(--bpt-neutral-200);
    }
    
    /* Cost and timestamp badges */
    .message-metadata {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--bpt-neutral-200);
        font-size: 0.8rem;
        color: var(--bpt-neutral-400);
    }
    
    .cost-badge {
        background: var(--bpt-success);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.5rem;
        font-weight: 500;
        font-size: 0.75rem;
    }
    
    .timestamp-badge {
        font-style: italic;
    }
    
    /* Loading spinner customization */
    .stSpinner > div {
        border-top-color: var(--bpt-secondary) !important;
    }
    
    /* Responsive improvements */
    @media (max-width: 768px) {
        .main .block-container {
            max-width: 95%;
            padding: 1rem;
            width: 95%;
        }
        
        .welcome-container {
            padding: 2rem 1rem;
            min-height: 25vh;
        }
        
        .welcome-title {
            font-size: 2rem;
        }
        
        .welcome-subtitle {
            font-size: 1rem;
        }
        
        .stChatInput {
            padding: 0 1rem;
        }
        
        .empty-state-icon {
            font-size: 3rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create a stable container for the chat area
    chat_container = st.container()
    
    with chat_container:
        # Check for pending question from suggested questions
        pending_question = st.session_state.get('pending_question')
        if pending_question:
            # Clear the pending question to avoid reprocessing
            st.session_state.pop('pending_question', None)
            
            # Add user message to chat history with timestamp
            user_message = {
                "role": "user", 
                "content": pending_question,
                "timestamp": time.time()
            }
            st.session_state.messages.append(user_message)
            
            # Get the active transcript session_id
            active_transcript = session_manager.get_active_transcript()
            session_id = None
            if active_transcript.get("is_active"):
                session_id = active_transcript.get("transcript_id")
            
            # Process the question and get response
            try:
                with st.spinner("Searching transcripts..."):
                    start_time = time.time()
                    response = api_client.ask_question(pending_question, session_id=session_id)
                    end_time = time.time()
                    
                    if response.get("success"):
                        answer = response.get("answer", "")
                        sources = response.get("sources", [])
                        
                        # Add metadata if available
                        method = response.get("method", "unknown")
                        confidence = response.get("confidence")
                        processing_time = response.get("processing_time", end_time - start_time)
                        
                        # Build metadata string for display
                        metadata_parts = []
                        if confidence is not None:
                            metadata_parts.append(f"Confidence: {confidence:.2f}")
                        if processing_time is not None:
                            metadata_parts.append(f"⏱️ {processing_time:.2f}s")
                        if sources:
                            metadata_parts.append(f"📚 {len(sources)} sources")
                        
                        # Add metadata to answer if available
                        if metadata_parts:
                            answer += f"\n\n*{' • '.join(metadata_parts)}*"
                        
                        # Add assistant response with enhanced metadata
                        assistant_message = {
                            "role": "assistant", 
                            "content": answer,
                            "sources": sources,
                            "timestamp": time.time(),
                            "metadata": {
                                "confidence": confidence,
                                "processing_time": processing_time,
                                "method": method,
                                "user_question": pending_question  # Store for cost calculation
                            }
                        }
                        st.session_state.messages.append(assistant_message)
                    else:
                        error_msg = response.get("error", "I'm having trouble connecting to the BPT system.")
                        error_message = {
                            "role": "assistant", 
                            "content": error_msg,
                            "timestamp": time.time(),
                            "metadata": {"error": True}
                        }
                        st.session_state.messages.append(error_message)
                        
            except Exception as e:
                error_msg = "I'm having trouble connecting to the BPT system. Please check if the API is running."
                error_message = {
                    "role": "assistant", 
                    "content": error_msg,
                    "timestamp": time.time(),
                    "metadata": {"error": True, "exception": str(e)}
                }
                st.session_state.messages.append(error_message)
            
            # Rerun to display the new messages and scroll to chat area
            st.rerun()
        
        # Create a fixed-height chat area that prevents jumping
        if st.session_state.messages:
            # Add a scroll-to-top anchor for suggested questions
            st.markdown('<div id="chat-area"></div>', unsafe_allow_html=True)
            
            # Use a consistent container with fixed height for messages
            with st.container(height=400):  # Fixed height to prevent jumping
                # Display all messages to maintain consistency
                for message in st.session_state.messages:
                    render_message_with_metadata(message, session_manager, show_metadata=True)
            
            # Add JavaScript to scroll to chat area when new messages appear
            st.markdown("""
            <script>
            // Scroll to chat area when messages appear
            setTimeout(function() {
                const chatArea = document.getElementById('chat-area');
                if (chatArea) {
                    chatArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 100);
            </script>
            """, unsafe_allow_html=True)
        else:
            # Show enhanced empty state with floating icon and welcoming message
            st.markdown("""
            <div class="welcome-container">
                <div class="empty-state-icon">💬</div>
                <h1 class="welcome-title">BPT Trading Assistant</h1>
                <p class="welcome-subtitle">Ask me anything about your trading sessions</p>
                <p class="welcome-description">
                    I can help you find insights, analyze trades, and answer questions about your BPT sessions. Start by typing a question below or try one of the suggested prompts.
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Chat input with proper spacing
        prompt = st.chat_input("Ask about your trading sessions...", key="main_chat_input")
        
        # Handle user input
        if prompt:
            # Add user message to chat history with timestamp
            user_message = {
                "role": "user", 
                "content": prompt,
                "timestamp": time.time()
            }
            st.session_state.messages.append(user_message)
            
            # Get the active transcript session_id
            active_transcript = session_manager.get_active_transcript()
            session_id = None
            if active_transcript.get("is_active"):
                session_id = active_transcript.get("transcript_id")
            
            # Process the question and get response
            try:
                with st.spinner("Searching transcripts..."):
                    start_time = time.time()
                    response = api_client.ask_question(prompt, session_id=session_id)
                    end_time = time.time()
                    
                    if response.get("success"):
                        answer = response.get("answer", "")
                        sources = response.get("sources", [])
                        
                        # Add metadata if available
                        method = response.get("method", "unknown")
                        confidence = response.get("confidence")
                        processing_time = response.get("processing_time", end_time - start_time)
                        
                        # Build metadata string for display
                        metadata_parts = []
                        if confidence is not None:
                            metadata_parts.append(f"Confidence: {confidence:.2f}")
                        if processing_time is not None:
                            metadata_parts.append(f"⏱️ {processing_time:.2f}s")
                        if sources:
                            metadata_parts.append(f"📚 {len(sources)} sources")
                        
                        # Add metadata to answer if available
                        if metadata_parts:
                            answer += f"\n\n*{' • '.join(metadata_parts)}*"
                        
                        # Add assistant response with enhanced metadata
                        assistant_message = {
                            "role": "assistant", 
                            "content": answer,
                            "sources": sources,
                            "timestamp": time.time(),
                            "metadata": {
                                "confidence": confidence,
                                "processing_time": processing_time,
                                "method": method,
                                "user_question": prompt  # Store for cost calculation
                            }
                        }
                        st.session_state.messages.append(assistant_message)
                    else:
                        error_msg = response.get("error", "I'm having trouble connecting to the BPT system.")
                        error_message = {
                            "role": "assistant", 
                            "content": error_msg,
                            "timestamp": time.time(),
                            "metadata": {"error": True}
                        }
                        st.session_state.messages.append(error_message)
                        
            except Exception as e:
                error_msg = "I'm having trouble connecting to the BPT system. Please check if the API is running."
                error_message = {
                    "role": "assistant", 
                    "content": error_msg,
                    "timestamp": time.time(),
                    "metadata": {"error": True, "exception": str(e)}
                }
                st.session_state.messages.append(error_message)
            
            # Rerun to display the new messages
            st.rerun()
    
    # Separator and suggested questions (only show when no messages for cleaner experience)
    if not st.session_state.messages:
        st.markdown('<hr style="margin: 2rem 0; border: none; border-top: 1px solid #e5e7eb;">', unsafe_allow_html=True)
        st.markdown('<div class="suggestions-container">', unsafe_allow_html=True)
        render_suggested_questions(api_client, session_manager)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Optionally show a smaller "Ask another question" section
        with st.expander("💡 Ask another question", expanded=False):
            render_suggested_questions(api_client, session_manager)

def render_search_results_with_recency(sources: List[Dict[str, Any]], session_manager) -> None:
    """
    Render search results with recency indicators and enhanced visual formatting.
    
    Args:
        sources: List of source dictionaries from API response
        session_manager: SessionManager instance for transcript context
    """
    
    if not sources:
        return
    
    # Create an expandable section for sources
    with st.expander(f"📚 View Sources ({len(sources)} found)", expanded=False):
        
        # Sort sources by similarity (highest first)
        sorted_sources = sorted(sources, key=lambda x: x.get('similarity', 0), reverse=True)
        
        for i, source in enumerate(sorted_sources, 1):
            transcript_id = source.get('transcript_id', 'unknown')
            similarity = source.get('similarity', 0.0)
            text_preview = source.get('text_preview', '')
            chunk_id = source.get('chunk_id', '')
            entities = source.get('entities', [])
            
            # Get recency indicator for this transcript
            recency_indicator = get_transcript_recency_indicator(transcript_id, session_manager)
            
            # Create a container for each source with enhanced styling
            source_container = st.container()
            
            with source_container:
                # Header with recency indicator and similarity score
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{recency_indicator} Source {i}: {transcript_id}**")
                
                with col2:
                    # Similarity score with color coding
                    if similarity >= 0.8:
                        similarity_color = "#22c55e"  # Green
                        similarity_label = "🎯 High"
                    elif similarity >= 0.6:
                        similarity_color = "#f59e0b"  # Yellow
                        similarity_label = "📊 Medium"
                    else:
                        similarity_color = "#ef4444"  # Red
                        similarity_label = "📉 Low"
                    
                    st.markdown(f'<span style="color: {similarity_color}; font-weight: bold;">{similarity_label} ({similarity:.3f})</span>', 
                               unsafe_allow_html=True)
                
                with col3:
                    # Chunk information
                    st.markdown(f"*Chunk: {chunk_id}*")
                
                # Text preview with better formatting
                if text_preview:
                    # Truncate if too long and add styling
                    display_text = text_preview[:300] + "..." if len(text_preview) > 300 else text_preview
                    st.markdown(f'<div style="background-color: #f8f9fa; padding: 0.75rem; border-radius: 0.5rem; border-left: 3px solid {similarity_color}; margin: 0.5rem 0;">'
                               f'<em>"{display_text}"</em></div>', 
                               unsafe_allow_html=True)
                
                # Entities if available
                if entities:
                    entity_tags = " ".join([f"`{entity}`" for entity in entities[:5]])
                    st.markdown(f"**Entities:** {entity_tags}")
                
                # Add separator between sources
                if i < len(sorted_sources):
                    st.markdown('<hr style="margin: 1rem 0; border: none; border-top: 1px solid #e5e7eb;">', 
                               unsafe_allow_html=True)

def get_transcript_recency_indicator(transcript_id: str, session_manager) -> str:
    """
    Get a recency indicator for a transcript based on its age.
    
    Args:
        transcript_id: The transcript identifier
        session_manager: SessionManager instance for accessing transcript data
        
    Returns:
        String with emoji and text indicating recency
    """
    
    try:
        # Try to get transcript metadata from session manager's cache
        cached_transcripts = session_manager.get_cached_transcripts()
        
        if cached_transcripts and "transcripts" in cached_transcripts:
            for transcript in cached_transcripts["transcripts"]:
                if transcript.get("id") == transcript_id:
                    # Use the session manager's recency calculation
                    return session_manager.get_transcript_recency_indicator(transcript)
        
        # Fallback: try to parse timestamp from transcript_id if it contains date info
        if "_" in transcript_id:
            parts = transcript_id.split("_")
            for part in parts:
                # Look for date-like patterns (YYYYMMDD, YYYY-MM-DD, etc.)
                if len(part) >= 8 and part.replace("-", "").replace("_", "").isdigit():
                    try:
                        # Try different date formats
                        date_str = part.replace("-", "").replace("_", "")
                        if len(date_str) == 8:  # YYYYMMDD
                            transcript_date = datetime.strptime(date_str, "%Y%m%d")
                        elif len(date_str) == 6:  # YYMMDD
                            transcript_date = datetime.strptime(date_str, "%y%m%d")
                        else:
                            continue
                        
                        # Calculate age
                        age = datetime.now() - transcript_date
                        
                        if age.days == 0:
                            return "🆕 Today"
                        elif age.days == 1:
                            return "📅 Yesterday"
                        elif age.days <= 7:
                            return f"📅 {age.days} days ago"
                        elif age.days <= 30:
                            weeks = age.days // 7
                            return f"📄 {weeks} week{'s' if weeks > 1 else ''} ago"
                        else:
                            months = age.days // 30
                            return f"📄 {months} month{'s' if months > 1 else ''} ago"
                    except ValueError:
                        continue
        
        # Default fallback
        return "📄 Unknown age"
        
    except Exception:
        # Safe fallback
        return "📄 Recent"

def render_suggested_questions(api_client, session_manager):
    """Render suggested questions below the chat window in a broader, more ChatGPT-like layout."""
    
    suggested_questions = [
        "What is the current directional bias and key levels for the S&P 500?",
        "What setup and trigger levels are guiding the Gold trade thesis?",
        "What is the outlook for natural-gas volatility and positioning considerations?",
        "What is the current interpretation of Treasury-yield trends and bond risk?",
        "Which assets are highlighted as strongest bullish and strongest bearish cases?",
        "What adjustments have been made to the open trade sheet and associated levels?",
        "Which forthcoming macro event is considered the primary market catalyst to watch?",
        "How is the VIX (volatility index) being read for market sentiment implications?",
        "What key zones shape the prevailing Bitcoin thesis?",
        "Which audience question received the most insightful response, and what was that takeaway?"
    ]
    
    # Header with enhanced styling (only show when no messages)
    if not st.session_state.messages:
        st.markdown('<div class="suggestions-header">💡 Try asking me about:</div>', unsafe_allow_html=True)
    
    # Create a broader grid using 2 columns for better readability
    cols = st.columns(2, gap="large")
    for i, question in enumerate(suggested_questions):
        with cols[i % 2]:
            if st.button(
                question, 
                key=f"suggested_{i}",
                help="Click to ask this question",
                use_container_width=True
            ):
                # Set the question in session state to be processed by main chat logic
                # This avoids the spinner appearing on the button
                st.session_state['pending_question'] = question
                st.rerun()
    
    # Add some bottom spacing for better visual separation
    if not st.session_state.messages:
        st.markdown('<div style="margin-bottom: 2rem;"></div>', unsafe_allow_html=True)

def render_quick_actions():
    """Render quick action buttons at the bottom."""
    
    if len(st.session_state.messages) > 0:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🔄 New Chat", help="Start a new conversation", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        with col2:
            if st.button("📤 Export", help="Export chat history", use_container_width=True):
                # Simple export
                if st.session_state.messages:
                    chat_text = "\n\n".join([
                        f"**{msg['role'].title()}:** {msg['content']}" 
                        for msg in st.session_state.messages
                    ])
                    st.download_button(
                        label="💾 Download",
                        data=chat_text,
                        file_name=f"bpt_chat_{time.strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown"
                    )
        
        with col3:
            if st.button("⚙️ Tools", help="Open tools sidebar", use_container_width=True):
                st.session_state.show_sidebar = not st.session_state.get('show_sidebar', False)
                st.rerun()

def render_welcome_section():
    """Render welcome message for new users."""
    
    st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 1rem; margin-bottom: 2rem;'>
        <h3 style='color: #2E8B57; margin-bottom: 1rem;'>👋 Welcome to BPT Trading Assistant!</h3>
        <p style='color: #666; font-size: 1.1rem; margin-bottom: 0;'>
            Ask questions about your trading sessions, get insights, and explore your trading data with natural language.
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_example_questions():
    """Render example questions to help users get started."""
    
    with st.expander("💡 Example Questions", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📈 Trading Questions:**")
            examples = [
                "What trades did we discuss today?",
                "Show me all AAPL mentions",
                "Any options strategies discussed?"
            ]
            for example in examples:
                if st.button(f"💬 {example}", key=f"ex1_{hash(example)}", use_container_width=True):
                    st.session_state.pending_question = example
        
        with col2:
            st.markdown("**🎯 Strategy Questions:**")
            examples = [
                "What swing trades were mentioned?",
                "Any sector rotation ideas?",
                "What's the risk management approach?"
            ]
            for example in examples:
                if st.button(f"💬 {example}", key=f"ex2_{hash(example)}", use_container_width=True):
                    st.session_state.pending_question = example
        
        with col3:
            st.markdown("**📊 Analysis Questions:**")
            examples = [
                "What's driving the market?",
                "Any earnings plays discussed?",
                "What technical levels were mentioned?"
            ]
            for example in examples:
                if st.button(f"💬 {example}", key=f"ex3_{hash(example)}", use_container_width=True):
                    st.session_state.pending_question = example

def handle_pending_questions(api_client, session_manager):
    """Handle pending questions from quick actions and examples."""
    
    if hasattr(st.session_state, 'pending_question') and st.session_state.pending_question:
        # Get the pending question
        prompt = st.session_state.pending_question
        st.session_state.pending_question = None
        
        # Avoid duplicates
        recent_messages = [msg["content"] for msg in st.session_state.messages[-5:]]
        if prompt not in recent_messages:
            # Add user message
            user_message = {
                "role": "user",
                "content": prompt,
                "timestamp": time.strftime("%H:%M:%S")
            }
            st.session_state.messages.append(user_message)
            
            # Process the question (similar to manual input)
            try:
                # Get the active transcript session_id
                active_transcript = session_manager.get_active_transcript()
                session_id = None
                if active_transcript.get("is_active"):
                    session_id = active_transcript.get("transcript_id")
                
                response = api_client.ask_question(prompt, session_id=session_id)
                
                if response and response.get("success", False) and "answer" in response:
                    answer = response["answer"]
                    
                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "timestamp": time.strftime("%H:%M:%S")
                    }
                    st.session_state.messages.append(assistant_message)
                
                else:
                    error_message = response.get("error", "I couldn't find relevant information for that question.")
                    session_manager.log_error(error_message, prompt, "quick_action")
                    
                    assistant_message = {
                        "role": "assistant",
                        "content": error_message,
                        "timestamp": time.strftime("%H:%M:%S")
                    }
                    st.session_state.messages.append(assistant_message)
            
            except Exception as e:
                session_manager.log_error(str(e), prompt, "quick_action_exception")
                
                assistant_message = {
                    "role": "assistant",
                    "content": "Sorry, I encountered an error processing that question. Please try again.",
                    "timestamp": time.strftime("%H:%M:%S")
                }
                st.session_state.messages.append(assistant_message)
            
            # Rerun to show the new messages
            st.rerun()

def clear_chat_history():
    """Clear the chat history and reset session state."""
    
    if st.button("🗑️ Clear Chat", help="Clear all messages and start fresh"):
        st.session_state.messages = []
        st.session_state.session_start = time.time()
        if "errors" in st.session_state:
            del st.session_state.errors
        st.success("Chat history cleared!")
        st.rerun()

def estimate_api_cost(question: str, answer: str, processing_time: float = None) -> float:
    """
    Estimate the API cost for a question-answer pair.
    
    Args:
        question: The user's question
        answer: The assistant's answer
        processing_time: Time taken to process (optional)
    
    Returns:
        Estimated cost in USD
    """
    # Rough estimation based on token count
    # Assuming ~4 characters per token and typical OpenAI pricing
    input_tokens = len(question) / 4
    output_tokens = len(answer) / 4
    
    # Estimated costs (these are rough approximations)
    input_cost_per_1k = 0.0015  # $0.0015 per 1K input tokens
    output_cost_per_1k = 0.002  # $0.002 per 1K output tokens
    
    input_cost = (input_tokens / 1000) * input_cost_per_1k
    output_cost = (output_tokens / 1000) * output_cost_per_1k
    
    return input_cost + output_cost

def format_timestamp(timestamp: float = None) -> str:
    """Format a timestamp into a human-readable string."""
    if timestamp is None:
        timestamp = time.time()
    
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%H:%M:%S")

def render_message_with_metadata(message: Dict[str, Any], session_manager, show_metadata: bool = True):
    """
    Render a chat message with optional cost and timestamp metadata.
    
    Args:
        message: The message dictionary
        session_manager: SessionManager instance for accessing transcript context
        show_metadata: Whether to show metadata badges
    """
    role = message["role"]
    content = message["content"]
    
    with st.chat_message(role):
        st.markdown(content)
        
        # Show metadata for assistant messages
        if show_metadata and role == "assistant":
            metadata = message.get("metadata", {})
            timestamp = message.get("timestamp", time.time())
            
            # Calculate estimated cost
            estimated_cost = 0.0
            if "user_question" in metadata:
                estimated_cost = estimate_api_cost(
                    metadata.get("user_question", ""),
                    content,
                    metadata.get("processing_time")
                )
            
            # Create metadata badges
            metadata_html = '<div class="message-metadata">'
            metadata_html += '<div class="metadata-left">'
            
            # Cost badge
            if estimated_cost > 0:
                metadata_html += f'<span class="cost-badge">${estimated_cost:.4f}</span>'
            
            # Processing time
            processing_time = metadata.get("processing_time")
            if processing_time:
                metadata_html += f'<span style="margin-left: 0.5rem; color: var(--bpt-neutral-400);">⏱️ {processing_time:.1f}s</span>'
            
            # Confidence score
            confidence = metadata.get("confidence")
            if confidence:
                metadata_html += f'<span style="margin-left: 0.5rem; color: var(--bpt-neutral-400);">🎯 {confidence:.2f}</span>'
            
            metadata_html += '</div>'
            metadata_html += f'<div class="timestamp-badge">{format_timestamp(timestamp)}</div>'
            metadata_html += '</div>'
            
            st.markdown(metadata_html, unsafe_allow_html=True)
        
        # Display sources with recency indicators if available
        if role == "assistant" and "sources" in message:
            render_search_results_with_recency(message["sources"], session_manager) 