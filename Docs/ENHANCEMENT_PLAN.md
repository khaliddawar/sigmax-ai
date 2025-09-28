# SignalScope Enhancement Implementation Plan

## Overview
This document provides a comprehensive, safety-first implementation plan for three critical enhancements to SignalScope's message capture system. Each enhancement includes detailed design, implementation steps, testing procedures, and rollback strategies.

## Enhancement Priority Matrix

| Enhancement | Priority | Risk Level | Implementation Effort | User Impact |
|------------|----------|------------|----------------------|-------------|
| Content-Based Message Hashing | HIGH | LOW | Medium (2-3 days) | Prevents all duplicates |
| Message Sequence Validation | MEDIUM | MEDIUM | High (3-4 days) | Detects missing messages |
| Connection State Recovery | HIGH | MEDIUM | High (4-5 days) | Handles disconnections |

---

## Enhancement 1: Content-Based Message Hashing

### Objective
Implement cryptographic hashing of message content to provide absolute duplicate prevention, even when message IDs differ.

### Design Specification

```javascript
// File: src/shared/message-hasher.js
export class MessageHasher {
  constructor() {
    this.hashCache = new Map(); // LRU cache for performance
    this.maxCacheSize = 1000;
  }

  async generateHash(message) {
    // Normalize message for consistent hashing
    const normalized = this.normalizeMessage(message);
    const cacheKey = this.getCacheKey(normalized);
    
    // Check cache first
    if (this.hashCache.has(cacheKey)) {
      return this.hashCache.get(cacheKey);
    }
    
    // Generate SHA-256 hash
    const hash = await this.computeHash(normalized);
    this.updateCache(cacheKey, hash);
    
    return hash;
  }

  normalizeMessage(message) {
    return {
      author: message.author?.toLowerCase().trim(),
      content: this.normalizeContent(message.content),
      channel: message.channel?.toLowerCase().trim(),
      // Round timestamp to nearest second to handle minor timing differences
      timestamp: Math.floor(message.timestamp / 1000)
    };
  }

  normalizeContent(content) {
    if (!content) return '';
    
    return content
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ')  // Normalize whitespace
      .replace(/[\u200B-\u200D\uFEFF]/g, ''); // Remove zero-width chars
  }

  async computeHash(normalized) {
    const encoder = new TextEncoder();
    const data = encoder.encode(JSON.stringify(normalized));
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  updateCache(key, value) {
    // Implement LRU eviction
    if (this.hashCache.size >= this.maxCacheSize) {
      const firstKey = this.hashCache.keys().next().value;
      this.hashCache.delete(firstKey);
    }
    this.hashCache.set(key, value);
  }

  getCacheKey(normalized) {
    return `${normalized.author}:${normalized.channel}:${normalized.timestamp}`;
  }
}
```

### Implementation Steps

#### Phase 1: Core Hashing (Day 1)
1. Create `message-hasher.js` module
2. Implement normalization logic
3. Add SHA-256 hashing with Web Crypto API
4. Implement LRU cache for performance

#### Phase 2: Integration (Day 2)
1. Update `message-parser.js` to include hash generation
2. Modify `webhook-manager.js` to check hash before queuing
3. Add hash storage in IndexedDB for persistence
4. Update message data structure

#### Phase 3: Testing & Optimization (Day 3)
1. Unit tests for hash consistency
2. Performance benchmarking
3. Cache tuning
4. Edge case handling

### Safety Measures
- **Feature Flag**: Enable/disable via settings
- **Backward Compatibility**: Works alongside existing ID system
- **Performance Monitoring**: Track hashing time
- **Fallback**: If hashing fails, fall back to ID-only deduplication

### Testing Strategy
```javascript
// Test cases to implement
describe('MessageHasher', () => {
  it('should generate consistent hashes for identical messages');
  it('should generate different hashes for different content');
  it('should handle Unicode and emoji correctly');
  it('should normalize whitespace variations');
  it('should handle missing fields gracefully');
  it('should maintain performance under load');
});
```

