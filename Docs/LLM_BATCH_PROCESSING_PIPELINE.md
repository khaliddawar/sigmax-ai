# LLM Batch Processing Pipeline for SignalScope

## Overview
This document details the LLM batch processing pipeline for SignalScope, designed to transform batched trading chat messages into actionable intelligence reports using prompt-driven analysis.

## Pipeline Architecture

### High-Level Flow
```
Message Batch → Context Preparation → LLM Processing → Report Generation → Validation → Storage → Distribution
```

## Batch Processing Strategy

### 1. Message Batch Preparation

```python
class MessageBatchPreparer:
    """Prepare message batches for LLM processing"""
    
    def prepare_batch_context(self, messages: List[Dict]) -> Dict:
        """Transform raw messages into structured context for LLM"""
        
        # Group messages by ticker
        ticker_groups = self.group_by_tickers(messages)
        
        # Extract key metrics
        metrics = {
            'total_messages': len(messages),
            'unique_authors': len(set(m['author'] for m in messages)),
            'time_span': self.calculate_time_span(messages),
            'dominant_sentiment': self.calculate_dominant_sentiment(messages),
            'top_tickers': self.get_top_tickers(messages, limit=10),
            'high_importance_count': sum(1 for m in messages if m['intelligence']['importance'] >= 8)
        }
        
        # Create structured context
        context = {
            'summary_stats': metrics,
            'ticker_analysis': ticker_groups,
            'temporal_distribution': self.analyze_temporal_patterns(messages),
            'sentiment_flow': self.track_sentiment_changes(messages),
            'key_messages': self.extract_key_messages(messages),
            'trading_signals': self.aggregate_trading_signals(messages)
        }
        
        return context
    
    def group_by_tickers(self, messages: List[Dict]) -> Dict:
        """Group messages by mentioned tickers"""
        ticker_groups = {}
        
        for message in messages:
            tickers = message['intelligence']['entities'].get('tickers', [])
            for ticker in tickers:
                if ticker not in ticker_groups:
                    ticker_groups[ticker] = {
                        'messages': [],
                        'sentiment_scores': [],
                        'trading_signals': [],
                        'price_mentions': [],
                        'volume_mentions': []
                    }
                
                ticker_groups[ticker]['messages'].append(message['content'])
                ticker_groups[ticker]['sentiment_scores'].append(
                    message['intelligence']['sentiment']['score']
                )
                
                if message['intelligence'].get('tradingSignal'):
                    ticker_groups[ticker]['trading_signals'].append(
                        message['intelligence']['tradingSignal']
                    )
                
                # Extract price and volume mentions
                for price in message['intelligence']['entities'].get('prices', []):
                    ticker_groups[ticker]['price_mentions'].append(price)
                
                for qty in message['intelligence']['entities'].get('quantities', []):
                    ticker_groups[ticker]['volume_mentions'].append(qty)
        
        # Calculate aggregate metrics for each ticker
        for ticker, data in ticker_groups.items():
            data['aggregate_sentiment'] = np.mean(data['sentiment_scores']) if data['sentiment_scores'] else 0
            data['message_count'] = len(data['messages'])
            data['signal_consensus'] = self.calculate_signal_consensus(data['trading_signals'])
        
        return ticker_groups
```

### 2. LLM Prompt Templates

