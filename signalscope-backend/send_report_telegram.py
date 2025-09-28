"""
Send the latest report to Telegram
"""
import asyncio
from app.services.telegram_service import TelegramService
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

async def send_latest_report():
    # Get latest report from database
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    supabase = create_client(url, key)
    
    # Get latest report
    result = supabase.table("reports").select("*").order("created_at", desc=True).limit(1).execute()
    
    if result.data:
        report = result.data[0]
        
        print("Sending report to Telegram...")
        print(f"Report type: {report['report_type']}")
        print(f"Tickers: {', '.join(report['mentioned_tickers'])}")
        
        # Send to Telegram
        telegram = TelegramService()
        
        if report['report_type'] == 'alert':
            success = await telegram.send_alert_report(report)
        elif report['report_type'] == 'hourly':
            success = await telegram.send_hourly_report(report)
        else:
            success = await telegram.send_daily_report(report)
        
        if success:
            print("Report sent to Telegram successfully!")
        else:
            print("Failed to send to Telegram")
    else:
        print("No reports found in database")

if __name__ == "__main__":
    asyncio.run(send_latest_report())