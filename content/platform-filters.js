import { createLogger } from '../shared/logger.js';

const logger = createLogger('PlatformFilters');

/**
 * Determine whether to skip a captured message based on platform-specific rules.
 * Centralized filtering so all capture paths (DOM/network) respect the same policy.
 *
 * @param {Object} message - Normalized message object
 * @returns {boolean} true if the message should be skipped
 */
export function shouldSkipMessage(message) {
  try {
    if (!message) return false;

    const platform = (message.platform || '').toLowerCase();
    const author = (message.author || '').trim();
    const content = (message.content || '').trim();

    // Normalize for emoji or symbols at the start of content
    const normalized = content.replace(/^[^A-Za-z]+/, '');

    // Telegram: skip system-style entries like "Unknown in #general"
    if (platform === 'telegram') {
      if (author === 'Unknown' && /^(Unknown\s+in\s+#)/i.test(normalized)) {
        logger.debug('Filtered Telegram system message (Unknown in #...)');
        return true;
      }
    }

    return false;
  } catch (error) {
    logger.error('Error in shouldSkipMessage:', error);
    return false;
  }
}

export default { shouldSkipMessage };


