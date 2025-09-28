"""
Celery Tasks for Asynchronous Processing
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio
from datetime import datetime, timedelta
import json
from typing import Dict, Any

# Import services
from app.services.batch_processor import BatchProcessor
from app.services.redis_service import RedisService
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService

logger = get_task_logger(__name__)

def run_async(coro):
    """Helper to run async functions in Celery"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@shared_task(name='tasks.process_realtime_batch')
def process_realtime_batch():
    """Process high-priority realtime messages"""
    try:
        logger.info("Processing realtime batch")
        processor = BatchProcessor()
        result = run_async(processor.process_single_batch("realtime"))
        logger.info(f"Realtime batch processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing realtime batch: {e}")
        raise

@shared_task(name='tasks.process_standard_batch')
def process_standard_batch():
    """Process standard priority messages"""
    try:
        logger.info("Processing standard batch")
        processor = BatchProcessor()
        result = run_async(processor.process_single_batch("standard"))
        logger.info(f"Standard batch processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing standard batch: {e}")
        raise

@shared_task(name='tasks.process_archive_batch')
def process_archive_batch():
    """Process low-priority archive messages"""
    try:
        logger.info("Processing archive batch")
        processor = BatchProcessor()
        result = run_async(processor.process_single_batch("archive"))
        logger.info(f"Archive batch processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing archive batch: {e}")
        raise

@shared_task(name='tasks.generate_report')
def generate_report(report_type: str = "hourly", ticker: str = None):
    """Generate an AI report on demand"""
    try:
        logger.info(f"Generating {report_type} report" + (f" for {ticker}" if ticker else ""))
        
        async def _generate():
            # Get messages from database
            supabase = SupabaseService()
            
            # Determine time range based on report type
            if report_type == "hourly":
                since = datetime.utcnow() - timedelta(hours=1)
            elif report_type == "daily":
                since = datetime.utcnow() - timedelta(days=1)
            elif report_type == "weekly":
                since = datetime.utcnow() - timedelta(days=7)
            else:
                since = datetime.utcnow() - timedelta(hours=1)
            
            # Query messages
            query = supabase.client.table("messages") \
                .select("*") \
                .gte("captured_at", since.isoformat() + "Z") \
                .order("captured_at", desc=False)
            
            if ticker:
                query = query.contains("tickers", [ticker])
            
            result = query.execute()
            messages = result.data
            
            if not messages:
                logger.info("No messages found for report generation")
                return {
                    "status": "no_data",
                    "report_type": report_type,
                    "ticker": ticker,
                    "message": "No messages found in the specified time range"
                }
            
            # Generate report using LLM
            llm_service = LLMService()
            report = await llm_service.generate_report(messages, report_type)
            
            # Save report to database
            db_report = {
                "report_type": report_type,
                "report_data": report.get("report_data", {}),
                "key_insights": report.get("key_insights", []),
                "mentioned_tickers": report.get("mentioned_tickers", []),
                "overall_sentiment": report.get("overall_sentiment"),
                "trading_signals": report.get("trading_signals", []),
                "confidence_score": report.get("confidence_score", 0.5),
                "messages_analyzed": len(messages),
                "llm_tokens_used": report.get("llm_tokens_used"),
                "llm_model_used": report.get("llm_model_used"),
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            report_result = supabase.client.table("reports").insert(db_report).execute()
            report_id = report_result.data[0]["id"]
            
            logger.info(f"Report generated and saved: {report_id}")
            
            return {
                "status": "success",
                "report_id": report_id,
                "report_type": report_type,
                "ticker": ticker,
                "messages_analyzed": len(messages),
                "insights": len(report.get("key_insights", [])),
                "signals": len(report.get("trading_signals", []))
            }
        
        result = run_async(_generate())
        return result
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise

@shared_task(name='tasks.generate_daily_report')
def generate_daily_report():
    """Generate daily summary report"""
    return generate_report.apply_async(kwargs={"report_type": "daily"})

@shared_task(name='tasks.process_single_message')
def process_single_message(message: Dict[str, Any]):
    """Process a single high-priority message immediately"""
    try:
        logger.info(f"Processing single message: {message.get('id')}")
        
        async def _process():
            # Check if it needs an alert
            llm_service = LLMService()
            alert = await llm_service.generate_alert(message)
            
            if alert:
                logger.warning(f"ALERT GENERATED: {alert}")
                # TODO: Send notifications (email, webhook, etc.)
            
            return {
                "status": "processed",
                "message_id": message.get('id'),
                "alert_generated": alert is not None
            }
        
        result = run_async(_process())
        return result
        
    except Exception as e:
        logger.error(f"Error processing single message: {e}")
        raise

@shared_task(name='tasks.cleanup_old_messages')
def cleanup_old_messages(days_old: int = 30):
    """Clean up old messages from database"""
    try:
        logger.info(f"Cleaning up messages older than {days_old} days")
        
        async def _cleanup():
            supabase = SupabaseService()
            cutoff = datetime.utcnow() - timedelta(days=days_old)
            
            # Delete old messages
            result = supabase.client.table("messages") \
                .delete() \
                .lt("created_at", cutoff.isoformat() + "Z") \
                .execute()
            
            deleted_count = len(result.data) if result.data else 0
            
            logger.info(f"Deleted {deleted_count} old messages")
            
            return {
                "status": "success",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff.isoformat()
            }
        
        result = run_async(_cleanup())
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning up old messages: {e}")
        raise

@shared_task(name='tasks.analyze_ticker')
def analyze_ticker(ticker: str, hours: int = 24):
    """Analyze a specific ticker over a time period"""
    try:
        logger.info(f"Analyzing ticker {ticker} for last {hours} hours")
        
        async def _analyze():
            supabase = SupabaseService()
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Get messages mentioning this ticker
            result = supabase.client.table("messages") \
                .select("*") \
                .contains("tickers", [ticker]) \
                .gte("captured_at", since.isoformat() + "Z") \
                .order("captured_at", desc=False) \
                .execute()
            
            messages = result.data
            
            if not messages:
                return {
                    "status": "no_data",
                    "ticker": ticker,
                    "message": f"No messages found for {ticker} in the last {hours} hours"
                }
            
            # Analyze with LLM
            llm_service = LLMService()
            analysis = await llm_service.analyze_ticker(ticker, messages)
            
            # Update ticker stats
            stats_result = supabase.client.table("ticker_stats") \
                .upsert({
                    "ticker": ticker,
                    "date": datetime.utcnow().date().isoformat(),
                    "mention_count": len(messages),
                    "bullish_count": sum(1 for m in messages if m.get("sentiment") == "bullish"),
                    "bearish_count": sum(1 for m in messages if m.get("sentiment") == "bearish"),
                    "neutral_count": sum(1 for m in messages if m.get("sentiment") == "neutral"),
                    "average_importance": sum(m.get("importance_score", 5) for m in messages) / len(messages),
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                }) \
                .execute()
            
            return {
                "status": "success",
                "ticker": ticker,
                "messages_analyzed": len(messages),
                "analysis": analysis,
                "time_period_hours": hours
            }
        
        result = run_async(_analyze())
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing ticker {ticker}: {e}")
        raise

@shared_task(name='tasks.health_check')
def health_check():
    """Health check task for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker": "signalscope-celery"
    }