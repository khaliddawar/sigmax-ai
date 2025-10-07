"""Admin routes for the BPT application"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("bpt-admin")
router = APIRouter(prefix="/admin", tags=["admin"])

class TestEmailRequest(BaseModel):
    recipient_email: str = "khalid.noor@live.com"
    test_subject: str = "BPT Email Configuration Test"
    test_content: str = "This is a test email to verify SMTP configuration."

@router.post("/test-email")
async def test_email(request: TestEmailRequest):
    """Test email configuration by sending a test email"""
    try:
        from app.services.email_router import email_router
        
        if not email_router.is_configured:
            return {
                "success": False,
                "error": "Email service not configured",
                "details": "No email service configured"
            }
        
        # Send test email
        result = await email_router.send_notification_email(
            recipient_email=request.recipient_email,
            notification_type="Configuration Test",
            message=request.test_content
        )
        
        return {
            "success": result.get("success", False),
            "message": "Test email sent" if result.get("success") else "Failed to send test email",
            "details": result
        }
        
    except Exception as e:
        logger.error(f"Error testing email: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/health")
async def admin_health():
    """Admin health check"""
    return {"status": "healthy", "service": "admin"} 