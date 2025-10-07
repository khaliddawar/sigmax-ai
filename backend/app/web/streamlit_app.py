"""
BPT Trading Assistant - Streamlit Web Interface

A minimalist ChatGPT-like web interface for the Big Picture Trading (BPT) system.
"""

import streamlit as st
import requests
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Get absolute paths to avoid relative import issues
current_file = os.path.abspath(__file__)
web_dir = os.path.dirname(current_file)
components_dir = os.path.join(web_dir, 'components')
utils_dir = os.path.join(web_dir, 'utils')
project_root = os.path.dirname(os.path.dirname(web_dir))

# Add all necessary paths to sys.path
paths_to_add = [web_dir, components_dir, utils_dir, project_root]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"🔧 Added to Python path: {paths_to_add}")
print(f"📁 Current working directory: {os.getcwd()}")
print(f"📄 Current file: {current_file}")
print(f"🌐 Web directory: {web_dir}")

# Import components using direct module names (no relative imports)
try:
    import chat_interface
    import sidebar
    import transcript_header
    import api_client
    import session_manager
    
    # Get the functions we need
    render_chat_interface = chat_interface.render_chat_interface
    render_sidebar = sidebar.render_sidebar
    render_transcript_header = transcript_header.render_transcript_header
    BPTAPIClient = api_client.BPTAPIClient
    SessionManager = session_manager.SessionManager
    
    print("✅ SUCCESS: Direct module imports worked!")
    
except ImportError as e:
    print(f"❌ Direct module imports failed: {e}")
    print(f"📊 Python path: {sys.path}")
    print(f"📁 Components dir exists: {os.path.exists(components_dir)}")
    print(f"📁 Utils dir exists: {os.path.exists(utils_dir)}")
    
    if os.path.exists(components_dir):
        print(f"📋 Components dir contents: {os.listdir(components_dir)}")
    if os.path.exists(utils_dir):
        print(f"📋 Utils dir contents: {os.listdir(utils_dir)}")
    
    st.error("❌ IMPORT ERROR: Could not load required components")
    st.error(f"Error details: {e}")
    st.error("Debug information:")
    st.error(f"- Current file: {current_file}")
    st.error(f"- Web directory: {web_dir}")
    st.error(f"- Components directory: {components_dir}")
    st.error(f"- Utils directory: {utils_dir}")
    st.stop()

