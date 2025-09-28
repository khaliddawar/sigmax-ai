import asyncio
from app.services.redis_service import RedisService

async def check():
    rs = RedisService()
    await rs.initialize()
    
    # Get queue depths
    depths = await rs.get_queue_depths()
    print('Current Queue Depths:')
    for priority, count in depths.items():
        print(f'  {priority}: {count} messages')
    
    # Get total messages
    total = sum(depths.values())
    print(f'\nTotal messages in Redis: {total}')
    
    # Check metrics
    metrics = await rs.get_metrics()
    print('\nMetrics:')
    print(f'  Messages queued total: {metrics.get("messages_queued_total", 0)}')
    print(f'  Messages processed total: {metrics.get("messages_processed_total", 0)}')
    print(f'  Reports generated: {metrics.get("reports_generated_total", 0)}')

if __name__ == "__main__":
    asyncio.run(check())