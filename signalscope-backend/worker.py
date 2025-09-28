"""
SignalScope Background Worker
Continuously processes messages from Redis queues
"""
import time
import redis
import subprocess
import sys
from datetime import datetime

def run_worker():
    """Main worker loop"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print("\n" + "="*60)
    print("SIGNALSCOPE BACKGROUND WORKER")
    print("="*60)
    print("Processing Schedule:")
    print("  - Realtime messages: Every 5 minutes")
    print("  - Standard messages: Every 15 minutes")
    print("  - Archive messages: Every 60 minutes")
    print("\nPress Ctrl+C to stop")
    print("="*60)
    
    last_realtime = 0
    last_standard = 0
    last_archive = 0
    
    while True:
        try:
            current_time = time.time()
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Check queue sizes
            realtime_count = r.xlen("signalscope:messages:realtime")
            standard_count = r.xlen("signalscope:messages:standard")
            archive_count = r.xlen("signalscope:messages:archive")
            
            # Display status every 30 seconds
            print(f"\n[{timestamp}] Queue Status:")
            print(f"  Realtime: {realtime_count} | Standard: {standard_count} | Archive: {archive_count}")
            
            processed_any = False
            
            # Process realtime every 5 minutes (300 seconds) or if queue has 10+ messages
            if (current_time - last_realtime >= 300 or realtime_count >= 10) and realtime_count > 0:
                print(f"  Processing {realtime_count} realtime messages...")
                subprocess.run([sys.executable, "process_batch.py"], 
                             capture_output=True, text=True, cwd=".")
                print(f"  [DONE] Alert sent to Telegram!")
                last_realtime = current_time
                processed_any = True
            
            # Process standard every 15 minutes (900 seconds) or if queue has 20+ messages
            if (current_time - last_standard >= 900 or standard_count >= 20) and standard_count > 0:
                print(f"  Processing {standard_count} standard messages...")
                subprocess.run([sys.executable, "process_batch.py"], 
                             capture_output=True, text=True, cwd=".")
                print(f"  [DONE] Hourly report sent to Telegram!")
                last_standard = current_time
                processed_any = True
            
            # Process archive every 60 minutes (3600 seconds) or if queue has 50+ messages
            if (current_time - last_archive >= 3600 or archive_count >= 50) and archive_count > 0:
                print(f"  Processing {archive_count} archive messages...")
                subprocess.run([sys.executable, "process_batch.py"], 
                             capture_output=True, text=True, cwd=".")
                print(f"  [DONE] Daily report sent to Telegram!")
                last_archive = current_time
                processed_any = True
            
            if not processed_any and (realtime_count + standard_count + archive_count) == 0:
                print(f"  Waiting for messages...")
            
            # Check every 30 seconds
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n\nWorker stopped by user.")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("Retrying in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        print("\nShutting down worker...")
        sys.exit(0)