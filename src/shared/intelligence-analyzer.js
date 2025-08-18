import { createLogger } from './logger.js';

const logger = createLogger('IntelligenceAnalyzer');

class IntelligenceAnalyzer {
  analyzeMessage(content) {
    try {
      const entities = this.extractEntities(content);
      const sentiment = this.analyzeSentiment(content);
      const importance = this.calculateImportance(content, entities, sentiment);
      const tradingSignal = this.extractTradingSignal(content, entities, sentiment);
      
      return {
        entities,
        sentiment,
        importance,
        tradingSignal
      };
    } catch (error) {
      logger.error('Error analyzing message:', error);
      return this.getDefaultIntelligence();
    }
  }
  
  extractEntities(content) {
    const tickers = this.extractTickers(content);
    const prices = this.extractPrices(content);
    const percentages = this.extractPercentages(content);
    const quantities = this.extractQuantities(content);
    
    return {
      tickers,
      prices,
      percentages,
      quantities
    };
  }
  
  extractTickers(content) {
    const tickers = [];
    
    // Match common stock patterns ($SYMBOL or SYMBOL in all caps 2-5 chars)
    const tickerPattern = /\$[A-Z]{1,5}|\b[A-Z]{2,5}\b/g;
    const matches = content.match(tickerPattern) || [];
    
    // Filter and clean
    matches.forEach(match => {
      const ticker = match.replace('$', '').trim();
      // Basic validation - exclude common words
      const commonWords = ['I', 'A', 'THE', 'AND', 'OR', 'BUT', 'NOT', 'FOR', 'TO', 'AT', 'BY', 'IN', 'ON', 'UP', 'DO', 'IT', 'IS', 'BE', 'AS', 'IF', 'SO', 'NO', 'YES', 'OK', 'GO'];
      if (!commonWords.includes(ticker) && ticker.length >= 2) {
        tickers.push(ticker);
      }
    });
    
    return [...new Set(tickers)]; // Remove duplicates
  }
  
  extractPrices(content) {
    const prices = [];
    
    // Match price patterns ($123.45, 123.45, etc)
    const pricePattern = /\$[\d,]+\.?\d*|\b\d+\.?\d*\s*(?:dollars?|usd|cents?)\b/gi;
    const matches = content.match(pricePattern) || [];
    
    matches.forEach(match => {
      prices.push(match.trim());
    });
    
    return prices;
  }
  
  extractPercentages(content) {
    const percentages = [];
    
    // Match percentage patterns (12%, +5.5%, -3.2%, etc)
    const percentPattern = /[+-]?\d+\.?\d*\s*%/g;
    const matches = content.match(percentPattern) || [];
    
    matches.forEach(match => {
      percentages.push(match.trim());
    });
    
    return percentages;
  }
  
  extractQuantities(content) {
    const quantities = [];
    
    // Match quantity patterns (100 shares, 5k, 10M, etc)
    const quantityPattern = /\b\d+\.?\d*\s*(?:shares?|contracts?|lots?|units?|[kmb])\b/gi;
    const matches = content.match(quantityPattern) || [];
    
    matches.forEach(match => {
      quantities.push(match.trim());
    });
    
    return quantities;
  }
  
  analyzeSentiment(content) {
    const lowerContent = content.toLowerCase();
    
    // Simple keyword-based sentiment analysis
    const bullishKeywords = [
      'bullish', 'buy', 'long', 'call', 'calls', 'moon', 'rocket', 'up', 'green',
      'pump', 'rally', 'breakout', 'strong', 'positive', 'good', 'great', 'excellent',
      'growth', 'gain', 'profit', 'winner', 'surge', 'soar', 'rise'
    ];
    
    const bearishKeywords = [
      'bearish', 'sell', 'short', 'put', 'puts', 'dump', 'crash', 'down', 'red',
      'drop', 'fall', 'decline', 'negative', 'bad', 'weak', 'loss', 'loser',
      'plunge', 'tank', 'sink', 'collapse'
    ];
    
    let bullishScore = 0;
    let bearishScore = 0;
    
    bullishKeywords.forEach(keyword => {
      if (lowerContent.includes(keyword)) bullishScore++;
    });
    
    bearishKeywords.forEach(keyword => {
      if (lowerContent.includes(keyword)) bearishScore++;
    });
    
    // Calculate sentiment
    let sentiment = 'neutral';
    let score = 0;
    let confidence = 0.5;
    
    if (bullishScore > bearishScore) {
      sentiment = 'bullish';
      score = Math.min(1, bullishScore / 5);
      confidence = Math.min(1, (bullishScore - bearishScore) / 5);
    } else if (bearishScore > bullishScore) {
      sentiment = 'bearish';
      score = Math.max(-1, -bearishScore / 5);
      confidence = Math.min(1, (bearishScore - bullishScore) / 5);
    } else {
      sentiment = 'neutral';
      score = 0;
      confidence = 0.3;
    }
    
    return {
      score,
      sentiment,
      confidence
    };
  }
  
  calculateImportance(content, entities, sentiment) {
    let importance = 5; // Base importance
    
    // Increase importance based on entities
    if (entities.tickers.length > 0) importance += 1;
    if (entities.prices.length > 0) importance += 1;
    if (entities.percentages.length > 0) importance += 1;
    
    // Increase importance for strong sentiment
    if (Math.abs(sentiment.score) > 0.5) importance += 1;
    if (sentiment.confidence > 0.7) importance += 1;
    
    // Check for urgency keywords
    const urgencyKeywords = ['now', 'urgent', 'alert', 'breaking', 'immediately', 'asap'];
    const lowerContent = content.toLowerCase();
    if (urgencyKeywords.some(keyword => lowerContent.includes(keyword))) {
      importance += 2;
    }
    
    // Cap at 10
    return Math.min(10, Math.round(importance));
  }
  
  extractTradingSignal(content, entities, sentiment) {
    // Only extract trading signal if we have tickers and clear sentiment
    if (entities.tickers.length === 0 || sentiment.confidence < 0.5) {
      return null;
    }
    
    let action = 'HOLD';
    let strength = 'moderate';
    
    if (sentiment.sentiment === 'bullish') {
      action = 'BUY';
      if (sentiment.score > 0.7) strength = 'strong';
      else if (sentiment.score < 0.3) strength = 'weak';
    } else if (sentiment.sentiment === 'bearish') {
      action = 'SELL';
      if (sentiment.score < -0.7) strength = 'strong';
      else if (sentiment.score > -0.3) strength = 'weak';
    }
    
    return {
      action,
      tickers: entities.tickers,
      strength
    };
  }
  
  getDefaultIntelligence() {
    return {
      entities: {
        tickers: [],
        prices: [],
        percentages: [],
        quantities: []
      },
      sentiment: {
        score: 0,
        sentiment: 'neutral',
        confidence: 0.1
      },
      importance: 3,
      tradingSignal: null
    };
  }
}

export default IntelligenceAnalyzer;