import os
import logging
import json
import openai
from typing import Dict, Any, List, Optional, Tuple
import traceback
import re
from app.services.transcript_processor import bucketed_text
from app.settings import OPENAI_MODEL_NAME
from app.services.validation.llm_validator import LLMValidator, ValidationConfig

logger = logging.getLogger("bpt-summary-service")

class HallucinationGuardrails:
    """Enhanced hallucination prevention with numeric and quote validation"""
    
    def __init__(self):
        self.numeric_pattern = re.compile(r'[\d,]+\.?\d*%?|\$[\d,]+\.?\d*|[\d,]+\.?\d*[KMB]?')
        self.quote_min_words = 6  # Minimum words for quote validation
        
    def validate_numeric_consistency(self, summary_json: Dict[str, Any], transcript_text: str) -> Dict[str, Any]:
        """
        Validate that all numeric values in the summary exist in the transcript
        
        Args:
            summary_json: Generated summary in JSON format
            transcript_text: Original transcript text
            
        Returns:
            Validation result with details
        """
        try:
            # Extract all numbers from summary
            summary_text = json.dumps(summary_json)
            summary_numbers = self.numeric_pattern.findall(summary_text)
            
            # Extract all numbers from transcript
            transcript_numbers = self.numeric_pattern.findall(transcript_text)
            
            # Normalize numbers for comparison (remove commas, etc.)
            def normalize_number(num_str):
                return re.sub(r'[,$]', '', num_str.lower())
            
            normalized_transcript = [normalize_number(num) for num in transcript_numbers]
            
            invalid_numbers = []
            for num in summary_numbers:
                normalized_num = normalize_number(num)
                if normalized_num not in normalized_transcript:
                    invalid_numbers.append(num)
            
            is_valid = len(invalid_numbers) == 0
            
            return {
                "is_valid": is_valid,
                "summary_numbers": summary_numbers,
                "transcript_numbers": transcript_numbers,
                "invalid_numbers": invalid_numbers,
                "validation_type": "numeric_consistency"
            }
            
        except Exception as e:
            logger.error(f"Error in numeric validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validation_type": "numeric_consistency"
            }
    
    def validate_quote_accuracy(self, summary_json: Dict[str, Any], transcript_text: str) -> Dict[str, Any]:
        """
        Validate that quotes in the summary appear verbatim in the transcript
        
        Args:
            summary_json: Generated summary in JSON format
            transcript_text: Original transcript text
            
        Returns:
            Validation result with details
        """
        try:
            invalid_quotes = []
            all_quotes = []
            
            # Extract quotes from notable_quotes section
            if "notable_quotes" in summary_json:
                for quote_item in summary_json["notable_quotes"]:
                    if isinstance(quote_item, dict) and "quote" in quote_item:
                        quote_text = quote_item["quote"].strip('"\'')
                        all_quotes.append(quote_text)
                        
                        # Only validate quotes with minimum word count
                        if len(quote_text.split()) >= self.quote_min_words:
                            # Check if quote appears verbatim in transcript (case-insensitive)
                            if quote_text.lower() not in transcript_text.lower():
                                # Try to find partial matches (at least 80% of words)
                                quote_words = quote_text.lower().split()
                                transcript_lower = transcript_text.lower()
                                
                                matching_words = sum(1 for word in quote_words if word in transcript_lower)
                                match_ratio = matching_words / len(quote_words)
                                
                                if match_ratio < 0.8:  # Less than 80% match
                                    invalid_quotes.append({
                                        "quote": quote_text,
                                        "match_ratio": match_ratio,
                                        "speaker": quote_item.get("speaker", "Unknown")
                                    })
            
            is_valid = len(invalid_quotes) == 0
            
            return {
                "is_valid": is_valid,
                "all_quotes": all_quotes,
                "invalid_quotes": invalid_quotes,
                "validation_type": "quote_accuracy"
            }
            
        except Exception as e:
            logger.error(f"Error in quote validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validation_type": "quote_accuracy"
            }
    
    def validate_domain_factual_consistency(self, summary_json: Dict[str, Any], transcript_text: str, active_domains: List[str]) -> Dict[str, Any]:
        """
        Domain-agnostic factual consistency checks
        
        Args:
            summary_json: Generated summary in JSON format
            transcript_text: Original transcript text
            active_domains: List of active domain supplements
            
        Returns:
            Validation result with details
        """
        try:
            issues = []
            
            # Check for domain-specific factual claims
            if "finance" in active_domains and "trade_ideas" in summary_json:
                for trade in summary_json["trade_ideas"]:
                    if isinstance(trade, dict):
                        asset = trade.get("asset", "")
                        if asset and asset.lower() not in transcript_text.lower():
                            issues.append(f"Asset '{asset}' not mentioned in transcript")
            
            if "coding" in active_domains and "code_snippets" in summary_json:
                for snippet in summary_json["code_snippets"]:
                    if isinstance(snippet, dict):
                        language = snippet.get("language", "")
                        if language and language.lower() not in transcript_text.lower():
                            issues.append(f"Programming language '{language}' not mentioned in transcript")
            
            # Check key takeaways for factual grounding
            if "key_takeaways" in summary_json:
                for takeaway in summary_json["key_takeaways"]:
                    if isinstance(takeaway, str):
                        # Check if key concepts from takeaway appear in transcript
                        key_words = [word for word in takeaway.split() if len(word) > 4]
                        if key_words:
                            concept_matches = sum(1 for word in key_words if word.lower() in transcript_text.lower())
                            if concept_matches / len(key_words) < 0.3:  # Less than 30% concept match
                                issues.append(f"Key takeaway may not be grounded in transcript: {takeaway[:50]}...")
            
            is_valid = len(issues) == 0
            
            return {
                "is_valid": is_valid,
                "issues": issues,
                "validation_type": "domain_factual_consistency"
            }
            
        except Exception as e:
            logger.error(f"Error in domain factual validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validation_type": "domain_factual_consistency"
            }

