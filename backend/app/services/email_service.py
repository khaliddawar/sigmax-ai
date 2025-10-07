import os
import logging
import smtplib
import asyncio
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("bpt-email")

class EmailService:
    """Service for sending emails with enhanced card-grid layout support"""
    
    def __init__(self):
        """Initialize the email service"""
        # Get configuration from environment variables
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL")
        
        # Initialize template environment
        self._initialize_template_env()
        
        # Check if properly configured
        self.is_configured = (
            self.smtp_server and 
            self.smtp_port and 
            self.smtp_username and 
            self.smtp_password and 
            self.sender_email
        )
        
        if self.is_configured:
            logger.info(f"Email service initialized with {self.smtp_server}:{self.smtp_port}")
        else:
            logger.warning("Email service not fully configured - emails will not be sent")
            missing = []
            if not self.smtp_server: missing.append("SMTP_SERVER")
            if not self.smtp_port: missing.append("SMTP_PORT")
            if not self.smtp_username: missing.append("SMTP_USERNAME")
            if not self.smtp_password: missing.append("SMTP_PASSWORD")
            if not self.sender_email: missing.append("SENDER_EMAIL")
            logger.warning(f"Missing email configuration: {', '.join(missing)}")
    
    def _initialize_template_env(self):
        """Initialize the Jinja2 template environment - NO FALLBACKS"""
        # Set up template directory
        templates_path = Path(__file__).parent.parent / "templates"
        templates_path.mkdir(exist_ok=True)
        
        # Create default template if it doesn't exist
        self._initialize_default_template(templates_path)
        
        # Initialize Jinja2 environment - fail explicitly if this doesn't work
        self.template_env = Environment(
            loader=FileSystemLoader(templates_path),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        logger.info(f"Template environment initialized with templates from: {templates_path}")
    
    async def send_email(self, recipients: List[str], subject: str, body: str, is_html: bool = False) -> bool:
        """
        Send an email to recipients
        
        Args:
            recipients: List of email addresses to send to
            subject: Email subject
            body: Email body
            is_html: Whether the body is HTML
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - email not sent")
            return False
            
        if not recipients:
            logger.warning("No recipients provided - email not sent")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"TubeVibe <{self.sender_email}>"
            msg["To"] = ", ".join(recipients)
            
            # Convert markdown to HTML if needed
            if not is_html and body and "##" in body:
                try:
                    import markdown
                    html_body = markdown.markdown(body)
                    msg.attach(MIMEText(body, "plain"))
                    msg.attach(MIMEText(html_body, "html"))
                except ImportError:
                    logger.warning("Markdown library not available - sending plain text only")
                    msg.attach(MIMEText(body, "plain"))
            else:
                # Attach body in appropriate format
                if is_html:
                    msg.attach(MIMEText(body, "html"))
                else:
                    msg.attach(MIMEText(body, "plain"))
            
            # Send via event loop to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_mail, recipients, msg.as_string())
            
        except Exception as e:
            logger.error(f"Error preparing email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _clean_summary_content(self, summary: str) -> str:
        """Clean up summary content and add inline styles for email clients."""
        if not summary:
            return summary
            
        # Remove markdown code block indicators
        import re
        
        # Remove ```html at the beginning
        summary = re.sub(r'^```html\s*', '', summary, flags=re.IGNORECASE)
        
        # Remove ``` at the end
        summary = re.sub(r'\s*```\s*$', '', summary)
        
        # Remove any other code block indicators
        summary = re.sub(r'```[a-zA-Z]*\s*', '', summary)
        
        # Add inline styles to make content more email-client friendly
        
        # Style h2 with session-summary class
        summary = re.sub(
            r'<h2 class="session-summary"([^>]*)>',
            r'<h2 class="session-summary"\1 style="color: #1e40af; font-size: 20px; margin: 20px 0 15px 0; font-weight: 600; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">',
            summary
        )
        
        # Style h3 with section-heading class
        summary = re.sub(
            r'<h3 class="section-heading"([^>]*)>',
            r'<h3 class="section-heading"\1 style="color: #1e40af; font-size: 16px; margin: 15px 0 10px 0; font-weight: 600; border-bottom: 1px solid #e5e7eb; padding-bottom: 5px;">',
            summary
        )
        
        # Style regular h3 headings (fallback)
        summary = re.sub(
            r'<h3(?![^>]*class="section-heading")([^>]*)>',
            r'<h3\1 style="color: #1e40af; font-size: 16px; margin: 15px 0 10px 0; font-weight: 600; border-bottom: 1px solid #e5e7eb; padding-bottom: 5px;">',
            summary
        )
        
        # Style paragraphs with market-insight class
        summary = re.sub(
            r'<p class="market-insight"([^>]*)>',
            r'<p class="market-insight"\1 style="background: #fff; padding: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 15px; border-left: 3px solid #1e40af; line-height: 1.6;">',
            summary
        )
        
        # Style regular paragraphs (but not those with specific classes)
        summary = re.sub(
            r'<p(?![^>]*class="market-insight")([^>]*)>',
            r'<p\1 style="margin: 10px 0; line-height: 1.6; color: #333;">',
            summary
        )
        
        # Style strong tags
        summary = re.sub(
            r'<strong([^>]*)>',
            r'<strong\1 style="color: #1e40af; font-weight: 600;">',
            summary
        )
        
        # Style em/italic tags
        summary = re.sub(
            r'<em([^>]*)>',
            r'<em\1 style="color: #6b7280; font-style: italic;">',
            summary
        )
        
        # Style ul lists
        summary = re.sub(
            r'<ul([^>]*)>',
            r'<ul\1 style="margin: 10px 0; padding-left: 20px;">',
            summary
        )
        
        # Style li items
        summary = re.sub(
            r'<li([^>]*)>',
            r'<li\1 style="margin-bottom: 5px; line-height: 1.6;">',
            summary
        )
        
        # Clean up excessive whitespace
        summary = re.sub(r'\n\s*\n\s*\n+', '\n\n', summary)
        
        return summary.strip()

    def _send_mail(self, recipients: List[str], message: str) -> bool:
        """
        Actually send the email via SMTP (runs in executor)
        
        Args:
            recipients: List of email addresses
            message: Formatted email message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                # Start TLS encryption
                server.starttls()
                
                # Login
                server.login(self.smtp_username, self.smtp_password)
                
                # Send email
                server.sendmail(self.sender_email, recipients, message)
                
            logger.info(f"Email sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _initialize_default_template(self, templates_path: Path):
        """Create the default email template if it doesn't exist"""
        template_path = templates_path / "email_quicksheet.html"
        
        if not template_path.exists():
            logger.info("Creating default email template")
            default_template = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ session_title }} - Quick-Sheet</title>
  <style>
    body { 
      font-family: Arial, Helvetica, sans-serif; 
      line-height: 1.6; 
      color: #333; 
      max-width: 700px; 
      margin: 0 auto; 
      background-color: #f9fafb;
    }
    .container {
      background-color: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
      margin: 20px auto;
    }
    .header { 
      background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
      background-color: #1e40af;
      color: white;
      padding: 25px; 
    }
    .header h1 {
      margin: 0 0 5px 0;
      font-size: 22px;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: white !important;
    }
    .header p {
      margin: 0;
      font-size: 14px;
      opacity: 0.9;
      color: white !important;
    }
    .content {
      padding: 25px;
    }
    
    /* Enhanced styles for rich summary content */
    .summary h3 {
      color: #1e40af !important;
      font-size: 16px !important;
      margin: 15px 0 10px 0 !important;
      font-weight: 600 !important;
      border-bottom: 1px solid #e5e7eb !important;
      padding-bottom: 5px !important;
    }
    .summary p {
      margin: 10px 0 !important;
      line-height: 1.6 !important;
      color: #333 !important;
    }
    .summary p.market-insight {
      background: #fff !important;
      padding: 15px !important;
      border-radius: 5px !important;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
      margin-bottom: 15px !important;
      border-left: 3px solid #1e40af !important;
    }
    .summary ul {
      margin: 10px 0 !important;
      padding-left: 20px !important;
    }
    .summary li {
      margin-bottom: 5px !important;
      line-height: 1.6 !important;
    }
    .summary strong {
      color: #1e40af !important;
      font-weight: 600 !important;
    }
    
    /* Trades section */
    .trades { 
      padding: 20px 0; 
      border-top: 1px solid #e5e7eb;
    }
    .trades h3 {
      color: #1e40af;
      font-size: 16px;
      margin-bottom: 12px;
      font-weight: 600;
    }
    table { 
      width: 100%; 
      border-collapse: collapse; 
      margin: 12px 0;
      font-size: 13px;
    }
    th, td { 
      padding: 8px; 
      text-align: left; 
      border-bottom: 1px solid #e5e7eb; 
    }
    th { 
      background-color: #f3f4f6;
      font-weight: 600;
    }
    
    /* Footer */
    .footer { 
      background-color: #f9fafb;
      padding: 15px 25px; 
      font-size: 12px; 
      color: #6b7280; 
      text-align: center;
      border-top: 1px solid #e5e7eb;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header" style="background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%); background-color: #1e40af; color: white; padding: 25px;">
      <h1 style="margin: 0 0 15px 0; font-size: 22px; font-weight: 600; letter-spacing: -0.02em; color: white !important;">{{ session_title }}</h1>
      
      <div style="font-size: 14px; line-height: 1.6; margin-top: 15px;">
        {% if channel_name %}
        <div style="margin-bottom: 8px;">
          <strong style="color: #ffffff;">Channel:</strong> 
          <span style="color: #e2e8f0;">{{ channel_name }}</span>
        </div>
        {% endif %}
        {% if duration_formatted %}
        <div style="margin-bottom: 8px;">
          <strong style="color: #ffffff;">Duration:</strong> 
          <span style="color: #e2e8f0;">{{ duration_formatted }}</span>
        </div>
        {% endif %}
        {% if transcript_length %}
        <div style="margin-bottom: 0;">
          <strong style="color: #ffffff;">Transcript Length:</strong> 
          <span style="color: #e2e8f0;">{{ transcript_length }}</span>
        </div>
        {% endif %}
      </div>
    </div>
    
    <div class="content">
      <div class="summary">
        <h3 style="color: #1e40af; font-size: 18px; margin-bottom: 15px; font-weight: 600;">Session Summary</h3>
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          {{ summary|safe }}
        </div>
      </div>
      

    </div>
    
    <div class="footer">
      <p>Generated by TubeVibe Transcription and Analysis System on {{ session_date }}</p>
    </div>
  </div>
</body>
</html>"""
            with open(template_path, "w") as f:
                f.write(default_template)
        
    async def send_quicksheet_email(self, 
                                  recipient_email: str, 
                                  session_data: Dict[str, Any], 
                                  summary: str, 
                                  trades: List[Dict[str, Any]], 
                                  action_items: List[Dict[str, Any]] = None,
                                  transcript_id: str = None,
                                  app_url: str = None,
                                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a Quick-Sheet email with session summary and trades
        
        Args:
            recipient_email: Email address of the recipient
            session_data: Dictionary with session title and date
            summary: Session summary text
            trades: List of trade dictionaries
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured:
            logger.warning("Email service not configured - email not sent")
            return {
                "success": False,
                "error": "Email service not configured"
            }
        
        try:
            # Format the date to a more readable format
            formatted_date = session_data.get("date", "")
            if formatted_date:
                try:
                    from datetime import datetime
                    # Parse ISO format date and convert to readable format
                    if "T" in formatted_date:  # ISO format
                        dt = datetime.fromisoformat(formatted_date.replace('Z', '+00:00'))
                        formatted_date = dt.strftime("%B %d, %Y")
                    # If it's already in a simple format, keep it
                except Exception as date_error:
                    logger.warning(f"Could not format date '{formatted_date}': {date_error}")
                    # Keep original date if formatting fails
            
            # Clean up summary content before rendering
            cleaned_summary = self._clean_summary_content(summary)
            
            # Extract video metadata for header display
            video_metadata = metadata or {}
            channel_name = video_metadata.get("channel_name", "")
            duration = video_metadata.get("duration", 0)
            
            # Format duration from seconds to readable format
            duration_formatted = ""
            if duration and isinstance(duration, (int, float)) and duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                if minutes > 0:
                    duration_formatted = f"{minutes}:{seconds:02d}"
                else:
                    duration_formatted = f"0:{seconds:02d}"
            
            # Get pre-calculated transcript length from metadata
            transcript_length = video_metadata.get("transcript_length", "")

            # Render email template - NO FALLBACKS, fail explicitly if template issues occur
            template = self.template_env.get_template("email_quicksheet.html")
            html_content = template.render(
                session_title=session_data.get("title", "Trading Session"),
                session_date=formatted_date,
                summary=cleaned_summary,
                trades=trades,
                action_items=action_items or [],
                transcript_id=transcript_id,
                app_url=app_url or os.getenv("FRONTEND_APP_URL", "https://your-bpt-app.railway.app"),
                # Video metadata for header
                channel_name=channel_name,
                duration_formatted=duration_formatted,
                transcript_length=transcript_length
            )
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = session_data.get('title', 'Trading Session')
            message["From"] = f"TubeVibe <{self.sender_email}>"
            message["To"] = recipient_email
            
            # Create a plain text version (simplified)
            plain_text = f"""
Session: {session_data.get('title', 'Trading Session')}
Date: {formatted_date}

SUMMARY:
{summary}

TRADES DISCUSSED:
"""
            if trades:
                for trade in trades:
                    plain_text += f"\n- {trade.get('ticker', '')}: {trade.get('direction', '')} at {trade.get('entry_price', '-')}"
            else:
                plain_text += "\nNo specific trades were discussed in this session."
            
            # Attach parts
            message.attach(MIMEText(plain_text, "plain"))
            message.attach(MIMEText(html_content, "html"))
            
            # Use asyncio to run SMTP in a thread pool
            loop = asyncio.get_event_loop()
            send_result = await loop.run_in_executor(
                None, self._send_mail, [recipient_email], message.as_string()
            )
            
            # Return properly formatted result
            return {
                "success": send_result,
                "recipient": recipient_email,
                "subject": session_data.get('title', 'Trading Session')
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_notification_email(self, 
                                   recipient_email: str, 
                                   subject: str, 
                                   content: str) -> Dict[str, Any]:
        """
        Send a simple notification email
        
        Args:
            recipient_email: Email address of the recipient
            subject: Email subject
            content: Email content (can be HTML)
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured:
            logger.warning("Email service not configured - email not sent")
            return {
                "success": False,
                "error": "Email service not configured"
            }
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"TubeVibe <{self.sender_email}>"
            message["To"] = recipient_email
            
            # Check if content is HTML
            is_html = bool(content.strip().startswith("<") and "html" in content.lower())
            
            # Create plain text version if content is HTML
            if is_html:
                # Very basic HTML to text conversion
                plain_text = content.replace("<br>", "\n").replace("<p>", "\n").replace("</p>", "\n")
                plain_text = ' '.join(plain_text.split())  # Normalize whitespace
                message.attach(MIMEText(plain_text, "plain"))
                message.attach(MIMEText(content, "html"))
            else:
                message.attach(MIMEText(content, "plain"))
            
            # Use asyncio to run SMTP in a thread pool
            loop = asyncio.get_event_loop()
            send_result = await loop.run_in_executor(
                None, self._send_mail, [recipient_email], message.as_string()
            )
            
            # Return properly formatted result
            return {
                "success": send_result,
                "recipient": recipient_email,
                "subject": subject
            }
            
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_session_summary_email(self, 
                                      transcript_id: str,
                                      session_title: str, 
                                      summary: str, 
                                      trades: List[Dict[str, Any]], 
                                      action_items: List[Dict[str, Any]] = None,
                                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a session summary email - wrapper around send_quicksheet_email
        
        Args:
            transcript_id: ID of the transcript
            session_title: Title of the session
            summary: Session summary text
            trades: List of trade dictionaries
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Get subscribers from the database
            from app.services.supabase_client import SupabaseService
            supabase_service = SupabaseService()
            
            subscribers_result = await supabase_service.get_subscribers()
            if not subscribers_result.get("success") or not subscribers_result.get("subscribers"):
                logger.warning("No subscribers found for session summary email")
                return {
                    "success": False,
                    "error": "No subscribers found"
                }
            
            subscribers = subscribers_result.get("subscribers", [])
            
            # Send to each subscriber using the fancy quicksheet template
            results = []
            for subscriber in subscribers:
                recipient_email = subscriber.get("email")
                if not recipient_email:
                    continue
                    
                # Use current date for session data
                session_data = {
                    "title": session_title,
                    "date": datetime.now().strftime("%B %d, %Y")
                }
                
                # Send the formatted email
                result = await self.send_quicksheet_email(
                    recipient_email=recipient_email,
                    session_data=session_data,
                    summary=summary,
                    trades=trades,
                    action_items=action_items,
                    transcript_id=transcript_id,
                    metadata=metadata
                )
                
                results.append(result)
            
            # Check if any emails were sent successfully
            successful_sends = [r for r in results if r.get("success")]
            
            if successful_sends:
                logger.info(f"Session summary email sent to {len(successful_sends)} recipients")
                return {
                    "success": True,
                    "recipients_count": len(successful_sends),
                    "total_attempted": len(results)
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send to any recipients",
                    "results": results
                }
                
        except Exception as e:
            logger.error(f"Error sending session summary email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

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
        duration = video_data.get('duration_formatted', video_data.get('duration', 'Unknown'))
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
                <div class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white p-8 rounded-t-xl">
                    <h1 class="text-2xl font-bold mb-4">{video_title}</h1>
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
                "message": "SMTP configuration not complete"
            }
        
        try:
            subject = f"📺 {video_data.get('title', 'YouTube Video Summary')}"
            
            # Parse summary data
            summary_data = self._parse_summary_json(summary)
            
            # Generate enhanced HTML content
            html_content = self._generate_card_grid_html(video_data, summary_data)
            
            # Create plain text version (simplified)
            plain_text = f"""
{video_data.get('title', 'YouTube Video Summary')}

Channel: {video_data.get('channel_name', 'Unknown Channel')}
Duration: {video_data.get('duration', 'Unknown')}

SUMMARY:
{summary if isinstance(summary, str) and not summary.strip().startswith('{') else 'Enhanced summary available in HTML version'}

Generated by TubeVibe Chrome Extension
            """
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"TubeVibe <{self.sender_email}>"
            message["To"] = recipient_email
            
            # Attach parts
            message.attach(MIMEText(plain_text, "plain"))
            message.attach(MIMEText(html_content, "html"))
            
            # Use asyncio to run SMTP in a thread pool
            loop = asyncio.get_event_loop()
            send_result = await loop.run_in_executor(
                None, self._send_mail, [recipient_email], message.as_string()
            )
            
            if send_result:
                logger.info(f"Enhanced YouTube summary email sent to {recipient_email}")
                return {
                    "success": True,
                    "message": f"Summary email sent to {recipient_email}",
                    "recipient": recipient_email
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send email via SMTP"
                }
                
        except Exception as e:
            logger.error(f"Error sending YouTube summary email: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Initialize service instance
email_service = EmailService() 