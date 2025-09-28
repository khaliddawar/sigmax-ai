# SignalScope Coding Standards

## Overview
This document defines the coding standards and best practices for the SignalScope Chrome Extension project.

## General Principles
- **Clarity over cleverness**: Write code that is easy to understand
- **Consistency**: Follow established patterns throughout the codebase
- **Security first**: Always validate inputs and sanitize outputs
- **Performance conscious**: Optimize for minimal memory footprint in extension context

## JavaScript/TypeScript Standards

### File Naming
- Use kebab-case for file names: `message-handler.js`, `webhook-client.ts`
- Test files: `{filename}.test.js` or `{filename}.spec.ts`
- Constants files: `{feature}.constants.js`

### Code Style
- **Indentation**: 2 spaces
- **Quotes**: Single quotes for strings, except JSON
- **Semicolons**: Always use semicolons
- **Line length**: Max 100 characters
- **Comments**: JSDoc for functions, inline for complex logic

### Naming Conventions
```javascript
// Classes: PascalCase
class WebhookManager {}

// Functions/Methods: camelCase
function processMessage() {}

// Constants: UPPER_SNAKE_CASE
const MAX_RETRY_ATTEMPTS = 3;

// Variables: camelCase
let messageQueue = [];

// Private methods: prefix with underscore
_validateSelector() {}
```

### Async/Await
- Always use async/await over promises when possible
- Handle errors with try/catch blocks
- Never ignore caught errors

### Error Handling
```javascript
try {
  const result = await sendWebhook(data);
  return result;
} catch (error) {
  console.error('[WebhookManager] Send failed:', error);
  // Implement retry logic or user notification
  throw new WebhookError('Failed to send webhook', error);
}
```

## Chrome Extension Specific

### Manifest V3 Compliance
- Use service workers instead of background pages
- Implement proper message passing between contexts
- Follow Chrome's security best practices

### Message Passing
```javascript
// Always validate message source and type
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id) return;
  
  switch(request.type) {
    case 'CAPTURE_MESSAGE':
      handleCapture(request.data);
      break;
    default:
      console.warn('Unknown message type:', request.type);
  }
});
```

### Storage
- Use chrome.storage.sync for user preferences
- Use chrome.storage.local for cache and temporary data
- Always handle storage quota errors

## HTML/CSS Standards

### HTML
- Semantic HTML5 elements
- Accessibility attributes (aria-labels, roles)
- Data attributes for JavaScript hooks: `data-action`, `data-target`

### CSS
- BEM naming convention for classes
- CSS variables for theming
- Mobile-first responsive design

```css
/* Block__Element--Modifier */
.webhook-form {}
.webhook-form__input {}
.webhook-form__input--error {}

/* CSS Variables */
:root {
  --color-primary: #4287f5;
  --spacing-unit: 8px;
}
```

## Testing Standards

### Unit Tests
- Test coverage minimum: 80%
- Test file structure mirrors source
- Use descriptive test names

```javascript
describe('WebhookManager', () => {
  describe('sendWebhook', () => {
    it('should successfully send webhook with valid data', async () => {
      // Test implementation
    });
    
    it('should retry on network failure', async () => {
      // Test implementation
    });
  });
});
```

### Integration Tests
- Test message passing between contexts
- Test storage operations
- Test webhook delivery

## Git Commit Standards

### Commit Message Format
```
type(scope): subject

body (optional)

footer (optional)
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build process or auxiliary tool changes

### Examples
```
feat(webhook): add retry logic for failed requests

fix(selector): handle dynamic DOM changes in Discord

docs(readme): update installation instructions
```

## Code Review Checklist
- [ ] Code follows naming conventions
- [ ] Proper error handling implemented
- [ ] Security considerations addressed
- [ ] Performance impact assessed
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No console.log statements in production code
- [ ] No hardcoded values (use constants/config)

## Security Standards

### Data Handling
- Never log sensitive data (tokens, passwords)
- Sanitize all user inputs
- Validate webhook URLs
- Implement rate limiting

### Permissions
- Request minimal Chrome permissions
- Explain permission usage in documentation
- Implement permission checks before operations

## Performance Standards

### Memory Management
- Clean up event listeners
- Clear intervals/timeouts
- Implement garbage collection friendly patterns
- Monitor memory usage in DevTools

### Optimization
- Debounce/throttle event handlers
- Batch DOM operations
- Lazy load non-critical resources
- Implement virtual scrolling for large lists

## Documentation Standards

### Code Documentation
- JSDoc for all public functions
- README for each major module
- Inline comments for complex algorithms
- API documentation for webhook format

### User Documentation
- Installation guide
- Configuration guide
- Troubleshooting guide
- Video tutorials for complex features