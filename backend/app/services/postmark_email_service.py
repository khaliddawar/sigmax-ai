"""
Postmark Email Service
Replaces Gmail SMTP with Postmark API for better deliverability and tracking
Enhanced with card-grid layout for topic-agnostic summaries
"""

import os
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from postmarker.core import PostmarkClient

logger = logging.getLogger("postmark-email")

class PostmarkEmailService:
    """Service for sending emails via Postmark API with enhanced card-grid layout"""
    
    def __init__(self):
        """Initialize the Postmark email service"""
        # Get configuration from environment variables
        self.api_token = os.getenv("POSTMARK_API_TOKEN")
        self.sender_email = os.getenv("POSTMARK_SENDER_EMAIL")
        self.sender_name = os.getenv("POSTMARK_SENDER_NAME", "TubeVibe")
        
        # Postmark template configuration
        self.youtube_summary_template_id = os.getenv("POSTMARK_YOUTUBE_TEMPLATE_ID")  # Main template ID
        self.notification_template_id = os.getenv("POSTMARK_NOTIFICATION_TEMPLATE_ID")  # Notification template
        
        # Initialize Postmark client
        self.client = None
        if self.api_token:
            self.client = PostmarkClient(server_token=self.api_token)
        
        # Check if properly configured
        self.is_configured = bool(self.api_token and self.sender_email)
        
        if self.is_configured:
            logger.info(f"Postmark email service initialized with sender: {self.sender_email}")
            if self.youtube_summary_template_id:
                logger.info(f"Using YouTube summary template ID: {self.youtube_summary_template_id}")
            else:
                logger.warning("POSTMARK_YOUTUBE_TEMPLATE_ID not set - will use hardcoded HTML")
        else:
            logger.warning("Postmark email service not fully configured - emails will not be sent")
    
    def _parse_summary_json(self, summary: str) -> Dict[str, Any]:
        """
        Parse the summary content to extract JSON structure
        Falls back to treating as HTML if not JSON
        """
        try:
            # Try to parse as JSON first
            if summary.strip().startswith('{'):
                return json.loads(summary)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # If not JSON, return a structure that works with the template
        return {
            "legacy_html": summary,
            "key_takeaways": [],
            "hero_numbers": [],
            "step_by_step": [],
            "notable_quotes": []
        }
    
    def _generate_card_grid_html(self, video_data: Dict[str, Any], summary_data: Dict[str, Any]) -> str:
        """
        Generate modern card-grid layout HTML using Tailwind CSS
        """
        video_id = video_data.get('video_id', '')
        video_title = video_data.get('title', 'YouTube Video Summary')
        channel_name = video_data.get('channel_name', 'Unknown Channel')
        duration = video_data.get('duration', 'Unknown')
        transcript_length = video_data.get('transcript_length', 'Unknown')
        
        # Build hero numbers section
        hero_numbers_html = ""
        if summary_data.get("hero_numbers"):
            hero_numbers_html = """
            <div class="mb-8">
                <h2 class="text-xl font-bold text-gray-800 mb-4 flex items-center">
                    <span class="text-2xl mr-2">📊</span>
                    Key Numbers
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            """
            for number_item in summary_data["hero_numbers"]:
                if isinstance(number_item, dict):
                    number = number_item.get("number", "")
                    context = number_item.get("context", "")
                else:
                    number = str(number_item)
                    context = ""
                
                hero_numbers_html += f"""
                    <div class="bg-gradient-to-br from-blue-50 to-indigo-100 p-6 rounded-xl border-l-4 border-blue-500">
                        <div class="text-3xl font-bold text-blue-700 mb-2">{number}</div>
                        <div class="text-sm text-gray-600">{context}</div>
                    </div>
                """
            hero_numbers_html += "</div></div>"
        
        # Build key takeaways section
        key_takeaways_html = ""
        if summary_data.get("key_takeaways"):
            key_takeaways_html = """
            <div class="mb-8">
                <h2 class="text-xl font-bold text-gray-800 mb-4 flex items-center">
                    <span class="text-2xl mr-2">💡</span>
                    Key Takeaways
                </h2>
                <div class="space-y-4">
            """
            for takeaway in summary_data["key_takeaways"]:
                if isinstance(takeaway, dict):
                    title = takeaway.get("title", "")
                    description = takeaway.get("description", "")
                else:
                    title = str(takeaway)
                    description = ""
                
                key_takeaways_html += f"""
                    <div class="bg-white p-6 rounded-xl shadow-md border-l-4 border-green-500">
                        <h3 class="font-semibold text-gray-800 mb-2">{title}</h3>
                        <p class="text-gray-600 text-sm">{description}</p>
                    </div>
                """
            key_takeaways_html += "</div></div>"
        
        # Build step-by-step section with card grid
        step_by_step_html = ""
        if summary_data.get("step_by_step"):
            step_by_step_html = """
            <div class="mb-8">
                <h2 class="text-xl font-bold text-gray-800 mb-4 flex items-center">
                    <span class="text-2xl mr-2">🔄</span>
                    Step by Step
                </h2>
                <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            """
            for i, step_item in enumerate(summary_data["step_by_step"], 1):
                if isinstance(step_item, dict):
                    title = step_item.get("title", f"Step {i}")
                    description = step_item.get("description", "")
                else:
                    title = f"Step {i}"
                    description = str(step_item)
                
                step_by_step_html += f"""
                    <div class="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow">
                        <div class="flex items-center mb-3">
                            <span class="bg-blue-500 text-white text-sm font-bold px-3 py-1 rounded-full mr-3">{i}</span>
                            <h3 class="font-semibold text-lg text-gray-800">{title}</h3>
                        </div>
                        <p class="text-gray-600 text-sm leading-relaxed">{description}</p>
                    </div>
                """
            step_by_step_html += "</div></div>"
        
        # Build notable quotes section
        notable_quotes_html = ""
        if summary_data.get("notable_quotes"):
            notable_quotes_html = """
            <div class="mb-8">
                <h2 class="text-xl font-bold text-gray-800 mb-4 flex items-center">
                    <span class="text-2xl mr-2">💬</span>
                    Notable Quotes
                </h2>
                <div class="space-y-4">
            """
            for quote_item in summary_data["notable_quotes"]:
                if isinstance(quote_item, dict):
                    quote = quote_item.get("quote", "")
                    speaker = quote_item.get("speaker", "")
                    context = quote_item.get("context", "")
                else:
                    quote = str(quote_item)
                    speaker = ""
                    context = ""
                
                notable_quotes_html += f"""
                    <div class="bg-gradient-to-r from-purple-50 to-pink-50 p-6 rounded-xl border-l-4 border-purple-500">
                        <blockquote class="text-gray-700 italic text-lg mb-3">"{quote}"</blockquote>
                        {f'<cite class="text-sm text-purple-600 font-medium">— {speaker}</cite>' if speaker else ''}
                        {f'<p class="text-xs text-gray-500 mt-2">{context}</p>' if context else ''}
                    </div>
                """
            notable_quotes_html += "</div></div>"
        
        # Build legacy HTML fallback
        legacy_html = ""
        if summary_data.get("legacy_html"):
            legacy_html = f"""
            <div class="mb-8">
                <h2 class="text-xl font-bold text-gray-800 mb-4">Summary</h2>
                <div class="bg-white p-6 rounded-xl shadow-md">
                    {summary_data["legacy_html"]}
                </div>
            </div>
            """
        
        # Build CTA section
        cta_html = ""
        if video_id:
            cta_html = f"""
            <div class="bg-gradient-to-r from-blue-50 to-indigo-100 p-8 rounded-xl text-center mb-8">
                <div class="text-4xl mb-4">🤖</div>
                <h3 class="text-xl font-bold text-gray-800 mb-4">Want to dive deeper?</h3>
                <a href="https://bptf.up.railway.app/chat/{video_id}" 
                   class="inline-block bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-8 py-4 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-indigo-700 transition-colors shadow-lg"
                   style="text-decoration: none; color: white;">
                    💬 Chat About This Video
                </a>
                <p class="text-gray-600 text-sm mt-4">Ask questions and get personalized insights from this content</p>
            </div>
            """
        
        # Combine all sections
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{video_title} - Summary</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                /* Email client compatibility styles */
                .shadow-md {{ box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important; }}
                .shadow-lg {{ box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important; }}
                .transition-shadow {{ transition: box-shadow 0.15s ease-in-out !important; }}
                .transition-colors {{ transition: background-color 0.15s ease-in-out, color 0.15s ease-in-out !important; }}
                
                /* Ensure links work in email clients */
                a {{ color: inherit !important; text-decoration: none !important; }}
                a:hover {{ color: inherit !important; }}
                
                /* Grid fallbacks for older email clients */
                @media (max-width: 768px) {{
                    .md\\:grid-cols-2 {{ grid-template-columns: 1fr !important; }}
                    .md\\:grid-cols-3 {{ grid-template-columns: 1fr !important; }}
                    .lg\\:grid-cols-3 {{ grid-template-columns: 1fr !important; }}
                }}
            </style>
        </head>
        <body class="bg-gray-50 font-sans">
            <div class="max-w-4xl mx-auto p-6">
                            <!-- Header -->
            <div class="text-white p-8 rounded-t-xl" style="background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);">
                <h1 class="text-2xl font-bold mb-4" style="color: white;">{video_title}</h1>
                <div class="bg-white bg-opacity-20 rounded-lg p-4 space-y-2 text-sm">
                    <div><strong>Channel:</strong> {channel_name}</div>
                    <div><strong>Duration:</strong> {duration}</div>
                    <div><strong>Transcript Length:</strong> {transcript_length}</div>
                </div>
            </div>
                
                <!-- Content -->
                <div class="bg-white rounded-b-xl p-8 shadow-lg">
                    {hero_numbers_html}
                    {key_takeaways_html}
                    {step_by_step_html}
                    {notable_quotes_html}
                    {legacy_html}
                    {cta_html}
                    
                    <!-- Footer -->
                    <div class="text-center text-gray-500 text-sm mt-8 pt-6 border-t border-gray-200">
                        <p>Generated by TubeVibe Chrome Extension • {datetime.now().strftime('%B %d, %Y')}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content

    async def send_youtube_summary_email(self, 
                                       recipient_email: str, 
                                       video_data: Dict[str, Any], 
                                       summary: str) -> Dict[str, Any]:
        """
        Send a YouTube video summary email with enhanced card-grid layout
        
        Args:
            recipient_email: Email address to send to
            video_data: Dictionary containing video metadata
            summary: JSON summary content or HTML fallback
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Email service not configured",
                "message": "Postmark API token or sender email not set"
            }
        
        try:
            subject = f"📺 {video_data.get('title', 'YouTube Video Summary')}"
            
            # Parse summary data
            summary_data = self._parse_summary_json(summary)
            
            # Generate enhanced HTML content
            html_content = self._generate_card_grid_html(video_data, summary_data)
            
            # Send email via Postmark
            email_data = {
                "From": f"{self.sender_name} <{self.sender_email}>",
                "To": recipient_email,
                "Subject": subject,
                "HtmlBody": html_content
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._send_postmark_email, email_data)
            
            if result:
                logger.info(f"Enhanced summary email sent to {recipient_email}")
                return {
                    "success": True,
                    "message": f"Summary email sent to {recipient_email}",
                    "recipient": recipient_email
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send email via Postmark"
                }
                
        except Exception as e:
            logger.error(f"Error sending YouTube summary email: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _send_postmark_email(self, email_data: Dict[str, str]) -> bool:
        """Send email via Postmark API. If TemplateId/TemplateModel keys are present, use the dedicated
        send_with_template endpoint exposed by postmarker (this avoids unexpected-argument errors)."""
        try:
            if "TemplateId" in email_data:
                # Use Postmark's template send helper (expects CamelCase keys)
                response = self.client.emails.send_with_template(**email_data)
            else:
                response = self.client.emails.send(**email_data)
            return hasattr(response, 'message_id') or (isinstance(response, dict) and 'MessageID' in response)
        except Exception as e:
            logger.error(f"Postmark API error: {str(e)}")
            return False

    # =============================================================================
    # Gmail-Compatible Methods for Drop-in Replacement
    # =============================================================================
    
    async def send_email(self, recipients: List[str], subject: str, body: str, is_html: bool = False) -> bool:
        """
        Basic email sending - Gmail-compatible interface
        
        Args:
            recipients: List of email addresses
            subject: Email subject
            body: Email body content
            is_html: Whether body is HTML (default: False)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured:
            logger.warning("Postmark not configured - cannot send email")
            return False
        
        try:
            # Convert markdown to HTML if needed
            html_body = body
            if not is_html and body and "##" in body:
                try:
                    import markdown
                    html_body = markdown.markdown(body)
                except ImportError:
                    logger.warning("Markdown library not available - sending as plain text")
                    html_body = f"<pre>{body}</pre>"
            elif not is_html:
                html_body = f"<pre>{body}</pre>"
            
            # Send to each recipient
            for recipient in recipients:
                email_data = {
                    "From": f"{self.sender_name} <{self.sender_email}>",
                    "To": recipient,
                    "Subject": subject,
                    "HtmlBody": html_body
                }
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._send_postmark_email, email_data)
                
                if not result:
                    logger.error(f"Failed to send email to {recipient}")
                    return False
            
            logger.info(f"Email sent to {len(recipients)} recipients via Postmark")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email via Postmark: {str(e)}")
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
        Send enhanced meeting summary email using professional Postmark template
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Postmark not configured"
            }
        
        try:
            subject = f"📋 YouTube Summary: {meeting_data.get('title', 'Session Summary')}"
            
            # Use Postmark template if available, otherwise fallback to hardcoded HTML
            if self.youtube_summary_template_id:
                # Prepare template variables for professional template
                template_vars = {
                    "session_title": meeting_data.get('title', 'Session Summary'),
                    "channel_name": metadata.get('channel_name') if metadata else None,
                    "duration_formatted": metadata.get('duration_formatted') if metadata else None,
                    "transcript_length": metadata.get('transcript_length') if metadata else None,
                    "summary": summary,
                    "transcript_id": transcript_id,
                    "action_items": action_items if action_items else None,
                    "trades": trades if trades else None,
                    "session_date": datetime.now().strftime("%B %d, %Y")
                }
                
                email_data = {
                    "From": f"{self.sender_name} <{self.sender_email}>",
                    "To": recipient_email,
                    "TemplateId": int(self.youtube_summary_template_id),
                    "TemplateModel": template_vars
                }
                
                logger.info(f"Sending templated email to {recipient_email} using template {self.youtube_summary_template_id}")
            else:
                # Fallback to hardcoded HTML (legacy)
                html_content = self._generate_quicksheet_html(meeting_data, summary, trades, action_items, metadata)
                
                email_data = {
                    "From": f"{self.sender_name} <{self.sender_email}>",
                    "To": recipient_email,
                    "Subject": subject,
                    "HtmlBody": html_content
                }
                
                logger.info(f"Sending hardcoded HTML email to {recipient_email} (no template configured)")
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._send_postmark_email, email_data)
            
            if result:
                return {
                    "success": True,
                    "message": f"Professional email sent to {recipient_email}",
                    "recipient": recipient_email,
                    "template_used": bool(self.youtube_summary_template_id)
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send via Postmark"
                }
                
        except Exception as e:
            logger.error(f"Error sending quicksheet email: {str(e)}")
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
        Send admin notification email - Gmail-compatible interface
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Postmark not configured"
            }
        
        try:
            subject = f"🔔 TubeVibe Notification: {notification_type}"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">TubeVibe Notification</h2>
                    <p><strong>Type:</strong> {notification_type}</p>
                    <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p>{message}</p>
                    </div>
                    {f'<p><small>Metadata: {metadata}</small></p>' if metadata else ''}
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                    <p style="color: #6b7280; font-size: 14px;">
                        This is an automated notification from TubeVibe.
                    </p>
                </div>
            </body>
            </html>
            """
            
            email_data = {
                "From": f"{self.sender_name} <{self.sender_email}>",
                "To": recipient_email,
                "Subject": subject,
                "HtmlBody": html_content
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._send_postmark_email, email_data)
            
            if result:
                return {
                    "success": True,
                    "message": f"Notification sent to {recipient_email}",
                    "recipient": recipient_email
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send via Postmark"
                }
                
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}")
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
        Send session summary email - Gmail-compatible interface
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Postmark not configured"
            }
        
        try:
            subject = f"📊 Session Summary: {title}"
            
            # Generate session summary HTML
            html_content = self._generate_session_summary_html(title, summary, trades, transcript_id)
            
            # Get subscribers (similar to Gmail service logic)
            # For now, we'll use a placeholder - this should be replaced with actual subscriber logic
            
            email_data = {
                "From": f"{self.sender_name} <{self.sender_email}>",
                "Subject": subject,
                "HtmlBody": html_content
            }
            
            # TODO: Get actual subscribers from database
            # For now, return success without sending
            logger.info(f"Session summary prepared for transcript {transcript_id}")
            
            return {
                "success": True,
                "message": "Session summary email prepared",
                "transcript_id": transcript_id
            }
                
        except Exception as e:
            logger.error(f"Error preparing session summary email: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_quicksheet_html(self, meeting_data: Dict[str, Any], summary: str, 
                                trades: List[Dict[str, Any]], action_items: List[str],
                                metadata: Optional[Dict[str, Any]] = None) -> str:
        """Generate HTML for quicksheet email"""
        trades_html = ""
        if trades:
            trades_html = "<h3>📈 Trades</h3><ul>"
            for trade in trades:
                trades_html += f"""
                <li><strong>{trade.get('symbol', 'N/A')}</strong> - 
                {trade.get('action', 'N/A')} at {trade.get('price', 'N/A')} 
                (Qty: {trade.get('quantity', 'N/A')})</li>
                """
            trades_html += "</ul>"
        
        action_items_html = ""
        if action_items:
            action_items_html = "<h3>✅ Action Items</h3><ul>"
            for item in action_items:
                action_items_html += f"<li>{item}</li>"
            action_items_html += "</ul>"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">📋 {meeting_data.get('title', 'Meeting Summary')}</h1>
                <p><strong>Date:</strong> {meeting_data.get('date', 'N/A')}</p>
                
                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h2>Summary</h2>
                    {summary}
                </div>
                
                {trades_html}
                {action_items_html}
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 14px;">
                    Generated by TubeVibe • summary@tubevibe.app
                </p>
            </div>
        </body>
        </html>
        """

    def _generate_session_summary_html(self, title: str, summary: str, 
                                     trades: List[Dict[str, Any]], transcript_id: str) -> str:
        """Generate HTML for session summary email"""
        trades_html = ""
        if trades:
            trades_html = "<h3>📈 Trading Activity</h3><ul>"
            for trade in trades:
                trades_html += f"""
                <li><strong>{trade.get('symbol', 'N/A')}</strong> - 
                {trade.get('action', 'N/A')} at {trade.get('price', 'N/A')}</li>
                """
            trades_html += "</ul>"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">📊 {title}</h1>
                
                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    {summary}
                </div>
                
                {trades_html}
                
                <p><small>Transcript ID: {transcript_id}</small></p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 14px;">
                    Generated by TubeVibe • summary@tubevibe.app
                </p>
            </div>
        </body>
        </html>
        """

# Initialize service instance
postmark_email_service = PostmarkEmailService() 