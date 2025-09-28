// Application constants
export const APP_NAME = 'SignalScope';
export const APP_VERSION = '1.0.0';

// Storage keys
export const STORAGE_KEYS = {
  WEBHOOK_URL: 'webhookUrl',
  WEBHOOK_SECRET: 'webhookSecret',
  ENABLED: 'enabled',
  PLATFORMS: 'platforms',
  SELECTORS: 'selectors',
  BATCH_SIZE: 'batchSize',
  BATCH_INTERVAL: 'batchInterval',
  RETRY_ATTEMPTS: 'retryAttempts',
  MESSAGE_QUEUE: 'messageQueue',
  FAILED_QUEUE: 'failedQueue',
  STATS: 'stats'
};

// Message types for communication
export const MESSAGE_TYPES = {
  CAPTURE_MESSAGE: 'CAPTURE_MESSAGE',
  SEND_WEBHOOK: 'SEND_WEBHOOK',
  UPDATE_SETTINGS: 'UPDATE_SETTINGS',
  GET_STATS: 'GET_STATS',
  CLEAR_QUEUE: 'CLEAR_QUEUE',
  TEST_WEBHOOK: 'TEST_WEBHOOK',
  PLATFORM_DETECTED: 'PLATFORM_DETECTED',
  ERROR: 'ERROR',
  SUCCESS: 'SUCCESS'
};

// Webhook configuration
export const WEBHOOK_CONFIG = {
  DEFAULT_BATCH_SIZE: 10,
  DEFAULT_BATCH_INTERVAL: 5000, // 5 seconds
  MAX_RETRY_ATTEMPTS: 3,
  RETRY_DELAY_BASE: 1000, // 1 second
  RETRY_DELAY_MAX: 30000, // 30 seconds
  TIMEOUT: 10000, // 10 seconds
  MAX_QUEUE_SIZE: 1000
};

// Platform configurations
export const PLATFORMS = {
  DISCORD: {
    id: 'discord',
    name: 'Discord',
    hostname: 'discord.com',
    selectors: {
      message: '[id^="chat-messages-"]',
      author: '[class*="username-"]',
      content: '[class*="messageContent-"]',
      timestamp: 'time[datetime]',
      channel: '[class*="title-"] h1'
    }
  },
  TELEGRAM: {
    id: 'telegram',
    name: 'Telegram',
    hostname: 'web.telegram.org',
    selectors: {
      message: '.message, .message-in, .message-out',
      author: '.message-title, .peer-title, [class*="peer-title"], [class*="author"], .name, .translatable-message strong',
      content: '.message-text, .text-content, [class*="text-content"], .message-content, .translatable-message',
      timestamp: '.message-time, .time, [class*="time"], .timestamp',
      channel: '.chat-info-name, .peer-title, [class*="chat-title"], .title'
    }
  },
  SLACK: {
    id: 'slack',
    name: 'Slack',
    hostname: 'slack.com',
    selectors: {
      message: '[data-qa="message_container"]',
      author: '[data-qa="message_sender"]',
      content: '[data-qa="message_content"]',
      timestamp: '[data-qa="message_time"]',
      channel: '[data-qa="channel_name"]'
    }
  },
  WHATSAPP: {
    id: 'whatsapp',
    name: 'WhatsApp',
    hostname: 'web.whatsapp.com',
    selectors: {
      message: '[class*="message-"]',
      author: '[class*="copyable-text"][data-pre-plain-text]',
      content: '[class*="copyable-text"] span',
      timestamp: '[class*="copyable-text"][data-pre-plain-text]',
      channel: '[class*="chat-title"]'
    }
  }
};

// HTTP status codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504
};

// Error messages
export const ERROR_MESSAGES = {
  WEBHOOK_URL_REQUIRED: 'Webhook URL is required',
  INVALID_WEBHOOK_URL: 'Invalid webhook URL',
  WEBHOOK_SEND_FAILED: 'Failed to send webhook',
  STORAGE_ERROR: 'Storage operation failed',
  PLATFORM_NOT_DETECTED: 'Chat platform not detected',
  SELECTOR_NOT_FOUND: 'Required selector not found',
  QUEUE_FULL: 'Message queue is full',
  NETWORK_ERROR: 'Network error occurred',
  TIMEOUT_ERROR: 'Request timeout',
  UNKNOWN_ERROR: 'An unknown error occurred'
};

// Success messages
export const SUCCESS_MESSAGES = {
  WEBHOOK_SENT: 'Webhook sent successfully',
  SETTINGS_SAVED: 'Settings saved successfully',
  QUEUE_CLEARED: 'Queue cleared successfully',
  TEST_SUCCESSFUL: 'Webhook test successful',
  EXTENSION_ENABLED: 'Extension enabled',
  EXTENSION_DISABLED: 'Extension disabled'
};

// Alarm names
export const ALARM_NAMES = {
  BATCH_PROCESS: 'batchProcess',
  RETRY_FAILED: 'retryFailed',
  CLEANUP: 'cleanup'
};

// Default settings
export const DEFAULT_SETTINGS = {
  enabled: true,
  batchSize: WEBHOOK_CONFIG.DEFAULT_BATCH_SIZE,
  batchInterval: WEBHOOK_CONFIG.DEFAULT_BATCH_INTERVAL,
  retryAttempts: WEBHOOK_CONFIG.MAX_RETRY_ATTEMPTS,
  platforms: Object.keys(PLATFORMS).map((key) => PLATFORMS[key].id)
};