```python
# Prompt templates for different report types

REALTIME_ALERT_PROMPT = """
You are a trading intelligence analyst processing real-time chat data from trading communities.

CONTEXT:
- Time Window: {time_window}
- Message Count: {message_count}
- Unique Authors: {unique_authors}
- Dominant Sentiment: {dominant_sentiment}

TOP TICKERS MENTIONED:
{ticker_summary}

HIGH-IMPORTANCE MESSAGES:
{key_messages}

TRADING SIGNALS DETECTED:
{trading_signals}

Generate a REAL-TIME ALERT report with the following structure:

1. URGENT SIGNALS (if any):
   - Ticker, Action (BUY/SELL), Strength, Consensus Level
   - Supporting evidence from messages

2. SENTIMENT SHIFTS:
   - Any sudden sentiment changes for specific tickers
   - Volume spikes in mentions

3. RISK ALERTS:
   - Potential pump & dump patterns
   - Contradictory signals
   - Unusual activity patterns

4. ACTIONABLE INSIGHTS:
   - Top 3 immediate opportunities
   - Key levels to watch
   - Recommended actions

Format as JSON with clear, concise insights for immediate action.
"""

HOURLY_SUMMARY_PROMPT = """
You are a market analyst creating an hourly summary of trading community discussions.

BATCH STATISTICS:
- Messages Analyzed: {total_messages}
- Time Period: {start_time} to {end_time}
- Active Participants: {unique_authors}
- Overall Market Sentiment: {market_sentiment}

TICKER ANALYSIS:
{detailed_ticker_analysis}

SENTIMENT FLOW:
{sentiment_timeline}

NOTABLE PATTERNS:
{pattern_analysis}

Generate an HOURLY SUMMARY report including:

1. MARKET OVERVIEW:
   - Overall sentiment and mood
   - Key themes discussed
   - Market direction consensus

2. TOP MOVERS (by mention volume):
   - Ticker performance expectations
   - Sentiment analysis
   - Key price levels mentioned

3. TRADING IDEAS:
   - Best opportunities identified
   - Risk/reward assessments
   - Entry/exit suggestions

4. COMMUNITY INSIGHTS:
   - Influential voices and their positions
   - Emerging narratives
   - Contrarian views

5. RISK FACTORS:
   - Warning signs observed
   - Divergent opinions
   - Market concerns

Format as structured JSON optimized for dashboard display.
"""

DAILY_REPORT_PROMPT = """
You are a senior trading strategist preparing a comprehensive daily intelligence report.

DAILY OVERVIEW:
- Total Messages: {total_messages}
- Active Users: {unique_users}
- Tickers Discussed: {ticker_count}
- Trading Signals Generated: {signal_count}

DETAILED METRICS:
{comprehensive_metrics}

TEMPORAL ANALYSIS:
{intraday_patterns}

SENTIMENT EVOLUTION:
{sentiment_trends}

Generate a COMPREHENSIVE DAILY REPORT including:

1. EXECUTIVE SUMMARY:
   - Key takeaways (3-5 bullet points)
   - Market sentiment score (1-10)
   - Confidence level in signals

2. TICKER DEEP DIVE:
   - Top 10 tickers by relevance
   - Bull vs Bear case for each
   - Price targets and stop losses
   - Volume and momentum indicators

3. PATTERN RECOGNITION:
   - Recurring themes
   - Sentiment cycles
   - Correlation patterns
   - Anomaly detection

4. PREDICTIVE INSIGHTS:
   - Next day expectations
   - Key levels to monitor
   - Potential catalysts
   - Risk scenarios

5. PORTFOLIO RECOMMENDATIONS:
   - Suggested allocations
   - Risk management advice
   - Hedging strategies

6. METADATA:
   - Data quality score
   - Confidence intervals
   - Processing statistics

Return as comprehensive JSON suitable for automated trading systems and human review.
"""
```

### 3. LLM Processing Service

```python
class LLMBatchProcessor:
    """Process message batches through LLM for report generation"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model_selector = ModelSelector()
        self.token_optimizer = TokenOptimizer()
    
    async def process_batch(self, batch_context: Dict, report_type: str) -> Dict:
        """Process batch through appropriate LLM"""
        
        # Select optimal model based on report type and size
        model_config = self.model_selector.select_model(
            report_type=report_type,
            context_size=len(str(batch_context)),
            priority=batch_context.get('priority', 'standard')
        )
        
        # Optimize context to fit token limits
        optimized_context = self.token_optimizer.optimize(
            context=batch_context,
            max_tokens=model_config['context_window'],
            preserve_keys=['trading_signals', 'key_messages']
        )
        
        # Prepare prompt
        prompt = self.prepare_prompt(optimized_context, report_type)
        
        # Process through LLM
        if model_config['provider'] == 'openai':
            report = await self.process_with_openai(prompt, model_config)
        else:
            report = await self.process_with_anthropic(prompt, model_config)
        
        # Post-process and validate
        report = self.post_process_report(report, batch_context)
        
        return report
    
    async def process_with_openai(self, prompt: str, model_config: Dict) -> Dict:
        """Process with OpenAI models"""
        
        response = await self.openai_client.chat.completions.create(
            model=model_config['model_name'],  # gpt-4-turbo or gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are a professional trading analyst specializing in market intelligence extraction."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Lower temperature for consistency
            max_tokens=model_config['max_output_tokens']
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def process_with_anthropic(self, prompt: str, model_config: Dict) -> Dict:
        """Process with Anthropic Claude"""
        
        response = await self.anthropic_client.messages.create(
            model=model_config['model_name'],  # claude-3-opus or claude-3-sonnet
            messages=[{"role": "user", "content": prompt}],
            max_tokens=model_config['max_output_tokens'],
            temperature=0.3
        )
        
        # Extract JSON from Claude's response
        return self.extract_json_from_text(response.content[0].text)
```

### 4. Token Optimization

