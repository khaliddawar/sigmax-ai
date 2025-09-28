"""
Supabase service for database operations
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from supabase import create_client, Client

from app.settings import settings

logger = structlog.get_logger()


class SupabaseService:
    """Service for Supabase database operations"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize Supabase connection"""
        try:
            if not settings.supabase_url or not settings.supabase_key:
                logger.warning("Supabase credentials not configured")
                return
            
            # Create Supabase client
            self.client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            
            self.initialized = True
            logger.info("Supabase client initialized")
            
        except Exception as e:
            logger.error("Failed to initialize Supabase", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check Supabase connection health"""
        try:
            if not self.client:
                return False
            
            # Try a simple query
            result = self.client.table("messages").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error("Supabase health check failed", error=str(e))
            return False
    
    async def close(self) -> None:
        """Close Supabase connection"""
        # Supabase client doesn't need explicit closing
        logger.info("Supabase service closed")
    
    # Message operations
    async def insert_message(self, message_data: Dict) -> Optional[Dict]:
        """Insert a message into the database"""
        try:
            if not self.client:
                return None
            
            result = self.client.table("messages").insert(message_data).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error("Failed to insert message", error=str(e))
            return None
    
    async def insert_messages_batch(self, messages: List[Dict]) -> int:
        """Insert multiple messages in batch"""
        try:
            if not self.client or not messages:
                return 0
            
            result = self.client.table("messages").insert(messages).execute()
            return len(result.data) if result.data else 0
            
        except Exception as e:
            logger.error("Failed to insert message batch", error=str(e))
            return 0
    
    # Report operations
    async def insert_report(self, report_data: Dict) -> Optional[Dict]:
        """Insert a generated report"""
        try:
            if not self.client:
                return None
            
            result = self.client.table("reports").insert(report_data).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error("Failed to insert report", error=str(e))
            return None
    
    async def get_report_by_id(self, report_id: str) -> Optional[Dict]:
        """Get a report by ID"""
        try:
            if not self.client:
                return None
            
            result = self.client.table("reports").select("*").eq("id", report_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error("Failed to get report", report_id=report_id, error=str(e))
            return None
    
    async def get_latest_reports(
        self,
        report_type: Optional[str] = None,
        limit: int = 10,
        ticker: Optional[str] = None
    ) -> List[Dict]:
        """Get latest reports with optional filters"""
        try:
            if not self.client:
                return []
            
            query = self.client.table("reports").select("*")
            
            if report_type:
                query = query.eq("report_type", report_type)
            
            if ticker:
                query = query.contains("mentioned_tickers", [ticker])
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error("Failed to get latest reports", error=str(e))
            return []
    
    # Batch operations
    async def create_message_batch(self, batch_data: Dict) -> Optional[Dict]:
        """Create a new message batch"""
        try:
            if not self.client:
                return None
            
            result = self.client.table("message_batches").insert(batch_data).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error("Failed to create message batch", error=str(e))
            return None
    
    async def update_batch_status(
        self,
        batch_id: str,
        status: str,
        processed_at: Optional[datetime] = None
    ) -> bool:
        """Update batch processing status"""
        try:
            if not self.client:
                return False
            
            update_data = {"processing_status": status}
            if processed_at:
                update_data["processed_at"] = processed_at.isoformat()
            
            result = self.client.table("message_batches").update(update_data).eq("id", batch_id).execute()
            return bool(result.data)
            
        except Exception as e:
            logger.error("Failed to update batch status", batch_id=batch_id, error=str(e))
            return False
    
    # Subscription operations
    async def get_active_subscriptions(self, report_type: str) -> List[Dict]:
        """Get active report subscriptions"""
        try:
            if not self.client:
                return []
            
            result = (
                self.client.table("report_subscriptions")
                .select("*")
                .eq("report_type", report_type)
                .eq("is_active", True)
                .execute()
            )
            return result.data if result.data else []
            
        except Exception as e:
            logger.error("Failed to get subscriptions", error=str(e))
            return []