class SummaryService:
    """Service for generating topic-agnostic summaries of video transcripts using LLMs with enhanced hallucination guardrails"""
    
    def __init__(self):
        """Initialize the summary service with OpenAI API and validation infrastructure"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
        self.use_mock = os.getenv("USE_MOCK_OPENAI", "false").lower() == "true"
        
        # Initialize validation infrastructure
        validation_config = ValidationConfig()
        self.llm_validator = LLMValidator(validation_config)
        self.hallucination_guardrails = HallucinationGuardrails()
        
        if self.api_key and not self.use_mock:
            openai.api_key = self.api_key
            self.initialized = True
            logger.info(f"Summary service initialized with model: {self.model} and enhanced validation")
        else:
            self.initialized = False
            if self.use_mock:
                logger.info("Summary service initialized in mock mode with validation")
            else:
                logger.warning("OpenAI API key not found, summary service not fully initialized")
    
    def classify_content_domain(self, transcript_text: str) -> Dict[str, float]:
        """
        Classify the content domain to determine if domain supplements should be applied
        
        Args:
            transcript_text: Full transcript text
            
        Returns:
            Dictionary with domain confidence scores
        """
        # Simple keyword-based classification for now
        # In a production system, this could use a more sophisticated ML classifier
        
        finance_keywords = ['trading', 'market', 'stock', 'investment', 'portfolio', 'S&P', 'Bitcoin', 'dollar', 'bonds', 'commodity', 'gold', 'silver']
        coding_keywords = ['code', 'programming', 'function', 'API', 'framework', 'JavaScript', 'Python', 'React', 'database', 'algorithm']
        education_keywords = ['learn', 'teach', 'lesson', 'course', 'tutorial', 'explain', 'understand', 'concept', 'knowledge', 'study']
        
        text_lower = transcript_text.lower()
        
        finance_score = sum(1 for keyword in finance_keywords if keyword.lower() in text_lower) / len(finance_keywords)
        coding_score = sum(1 for keyword in coding_keywords if keyword.lower() in text_lower) / len(coding_keywords)
        education_score = sum(1 for keyword in education_keywords if keyword.lower() in text_lower) / len(education_keywords)
        
        return {
            'finance': min(finance_score * 3, 1.0),  # Scale up but cap at 1.0
            'coding': min(coding_score * 3, 1.0),
            'education': min(education_score * 3, 1.0)
        }
    
    async def generate_session_summary(self, transcript_text: str) -> Dict[str, Any]:
        """
        Generate a detailed summary from a transcript using topic-agnostic schema with enhanced validation
        
        Args:
            transcript_text: Full transcript text
            
        Returns:
            Dictionary containing summary data in JSON format and metadata
        """
        try:
            # Check if OpenAI API key is available
            openai_api_key = os.getenv("OPENAI_API_KEY")
            use_mock = not openai_api_key
            
            if use_mock:
                logger.warning("OpenAI API key not provided, using mock summary generation")
                return self._generate_mock_summary_json(transcript_text)
            
            logger.info("Generating session summary using OpenAI API with topic-agnostic schema and validation")
            
            # Configure OpenAI API
            client = openai.AsyncClient(api_key=openai_api_key)
            
            # Process transcript into bucketed text
            buckets = bucketed_text(transcript_text)
            prompt_chunks = "\n\n".join(
                f"[{k.upper()}]\n{v}" for k, v in buckets.items()
            )
            
            # Classify content domain
            domain_scores = self.classify_content_domain(transcript_text)
            logger.info(f"Domain classification scores: {domain_scores}")
            
            # Determine which domain supplements to include (confidence >= 0.7)
            active_domains = [domain for domain, score in domain_scores.items() if score >= 0.7]
            
            # Generate summary with validation
            summary_json, validation_results = await self._generate_validated_summary(
                client, prompt_chunks, active_domains, transcript_text
            )
            
            logger.info(f"Generated topic-agnostic summary JSON: {len(str(summary_json))} characters, domains: {active_domains}")
            logger.info(f"Validation results: {validation_results.get('overall_valid', False)}")
            
            return {
                "success": True,
                "summary_data": summary_json,
                "active_domains": active_domains,
                "validation_results": validation_results,
                "domain_scores": domain_scores
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            logger.error(traceback.format_exc())
            raise e
    
    async def _generate_validated_summary(self, client, prompt_chunks: str, active_domains: List[str], transcript_text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate summary with comprehensive validation and retry logic
        
        Args:
            client: OpenAI client
            prompt_chunks: Processed transcript chunks
            active_domains: List of active domain supplements
            transcript_text: Original transcript text
            
        Returns:
            Tuple of (summary_json, validation_results)
        """
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            is_strict_mode = attempt > 0  # Use strict mode for retries
            
            # Generate summary
            summary_json = await self._generate_summary_json(
                client, prompt_chunks, active_domains, is_strict_mode
            )
            
            # Comprehensive validation
            validation_results = await self._validate_summary_comprehensive(
                summary_json, transcript_text, active_domains
            )
            
            if validation_results["overall_valid"]:
                logger.info(f"Summary validation passed on attempt {attempt + 1}")
                return summary_json, validation_results
            
            if attempt < max_retries:
                logger.warning(f"Summary validation failed on attempt {attempt + 1}, retrying with strict mode")
                logger.warning(f"Validation issues: {validation_results.get('issues', [])}")
            else:
                logger.error(f"Summary validation failed after {max_retries + 1} attempts")
                # Return the last attempt even if validation failed
                return summary_json, validation_results
        
        return summary_json, validation_results
    
    async def _generate_summary_json(self, client, prompt_chunks: str, active_domains: List[str], strict_mode: bool = False) -> Dict[str, Any]:
        """
        Generate summary JSON with optional strict mode
        
        Args:
            client: OpenAI client
            prompt_chunks: Processed transcript chunks
            active_domains: List of active domain supplements
            strict_mode: Whether to use strict validation prompts
            
        Returns:
            Generated summary in JSON format
        """
        # Create topic-agnostic JSON schema
        base_schema = {
            "key_takeaways": [
                "String - Most important insight or lesson from the content",
                "String - Second key takeaway or principle discussed",
                "String - Third valuable insight (if available)"
            ],
            "hero_numbers": [
                {
                    "value": "String - Significant number, percentage, or statistic mentioned",
                    "context": "String - What this number represents or measures"
                }
            ],
            "step_by_step": [
                {
                    "step": "Integer - Step number (1, 2, 3, etc.)",
                    "title": "String - Brief title for this step",
                    "description": "String - Detailed explanation of what to do in this step"
                }
  ],
            "notable_quotes": [
                {
                    "quote": "String - Exact or paraphrased impactful statement",
                    "speaker": "String - Speaker name if available, or 'Host/Presenter' if unknown",
                    "context": "String - Brief context about why this quote is significant"
                }
            ]
        }
        
        # Add domain supplements if confidence >= 0.7
        domain_supplements = {}
        if 'finance' in active_domains:
            domain_supplements["trade_ideas"] = [
                {
          "asset": "String - Name of asset or instrument",
          "strategy": "String - Buy, Sell, Options strategy, etc.",
          "rationale": "String - Brief reason for the trade",
          "entry": "String - Entry level or conditions",
          "target": "String - Price target(s)",
          "stop": "String - Stop loss level"
                }
            ]
            domain_supplements["risk_alerts"] = [
                {
          "event": "String - Possible market event or trigger",
          "impact": "String - Brief description of potential market impact",
          "severity": "String - Use 'high', 'medium', or 'low'"
                }
            ]
        
        if 'coding' in active_domains:
            domain_supplements["code_snippets"] = [
                {
                    "language": "String - Programming language",
                    "code": "String - Key code example or snippet discussed",
                    "purpose": "String - What this code accomplishes"
                }
            ]
            domain_supplements["tech_insights"] = [
                {
                    "technology": "String - Framework, tool, or technology discussed",
                    "insight": "String - Key insight or recommendation about this technology"
                }
            ]
        
        if 'education' in active_domains:
            domain_supplements["learning_objectives"] = [
                "String - Key concept or skill being taught"
            ]
            domain_supplements["resources"] = [
                {
                    "type": "String - Type of resource (book, website, tool, etc.)",
                    "name": "String - Name of the resource",
                    "purpose": "String - How this resource helps with the topic"
                }
            ]
        
        # Combine base schema with active domain supplements
        full_schema = {**base_schema, **domain_supplements}
        
        # Create prompt with strict mode instructions if enabled
        strict_instructions = ""
        if strict_mode:
            strict_instructions = """
STRICT MODE ENABLED - CRITICAL ACCURACY REQUIREMENTS:
- ONLY use numbers that appear EXACTLY in the transcript
- ONLY use quotes that appear VERBATIM in the transcript (minimum 6 words)
- ONLY reference concepts that are explicitly discussed
- When in doubt, use null rather than guessing
- Double-check all factual claims against the source material
"""
        
        PROMPT_TEMPLATE = f"""
You are "TubeVibe Content Synthesizer," a universal content analyzer for any video topic.
Return ONLY valid JSON. Use null where data absent.

{strict_instructions}

IMPORTANT: This is a comprehensive video transcript analysis. You MUST extract meaningful content for ALL sections below. Do not leave sections empty unless there is genuinely no relevant content. Look carefully through the entire transcript for:

ROOT SCHEMA (ALWAYS EXTRACT):
- Key takeaways: Most important insights, lessons, or principles (3-5 items)
- Hero numbers: Significant statistics, percentages, quantities, dates mentioned
- Step-by-step: Any processes, methodologies, or sequential instructions
- Notable quotes: Impactful statements with speaker attribution when possible

DOMAIN SUPPLEMENTS (ONLY if content is relevant):
Active domains detected: {', '.join(active_domains) if active_domains else 'None - using root schema only'}

JSON schema:
{json.dumps(full_schema, indent=2)}

EXTRACTION GUIDANCE:
- For key_takeaways: Look for main lessons, insights, principles, or conclusions
- For hero_numbers: Search for any significant numbers, percentages, statistics, dates
- For step_by_step: Find any processes, methodologies, or sequential instructions
- For notable_quotes: Identify impactful statements, expert opinions, memorable phrases
- Be thorough and comprehensive - extract value from any video topic

### TRANSCRIPT ###
{prompt_chunks}
### END ###
"""
            
            # Generate summary with enforced JSON output
            resp = await client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
            messages=[{"role": "system", "content": PROMPT_TEMPLATE}],
                response_format={"type": "json_object"},
            temperature=0.1 if strict_mode else 0.2,  # Lower temperature for strict mode
            )
            data = json.loads(resp.choices[0].message.content)
            
        # Retry for empty fields in root schema (only if not in strict mode)
        if not strict_mode:
            missing_root = [k for k in base_schema.keys() if k not in data or data[k] in (None, [], "", {})]
            if missing_root:
                retry_prompt = (
                    f"IMPORTANT: Fill ONLY the root schema keys now null/empty in JSON format: {', '.join(missing_root)}\n"
                    "Search the transcript thoroughly for relevant content. These are universal fields that should have content for ANY video:\n"
                    "- key_takeaways: Main insights, lessons, or principles\n"
                    "- hero_numbers: Any significant numbers, statistics, percentages\n"
                    "- step_by_step: Processes, methodologies, or instructions\n"
                    "- notable_quotes: Impactful statements or memorable phrases\n"
                    "Return comprehensive JSON with meaningful content for these sections:\n"
                    f"### TRANSCRIPT ###\n{prompt_chunks}\n### END ###"
                )
                resp2 = await client.chat.completions.create(
                    model=OPENAI_MODEL_NAME,
                    messages=[{"role": "system", "content": retry_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                patch = json.loads(resp2.choices[0].message.content)
                # Only update root schema fields
                for key in missing_root:
                    if key in patch and patch[key] not in (None, [], "", {}):
                        data[key] = patch[key]
        
        return data
    
    async def _validate_summary_comprehensive(self, summary_json: Dict[str, Any], transcript_text: str, active_domains: List[str]) -> Dict[str, Any]:
        """
        Comprehensive validation of generated summary
        
        Args:
            summary_json: Generated summary in JSON format
            transcript_text: Original transcript text
            active_domains: List of active domain supplements
            
        Returns:
            Comprehensive validation results
        """
        validation_results = {
            "overall_valid": True,
            "issues": [],
            "validations": {}
        }
        
        try:
            # 1. Numeric consistency validation
            numeric_result = self.hallucination_guardrails.validate_numeric_consistency(summary_json, transcript_text)
            validation_results["validations"]["numeric"] = numeric_result
            if not numeric_result["is_valid"]:
                validation_results["overall_valid"] = False
                validation_results["issues"].extend([f"Invalid number: {num}" for num in numeric_result.get("invalid_numbers", [])])
            
            # 2. Quote accuracy validation
            quote_result = self.hallucination_guardrails.validate_quote_accuracy(summary_json, transcript_text)
            validation_results["validations"]["quotes"] = quote_result
            if not quote_result["is_valid"]:
                validation_results["overall_valid"] = False
                validation_results["issues"].extend([f"Invalid quote: {q['quote'][:50]}..." for q in quote_result.get("invalid_quotes", [])])
            
            # 3. Domain factual consistency validation
            factual_result = self.hallucination_guardrails.validate_domain_factual_consistency(summary_json, transcript_text, active_domains)
            validation_results["validations"]["factual"] = factual_result
            if not factual_result["is_valid"]:
                validation_results["overall_valid"] = False
                validation_results["issues"].extend(factual_result.get("issues", []))
            
            # 4. LLM Validator integration for structural validation
            llm_validation = self.llm_validator.validate_summary(summary_json, {"transcript": transcript_text})
            validation_results["validations"]["llm"] = llm_validation
            if not llm_validation.get("is_valid", True):
                # LLM validation is more lenient, so we don't fail overall validation
                # but we log the issues
                logger.info(f"LLM validation issues: {llm_validation.get('validation_summary', {})}")
            
            logger.info(f"Comprehensive validation completed: overall_valid={validation_results['overall_valid']}")
            
        except Exception as e:
            logger.error(f"Error in comprehensive validation: {e}")
            validation_results["overall_valid"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def _generate_mock_summary_json(self, transcript_text: str) -> Dict[str, Any]:
        """
        Generate a mock summary in JSON format for testing
        
        Args:
            transcript_text: Full transcript text
            
        Returns:
            Mock summary data in JSON format
        """
        # Extract some content from the transcript for a more realistic mock
        preview = transcript_text[:100] if len(transcript_text) > 100 else transcript_text
        word_count = len(transcript_text.split())
        
        mock_data = {
            "key_takeaways": [
                "This is a comprehensive analysis of the video content with actionable insights",
                "Important principle or methodology discussed in the video content",
                "Key learning points that viewers can apply immediately"
            ],
            "hero_numbers": [
                {"value": "75%", "context": "Success rate mentioned in the content"},
                {"value": f"{word_count}", "context": "Total words in transcript"}
            ],
            "step_by_step": [
                {"step": 1, "title": "Initial Setup", "description": "First step in the process outlined"},
                {"step": 2, "title": "Implementation", "description": "Core implementation details"},
                {"step": 3, "title": "Optimization", "description": "Final optimization steps"}
            ],
            "notable_quotes": [
                {"quote": "This is an example of an impactful statement from the content", "speaker": "Presenter", "context": "Discussing key concepts"}
            ]
        }
        
        logger.info("Generated topic-agnostic mock summary JSON")
        return {
            "success": True,
            "summary_data": mock_data,
            "active_domains": [],
            "validation_results": {"overall_valid": True, "mock": True},
            "domain_scores": {"finance": 0.0, "coding": 0.0, "education": 0.3}
        }

    def generate_html_from_summary_data(self, summary_result: Dict[str, Any]) -> str:
        """
        Convert summary result data to HTML format
        
        Args:
            summary_result: Result from generate_session_summary
            
        Returns:
            HTML formatted summary
        """
        if not summary_result.get("success"):
            return "<p>Error generating summary</p>"
        
        summary_data = summary_result.get("summary_data", {})
        active_domains = summary_result.get("active_domains", [])
        
        return self.convert_json_to_html(summary_data, active_domains)
        
    def convert_json_to_html(self, data: dict, active_domains: List[str] = None) -> str:
        """
        Convert JSON data to HTML format using topic-agnostic schema
        
        Args:
            data: JSON data to convert
            active_domains: List of active domain supplements
            
        Returns:
            HTML formatted summary
        """
        html = []
        
        # Key Takeaways Section (Root Schema)
        if data.get("key_takeaways"):
            html.append('<h2 class="section-heading">🎯 Key Takeaways</h2>')
            html.append('<div class="takeaway-cards">')
            for i, takeaway in enumerate(data["key_takeaways"], 1):
                if isinstance(takeaway, str) and takeaway.strip():
                    html.append(f'<div class="takeaway-card">')
                    html.append(f'<h4>💡 Insight #{i}</h4>')
                    html.append(f'<p>{takeaway}</p>')
                    html.append('</div>')
            html.append('</div>')
        
        # Hero Numbers Section (Root Schema)
        if data.get("hero_numbers"):
            html.append('<h2 class="section-heading">📊 Hero Numbers</h2>')
            html.append('<div class="hero-numbers">')
            for number_item in data["hero_numbers"]:
                if isinstance(number_item, dict):
                    value = number_item.get("value", "")
                    context = number_item.get("context", "")
                    if value:
                        html.append('<div class="number-card">')
                        html.append(f'<span class="number">{value}</span>')
                        if context:
                            html.append(f'<span class="context">{context}</span>')
                        html.append('</div>')
                elif isinstance(number_item, str) and number_item.strip():
                    # Handle simple string format
                    html.append('<div class="number-card">')
                    html.append(f'<span class="number">{number_item}</span>')
                    html.append('</div>')
            html.append('</div>')
        
        # Step-by-Step Section (Root Schema)
        if data.get("step_by_step"):
            html.append('<h2 class="section-heading">🔧 Step-by-Step Process</h2>')
            html.append('<div class="step-cards">')
            for step_item in data["step_by_step"]:
                if isinstance(step_item, dict):
                    step_num = step_item.get("step", "")
                    title = step_item.get("title", "")
                    description = step_item.get("description", "")
                    
                    html.append('<div class="step-card">')
                    html.append(f'<div class="step-number">{step_num}</div>')
                    html.append('<div class="step-content">')
                    if title:
                        html.append(f'<h4>{title}</h4>')
                    if description:
                        html.append(f'<p>{description}</p>')
                    html.append('</div>')
                    html.append('</div>')
                elif isinstance(step_item, str) and step_item.strip():
                    # Handle simple string format
                    html.append('<div class="step-card">')
                    html.append(f'<p>{step_item}</p>')
                    html.append('</div>')
            html.append('</div>')
        
        # Notable Quotes Section (Root Schema)
        if data.get("notable_quotes"):
            html.append('<h2 class="section-heading">💬 Notable Quotes</h2>')
            html.append('<div class="quote-cards">')
            for quote_item in data["notable_quotes"]:
                if isinstance(quote_item, dict):
                    quote = quote_item.get("quote", "")
                    speaker = quote_item.get("speaker", "")
                    context = quote_item.get("context", "")
                    
                    if quote:
                        html.append('<div class="quote-card">')
                        html.append(f'<blockquote>"{quote}"</blockquote>')
                        if speaker:
                            html.append(f'<cite>— {speaker}</cite>')
                        if context:
                            html.append(f'<p class="quote-context">{context}</p>')
                        html.append('</div>')
                elif isinstance(quote_item, str) and quote_item.strip():
                    # Handle simple string format
                    html.append('<div class="quote-card">')
                    html.append(f'<blockquote>"{quote_item}"</blockquote>')
                    html.append('</div>')
            html.append('</div>')
        
        # Domain Supplements (only if active)
        if active_domains and 'finance' in active_domains:
        # Trade Ideas Section
        if data.get("trade_ideas"):
                html.append('<h2 class="section-heading">🏦 Trade Ideas & Action Points</h2>')
                html.append("<ul>")
                for trade in data["trade_ideas"]:
                    if isinstance(trade, dict):
                        asset = trade.get("asset", "")
                        strategy = trade.get("strategy", "")
                        rationale = trade.get("rationale", "")
                        
                        if asset and strategy:
                            html.append(f'<li>🔑 {asset} – {strategy}</li>')
                        if rationale:
                            html.append(f'<li style="margin-left: 20px;">Rationale: {rationale}</li>')
                html.append("</ul>")
        
        # Risk Alerts Section
        if data.get("risk_alerts"):
                html.append('<h2 class="section-heading">⚠️ Risk Alerts</h2>')
                html.append("<ul>")
                for alert in data["risk_alerts"]:
                    if isinstance(alert, dict):
                        event = alert.get("event", "")
                        impact = alert.get("impact", "")
                        severity = alert.get("severity", "").lower()
                        
                        prefix = "→"
                        if severity == "high":
                            prefix = "⚠️"
                            
                        if event and impact:
                        html.append(f'<li>{prefix} {event} → {impact}</li>')
                html.append("</ul>")
        
        if active_domains and 'coding' in active_domains:
            # Code Snippets Section
            if data.get("code_snippets"):
                html.append('<h2 class="section-heading">💻 Code Snippets</h2>')
                for snippet in data["code_snippets"]:
                    if isinstance(snippet, dict):
                        language = snippet.get("language", "")
                        code = snippet.get("code", "")
                        purpose = snippet.get("purpose", "")
                        
                        if code:
                            html.append(f'<div class="code-snippet">')
                            if language:
                                html.append(f'<h4>{language}</h4>')
                            html.append(f'<pre><code>{code}</code></pre>')
                            if purpose:
                                html.append(f'<p class="code-purpose">{purpose}</p>')
                            html.append('</div>')
            
            # Tech Insights Section
            if data.get("tech_insights"):
                html.append('<h2 class="section-heading">🔧 Tech Insights</h2>')
                html.append("<ul>")
                for insight in data["tech_insights"]:
                    if isinstance(insight, dict):
                        technology = insight.get("technology", "")
                        insight_text = insight.get("insight", "")
                        
                        if technology and insight_text:
                            html.append(f'<li><strong>{technology}:</strong> {insight_text}</li>')
                html.append("</ul>")
        
        if active_domains and 'education' in active_domains:
            # Learning Objectives Section
            if data.get("learning_objectives"):
                html.append('<h2 class="section-heading">📚 Learning Objectives</h2>')
            html.append("<ul>")
                for objective in data["learning_objectives"]:
                    if isinstance(objective, str) and objective.strip():
                        html.append(f'<li>🎓 {objective}</li>')
                html.append("</ul>")
            
            # Resources Section
            if data.get("resources"):
                html.append('<h2 class="section-heading">🛠️ Resources</h2>')
                html.append("<ul>")
                for resource in data["resources"]:
                    if isinstance(resource, dict):
                        resource_type = resource.get("type", "")
                        name = resource.get("name", "")
                        purpose = resource.get("purpose", "")
                        
                        if name:
                            html.append(f'<li><strong>{name}</strong>')
                            if resource_type:
                                html.append(f' ({resource_type})')
                            if purpose:
                                html.append(f' – {purpose}')
                html.append('</li>')
            html.append("</ul>")
        
        return "\n".join(html)

# Standalone function for backward compatibility
async def generate_session_summary(transcript_text: str) -> str:
    """
    Standalone function to generate session summary for backward compatibility
    
    Args:
        transcript_text: Full transcript text
        
    Returns:
        Generated summary as HTML string (for backward compatibility)
    """
    service = SummaryService()
    result = await service.generate_session_summary(transcript_text)
    return service.generate_html_from_summary_data(result) 