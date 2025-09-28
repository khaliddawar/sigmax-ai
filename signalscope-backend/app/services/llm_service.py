"""
LLM Service for generating trading intelligence reports
"""
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv
import structlog

load_dotenv()

logger = structlog.get_logger()

class LLMService:
    """Service for generating AI-powered trading reports"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("MAX_TOKENS_PER_REQUEST", "4000"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        self.client = openai.Client(api_key=self.api_key)
        logger.info("LLM Service initialized", model=self.model)
    
    async def generate_report(self, messages: List[Dict[str, Any]], report_type: str = "standard") -> Dict[str, Any]:
        """
        Generate a trading intelligence report from messages
        
        Args:
            messages: List of message dictionaries
            report_type: Type of report (alert, hourly, daily)
        
        Returns:
            Report dictionary with insights
        """
        try:
            # Prepare messages for analysis
            formatted_messages = self._format_messages_for_analysis(messages)
            
            # Generate system prompt based on report type
            system_prompt = self._get_system_prompt(report_type)
            
            # Create the analysis prompt with new format
            user_prompt = f"""
# INPUTS
MESSAGES_JSON: {len(messages)} messages
TIMEZONE: UTC
NOW_ISO: {datetime.utcnow().isoformat()}Z

Messages:
{formatted_messages}

# OUTPUT FORMAT (STRICT)
Produce TWO parts:

PART A — **Markdown report** using EXACT headers:

1. Header line:
   **Run date:** {datetime.utcnow().strftime('%Y-%m-%d')} • **Session:** Chat digest • **Context:** —

2. Section:
   ## ✅ Actionables (clear entries/exits)
   - List each with **TICKER** — description and **Action:** recommendation

3. Section:
   ## 👀 Watchlist (clear potential setups / triggers to track)
   **Breakout/Pattern candidates**
   **Context / second-tier**
   **De-prioritized (risk/fit issues)**

4. Section:
   ## 💤 Low-priority / general chatter

