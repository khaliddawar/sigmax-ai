"""
Check Redis queue contents
"""
import redis
import json

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

print("Redis Queue Status")
print("=" * 50)

# Check each stream
streams = [
    "signalscope:messages:realtime",
    "signalscope:messages:standard",
    "signalscope:messages:archive"
]

for stream in streams:
    try:
        # Get stream length
        length = r.xlen(stream)
        print(f"\n{stream}:")
        print(f"  Messages in queue: {length}")
        
        # Get first few messages
        if length > 0:
            messages = r.xrange(stream, count=2)
            for msg_id, data in messages:
                content = json.loads(data.get('content', '{}'))
                print(f"  - ID: {msg_id}")
                print(f"    Author: {content.get('author', 'Unknown')}")
                print(f"    Content: {content.get('content', '')[:50]}...")
                print(f"    Tickers: {data.get('tickers', '[]')}")
                print(f"    Importance: {data.get('importance', 'N/A')}")
    except Exception as e:
        print(f"  Error: {e}")

# Check metrics
print("\n" + "=" * 50)
print("Metrics:")
metrics = r.hgetall("signalscope:metrics")
for key, value in metrics.items():
    print(f"  {key}: {value}")