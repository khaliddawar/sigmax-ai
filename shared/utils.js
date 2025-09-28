// Utility functions

/**
 * Validate URL format
 * @param {string} url - URL to validate
 * @returns {boolean} - True if valid URL
 */
export function isValidUrl(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.protocol === 'https:' || urlObj.protocol === 'http:';
  } catch {
    return false;
  }
}

/**
 * Generate unique ID
 * @returns {string} - Unique identifier
 */
export function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Debounce function execution
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function execution
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} - Throttled function
 */
export function throttle(func, limit) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Deep clone object
 * @param {Object} obj - Object to clone
 * @returns {Object} - Cloned object
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  if (obj instanceof Date) {
    return new Date(obj.getTime());
  }
  if (obj instanceof Array) {
    return obj.map((item) => deepClone(item));
  }
  if (obj instanceof Object) {
    const clonedObj = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key]);
      }
    }
    return clonedObj;
  }
}

/**
 * Retry function with exponential backoff
 * @param {Function} fn - Function to retry
 * @param {number} maxAttempts - Maximum retry attempts
 * @param {number} baseDelay - Base delay in milliseconds
 * @returns {Promise} - Promise resolving to function result
 */
export async function retryWithBackoff(fn, maxAttempts = 3, baseDelay = 1000) {
  let lastError;
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (attempt < maxAttempts - 1) {
        const delay = Math.min(baseDelay * Math.pow(2, attempt), 30000);
        await sleep(delay);
      }
    }
  }
  
  throw lastError;
}

/**
 * Sleep for specified duration
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise} - Promise that resolves after timeout
 */
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Format timestamp to ISO string
 * @param {number|Date|string} timestamp - Timestamp to format
 * @returns {string} - ISO formatted string
 */
export function formatTimestamp(timestamp) {
  if (!timestamp) {
    return new Date().toISOString();
  }
  
  if (timestamp instanceof Date) {
    return timestamp.toISOString();
  }
  
  if (typeof timestamp === 'string') {
    return new Date(timestamp).toISOString();
  }
  
  if (typeof timestamp === 'number') {
    return new Date(timestamp).toISOString();
  }
  
  return new Date().toISOString();
}

/**
 * Sanitize HTML content
 * @param {string} html - HTML string to sanitize
 * @returns {string} - Sanitized text content
 */
export function sanitizeHtml(html) {
  const temp = document.createElement('div');
  temp.textContent = html;
  return temp.innerHTML;
}

/**
 * Extract text from HTML
 * @param {string} html - HTML string
 * @returns {string} - Plain text content
 */
export function extractText(html) {
  const temp = document.createElement('div');
  temp.innerHTML = html;
  return temp.textContent || temp.innerText || '';
}

/**
 * Chunk array into smaller arrays
 * @param {Array} array - Array to chunk
 * @param {number} size - Chunk size
 * @returns {Array} - Array of chunks
 */
export function chunkArray(array, size) {
  const chunks = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

/**
 * Get domain from URL
 * @param {string} url - URL to parse
 * @returns {string} - Domain name
 */
export function getDomain(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname;
  } catch {
    return '';
  }
}

/**
 * Check if running in extension context
 * @returns {boolean} - True if in extension context
 */
export function isExtensionContext() {
  return typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id;
}

/**
 * Get current tab info
 * @returns {Promise<Object>} - Current tab information
 */
export async function getCurrentTab() {
  if (!isExtensionContext()) {
    return null;
  }
  
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0] || null);
    });
  });
}

/**
 * Safe JSON parse
 * @param {string} str - JSON string to parse
 * @param {*} defaultValue - Default value if parsing fails
 * @returns {*} - Parsed object or default value
 */
export function safeJsonParse(str, defaultValue = null) {
  try {
    return JSON.parse(str);
  } catch {
    return defaultValue;
  }
}

/**
 * Create idempotency key
 * @param {Object} data - Data to create key from
 * @returns {string} - Idempotency key
 */
export function createIdempotencyKey(data) {
  const str = JSON.stringify(data);
  // Convert to UTF-8 then base64 to handle non-Latin1 characters
  const encoded = btoa(unescape(encodeURIComponent(str)));
  return encoded.replace(/[^a-zA-Z0-9]/g, '').substring(0, 32);
}

/**
 * Detect platform from URL
 * @param {string} url - Current page URL
 * @returns {string|null} - Platform ID or null
 */
export function detectPlatform(url) {
  const domain = getDomain(url);
  
  if (domain.includes('discord.com')) {
    return 'discord';
  }
  if (domain.includes('telegram.org')) {
    return 'telegram';
  }
  if (domain.includes('slack.com')) {
    return 'slack';
  }
  if (domain.includes('whatsapp.com')) {
    return 'whatsapp';
  }
  
  return null;
}