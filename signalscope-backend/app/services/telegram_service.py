"""
Telegram Bot Service for SignalScope Trading Alerts
"""
import os
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from dotenv import load_dotenv
import structlog

load_dotenv()

logger = structlog.get_logger()

class TelegramService:
    """Service for sending trading alerts via Telegram"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured")
            self.enabled = False
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if self.enabled:
            logger.info(f"Telegram service initialized for chat {self.chat_id}")
    
    async def send_message(self, text: str, parse_mode: str = "HTML", disable_notification: bool = False) -> bool:
        """
        Send a message to Telegram
        
        Args:
            text: Message text (supports HTML formatting)
            parse_mode: 'HTML' or 'Markdown'
            disable_notification: Silent notification if True
        
        Returns:
            Success status
        """
        if not self.enabled:
            logger.debug("Telegram disabled, skipping message")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification,
                "disable_web_page_preview": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Telegram message sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Telegram API error: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_alert_report(self, report: Dict[str, Any]) -> bool:
        """
        Send an alert report for high-priority trading signals
        
        Args:
            report: Report dictionary with trading signals
        
        Returns:
            Success status
        """
        try:
            # Format alert message
            message = self._format_alert_message(report)
            
            # Send with high priority (with notification)
            return await self.send_message(message, disable_notification=False)
            
        except Exception as e:
            logger.error(f"Failed to send alert report: {e}")
            return False
    
    async def send_hourly_report(self, report: Dict[str, Any]) -> bool:
        """
        Send an hourly summary report
        
        Args:
            report: Report dictionary with hourly analysis
        
        Returns:
            Success status
        """
        try:
            # Format hourly summary
            message = self._format_hourly_message(report)
            
            # Send silently (no notification)
            return await self.send_message(message, disable_notification=True)
            
        except Exception as e:
            logger.error(f"Failed to send hourly report: {e}")
            return False
    
    async def send_daily_report(self, report: Dict[str, Any]) -> bool:
        """
        Send a daily summary report
        
        Args:
            report: Report dictionary with daily analysis
        
        Returns:
            Success status
        """
        try:
            # Format daily summary
            message = self._format_daily_message(report)
            
            # Send with notification
            return await self.send_message(message, disable_notification=False)
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            return False
    
    async def send_trade_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Send an immediate trading signal
        
        Args:
            signal: Trading signal dictionary
        
        Returns:
            Success status
        """
        try:
            # Format trading signal
            message = self._format_signal_message(signal)
            
            # Always send with notification for immediate signals
            return await self.send_message(message, disable_notification=False)
            
        except Exception as e:
            logger.error(f"Failed to send trade signal: {e}")
            return False
    
    def _format_alert_message(self, report: Dict[str, Any]) -> str:
        """Format an alert report for Telegram"""
        report_data = report.get("report_data", {})
        
        # Determine urgency emoji
        confidence = report.get("confidence_score", 0)
        if confidence >= 0.8:
            emoji = "🚨"
        elif confidence >= 0.6:
            emoji = "⚠️"
        else:
            emoji = "📊"
        
        message = f"<b>{emoji} TRADING ALERT</b>\n"
        message += f"<i>{datetime.now().strftime('%H:%M UTC')}</i>\n"
        message += "━━━━━━━━━━━━━━━━\n\n"
        
        # Summary
        if report_data.get("summary"):
            message += f"<b>Summary:</b>\n{report_data['summary']}\n\n"
        
        # Trading Signals
        signals = report_data.get("trading_signals", [])
        if signals:
            message += "<b>🎯 TRADING SIGNALS:</b>\n"
            for signal in signals[:3]:  # Top 3 signals
                action = signal.get("action", "")
                ticker = signal.get("ticker", "")
                strength = signal.get("strength", "")
                reasoning = signal.get("reasoning", "")
                
                # Action emoji
                action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(action, "⚪")
                
                message += f"\n{action_emoji} <b>{action} ${ticker}</b> ({strength})\n"
                message += f"   └ {reasoning[:100]}\n"
        
        # Key Insights
        insights = report_data.get("key_insights", [])
        if insights:
            message += "\n<b>💡 Key Insights:</b>\n"
            for i, insight in enumerate(insights[:3], 1):
                message += f"{i}. {insight[:150]}\n"
        
        # Market Sentiment
        sentiment = report_data.get("market_sentiment", {})
        if sentiment:
            overall = sentiment.get("overall", "neutral")
            score = sentiment.get("score", 0)
            
            sentiment_emoji = {
                "bullish": "📈", "bearish": "📉", 
                "neutral": "➡️", "mixed": "🔄"
            }.get(overall, "❓")
            
            message += f"\n<b>Market Sentiment:</b> {sentiment_emoji} {overall.upper()} ({score:+.2f})\n"
        
        # Statistics
        message += f"\n<i>Messages analyzed: {report.get('messages_analyzed', 0)}</i>\n"
        message += f"<i>Confidence: {confidence:.0%}</i>"
        
        return message
    
    def _format_hourly_message(self, report: Dict[str, Any]) -> str:
        """Format an hourly summary for Telegram"""
        report_data = report.get("report_data", {})
        
        message = "<b>📊 TRADING DIGEST</b>\n"
        message += f"<i>{datetime.now().strftime('%H:%M UTC')}</i>\n"
        message += "━━━━━━━━━━━━━━━━\n\n"
        
        # Actionables
        actionables = report_data.get("actionables", [])
        if actionables:
            message += "<b>✅ ACTIONABLES:</b>\n"
            for item in actionables[:5]:  # Top 5
                ticker = item.get("ticker", "")
                direction = item.get("direction", "")
                entry = item.get("entry", "")
                stop = item.get("stop", "")
                author = item.get("author", "Unknown")
                time_local = item.get("time_local", "")
                
                emoji = {"long": "🟢", "short": "🔴", "exit": "🚪", "hold": "🟡"}.get(direction, "❓")
                message += f"{emoji} <b>${ticker}</b> - {direction}"
                if entry and entry != "null":
                    message += f" @ {entry}"
                if stop and stop != "null":
                    message += f" (stop: {stop})"
                message += f"\n   <i>by @{author} at {time_local}</i>\n"
            message += "\n"
        
        # Watchlist highlights
        watchlist = report_data.get("watchlist", {})
        breakouts = watchlist.get("breakouts", [])
        if breakouts:
            message += "<b>👀 WATCHLIST (Breakout candidates):</b>\n"
            for item in breakouts[:3]:  # Top 3
                ticker = item.get("ticker", "")
                notes = item.get("notes", "")
                author = item.get("author", "")
                message += f"• <b>${ticker}</b>"
                if notes:
                    message += f" - {notes[:50]}"
                if author:
                    message += f" (@{author})"
                message += "\n"
            message += "\n"
        
        # Summary
        if report_data.get("summary"):
            message += f"<i>{report_data['summary'][:200]}</i>\n\n"
        
        # Stats
        message += f"<i>Messages analyzed: {report.get('messages_analyzed', 0)}</i>\n"
        message += f"<i>Tickers mentioned: {len(report.get('mentioned_tickers', []))}</i>"
        
        return message
    
    def _format_daily_message(self, report: Dict[str, Any]) -> str:
        """Format a daily summary for Telegram"""
        report_data = report.get("report_data", {})
        
        message = "<b>📈 DAILY TRADING REPORT</b>\n"
        message += f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</i>\n"
        message += "━━━━━━━━━━━━━━━━\n\n"
        
        # Executive Summary
        if report_data.get("summary"):
            message += f"<b>Executive Summary:</b>\n{report_data['summary']}\n\n"
        
        # Top Opportunities
        opportunities = report_data.get("opportunities", [])
        if opportunities:
            message += "<b>🎯 Top Opportunities:</b>\n"
            for opp in opportunities[:3]:
                message += f"• {opp}\n"
            message += "\n"
        
        # Risk Warnings
        warnings = report_data.get("risk_warnings", [])
        if warnings:
            message += "<b>⚠️ Risk Warnings:</b>\n"
            for warning in warnings[:3]:
                message += f"• {warning}\n"
            message += "\n"
        
        # Statistics
        message += "<b>📊 Daily Statistics:</b>\n"
        message += f"Messages Analyzed: {report.get('messages_analyzed', 0)}\n"
        message += f"Tickers Tracked: {len(report.get('mentioned_tickers', []))}\n"
        message += f"Confidence Score: {report.get('confidence_score', 0):.0%}\n"
        
        return message
    
    def _format_signal_message(self, signal: Dict[str, Any]) -> str:
        """Format an immediate trading signal for Telegram"""
        action = signal.get("action", "")
        ticker = signal.get("ticker", "")
        
        # Determine emoji based on action
        if action == "BUY":
            emoji = "🟢🚀"
        elif action == "SELL":
            emoji = "🔴⚠️"
        else:
            emoji = "🟡"
        
        message = f"<b>{emoji} IMMEDIATE SIGNAL</b>\n\n"
        message += f"<b>{action} ${ticker}</b>\n"
        
        if signal.get("entry_price"):
            message += f"Entry: ${signal['entry_price']}\n"
        
        if signal.get("target_price"):
            message += f"Target: ${signal['target_price']}\n"
        
        if signal.get("stop_loss"):
            message += f"Stop Loss: ${signal['stop_loss']}\n"
        
        if signal.get("reasoning"):
            message += f"\nReasoning: {signal['reasoning']}\n"
        
        if signal.get("confidence"):
            message += f"\nConfidence: {signal['confidence']:.0%}"
        
        message += f"\n\n<i>Time: {datetime.now().strftime('%H:%M:%S UTC')}</i>"
        
        return message
    
    async def send_photo(self, photo_data: bytes, caption: str = "", filename: str = "chart.png") -> bool:
        """
        Send a photo to Telegram
        
        Args:
            photo_data: Image data as bytes
            caption: Photo caption
            filename: Filename for the photo
        
        Returns:
            Success status
        """
        if not self.enabled:
            logger.debug("Telegram disabled, skipping photo")
            return False
        
        try:
            url = f"{self.base_url}/sendPhoto"
            
            # Create form data
            data = aiohttp.FormData()
            data.add_field('chat_id', self.chat_id)
            data.add_field('caption', caption)
            data.add_field('photo', photo_data, filename=filename, content_type='image/png')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        logger.info("Telegram photo sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Telegram photo API error: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Telegram photo: {e}")
            return False
    
    async def send_raw_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a raw message from SignalScope extension directly to Telegram
        
        Args:
            message: Raw message dict from extension
        
        Returns:
            Success status
        """
        try:
            # Format the raw message for Telegram
            formatted_text = self._format_raw_message(message)
            
            # If formatter returned empty string, skip sending
            if not formatted_text or formatted_text.strip() == "":
                logger.debug("Skipping message with empty formatted text")
                return True  # Return True to avoid retry loops
            
            # Send the text message
            success = await self.send_message(formatted_text, parse_mode="HTML")
            
            # Handle attachments if present
            if success and message.get('attachments'):
                await self._send_message_attachments(message['attachments'])
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send raw message: {e}")
            return False
    
    async def send_message_batch(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Send a batch of raw messages to Telegram
        
        Args:
            messages: List of raw message dicts from extension
        
        Returns:
            Success status
        """
        try:
            success_count = 0
            
            for message in messages:
                if await self.send_raw_message(message):
                    success_count += 1
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
            
            logger.info(f"Sent {success_count}/{len(messages)} messages to Telegram")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send message batch: {e}")
            return False
    
    def _format_raw_message(self, message: Dict[str, Any]) -> str:
        """Format a raw message from extension for Telegram"""
        author = message.get('author', 'Unknown')
        content = message.get('content', '')
        platform = message.get('platform', 'unknown')
        timestamp = message.get('timestamp', '')
        channel = message.get('channel', 'general')
        
        # Note: Filtering is now handled at server level, so we format all messages that reach here
        
        # Parse timestamp for display
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime('%H:%M')
            else:
                time_str = datetime.now().strftime('%H:%M')
        except:
            time_str = datetime.now().strftime('%H:%M')
        
        # Platform emoji mapping
        platform_emojis = {
            'circle': '🔵',
            'discord': '🎮', 
            'telegram': '✈️',
            'slack': '💬',
            'whatsapp': '📱'
        }
        platform_emoji = platform_emojis.get(platform, '💭')
        
        # Format message
        message_text = f"{platform_emoji} <b>{author}</b> in #{channel}\n"
        message_text += f"<i>{time_str}</i>\n\n"
        message_text += f"{content}"
        
        # Add attachment indicator if present
        attachments = message.get('attachments', [])
        if attachments:
            image_count = len([a for a in attachments if a.get('type') == 'image'])
            link_count = len([a for a in attachments if a.get('type') == 'link'])
            
            if image_count > 0:
                message_text += f"\n\n📸 {image_count} image(s) attached"
            if link_count > 0:
                message_text += f"\n🔗 {link_count} link(s) attached"
        
        return message_text
    
    async def _send_message_attachments(self, attachments: List[Dict[str, Any]]):
        """Send message attachments (images, links) to Telegram"""
        try:
            for attachment in attachments:
                attachment_type = attachment.get('type', '')
                
                if attachment_type == 'image':
                    # Handle image attachments
                    await self._send_image_attachment(attachment)
                elif attachment_type == 'link':
                    # Handle link attachments
                    await self._send_link_attachment(attachment)
                
                # Small delay between attachments
                await asyncio.sleep(0.2)
                
        except Exception as e:
            logger.error(f"Failed to send attachments: {e}")
    
    async def _send_image_attachment(self, attachment: Dict[str, Any]):
        """Send an image attachment to Telegram"""
        try:
            image_data = attachment.get('data', '')
            image_url = attachment.get('url', '')
            context = attachment.get('context', '')
            
            if image_data and image_data.startswith('data:image'):
                # Handle base64 image data
                import base64
                header, data = image_data.split(',', 1)
                image_bytes = base64.b64decode(data)
                
                caption = f"📈 {context}" if context else "📈 Chart"
                await self.send_photo(image_bytes, caption)
                
            elif image_url:
                # Download and send the actual image
                try:
                    # Add headers to mimic browser request for better compatibility
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://members.julian-komar.com/'
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url, headers=headers) as response:
                            if response.status == 200:
                                image_bytes = await response.read()
                                caption = f"📈 {context}" if context else "📈 Trading Chart"
                                await self.send_photo(image_bytes, caption)
                                logger.info(f"Successfully sent image from URL: {image_url}")
                            else:
                                # Try Telegram's sendPhoto with URL directly (Telegram will download it)
                                try:
                                    url = f"{self.base_url}/sendPhoto"
                                    payload = {
                                        "chat_id": self.chat_id,
                                        "photo": image_url,
                                        "caption": f"📈 {context}" if context else "📈 Trading Chart"
                                    }
                                    
                                    async with aiohttp.ClientSession() as session2:
                                        async with session2.post(url, json=payload) as tg_response:
                                            if tg_response.status == 200:
                                                logger.info(f"Successfully sent image URL directly to Telegram: {image_url}")
                                                return
                                except Exception as direct_send_error:
                                    logger.debug(f"Direct URL send failed: {direct_send_error}")
                                
                                # Final fallback to link
                                link_text = f"📸 <a href='{image_url}'>View Chart</a>"
                                if context:
                                    link_text += f"\n<i>{context}</i>"
                                await self.send_message(link_text, parse_mode="HTML")
                                logger.warning(f"Failed to download image (status {response.status}), sent as link instead")
                except Exception as download_error:
                    logger.error(f"Failed to download image from {image_url}: {download_error}")
                    # Fallback to link
                    link_text = f"📸 <a href='{image_url}'>View Chart</a>"
                    if context:
                        link_text += f"\n<i>{context}</i>"
                    await self.send_message(link_text, parse_mode="HTML")
                
        except Exception as e:
            logger.error(f"Failed to send image attachment: {e}")
    
    async def _send_link_attachment(self, attachment: Dict[str, Any]):
        """Send a link attachment to Telegram"""
        try:
            url = attachment.get('url', '')
            title = attachment.get('title', '')
            
            if url:
                if title:
                    link_text = f"🔗 <a href='{url}'>{title}</a>"
                else:
                    link_text = f"🔗 {url}"
                
                await self.send_message(link_text, parse_mode="HTML")
                
        except Exception as e:
            logger.error(f"Failed to send link attachment: {e}")

    async def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            test_message = (
                "<b>🚀 SignalScope Connected!</b>\n\n"
                "Your Telegram bot is successfully configured.\n"
                "You will receive:\n"
                "• 🚨 High-priority trading alerts\n"
                "• 📊 Hourly market summaries\n"
                "• 📈 Daily trading reports\n"
                "• 💬 Live chat messages\n\n"
                f"<i>Chat ID: {self.chat_id}</i>"
            )
            
            return await self.send_message(test_message)
            
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False