```python
class TokenOptimizer:
    """Optimize context to fit within token limits"""
    
    def optimize(self, context: Dict, max_tokens: int, preserve_keys: List[str]) -> Dict:
        """Intelligently reduce context size while preserving key information"""
        
        current_tokens = self.estimate_tokens(context)
        
        if current_tokens <= max_tokens:
            return context
        
        # Optimization strategies in order of preference
        optimized = context.copy()
        
        # 1. Summarize long message lists
        if 'key_messages' in optimized and len(optimized['key_messages']) > 20:
            optimized['key_messages'] = self.summarize_messages(
                optimized['key_messages'], 
                target_count=20
            )
        
        # 2. Reduce ticker groups to top N
        if 'ticker_analysis' in optimized and len(optimized['ticker_analysis']) > 15:
            optimized['ticker_analysis'] = self.get_top_tickers(
                optimized['ticker_analysis'], 
                limit=15
            )
        
        # 3. Aggregate temporal data
        if 'temporal_distribution' in optimized:
            optimized['temporal_distribution'] = self.aggregate_temporal_data(
                optimized['temporal_distribution']
            )
        
        # 4. Remove redundant sentiment data
        if 'sentiment_flow' in optimized:
            optimized['sentiment_flow'] = self.compress_sentiment_data(
                optimized['sentiment_flow']
            )
        
        # 5. Last resort: truncate messages
        if self.estimate_tokens(optimized) > max_tokens:
            optimized = self.truncate_to_fit(optimized, max_tokens, preserve_keys)
        
        return optimized
    
    def estimate_tokens(self, data: Any) -> int:
        """Estimate token count for data"""
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        text = json.dumps(data) if isinstance(data, dict) else str(data)
        return len(encoding.encode(text))
```

### 5. Report Validation and Enhancement

```python
class ReportValidator:
    """Validate and enhance LLM-generated reports"""
    
    def validate_report(self, report: Dict, original_context: Dict) -> Dict:
        """Validate report accuracy and completeness"""
        
        validation_results = {
            'is_valid': True,
            'issues': [],
            'enhancements': []
        }
        
        # Check ticker accuracy
        report_tickers = self.extract_tickers_from_report(report)
        context_tickers = set(original_context.get('ticker_analysis', {}).keys())
        
        invalid_tickers = report_tickers - context_tickers
        if invalid_tickers:
            validation_results['issues'].append(f"Invalid tickers: {invalid_tickers}")
            validation_results['is_valid'] = False
        
        # Verify numerical consistency
        numbers_valid = self.verify_numbers(report, original_context)
        if not numbers_valid:
            validation_results['issues'].append("Numerical inconsistencies detected")
        
        # Check sentiment alignment
        sentiment_valid = self.verify_sentiment_consistency(report, original_context)
        if not sentiment_valid:
            validation_results['issues'].append("Sentiment analysis mismatch")
        
        # Enhance with additional metrics
        report['metadata'] = {
            'validation': validation_results,
            'confidence_score': self.calculate_confidence(report, original_context),
            'data_quality': self.assess_data_quality(original_context),
            'processing_timestamp': datetime.utcnow().isoformat()
        }
        
        return report
    
    def calculate_confidence(self, report: Dict, context: Dict) -> float:
        """Calculate confidence score for the report"""
        
        factors = []
        
        # Message volume factor
        msg_count = context.get('summary_stats', {}).get('total_messages', 0)
        volume_score = min(msg_count / 100, 1.0)  # Max at 100 messages
        factors.append(volume_score)
        
        # Author diversity factor
        unique_authors = context.get('summary_stats', {}).get('unique_authors', 1)
        diversity_score = min(unique_authors / 20, 1.0)  # Max at 20 authors
        factors.append(diversity_score)
        
        # Signal consensus factor
        if 'trading_signals' in context:
            consensus = self.calculate_signal_consensus(context['trading_signals'])
            factors.append(consensus)
        
        # Time coverage factor
        time_span = context.get('summary_stats', {}).get('time_span', 0)
        coverage_score = min(time_span / 3600, 1.0)  # Max at 1 hour
        factors.append(coverage_score)
        
        return sum(factors) / len(factors) if factors else 0.5
```

### 6. Report Storage and Distribution

