"""
Email Service Router
Provides safe migration from Gmail SMTP to Postmark with feature flag control
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("email-router")

class EmailRouter:
    """
    Router that switches between Gmail SMTP and Postmark based on configuration
    Provides backwards-compatible interface for all email methods
    """
    
    def __init__(self):
        """Initialize the email router with both services"""
        # Import services
        from .email_service import email_service as gmail_service
        from .postmark_email_service import postmark_email_service
        
        self.gmail_service = gmail_service
        self.postmark_service = postmark_email_service
        
        # Check which service to use
        self.use_postmark = os.getenv("USE_POSTMARK_EMAIL", "false").lower() == "true"
        
        # Determine active service
        if self.use_postmark and self.postmark_service.is_configured:
            self.active_service = self.postmark_service
            self.service_name = "Postmark"
            logger.info("Email router initialized with Postmark as primary service")
        elif self.gmail_service.is_configured:
            self.active_service = self.gmail_service
            self.service_name = "Gmail SMTP"
            logger.info("Email router initialized with Gmail SMTP as primary service")
        elif self.postmark_service.is_configured:
            # Fallback to Postmark if Gmail not configured
            self.active_service = self.postmark_service
            self.service_name = "Postmark (fallback)"
            logger.warning("Gmail SMTP not configured, using Postmark as fallback")
        else:
            self.active_service = None
            self.service_name = "None"
            logger.error("No email service configured!")
    
    @property
    def is_configured(self) -> bool:
        """Check if any email service is configured"""
        return self.active_service is not None and self.active_service.is_configured
    
    @property
    def sender_email(self) -> Optional[str]:
        """Get sender email from active service"""
        return self.active_service.sender_email if self.active_service else None
    
    async def send_email(self, recipients: List[str], subject: str, body: str, is_html: bool = False) -> bool:
        """
        Send basic email via active service
        """
        if not self.is_configured:
            logger.error("No email service configured")
            return False
        
        try:
            logger.info(f"Sending email via {self.service_name} to {len(recipients)} recipients")
            return await self.active_service.send_email(recipients, subject, body, is_html)
        except Exception as e:
            logger.error(f"Error sending email via {self.service_name}: {str(e)}")
            return False
    
    async def send_quicksheet_email(self,
                                  recipient_email: str,
                                  meeting_data: Dict[str, Any],
                                  summary: str,
                                  trades: List[Dict[str, Any]],
                                  action_items: List[str],
                                  transcript_id: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send quicksheet email via active service
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "No email service configured"
            }
        
        try:
            logger.info(f"Sending quicksheet email via {self.service_name} to {recipient_email}")
            return await self.active_service.send_quicksheet_email(
                recipient_email, meeting_data, summary, trades, action_items, transcript_id, metadata
            )
        except Exception as e:
            logger.error(f"Error sending quicksheet email via {self.service_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_notification_email(self,
                                    recipient_email: str,
                                    notification_type: str,
                                    message: str,
                                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification email via active service
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "No email service configured"
            }
        
        try:
            logger.info(f"Sending notification email via {self.service_name} to {recipient_email}")
            return await self.active_service.send_notification_email(
                recipient_email, notification_type, message, metadata
            )
        except Exception as e:
            logger.error(f"Error sending notification email via {self.service_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_session_summary_email(self,
                                       transcript_id: str,
                                       title: str,
                                       summary: str,
                                       trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send session summary email via active service
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "No email service configured"
            }
        
        try:
            logger.info(f"Sending session summary email via {self.service_name} for transcript {transcript_id}")
            return await self.active_service.send_session_summary_email(
                transcript_id, title, summary, trades
            )
        except Exception as e:
            logger.error(f"Error sending session summary email via {self.service_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_youtube_summary_email(self,
                                       recipient_email: str,
                                       video_data: Dict[str, Any],
                                       summary: str) -> Dict[str, Any]:
        """
        Send YouTube summary email via active service
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "No email service configured"
            }
        
        try:
            logger.info(f"Sending YouTube summary email via {self.service_name} to {recipient_email}")
            return await self.active_service.send_youtube_summary_email(
                recipient_email, video_data, summary
            )
        except Exception as e:
            logger.error(f"Error sending YouTube summary email via {self.service_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status information about email services
        """
        return {
            "active_service": self.service_name,
            "use_postmark_flag": self.use_postmark,
            "gmail_configured": self.gmail_service.is_configured,
            "postmark_configured": self.postmark_service.is_configured,
            "is_configured": self.is_configured
        }

# Initialize router instance for global use
email_router = EmailRouter()