---

## Enhancement 2: Message Sequence Validation

### Objective
Detect gaps in message sequences to identify potentially missed messages and maintain conversation integrity.

### Design Specification

```javascript
// File: src/shared/sequence-validator.js
export class MessageSequenceValidator {
  constructor() {
    this.sequences = new Map(); // channelId -> sequence data
    this.gapThreshold = 5000; // 5 seconds
    this.maxSequenceAge = 3600000; // 1 hour
  }

  async validateSequence(channelId, message) {
    const sequence = this.getOrCreateSequence(channelId);
    const validation = {
      isValid: true,
      gaps: [],
      warnings: []
    };

    // Check temporal sequence
    if (sequence.lastTimestamp) {
      const timeDiff = message.timestamp - sequence.lastTimestamp;
      
      if (timeDiff < 0) {
        validation.warnings.push({
          type: 'out_of_order',
          expected: sequence.lastTimestamp,
          actual: message.timestamp
        });
      } else if (timeDiff > this.gapThreshold) {
        validation.gaps.push({
          start: sequence.lastTimestamp,
          end: message.timestamp,
          duration: timeDiff
        });
      }
    }

    // Check message counter if available
    if (message.messageNumber && sequence.lastMessageNumber) {
      const expectedNumber = sequence.lastMessageNumber + 1;
      if (message.messageNumber !== expectedNumber) {
        validation.gaps.push({
          type: 'missing_messages',
          expected: expectedNumber,
          actual: message.messageNumber,
          missing: message.messageNumber - expectedNumber
        });
      }
    }

    // Update sequence
    this.updateSequence(channelId, message);
    
    // Clean old sequences
    this.cleanOldSequences();
    
    return validation;
  }

  getOrCreateSequence(channelId) {
    if (!this.sequences.has(channelId)) {
      this.sequences.set(channelId, {
        lastTimestamp: null,
        lastMessageNumber: null,
        lastMessageId: null,
        messageCount: 0,
        gapCount: 0,
        createdAt: Date.now()
      });
    }
    return this.sequences.get(channelId);
  }

  updateSequence(channelId, message) {
    const sequence = this.sequences.get(channelId);
    sequence.lastTimestamp = message.timestamp;
    sequence.lastMessageNumber = message.messageNumber || null;
    sequence.lastMessageId = message.id;
    sequence.messageCount++;
    sequence.updatedAt = Date.now();
  }

  cleanOldSequences() {
    const now = Date.now();
    for (const [channelId, sequence] of this.sequences) {
      if (now - sequence.updatedAt > this.maxSequenceAge) {
        this.sequences.delete(channelId);
      }
    }
  }

  async handleGap(channelId, gap) {
    // Log gap for monitoring
    console.warn(`Message gap detected in ${channelId}:`, gap);
    
    // Store gap information for recovery attempts
    await this.storeGap(channelId, gap);
    
    // Trigger recovery if configured
    if (this.isRecoveryEnabled()) {
      await this.attemptGapRecovery(channelId, gap);
    }
  }

  async storeGap(channelId, gap) {
    const gaps = await chrome.storage.local.get('messageGaps') || {};
    if (!gaps[channelId]) gaps[channelId] = [];
    gaps[channelId].push({
      ...gap,
      detectedAt: Date.now()
    });
    await chrome.storage.local.set({ messageGaps: gaps });
  }
}
```

### Implementation Steps

#### Phase 1: Core Validation (Day 1-2)
1. Create sequence validator module
2. Implement temporal validation logic
3. Add message number tracking (if available)
4. Create gap detection algorithms

#### Phase 2: Storage & Persistence (Day 2-3)
1. Design IndexedDB schema for sequences
2. Implement sequence persistence
3. Add gap logging and storage
4. Create recovery markers

