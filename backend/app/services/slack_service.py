import os
import logging
from typing import Dict, Any, Optional
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

class SlackService:
    """Provides methods to interact with the Slack API using Slack Bolt."""
    
    def __init__(
        self, 
        app_token: Optional[str] = None, 
        bot_token: Optional[str] = None, 
        qa_endpoint: str = "http://localhost:8000/api/qa"
    ):
        """
        Initialize the Slack service.
        
        Args:
            app_token: The Slack app-level token starting with 'xapp-'
            bot_token: The Slack bot token starting with 'xoxb-'
            qa_endpoint: The endpoint to use for QA service
        """
        self.app_token = app_token or os.getenv("SLACK_APP_TOKEN")
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.qa_endpoint = qa_endpoint
        
        # Log token availability for debugging
        logger.info(f"SLACK_APP_TOKEN set: {self.app_token is not None}")
        logger.info(f"SLACK_BOT_TOKEN set: {self.bot_token is not None}")
        
        # Validate token format if available
        is_valid = True
        try:
            if self.app_token:
                logger.info(f"App token prefix: {self.app_token[:8]}...")
                if not self.app_token.startswith("xapp-"):
                    logger.error("App token does not start with 'xapp-'. This is likely invalid.")
                    is_valid = False
                    
            if self.bot_token:
                logger.info(f"Bot token prefix: {self.bot_token[:8]}...")
                if not self.bot_token.startswith("xoxb-"):
                    logger.error("Bot token does not start with 'xoxb-'. This is likely invalid.")
                    is_valid = False
        except Exception as e:
            logger.error(f"Error validating tokens: {str(e)}")
            is_valid = False
        
        if not self.app_token or not self.bot_token or not is_valid:
            logger.warning("Slack tokens not found or invalid. Please set SLACK_APP_TOKEN and SLACK_BOT_TOKEN.")
            self.is_configured = False
            self.app = None
            self.handler = None
            return
            
        # Initialize the Slack Bolt app
        self.app = App(token=self.bot_token)
        self.handler = None
        self.is_configured = True
        logger.info("Slack service successfully configured")
        
        # Register event handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register all the event handlers for the app."""
        if not self.app:
            return
            
        # Handle /ask-bpt slash command
        @self.app.command("/ask-bpt")
        def handle_ask_command(ack, command, client):
            # Acknowledge command received
            ack()
            
            # Get the question from the command text
            question = command["text"].strip()
            user_id = command["user_id"]
            channel_id = command["channel_id"]
            
            if not question:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=("Please include your question after the command. "
                          "For example: `/ask-bpt What were the key points in today's meeting?`")
                )
                return
                
            # Show a loading message
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"Looking up the answer to: *{question}*"
            )
            
            # Call the QA service (this would be implemented to make HTTP request to QA endpoint)
            answer = self.get_answer(question)
            
            # Post the answer
            client.chat_postMessage(
                channel=channel_id,
                text=f"*Question:* {question}\n\n*Answer:* {answer}",
                unfurl_links=False
            )
            
        # Add help command
        @self.app.command("/ask-bpt-help")
        def handle_help_command(ack, command, client):
            ack()
            user_id = command["user_id"]
            channel_id = command["channel_id"]
            
            help_text = (
                "*BPT Meeting Assistant Help*\n\n"
                "*Available Commands:*\n"
                "• `/ask-bpt [question]` - Ask a question about a recent meeting\n"
                "• `/ask-bpt-help` - Show this help message\n\n"
                "*Examples:*\n"
                "• `/ask-bpt What were the key points discussed about NVDA?`\n"
                "• `/ask-bpt What is the stop loss for TSLA?`\n"
                "• `/ask-bpt Summarize today's market outlook`"
            )
            
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=help_text
            )
    
    def get_answer(self, question: str) -> str:
        """
        Get an answer to a question by calling the QA endpoint.
        
        Args:
            question: The question to ask
            
        Returns:
            The answer from the QA service
        """
        import httpx
        import asyncio
        
        # Get or create an event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If we're not in the main thread, create a new loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Define the async function
        async def fetch_answer():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.qa_endpoint,
                        json={"question": question}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return result.get("answer", "Sorry, I couldn't find an answer to that question.")
                    else:
                        logger.error(f"Error from QA service: {response.status_code} - {response.text}")
                        return "Sorry, there was an error processing your question. Please try again later."
                        
            except Exception as e:
                logger.error(f"Error calling QA service: {str(e)}")
                return "Sorry, there was an error connecting to the BPT service. Please try again later."
        
        # Run the async function in the event loop
        try:
            return loop.run_until_complete(fetch_answer())
        except Exception as e:
            logger.error(f"Error in event loop: {str(e)}")
            return "Sorry, there was an error processing your request. Please try again later."
    
    def start(self):
        """Start the Slack app using Socket Mode."""
        if not self.is_configured:
            logger.warning("Slack service is not properly configured. Cannot start.")
            return False
            
        try:
            import threading
            import asyncio
            
            # Create the handler but don't start it directly
            self.handler = SocketModeHandler(self.app, self.app_token)
            
            # Create a separate thread for the handler
            def socket_mode_worker():
                try:
                    # Use connect instead of start to avoid signal handling issues
                    self.handler.connect()
                    logger.info("Slack socket mode connected")
                except Exception as e:
                    logger.error(f"Error in socket mode worker: {str(e)}")
            
            # Start the worker in a background thread
            thread = threading.Thread(target=socket_mode_worker, daemon=True)
            thread.start()
            
            logger.info("Slack bot started successfully in Socket Mode")
            return True
        except Exception as e:
            logger.error(f"Failed to start Slack bot: {str(e)}")
            return False
            
    def stop(self):
        """Stop the Slack app."""
        if self.handler:
            self.handler.close()
            logger.info("Slack bot stopped") 