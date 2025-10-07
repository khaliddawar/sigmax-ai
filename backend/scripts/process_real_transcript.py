#!/usr/bin/env python
"""
Python script to process a large transcript file
This avoids issues with JSON escaping in PowerShell
"""

import json
import os
import requests
import sys
from pathlib import Path

# Configuration
TRANSCRIPT_PATH = "real_meeting.txt"
API_URL = "http://localhost:8001/api/transcripts"
OUTPUT_DIR = "scripts/temp"

def main():
    # Create temp directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Temp directory: {OUTPUT_DIR}")
    
    # Read the transcript file
    try:
        with open(TRANSCRIPT_PATH, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        print(f"Read transcript file: {TRANSCRIPT_PATH}")
        print(f"File size: {len(transcript_text)} bytes")
    except Exception as e:
        print(f"Error reading transcript file: {e}")
        return 1
    
    # Create request payload
    payload = {
        "transcript_id": "real_meeting_test",
        "transcript_text": transcript_text,
        "metadata": {
            "title": "Macro Roadmap Trading Discussion",
            "meeting_id": "macro-20250519",
            "source": "manual"
        }
    }
    
    # Save payload to file for debugging
    json_path = os.path.join(OUTPUT_DIR, "real_meeting_payload.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        print(f"Saved JSON payload to: {json_path}")
        print(f"JSON file size: {os.path.getsize(json_path)} bytes")
    except Exception as e:
        print(f"Error saving JSON payload: {e}")
        return 1
    
    # Send API request
    print("Sending request to API...")
    try:
        response = requests.post(API_URL, json=payload)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        print("Successfully processed transcript!")
        print(f"Transcript ID: {result.get('transcript_id')}")
        
        # Save transcript ID for later use
        id_path = os.path.join(OUTPUT_DIR, "current_transcript_id.txt")
        with open(id_path, 'w') as f:
            f.write(str(result.get('transcript_id')))
        
        print(f"Saved transcript ID to: {id_path}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print("Response content:")
            print(e.response.text)
        return 1
    
    print("Script completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 