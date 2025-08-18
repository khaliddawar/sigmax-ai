// Trading Intelligence Module for SignalScope
// Extracts trading signals, entities, and sentiment from chat messages

// Stock ticker patterns
const TICKER_PATTERNS = {
  US_STOCK: /\b[A-Z]{1,5}\b(?=\s|$|[,.])/g,  // AAPL, MSFT, etc.
  CRYPTO: /\b(BTC|ETH|SOL|DOGE|ADA|DOT|MATIC|LINK|UNI|AVAX)\b/gi,
  FOREX: /\b(EUR\/USD|GBP\/USD|USD\/JPY|AUD\/USD|USD\/CAD)\b/gi
};

// Common trading keywords
const TRADING_KEYWORDS = {
  BUY: ['buy', 'buying', 'bought', 'long', 'bullish', 'calls', 'accumulate', 'adding', 'loading', 'grab'],
  SELL: ['sell', 'selling', 'sold', 'short', 'bearish', 'puts', 'dump', 'exit', 'close'],
  HOLD: ['hold', 'holding', 'keep', 'maintain', 'staying'],
  WATCH: ['watch', 'watching', 'monitor', 'eye on', 'radar'],
  POSITIVE: ['up', 'gain', 'profit', 'green', 'moon', 'rocket', 'breakout', 'surge'],
  NEGATIVE: ['down', 'loss', 'red', 'crash', 'dump', 'plunge', 'fall', 'drop'],
  NEUTRAL: ['flat', 'sideways', 'consolidate', 'range']
};

// Price and number patterns
const NUMBER_PATTERNS = {
  PRICE: /\$[\d,]+\.?\d*/g,  // $123.45
  PERCENTAGE: /[\+\-]?\d+\.?\d*%/g,  // +15%, -3.2%
  QUANTITY: /\b\d+[kKmMbB]?\s*(shares?|units?|coins?|lots?)\b/gi,  // 1000 shares, 5k units
  MILLION_BILLION: /\b\d+\.?\d*\s*(million|billion|mil|bil|mn|bn)\b/gi
};

// Influential traders/investors
const INFLUENCERS = {
  'warren': 'Warren Buffett',
  'buffett': 'Warren Buffett',
  'elon': 'Elon Musk',
  'musk': 'Elon Musk',
  'cathie': 'Cathie Wood',
  'wood': 'Cathie Wood',
  'dalio': 'Ray Dalio',
  'ackman': 'Bill Ackman',
  'soros': 'George Soros',
  'cohen': 'Steve Cohen',
  'druckenmiller': 'Stanley Druckenmiller'
};

class TradingIntelligence {
  
  // Extract all entities from message
  static extractEntities(text) {
    const entities = {
      tickers: [],
      prices: [],
      percentages: [],
      quantities: [],
      persons: [],
      currencies: []
    };
    
    // Extract tickers
    const tickers = new Set();
    
    // US Stocks
    const stockMatches = text.match(TICKER_PATTERNS.US_STOCK) || [];
    stockMatches.forEach(ticker => {
      // Filter out common words that match pattern but aren't tickers
      if (ticker.length > 1 && !this.isCommonWord(ticker)) {
        tickers.add(ticker);
      }
    });
    
    // Crypto
    const cryptoMatches = text.match(TICKER_PATTERNS.CRYPTO) || [];
    cryptoMatches.forEach(ticker => tickers.add(ticker.toUpperCase()));
    
    // Forex
    const forexMatches = text.match(TICKER_PATTERNS.FOREX) || [];
    forexMatches.forEach(pair => entities.currencies.push(pair));
    
    entities.tickers = Array.from(tickers);
    
    // Extract prices
    const priceMatches = text.match(NUMBER_PATTERNS.PRICE) || [];
    entities.prices = priceMatches;
    
    // Extract percentages
    const percentMatches = text.match(NUMBER_PATTERNS.PERCENTAGE) || [];
    entities.percentages = percentMatches;
    
    // Extract quantities
    const quantityMatches = text.match(NUMBER_PATTERNS.QUANTITY) || [];
    const millionBillionMatches = text.match(NUMBER_PATTERNS.MILLION_BILLION) || [];
    entities.quantities = [...quantityMatches, ...millionBillionMatches];
    
    // Extract influential persons
    const lowerText = text.toLowerCase();
    Object.keys(INFLUENCERS).forEach(key => {
      if (lowerText.includes(key)) {
        entities.persons.push(INFLUENCERS[key]);
      }
    });
    
    return entities;
  }
  
  // Analyze sentiment of the message
  static analyzeSentiment(text) {
    const lowerText = text.toLowerCase();
    let score = 0;
    let signals = [];
    
    // Count positive indicators
    TRADING_KEYWORDS.BUY.forEach(word => {
      if (lowerText.includes(word)) {
        score += 1;
        signals.push({ word, type: 'buy' });
      }
    });
    
    TRADING_KEYWORDS.POSITIVE.forEach(word => {
      if (lowerText.includes(word)) {
        score += 0.5;
        signals.push({ word, type: 'positive' });
      }
    });
    
    // Count negative indicators
    TRADING_KEYWORDS.SELL.forEach(word => {
      if (lowerText.includes(word)) {
        score -= 1;
        signals.push({ word, type: 'sell' });
      }
    });
    
    TRADING_KEYWORDS.NEGATIVE.forEach(word => {
      if (lowerText.includes(word)) {
        score -= 0.5;
        signals.push({ word, type: 'negative' });
      }
    });
    
    // Normalize score to -1 to 1
    const normalizedScore = Math.max(-1, Math.min(1, score / 5));
    
    // Determine overall sentiment
    let sentiment = 'neutral';
    if (normalizedScore > 0.3) sentiment = 'bullish';
    else if (normalizedScore < -0.3) sentiment = 'bearish';
    
    // Calculate confidence based on signal count
    const confidence = Math.min(1, signals.length / 10);
    
    return {
      score: normalizedScore,
      sentiment,
      confidence,
      signals
    };
  }
  