# Configure Streamlit page
st.set_page_config(
    page_title="BPT Trading Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",  # Changed from "expanded" to "collapsed" so sidebar is closed by default
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Minimalist CSS styling with broader, shorter chat window
st.markdown("""
<style>
    /* Import Montserrat font */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@100;200;300;400;500;600;700;800;900&display=swap');
    
    /* Global font override */
    * {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif !important;
    }
    
    .stApp {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif !important;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e2e8f0 100%);
        background-attachment: fixed;
        min-height: 100vh;
    }
    
    /* Hide Streamlit branding and clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Hide unwanted input instruction elements globally */
    [data-testid="InputInstructions"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    .st-emotion-cache-o0516v {
        display: none !important;
    }
    
    .e1gk92lc2 {
        display: none !important;
    }
    
    /* Clean, minimal styling with ChatGPT-like broader layout */
    .main .block-container {
        max-width: 1000px !important;  /* Reduced from 1200px for wider margins */
        margin: 0 auto !important;     /* Center horizontally */
        padding: 2rem 1.5rem !important;  /* Comfortable padding */
        background: rgba(255, 255, 255, 0.95);  /* Semi-transparent white background */
        border-radius: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);  /* Subtle shadow for depth */
        backdrop-filter: blur(10px);  /* Glass effect */
        border: 1px solid rgba(255, 255, 255, 0.2);
        width: calc(100% - 3rem) !important;  /* Responsive width with margins */
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
        min-height: calc(100vh - 3rem);  /* Full height minus margins */
    }
    
    /* Dashboard header area */
    .dashboard-header {
        text-align: center;
        margin-bottom: 2rem;
        padding: 0 1rem;
    }
    
    /* Chat area as dashboard widget */
    .chat-dashboard-widget {
        background: white;
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        min-height: 400px;  /* Dashboard widget height */
        max-height: 600px;  /* Limit maximum height */
        display: flex;
        flex-direction: column;
    }
    
    /* Chat messages container within dashboard widget */
    .stChatMessage {
        padding: 1rem 1.5rem;
        margin-bottom: 0.75rem;
        border-radius: 0.75rem;
        border: none;
        max-width: 85%;
        width: fit-content;
        font-size: 1rem;
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Dashboard chat input area */
    .stChatInput {
        max-width: 100%;
        margin: 1rem 0 0 0;
        padding: 0;
        position: relative;  /* Remove sticky for dashboard layout */
        background: transparent;
        z-index: 10;
    }
    
    /* Remove white spaces around chat input container */
    .stElementContainer[data-testid="stElementContainer"] {
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
    }
    
    .st-key-main_chat_input.stElementContainer {
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        border: none !important;
    }
    
    .st-emotion-cache-17lr0tt {
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
    }
    
    /* Target the specific chat input wrapper */
    .stChatInput.st-emotion-cache-1eeryuo {
        padding: 0 !important;
        margin: 0 auto !important;
        background: transparent !important;
        max-width: 100% !important;
    }
    
    /* Clean up the inner chat input containers */
    .st-emotion-cache-yd4u6l {
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;  /* Space between textarea and button */
    }
    
    .stChatInput > div {
        max-width: 100%;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
    }
    
    .stChatInput > div > div {
        max-width: 100%;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
    }
    
    .stChatInput > div > div > textarea {
        border-radius: 1.5rem;
        border: 1px solid #d1d5db;
        padding: 1rem 1.5rem;  /* More padding for comfort */
        font-size: 1.1rem;  /* Larger font size */
        min-height: 55px;  /* Slightly taller input */
        max-height: 120px;  /* Allow more expansion */
        width: 100%;
        max-width: 100%;
        line-height: 1.5;
        margin: 0 !important;  /* Remove any default margins */
        background: white !important;  /* Ensure white background */
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;  /* Add subtle shadow */
    }
    
    /* More specific targeting for the textarea to ensure white background */
    [data-testid="stChatInputTextArea"] {
        background: white !important;
        border-radius: 1.5rem !important;
        border: 1px solid #d1d5db !important;
        padding: 1rem 1.5rem !important;
        font-size: 1.1rem !important;
        min-height: 55px !important;
        max-height: 120px !important;
        line-height: 1.5 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.2s ease !important;
    }
    
    /* Focus state for textarea */
    [data-testid="stChatInputTextArea"]:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1), 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        outline: none !important;
    }
    
    /* Ensure the base input wrapper has no spacing but doesn't affect textarea background */
    [data-baseweb="base-input"] {
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        border: none !important;
    }
    
    /* Clean up textarea wrapper but preserve textarea styling */
    [data-baseweb="textarea"] {
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        border: none !important;
        border-radius: 1.5rem !important;  /* Match the textarea border radius */
    }
    
    /* Ensure the textarea gets proper visual priority */
    [data-baseweb="textarea"] > [data-baseweb="base-input"] > textarea {
        background: white !important;
        position: relative !important;
        z-index: 2 !important;
    }
    
    /* Remove spacing from submit button container */
    .st-emotion-cache-sey4o0 {
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 100% !important;
    }
    
    /* Style the submit button to match input height and center it */
    [data-testid="stChatInputSubmitButton"] {
        height: 55px !important;  /* Match textarea min-height */
        width: 55px !important;   /* Make it square */
        border-radius: 50% !important;  /* Make it circular */
        background: #2563eb !important;  /* Blue background */
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
        margin-left: 0.5rem !important;  /* Small gap from textarea */
    }
    
    /* Button hover state */
    [data-testid="stChatInputSubmitButton"]:hover:not(:disabled) {
        background: #1d4ed8 !important;
        transform: scale(1.05) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
    }
    
    /* Button active state */
    [data-testid="stChatInputSubmitButton"]:active:not(:disabled) {
        transform: scale(0.95) !important;
    }
    
    /* Button disabled state */
    [data-testid="stChatInputSubmitButton"]:disabled {
        background: #9ca3af !important;
        cursor: not-allowed !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Style the SVG icon inside the button */
    [data-testid="stChatInputSubmitButton"] svg {
        width: 20px !important;
        height: 20px !important;
        color: white !important;
        fill: white !important;
    }
    
    /* Additional button class styling */
    .st-emotion-cache-1nzi1q1 {
        height: 55px !important;
        width: 55px !important;
        border-radius: 50% !important;
        background: #2563eb !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Main chat container - much shorter vertically, broader horizontally */
    .chat-container {
        max-height: 35vh;  /* Much shorter - ChatGPT style */
        min-height: 25vh;  /* Minimum height */
        margin-bottom: 1rem;
        overflow-y: auto;
        width: 100%;
    }
    
    /* Chat messages area styling - shorter but broader */
    [data-testid="stChatMessageContainer"] {
        max-height: 30vh;  /* Limit message area height - shorter */
        overflow-y: auto;
        padding: 0.5rem 0;
        width: 100%;
    }
    
    /* Suggested questions styling - positioned below chat, broader */
    .suggested-questions-section {
        margin-top: 1.5rem;
        padding: 0 3rem;  /* More padding for broader layout */
    }
    
    .suggested-question {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.75rem;
        padding: 1rem 1.25rem;  /* More padding */
        margin: 0.5rem;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 1rem;  /* Larger font size */
        color: #374151;
        text-align: left;
        width: 100%;
        line-height: 1.4;
    }
    
    .suggested-question:hover {
        background: #f9fafb;
        border-color: #d1d5db;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Header styling with larger fonts */
    .chat-header {
        text-align: center;
        margin-bottom: 2rem;
        padding: 0 1rem;
    }
    
    .chat-title {
        font-size: 2.25rem;  /* Dashboard title size */
        font-weight: 600;
        color: #111827;
        margin-bottom: 0.75rem;
    }
    
    .chat-subtitle {
        color: #6b7280;
        font-size: 1.1rem;
    }
    
    /* Ensure sidebar is visible and properly sized */
    .css-1d391kg {
        width: auto;
        min-width: 280px;
        background: rgba(248, 250, 252, 0.95);
        backdrop-filter: blur(10px);
    }
    
    /* Center layout better and make it broader */
    .main-content {
        display: flex;
        flex-direction: column;
        width: 100%;
        max-width: 100%;
    }
    
    /* Ensure full width usage */
    .stVerticalBlock {
        width: 100%;
        max-width: 100%;
    }
    
    .element-container {
        width: 100%;
        max-width: 100%;
    }
    
    /* Button styling for suggested questions - larger fonts */
    .stButton > button {
        width: 100%;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
        background: white;
        color: #374151;
        padding: 0.875rem 1rem;
        text-align: left;
        font-size: 0.95rem;
        transition: all 0.2s;
        line-height: 1.4;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .stButton > button:hover {
        background: #f9fafb;
        border-color: #d1d5db;
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    
    /* General text size improvements */
    .stMarkdown p {
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 1rem;
    }
    
    .streamlit-expanderContent {
        font-size: 1rem;
    }
    
    /* Caption text larger */
    .stCaption {
        font-size: 0.95rem;
    }
    
    /* Responsive design */
    @media (max-width: 1280px) {
        .main .block-container {
            max-width: 95% !important;
            margin: 1rem auto !important;
            width: calc(100% - 2rem) !important;
        }
    }
    
    @media (max-width: 768px) {
        .main .block-container {
            max-width: calc(100% - 1rem) !important;
            margin: 0.5rem auto !important;
            padding: 1rem !important;
            width: calc(100% - 1rem) !important;
            border-radius: 0.5rem;
            min-height: calc(100vh - 1rem);
        }
        
        .chat-dashboard-widget {
            padding: 1rem;
            margin-bottom: 1rem;
            min-height: 300px;
        }
        
        .chat-title {
            font-size: 1.75rem;
        }
        
        .chat-subtitle {
            font-size: 1rem;
        }
        
        .dashboard-header {
            margin-bottom: 1rem;
            padding-bottom: 1rem;
        }
    }
    
    /* Force broader layout */
    .stApp {
        max-width: none;
    }
    
    /* Columns for suggested questions - broader spacing */
    .stColumn {
        padding: 0 0.5rem;
    }
    
    /* Chat input specific styling for full width */
    [data-testid="stChatInput"] {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Message container full width */
    [data-testid="stVerticalBlockBorderWrapper"] {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Ensure chat messages are properly sized */
    [data-testid="stChatMessage"] {
        font-size: 1rem !important;
        line-height: 1.6 !important;
        max-width: 85% !important;
    }
    
    /* User and assistant message styling */
    [data-testid="stChatMessage"][data-testid*="user"] {
        margin-left: auto;
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #bfdbfe;
    }
    
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        margin-right: auto;
        background: white;
        border: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application entry point."""
    
    # Initialize session manager
    session_manager = SessionManager()
    
    # Initialize API client
    api_client = BPTAPIClient()
    
    # Initialize session state
    session_manager.initialize_session_state()
    
    # Render transcript context header
    render_transcript_header(session_manager)
    
    # Render the main chat interface (includes suggested questions below)
    render_chat_interface(api_client, session_manager)
    
    # Sidebar (always show for system status)
    with st.sidebar:
        st.markdown("### 🛠️ BPT Assistant")
        render_sidebar(api_client, session_manager)

if __name__ == "__main__":
    main() 