#### Phase 3: Integration & Recovery (Day 3-4)
1. Integrate with message parser
2. Add recovery attempt mechanisms
3. Implement gap notification system
4. Create monitoring dashboard

### Safety Measures
- **Non-Blocking**: Validation runs asynchronously
- **Configurable Thresholds**: Adjustable gap detection
- **Graceful Degradation**: Works without message numbers
- **Memory Management**: Auto-cleanup of old sequences

### Testing Strategy
```javascript
describe('SequenceValidator', () => {
  it('should detect temporal gaps');
  it('should identify out-of-order messages');
  it('should handle missing message numbers');
  it('should clean up old sequences');
  it('should persist gap information');
  it('should handle high-frequency channels');
});
```

---

## Enhancement 3: Connection State Recovery

### Objective
Maintain message capture continuity across page refreshes, network disconnections, and extension restarts.

### Design Specification

```javascript
// File: src/background/state-recovery.js
export class ConnectionStateManager {
  constructor() {
    this.checkpointInterval = 10000; // 10 seconds
    this.recoveryTimeout = 30000; // 30 seconds
    this.state = {
      isRecovering: false,
      lastCheckpoint: null,
      missedMessageEstimate: 0
    };
  }

  async initialize() {
    // Restore last known state
    await this.restoreState();
    
    // Set up periodic checkpointing
    this.startCheckpointing();
    
    // Monitor connection events
    this.setupConnectionMonitoring();
    
    // Check if recovery needed on startup
    await this.checkRecoveryNeeded();
  }

  async createCheckpoint() {
    const checkpoint = {
      timestamp: Date.now(),
      channels: await this.getActiveChannels(),
      lastMessages: await this.getLastMessages(),
      queueState: await this.getQueueState(),
      statistics: await this.getCaptureStatistics()
    };
    
    await chrome.storage.local.set({
      lastCheckpoint: checkpoint,
      checkpointHistory: await this.updateCheckpointHistory(checkpoint)
    });
    
    return checkpoint;
  }

  async restoreState() {
    const stored = await chrome.storage.local.get([
      'lastCheckpoint',
      'checkpointHistory',
      'recoveryState'
    ]);
    
    if (stored.lastCheckpoint) {
      this.state.lastCheckpoint = stored.lastCheckpoint;
      
      // Check if we need recovery
      const timeSinceCheckpoint = Date.now() - stored.lastCheckpoint.timestamp;
      if (timeSinceCheckpoint > this.recoveryTimeout) {
        await this.initiateRecovery(stored.lastCheckpoint);
      }
    }
  }

  async initiateRecovery(fromCheckpoint) {
    if (this.state.isRecovering) {
      console.log('Recovery already in progress');
      return;
    }
    
    this.state.isRecovering = true;
    
    try {
      console.log('Initiating connection state recovery...');
      
      // Phase 1: Identify gaps
      const gaps = await this.identifyGaps(fromCheckpoint);
      
      // Phase 2: Attempt to recover missed messages
      const recovered = await this.recoverMessages(gaps);
      
      // Phase 3: Update state and resume normal operation
      await this.finalizeRecovery(recovered);
      
      console.log(`Recovery complete. Recovered ${recovered.length} messages`);
    } catch (error) {
      console.error('Recovery failed:', error);
      await this.handleRecoveryFailure(error);
    } finally {
      this.state.isRecovering = false;
    }
  }

  async identifyGaps(fromCheckpoint) {
    const gaps = [];
    const currentChannels = await this.getActiveChannels();
    
    for (const channel of fromCheckpoint.channels) {
      const lastKnown = fromCheckpoint.lastMessages[channel.id];
      const current = await this.getCurrentChannelState(channel.id);
      
      if (this.hasGap(lastKnown, current)) {
        gaps.push({
          channelId: channel.id,
          startTime: lastKnown.timestamp,
          endTime: current.timestamp,
          estimatedMessages: this.estimateMissedMessages(lastKnown, current)
        });
      }
    }
    
    return gaps;
  }

  async recoverMessages(gaps) {
    const recovered = [];
    
    for (const gap of gaps) {
      try {
        // Strategy 1: Check local cache
        const cached = await this.checkLocalCache(gap);
        if (cached.length > 0) {
          recovered.push(...cached);
          continue;
        }
        
        // Strategy 2: Request from content script
        const fromContent = await this.requestFromContentScript(gap);
        if (fromContent.length > 0) {
          recovered.push(...fromContent);
          continue;
        }
        
        // Strategy 3: Mark gap for manual review
        await this.markGapForReview(gap);
      } catch (error) {
        console.error(`Failed to recover gap ${gap.channelId}:`, error);
      }
    }
    
    return recovered;
  }

  setupConnectionMonitoring() {
    // Monitor tab events
    chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
      if (changeInfo.status === 'loading') {
        await this.handleTabReload(tabId, tab);
      }
    });
    
    // Monitor network events
    chrome.webNavigation.onErrorOccurred.addListener(async (details) => {
      await this.handleNavigationError(details);
    });
    
    // Monitor extension lifecycle
    chrome.runtime.onSuspend.addListener(async () => {
      await this.handleSuspend();
    });
    
    chrome.runtime.onStartup.addListener(async () => {
      await this.handleStartup();
    });
  }

  async handleTabReload(tabId, tab) {
    // Create checkpoint before reload completes
    const checkpoint = await this.createCheckpoint();
    
    // Store tab-specific recovery info
    await chrome.storage.session.set({
      [`recovery_${tabId}`]: {
        checkpoint,
        url: tab.url,
        timestamp: Date.now()
      }
    });
  }

  async checkLocalCache(gap) {
    // Check IndexedDB for messages in the gap period
    const db = await this.openDatabase();
    const tx = db.transaction(['messages'], 'readonly');
    const store = tx.objectStore('messages');
    const index = store.index('timestamp');
    
    const range = IDBKeyRange.bound(gap.startTime, gap.endTime);
    const messages = await index.getAll(range);
    
    return messages.filter(msg => msg.channelId === gap.channelId);
  }

  async requestFromContentScript(gap) {
    // Try to get recent messages from content script memory
    const response = await chrome.tabs.sendMessage(gap.tabId, {
      type: 'GET_RECENT_MESSAGES',
      channelId: gap.channelId,
      since: gap.startTime
    });
    
    return response?.messages || [];
  }
}
```

