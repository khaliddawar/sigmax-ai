"""
View reports from Supabase database
"""
from supabase import create_client
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def view_reports():
    """View all reports in the database"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Supabase not configured")
        return
    
    supabase = create_client(url, key)
    
    # Get all reports
    reports = supabase.table("reports").select("*").order("created_at", desc=True).execute()
    
    print("\n" + "="*60)
    print("SignalScope AI Reports in Database")
    print("="*60)
    
    if not reports.data:
        print("No reports found")
        return
    
    for i, report in enumerate(reports.data, 1):
        print(f"\n--- Report #{i} ---")
        print(f"ID: {report['id']}")
        print(f"Type: {report['report_type']}")
        print(f"Created: {report['created_at']}")
        print(f"Messages Analyzed: {report['messages_analyzed']}")
        print(f"Overall Sentiment: {report['overall_sentiment']}")
        print(f"Confidence: {report['confidence_score']}")
        print(f"Tickers: {', '.join(report['mentioned_tickers'])}")
        
        print("\nKey Insights:")
        for insight in report['key_insights'][:3]:
            print(f"  - {insight}")
        
        print("\nTrading Signals:")
        for signal in report['trading_signals'][:2]:
            print(f"  - {signal['action']} {signal['ticker']} ({signal['strength']})")
            print(f"    {signal['reasoning']}")
    
    # Get message counts
    messages = supabase.table("messages").select("id", count="exact").execute()
    batches = supabase.table("message_batches").select("id", count="exact").execute()
    
    print("\n" + "="*60)
    print("Database Statistics")
    print("="*60)
    print(f"Total Reports: {len(reports.data)}")
    print(f"Total Messages: {messages.count}")
    print(f"Total Batches: {batches.count}")

if __name__ == "__main__":
    view_reports()