  // Classify trading signal type
  static classifyTradingSignal(text, entities, sentiment) {
    const lowerText = text.toLowerCase();
    let signal = null;
    
    // Check for explicit buy/sell signals
    const hasBuySignal = TRADING_KEYWORDS.BUY.some(word => lowerText.includes(word));
    const hasSellSignal = TRADING_KEYWORDS.SELL.some(word => lowerText.includes(word));
    const hasHoldSignal = TRADING_KEYWORDS.HOLD.some(word => lowerText.includes(word));
    const hasWatchSignal = TRADING_KEYWORDS.WATCH.some(word => lowerText.includes(word));
    
    if (hasBuySignal && entities.tickers.length > 0) {
      signal = {
        action: 'BUY',
        tickers: entities.tickers,
        strength: sentiment.score > 0.5 ? 'strong' : 'moderate',
        confidence: sentiment.confidence
      };
    } else if (hasSellSignal && entities.tickers.length > 0) {
      signal = {
        action: 'SELL',
        tickers: entities.tickers,
        strength: sentiment.score < -0.5 ? 'strong' : 'moderate',
        confidence: sentiment.confidence
      };
    } else if (hasHoldSignal && entities.tickers.length > 0) {
      signal = {
        action: 'HOLD',
        tickers: entities.tickers,
        strength: 'moderate',
        confidence: sentiment.confidence
      };
    } else if (hasWatchSignal && entities.tickers.length > 0) {
      signal = {
        action: 'WATCH',
        tickers: entities.tickers,
        strength: 'moderate',
        confidence: sentiment.confidence
      };
    }
    
    // Add price targets if found
    if (signal && entities.prices.length > 0) {
      signal.priceTargets = entities.prices;
    }
    
    // Add position size if found
    if (signal && entities.quantities.length > 0) {
      signal.positionSize = entities.quantities[0];
    }
    
    return signal;
  }
  
  // Check if a word is common (not a ticker)
  static isCommonWord(word) {
    const commonWords = ['I', 'A', 'THE', 'AND', 'OR', 'BUT', 'IT', 'IS', 'AT', 'TO', 'UP', 'IN', 'ON', 'BY', 'AS', 'MY', 'BE', 'DO', 'GO', 'NO', 'SO', 'HE', 'WE', 'ME', 'IF'];
    return commonWords.includes(word.toUpperCase());
  }
  
  // Extract thread context
  static extractContext(messageElement) {
    const context = {
      isReply: false,
      replyTo: null,
      thread_id: null,
      reactions: [],
      importance: 'normal'
    };
    
    // Check if it's a reply
    const replyIndicator = messageElement.querySelector('[class*="reply"], [class*="thread"]');
    if (replyIndicator) {
      context.isReply = true;
      context.replyTo = replyIndicator.textContent?.trim();
    }
    
    // Extract reactions/emojis
    const reactions = messageElement.querySelectorAll('[class*="reaction"], [class*="emoji"]');
    reactions.forEach(reaction => {
      const emoji = reaction.textContent?.trim();
      if (emoji) {
        context.reactions.push(emoji);
      }
    });
    
    // Determine importance based on reactions
    if (context.reactions.length > 5) {
      context.importance = 'high';
    } else if (context.reactions.length > 2) {
      context.importance = 'medium';
    }
    
    // Generate thread ID from position
    const parent = messageElement.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children);
      const index = siblings.indexOf(messageElement);
      context.thread_id = `thread-${index}`;
    }
    
    return context;
  }
  
  // Main processing function
  static processMessage(text, messageElement = null) {
    // Extract entities
    const entities = this.extractEntities(text);
    
    // Analyze sentiment
    const sentiment = this.analyzeSentiment(text);
    
    // Classify trading signal
    const tradingSignal = this.classifyTradingSignal(text, entities, sentiment);
    
    // Extract context if element provided
    const context = messageElement ? this.extractContext(messageElement) : null;
    
    // Build the result object
    const result = {
      entities,
      sentiment,
      tradingSignal,
      context,
      processed: true,
      processingVersion: '1.0'
    };
    
    // Calculate and add importance score
    result.importance = this.calculateImportance(result);
    
    return result;
  }
  
  // Calculate message importance score
  static calculateImportance(processedData) {
    let score = 0;
    
    // Has trading signal
    if (processedData.tradingSignal) {
      score += 3;
      if (processedData.tradingSignal.strength === 'strong') {
        score += 2;
      }
    }
    
    // Has tickers
    score += Math.min(processedData.entities.tickers.length * 0.5, 2);
    
    // Has influential person mentioned
    score += processedData.entities.persons.length * 2;
    
    // Has prices/targets
    score += processedData.entities.prices.length * 0.5;
    
    // Strong sentiment
    if (Math.abs(processedData.sentiment.score) > 0.7) {
      score += 1;
    }
    
    // High confidence
    if (processedData.sentiment.confidence > 0.7) {
      score += 1;
    }
    
    // Context importance
    if (processedData.context?.importance === 'high') {
      score += 2;
    }
    
    return Math.min(10, score); // Cap at 10
  }
}

// Export for use in content script
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TradingIntelligence;
} else if (typeof window !== 'undefined') {
  window.TradingIntelligence = TradingIntelligence;
}