### Implementation Steps

#### Phase 1: State Management (Day 1-2)
1. Create state recovery module
2. Implement checkpoint system
3. Design state storage schema
4. Add state serialization/deserialization

#### Phase 2: Gap Detection (Day 2-3)
1. Implement gap identification logic
2. Create message estimation algorithms
3. Add channel state tracking
4. Implement comparison mechanisms

#### Phase 3: Recovery Strategies (Day 3-4)
1. Implement local cache recovery
2. Add content script querying
3. Create fallback mechanisms
4. Add manual gap marking

#### Phase 4: Integration & Monitoring (Day 4-5)
1. Integrate with service worker lifecycle
2. Add connection event monitoring
3. Implement recovery UI notifications
4. Create recovery metrics dashboard

### Safety Measures
- **Checkpoint Validation**: Verify checkpoint integrity
- **Recovery Timeout**: Prevent infinite recovery loops
- **Resource Limits**: Cap recovery attempts
- **User Control**: Manual recovery trigger option
- **Data Integrity**: Validate recovered messages

### Testing Strategy
```javascript
describe('ConnectionStateManager', () => {
  it('should create valid checkpoints');
  it('should detect connection loss');
  it('should identify message gaps');
  it('should recover from local cache');
  it('should handle recovery failures gracefully');
  it('should prevent duplicate recovery attempts');
  it('should clean up old checkpoints');
});
```