```python
class ReportDistributor:
    """Store and distribute generated reports"""
    
    async def store_and_distribute(self, report: Dict, batch_id: str) -> Dict:
        """Store report and trigger distribution"""
        
        # Store in Supabase
        stored_report = await self.store_in_supabase(report, batch_id)
        
        # Trigger distributions based on report type
        distribution_results = await self.distribute_report(stored_report)
        
        return {
            'report_id': stored_report['id'],
            'storage_status': 'success',
            'distributions': distribution_results
        }
    
    async def store_in_supabase(self, report: Dict, batch_id: str) -> Dict:
        """Store report in Supabase"""
        
        supabase = get_supabase_client()
        
        # Extract key fields for indexing
        report_record = {
            'batch_id': batch_id,
            'report_type': report['metadata']['report_type'],
            'report_data': report,
            'key_insights': self.extract_key_insights(report),
            'mentioned_tickers': self.extract_all_tickers(report),
            'overall_sentiment': report.get('market_overview', {}).get('sentiment'),
            'trading_signals': report.get('trading_signals', []),
            'confidence_score': report['metadata']['confidence_score'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = await supabase.table('reports').insert(report_record).execute()
        return result.data[0]
    
    async def distribute_report(self, report: Dict) -> List[Dict]:
        """Distribute report to subscribers"""
        
        distributions = []
        
        # Get active subscriptions for this report type
        subscriptions = await self.get_active_subscriptions(report['report_type'])
        
        for subscription in subscriptions:
            if subscription['delivery_method'] == 'webhook':
                result = await self.send_webhook(report, subscription)
            elif subscription['delivery_method'] == 'email':
                result = await self.send_email(report, subscription)
            elif subscription['delivery_method'] == 'dashboard':
                result = await self.update_dashboard(report, subscription)
            
            distributions.append(result)
        
        return distributions
```

## Performance Optimization

### 1. Parallel Processing
```python
async def process_multiple_batches(self, batches: List[Dict]) -> List[Dict]:
    """Process multiple batches in parallel"""
    
    tasks = []
    for batch in batches:
        task = asyncio.create_task(
            self.process_batch(batch['context'], batch['report_type'])
        )
        tasks.append(task)
    
    # Process in parallel with concurrency limit
    results = []
    for chunk in chunks(tasks, size=5):  # Process 5 at a time
        chunk_results = await asyncio.gather(*chunk)
        results.extend(chunk_results)
    
    return results
```

### 2. Caching Strategy
```python
class ReportCache:
    """Cache frequently accessed reports and insights"""
    
    def __init__(self):
        self.redis = redis_client
        self.cache_ttl = {
            'realtime_alert': 300,  # 5 minutes
            'hourly_summary': 3600,  # 1 hour
            'daily_report': 86400  # 24 hours
        }
    
    async def get_or_generate(self, batch_id: str, generator_func) -> Dict:
        """Get from cache or generate new report"""
        
        cached = await self.get_cached_report(batch_id)
        if cached:
            return cached
        
        report = await generator_func()
        await self.cache_report(batch_id, report)
        return report
```

### 3. Cost Optimization
```python
class CostOptimizer:
    """Optimize LLM usage for cost efficiency"""
    
    def select_model_by_priority(self, priority: str, complexity: float) -> str:
        """Select most cost-effective model"""
        
        if priority == 'realtime' and complexity > 0.8:
            return 'gpt-4-turbo'  # High accuracy needed
        elif priority == 'standard' and complexity > 0.5:
            return 'gpt-3.5-turbo-16k'  # Good balance
        else:
            return 'gpt-3.5-turbo'  # Cost-effective
    
    def should_use_cache(self, context: Dict) -> bool:
        """Determine if cached analysis can be reused"""
        
        # Check if similar context was recently processed
        context_hash = self.hash_context(context)
        recent_similar = self.find_similar_recent(context_hash)
        
        return recent_similar is not None
```

## Monitoring and Metrics

### Key Performance Indicators
1. **Processing Latency**: Time from batch ready to report generated
2. **Token Efficiency**: Tokens used vs. information extracted
3. **Report Quality**: Validation scores and user feedback
4. **Cost per Report**: LLM costs divided by reports generated
5. **Cache Hit Rate**: Percentage of reports served from cache

### Implementation
```python
class PipelineMonitor:
    """Monitor LLM pipeline performance"""
    
    async def track_processing(self, batch_id: str, metrics: Dict):
        """Track processing metrics"""
        
        await self.prometheus.record({
            'batch_processing_duration': metrics['duration'],
            'tokens_used': metrics['tokens'],
            'model_used': metrics['model'],
            'report_quality_score': metrics['quality_score'],
            'cost_usd': metrics['estimated_cost']
        })
        
        # Alert on anomalies
        if metrics['duration'] > 30:  # seconds
            await self.alert("Slow LLM processing", batch_id)
        
        if metrics['quality_score'] < 0.7:
            await self.alert("Low quality report", batch_id)
```

## Next Steps

1. **Implement Core Pipeline**
   - Set up LLM clients (OpenAI, Anthropic)
   - Create prompt templates
   - Build validation system

2. **Optimize for Scale**
   - Implement caching layer
   - Add parallel processing
   - Set up monitoring

3. **Enhance Intelligence**
   - Add pattern recognition
   - Implement predictive models
   - Create custom fine-tuned models

4. **User Features**
   - Custom report templates
   - Real-time alerts
   - API access for reports