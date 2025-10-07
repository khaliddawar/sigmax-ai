#!/usr/bin/env python3
"""
Fix incomplete transcript processing
This script manually completes the summary generation for transcript 01JWKXERVJC4N2ZD7MXF0YSP3V
that failed during the domain loader performance issue.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.supabase_client import SupabaseService
from app.services.summary_service import SummaryService
from app.services.ingestion_service import IngestionService

async def fix_incomplete_transcript():
    """Fix the incomplete transcript processing"""
    
    transcript_id = "01JWKXERVJC4N2ZD7MXF0YSP3V"
    
    print(f"🔧 Fixing incomplete transcript: {transcript_id}")
    
    # Initialize services
    supabase_service = SupabaseService()
    summary_service = SummaryService()
    ingestion_service = IngestionService()
    
    # Check if transcript exists
    print("📋 Checking transcript in database...")
    transcript_result = await supabase_service.get_transcript_by_id(transcript_id)
    print(f"Transcript result: {transcript_result}")
    
    if not transcript_result.get("success"):
        print(f"❌ Transcript {transcript_id} not found in database")
        print(f"Error: {transcript_result.get('error', 'Unknown error')}")
        return
    
    transcript_data = transcript_result.get("transcript")
    if not transcript_data:
        print(f"❌ No transcript data returned")
        return
        
    print(f"✅ Found transcript: {transcript_data.get('title', 'No title')}")
    print(f"   Created: {transcript_data.get('created_at', 'Unknown')}")
    print(f"   Word count: {transcript_data.get('word_count', 0)}")
    print(f"   Current summary: {'✅ Present' if transcript_data.get('summary') else '❌ Missing'}")
    
    # Get transcript chunks from the response (they're already included)
    print("📄 Getting transcript chunks...")
    chunks = transcript_result.get("chunks", [])
    print(f"✅ Found {len(chunks)} chunks")
    
    if not chunks:
        print("❌ No chunks found, cannot reconstruct transcript")
        return
    
    # Reconstruct full transcript text
    full_text = "\n\n".join([chunk.get("text", "") for chunk in chunks])
    print(f"✅ Reconstructed transcript: {len(full_text)} characters")
    
    # Generate summary if missing
    if not transcript_data.get('summary'):
        print("🤖 Generating missing summary...")
        try:
            summary = await summary_service.generate_session_summary(full_text)
            print(f"✅ Generated summary: {len(summary)} characters")
            
            # Update transcript with summary
            update_result = await supabase_service.update_transcript_record(transcript_id, {"summary": summary})
            if update_result.get("success"):
                print("✅ Summary saved to database")
            else:
                print(f"❌ Failed to save summary: {update_result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error generating summary: {str(e)}")
            import traceback
            traceback.print_exc()
            return
    else:
        print("✅ Summary already exists, skipping generation")
        summary = transcript_data.get('summary')
    
    # Run email pipeline if needed
    print("📧 Running email pipeline...")
    try:
        email_result = await ingestion_service.send_email_summary(
            transcript_id=transcript_id,
            meeting_title=transcript_data.get('title', f'Transcript {transcript_id}'),
            meeting_date=transcript_data.get('created_at', ''),
            summary=summary
        )
        
        if email_result.get("success"):
            print("✅ Email pipeline completed successfully")
        else:
            print(f"❌ Email pipeline failed: {email_result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error in email pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"🎉 Transcript {transcript_id} processing completed!")

if __name__ == "__main__":
    asyncio.run(fix_incomplete_transcript()) 