---

## Implementation Timeline

### Week 1: Foundation
- **Day 1-2**: Implement content-based hashing
- **Day 3-4**: Begin sequence validation
- **Day 5**: Integration testing

### Week 2: Core Features
- **Day 1-2**: Complete sequence validation
- **Day 3-4**: Implement state recovery
- **Day 5**: System integration

### Week 3: Testing & Refinement
- **Day 1-2**: Comprehensive testing
- **Day 3**: Performance optimization
- **Day 4**: Documentation
- **Day 5**: Deployment preparation

---

## Risk Mitigation

### Performance Risks
- **Mitigation**: Implement caching, use Web Workers for heavy computation
- **Monitoring**: Add performance metrics collection
- **Fallback**: Ability to disable features if performance degrades

### Data Integrity Risks
- **Mitigation**: Validate all data transformations
- **Testing**: Extensive unit and integration tests
- **Backup**: Keep original message data unchanged

### Compatibility Risks
- **Mitigation**: Feature detection for browser APIs
- **Testing**: Test on minimum Chrome version
- **Graceful Degradation**: Features work independently

---

## Rollback Procedures

### Feature-Level Rollback
```javascript
// Each enhancement has a kill switch
const FEATURE_FLAGS = {
  contentHashing: true,
  sequenceValidation: true,
  stateRecovery: true
};

// Runtime toggle without restart
async function toggleFeature(feature, enabled) {
  await chrome.storage.local.set({
    [`feature_${feature}`]: enabled
  });
  
  // Reload affected modules
  await reloadFeatureModule(feature);
}
```

### Emergency Rollback
1. **Immediate**: Disable via feature flags
2. **Partial**: Rollback specific enhancement
3. **Complete**: Revert to previous version

---

## Success Metrics

### Key Performance Indicators
1. **Duplicate Rate**: < 0.01% (current: ~0.1%)
2. **Gap Detection**: 99.9% accuracy
3. **Recovery Success**: > 95% of gaps recovered
4. **Performance Impact**: < 10ms added latency
5. **Memory Usage**: < 50MB additional

### Monitoring Dashboard
```javascript
// Real-time metrics collection
class MetricsCollector {
  metrics = {
    hashingTime: [],
    duplicatesPreventend: 0,
    gapsDetected: 0,
    messagesRecovered: 0,
    performanceImpact: []
  };
  
  async reportMetrics() {
    // Send to monitoring service
    await fetch('/api/metrics', {
      method: 'POST',
      body: JSON.stringify(this.metrics)
    });
  }
}
```

---

## Testing Checklist

### Unit Tests
- [ ] Message hasher normalization
- [ ] Hash generation consistency
- [ ] Sequence validation logic
- [ ] Gap detection accuracy
- [ ] State checkpoint creation
- [ ] Recovery mechanism

### Integration Tests
- [ ] End-to-end message flow
- [ ] Multi-channel handling
- [ ] Performance under load
- [ ] Error recovery
- [ ] Feature flag toggling

### Manual Testing
- [ ] Page refresh recovery
- [ ] Network disconnection
- [ ] High message volume
- [ ] Unicode/emoji handling
- [ ] Platform compatibility

---

## Documentation Requirements

### Code Documentation
- JSDoc comments for all classes and methods
- Inline comments for complex logic
- Architecture decision records (ADRs)

### User Documentation
- Feature overview
- Configuration guide
- Troubleshooting guide
- FAQ section

### Developer Documentation
- API reference
- Extension development guide
- Testing guide
- Deployment procedures

---

## Conclusion

This comprehensive plan provides a safe, methodical approach to implementing the three critical enhancements. Each enhancement is designed to work independently, allowing for gradual rollout and easy rollback if issues arise. The focus on testing, monitoring, and safety measures ensures production stability while delivering significant improvements to message capture reliability.