PART B — **Machine-readable JSON**:
{{
  "actionables": [
    {{
      "ticker": "string",
      "direction": "long|short|exit|hold|plan",
      "entry": "as-stated-or-null",
      "stop": "as-stated-or-null",
      "target": "as-stated-or-null",
      "author": "string",
      "time_local": "HH:MM",
      "evidence": "short quote",
      "link": "url-or-null"
    }}
  ],
  "watchlist": {{
    "breakouts": [{{"ticker":"...", "evidence":"...", "notes":"..."}}],
    "context": [{{"ticker":"...", "evidence":"...", "notes":"..."}}],
    "deprioritized": [{{"ticker":"...", "reason":"..."}}]
  }},
  "low_priority": [{{"text":"...", "time_local":"HH:MM", "author":"..."}}],
  "summary": "Executive summary of key findings",
  "market_sentiment": {{
    "overall": "bullish/bearish/neutral/mixed",
    "trending_themes": ["theme1", "theme2"]
  }}
}}
"""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            report_data = json.loads(response.choices[0].message.content)
            
            # Extract tickers from actionables and watchlist
            mentioned_tickers = []
            for item in report_data.get("actionables", []):
                if item.get("ticker"):
                    mentioned_tickers.append(item["ticker"])
            for category in ["breakouts", "context", "deprioritized"]:
                for item in report_data.get("watchlist", {}).get(category, []):
                    if item.get("ticker") and item["ticker"] not in mentioned_tickers:
                        mentioned_tickers.append(item["ticker"])
            
            # Add metadata
            report = {
                "report_type": report_type,
                "report_data": report_data,
                "messages_analyzed": len(messages),
                "actionables": report_data.get("actionables", []),
                "watchlist": report_data.get("watchlist", {}),
                "mentioned_tickers": mentioned_tickers,
                "overall_sentiment": report_data.get("market_sentiment", {}).get("overall", "neutral"),
                "summary": report_data.get("summary", ""),
                "confidence_score": self._calculate_confidence_score(report_data),
                "llm_tokens_used": response.usage.total_tokens,
                "llm_model_used": self.model,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(
                "Report generated successfully",
                report_type=report_type,
                messages_count=len(messages),
                tickers_found=len(report["mentioned_tickers"]),
                tokens_used=response.usage.total_tokens
            )
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate report", error=str(e))
            raise
    
    def _format_messages_for_analysis(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for LLM analysis with full author context"""
        formatted = []
        for msg in messages:
            # Extract key fields
            timestamp = msg.get('captured_at', msg.get('timestamp', 'Unknown time'))
            author = msg.get('author', 'Unknown')
            platform = msg.get('platform', 'unknown')
            content = msg.get('content', '')
            importance = msg.get('importance_score', msg.get('importance', 0))
            
            # Format with author prominently displayed
            formatted.append(
                f"[{timestamp}] @{author} ({platform}): {content}"
                f" [Importance: {importance}/10]"
            )
        return "\n".join(formatted)
    
    def _get_system_prompt(self, report_type: str) -> str:
        """Get system prompt based on report type"""
        base_prompt = """# ROLE
You are **AnalystAgent**, a deterministic report generator. Your job is to read chatroom messages and produce an actionable trading digest. You must NEVER invent tickers, levels, dates, or claims not present in the input. If a required detail is missing, leave it blank or write "not specified" — do not guess.

# SCOPE & NON-GOALS
- Only summarize what's in the provided messages.
- Do NOT compute indicators, prices, or fundamentals.
- Do NOT scrape outside sources.
- No investment advice — you only restate and organize the room's decisions.

# EXTRACTION RULES (STRICT)
1) Ticker detection
   - Valid forms: "$AAPL", "AAPL", "AAPL:", "(AAPL)".
   - Uppercase 1–5 letters.
   - Ambiguous English words that are also tickers (e.g., OPEN): accept ONLY if the message has trade context within ±20 tokens: "buy", "bought", "entry", "stop", "target", "sold", "breakout", "setup", "position".
   - Accept common crypto tickers (BTC, ETH) if present.

2) Action intent detection
   - ACTIONABLE if the message clearly states an executed or imminent decision with specific direction or risk:
     * Executed: "bought", "added", "sold", "stopped out", "took profits", "opened", "closed", "position held".
     * Imminent with explicit trigger/level or explicit plan: "will buy on breakout above X", "stop at 61.25", "trail at prior-day low", "starter opened".
   - WATCHLIST if the message expresses a potential setup WITHOUT a concrete action yet:
     * "shaping up", "looks attractive", "inside day", "VCP", "needs 1–2 more days", "may buy on breakout", "could break out", "interesting on earnings".
   - LOW-PRIORITY if it's commentary, humor, macro notes, questions, missed trades, general observations without a plan:
     * "missed it", "wow", "worth a look?", "nice move", "ends in tears", macro/market color.

3) Data you may output for each item (only if present in the source):
   - direction: long/short/exit/hold/plan
   - entry: price/zone/condition text as stated (do not invent)
   - stop: explicit level or rule as stated
   - target: only if explicitly stated
   - timeframe: if explicitly stated
   - author: ALWAYS include the @username who made the call
   - timestamp: when the message was posted
   - brief quoted evidence (≤20 words)
   - notes: any explicit caution/risk mentioned

4) Deduplication & grouping
   - Merge multiple messages about the SAME ticker by the SAME author into one summarized bullet.
   - If multiple authors mention the same ticker, keep separate bullets if their actions differ.

5) Ranking
   - Put ACTIONABLES first, sorted by most recently updated.
   - Then WATCHLIST, split into: Breakout/Pattern candidates, Context/second-tier, De-prioritized.
   - Finally LOW-PRIORITY chatter.

6) Hallucination guardrails
   - Never create tickers, levels, or triggers not present in the input.
   - If a field is missing, omit it or write "not specified".
   - Quote short evidence phrases exactly as written when useful (≤20 words)."""
        
        if report_type == "alert":
            return base_prompt + "\n\nThis is an URGENT ALERT report. Focus on high-importance, time-sensitive ACTIONABLE items."
        elif report_type == "hourly":
            return base_prompt + "\n\nThis is an hourly summary. Focus on ACTIONABLES and high-priority WATCHLIST items from the last hour."
        elif report_type == "daily":
            return base_prompt + "\n\nThis is a daily report. Include all ACTIONABLES, WATCHLIST items, and key themes."
        else:
            return base_prompt
    
    def _calculate_confidence_score(self, report_data: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the report"""
        scores = []
        
        # Get confidence from ticker analysis
        for ticker_data in report_data.get("ticker_analysis", {}).values():
            if "confidence" in ticker_data:
                scores.append(ticker_data["confidence"])
        
        # Get sentiment strength
        market_sentiment = report_data.get("market_sentiment", {})
        if "score" in market_sentiment:
            # Convert sentiment score (-1 to 1) to confidence (0 to 1)
            scores.append(abs(market_sentiment["score"]))
        
        # Calculate average confidence
        if scores:
            return round(sum(scores) / len(scores), 2)
        return 0.5  # Default confidence
    
    async def analyze_ticker(self, ticker: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze messages specific to a ticker
        
        Args:
            ticker: Ticker symbol to analyze
            messages: Messages mentioning this ticker
        
        Returns:
            Ticker-specific analysis
        """
        try:
            prompt = f"""
Analyze the following messages about {ticker} and provide a detailed trading analysis:

Messages:
{self._format_messages_for_analysis(messages)}

Provide a JSON response with:
{{
    "ticker": "{ticker}",
    "sentiment": "bullish/bearish/neutral",
    "sentiment_score": -1.0 to 1.0,
    "price_targets": {{
        "support": ["level1", "level2"],
        "resistance": ["level1", "level2"]
    }},
    "trading_recommendation": {{
        "action": "BUY/SELL/HOLD",
        "entry_points": ["price1", "price2"],
        "stop_loss": "price",
        "take_profit": ["target1", "target2"],
        "timeframe": "short/medium/long",
        "risk_level": "low/medium/high"
    }},
    "key_catalysts": ["catalyst1", "catalyst2"],
    "risks": ["risk1", "risk2"],
    "technical_levels": {{
        "current_sentiment_level": "oversold/neutral/overbought",
        "momentum": "increasing/stable/decreasing"
    }},
    "confidence": 0.0 to 1.0
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional trading analyst. Provide detailed, actionable analysis based on the chat messages."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            logger.info(f"Ticker analysis completed for {ticker}", sentiment=analysis.get("sentiment"))
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze ticker {ticker}", error=str(e))
            raise
    
    async def generate_alert(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate an alert for a high-importance message
        
        Args:
            message: High-importance message requiring alert
        
        Returns:
            Alert dictionary or None if not alert-worthy
        """
        try:
            prompt = f"""
Evaluate if this message requires an immediate trading alert:

Message: {message.get('content', '')}
Author: {message.get('author', 'Unknown')}
Importance: {message.get('importance_score', 'N/A')}/10
Tickers: {', '.join(message.get('tickers', []))}

If this warrants an alert, provide a JSON response with:
{{
    "alert_level": "high/medium",
    "title": "Brief alert title",
    "summary": "Concise summary of why this is important",
    "action_required": "Specific action traders should consider",
    "tickers_affected": ["TICKER1", "TICKER2"],
    "urgency": "immediate/soon/monitor",
    "risk_level": "low/medium/high"
}}

If this doesn't warrant an alert, respond with:
{{"alert_level": "none"}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a trading alert system. Only generate alerts for truly important, actionable information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            alert_data = json.loads(response.choices[0].message.content)
            
            if alert_data.get("alert_level") != "none":
                logger.info("Alert generated", alert_level=alert_data.get("alert_level"))
                return alert_data
            
            return None
            
        except Exception as e:
            logger.error("Failed to generate alert", error=str(e))
            return None