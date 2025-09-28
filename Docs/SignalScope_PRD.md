# Product Requirements Document: SignalScope

**Version:** 2.0  
**Date:** August 14, 2025  
**Product Manager:** John 📋  
**Status:** Final Review

---

## Executive Summary

SignalScope is a Manifest V3 Chrome extension that transforms ANY web-based chatroom into a structured data API, enabling real-time capture and streaming of messages to configurable webhooks. The extension is platform-agnostic by design, working with any HTML-based chat interface through configurable CSS selectors. While it can be applied to popular platforms like Discord or Telegram's web versions, its primary strength is the ability to monitor ANY web-based chat interface - from proprietary trading platforms to custom community forums.

**Key Value Proposition:** "Turn any web-based chat into a structured data stream - capture conversations from ANY platform with configurable selectors and enterprise-grade reliability."

---

## 1. Product Vision & Strategy

### 1.1 Vision Statement
To become the universal adapter for ANY web-based chat interface, enabling users to extract structured data from both mainstream platforms and proprietary chat systems without requiring platform-specific APIs or integrations.

### 1.2 Mission
Empower users to capture, structure, and stream chat data from ANY web-based chatroom - regardless of platform, technology stack, or proprietary nature - with simple CSS selector configuration and enterprise-grade reliability.

### 1.3 Strategic Goals
- **Year 1:** Achieve product-market fit in crypto/trading vertical (5K paying users, $50K MRR)
- **Year 2:** Expand to enterprise compliance and community management ($1M ARR)
- **Year 3:** Platform ecosystem with AI insights and native integrations (exit opportunity)

### 1.4 Success Metrics
- **Activation Rate:** >80% users send first webhook within 5 minutes
- **Retention:** >80% monthly active users
- **Reliability:** 99.9% webhook delivery success rate
- **Performance:** <50ms message parse time, <50MB memory usage
- **Growth:** 30% month-over-month user growth

---

## 2. Market Analysis

### 2.1 Target Markets

#### Primary Market: Proprietary Web Chat Monitoring
- **Size:** 100,000+ businesses using custom/proprietary chat systems
- **Pain Points:** 
  - No API available for proprietary chat platforms
  - Custom-built chat systems with no export options
  - Legacy web applications without modern integrations
  - Need to monitor multiple different chat interfaces
  - Trading platforms with built-in chat (TradingView, thinkorswim, etc.)
- **Willingness to Pay:** Very High ($100-500/month for universal solution)

#### Secondary Markets
1. **Mainstream Platform Monitoring** (Discord, Telegram, Slack web versions)
   - Users who prefer browser-based monitoring over bots
   - Cross-platform aggregation needs
   - Backup when API access is restricted

2. **Crypto/Trading Signal Automation**
   - Monitor proprietary trading platform chats
   - Aggregate signals from multiple web-based sources
   - Custom broker platform chat rooms

3. **Enterprise Compliance**
   - Monitor internal web-based communication tools
   - Audit legacy systems without APIs
   - Compliance for proprietary platforms

### 2.2 User Personas

#### Persona 1: David - Enterprise Developer
- **Demographics:** 30-45 years old, works with legacy systems
- **Goals:** Extract data from proprietary web chat with no API
- **Frustrations:** Company uses custom-built chat system from 2015 with no export options
- **Success Criteria:** Reliable data extraction without modifying existing system

#### Persona 2: Lisa - Trading Platform User
- **Demographics:** 28-40 years old, active on multiple trading platforms
- **Goals:** Monitor chat rooms on TradingView, thinkorswim, and broker platforms
- **Frustrations:** Each platform has different chat system, no unified monitoring
- **Success Criteria:** Single tool that works across ALL web-based trading chats

#### Persona 3: Marcus - Compliance Manager
- **Demographics:** 35-50 years old, financial services
- **Goals:** Monitor proprietary internal chat system for compliance
- **Frustrations:** Internal tool built in-house with no audit capabilities
- **Success Criteria:** Extract all communications for regulatory review

#### Persona 4: Alex - Crypto Enthusiast (Secondary)
- **Demographics:** 25-35 years old, monitors multiple platforms
- **Goals:** Aggregate signals from various web-based chat rooms
- **Frustrations:** Some platforms don't allow bots or API access
- **Success Criteria:** Universal monitoring across any web chat

### 2.3 Competitive Landscape

| Competitor | Strengths | Weaknesses | Our Advantage |
|------------|-----------|------------|---------------|
| Platform-specific bots | Deep integration | Only works on one platform | Works on ANY web-based chat |
| Web scrapers (Octoparse) | General purpose | Not optimized for chat, complex | Chat-specific, real-time streaming |
| Custom development | Tailored solution | Expensive ($10K+), maintenance burden | Configurable, no coding required |
| Browser automation (Selenium) | Flexible | Resource heavy, complex setup | Lightweight, runs in browser |
| API integrations | Official support | Limited to platforms with APIs | Works where no API exists |

**Competitive Moat:**
- **Universal compatibility** - works with ANY web-based chat
- **No platform dependencies** - doesn't rely on APIs or bot permissions
- **Community selector library** - pre-built configs for hundreds of platforms
- **Zero-code configuration** - CSS selectors anyone can modify
- **Real-time streaming** - not batch processing or polling

---

## 3. Product Requirements

### 3.1 Functional Requirements

#### F1: Universal Message Capture
**Priority:** P0 - Critical

**Requirements:**
- Works with ANY web-based chat interface via configurable selectors
- Real-time DOM observation using MutationObserver
- Adaptive to different chat architectures (table, div, list-based)
- Handles dynamic content loading (AJAX, WebSocket updates)
- Periodic snapshot failsafe (every 60 seconds)
- Support for iframes and shadow DOM
- Handle pagination, infinite scroll, and lazy loading
- Deduplicate messages by configurable strategies

**Acceptance Criteria:**
- Captures ≥95% of visible messages on ANY web chat
- Works with unknown/proprietary chat platforms
- No duplicate message IDs
- Handles 1000+ messages efficiently
- Zero assumptions about DOM structure
- Supports chat rooms with no unique IDs (hash-based fallback)

#### F2: Message Normalization
**Priority:** P0 - Critical

**Message Schema:**
```json
{
  "msg_id": "stable-unique-identifier",
  "ts_iso": "2025-08-14T14:05:01Z",
  "author": "Display Name",
  "channel": "channel-name",
  "text": "Raw text without HTML",
  "html": "<p>Original HTML</p>",
  "images": ["url1", "url2"],
  "audios": ["url3"],
  "videos": ["url4"],
  "links": ["url5"],
  "permalink": "https://platform/message-link",
  "meta": {
    "edited": false,
    "deleted": false,
    "reply_count": 0,
    "reply_to_id": null,
    "reactions": [{"emoji": "👍", "count": 2}],
    "author_id": "user-123"
  },
  "source": {
    "url": "https://current-page",
    "selector_version": 1
  }
}
```

**Requirements:**
- Extract all fields from DOM using configurable selectors
- Generate stable msg_id from DOM attributes or content hash
- Parse attachments (images, audio, video, links)
- Track message edits and deletions
- Extract reactions and thread metadata

#### F3: Webhook Delivery
**Priority:** P0 - Critical

**Requirements:**
- Batch messages (max 20 per batch or 5 seconds)
- HMAC-SHA256 authentication
- Exponential backoff retry (1s, 2s, 4s, 8s, max 5min)
- Idempotency keys to prevent duplicates
- Respect rate limits (429 responses)
- Persistent outbox with 5MB storage limit

**Batch Envelope Format:**
```json
{
  "client": {
    "extension_version": "1.0.0",
    "installation_id": "uuid-v4",
    "browser": "Chrome",
    "tz": "America/New_York"
  },
  "source": {
    "origin": "https://discord.com",
    "page_title": "Trading Signals",
    "selector_version": 1
  },
  "messages": [/* array of messages */]
}
```

#### F4: Configuration Interface
**Priority:** P0 - Critical

**Requirements:**
- React-based options page with Tailwind CSS
- Visual selector builder with point-and-click selection
- CSS selector configuration with validation and syntax help
- Selector templates for common chat patterns
- Test selectors on active tab with live preview
- Import/export configurations
- Community selector library browser
- Auto-detect common chat patterns
- Multiple configuration profiles for different sites
- Privacy controls (exclude patterns, content filters)

**Selector Configuration Schema:**
```typescript
interface SelectorConfig {
  version: number;
  siteName: string;
  matchUrls: string[];
  containerSelector: string;
  messageSelector: string;
  authorSelector: string;
  timestampSelector?: string;
  textSelector: string;
  htmlSelector?: string;
  imageSelector?: string;
  audioSelector?: string;
  videoSelector?: string;
  linkSelector?: string;
  permalinkSelector?: string;
  reactionSelector?: string;
  deletedPredicate?: string;
  editedPredicate?: string;
  dedupeKey: "data-id" | "hash" | "auto";
  throttleMs: number;
  snapshotIntervalMs: number;
}
```

#### F5: Selector Testing
**Priority:** P1 - High

**Requirements:**
- Test button executes selectors on active tab
- Preview table shows parsed messages
- Highlight matching DOM elements
- Display parse success rate
- Show detailed error messages
- Export test results

#### F6: Diagnostics & Monitoring
**Priority:** P1 - High

**Requirements:**
- Verbose logging toggle
- Queue size monitoring
- Delivery success/failure stats
- Flush queue manually
- Clear storage option
- Export debug logs

### 3.2 Non-Functional Requirements

#### NF1: Performance
- **Parse Time:** <50ms per message
- **Memory Usage:** <50MB total
- **CPU Usage:** <1% when idle
- **Startup Time:** <500ms
- **No memory leaks over 24-hour operation**

#### NF2: Reliability
- **Uptime:** 99.9% availability
- **Data Loss:** Zero message loss
- **Recovery:** Automatic recovery from crashes
- **Persistence:** Survive browser restarts

#### NF3: Security
- **Permissions:** Minimal required only
- **Authentication:** HMAC-SHA256 for webhooks
- **Storage:** Encrypted secrets where possible
- **CSP:** Strict content security policy
- **No unsafe-eval or inline scripts**

#### NF4: Usability
- **Setup Time:** <5 minutes to first webhook
- **Configuration:** No coding required
- **Documentation:** Comprehensive guides
- **Error Messages:** Clear and actionable

#### NF5: Compatibility
- **Chrome:** Version 88+
- **Platforms:** Discord, Telegram, Slack web versions
- **Localization:** English (v1), multi-language (v2)

### 3.3 Technical Architecture

#### Frontend Components (Chrome Extension)
1. **Content Script** (`src/content/`)
   - MutationObserver implementation
   - Trading intelligence analysis
   - Message importance scoring
   - Author detection strategies

2. **Background Service Worker** (`src/background/`)
   - Message batching
   - Webhook delivery with HMAC
   - Retry logic with exponential backoff
   - Storage management

3. **Options UI** (`src/options/`)
   - React components
   - Configuration forms
   - Selector tester
   - Import/export

4. **Shared Utilities** (`src/shared/`)
   - Zod schemas
   - HMAC signer
   - Storage API
   - Logger

#### Backend Architecture (NEW - August 2025)
1. **API Layer** (FastAPI)
   - Webhook receiver with signature verification
   - RESTful endpoints for reports
   - WebSocket for real-time updates
   - Rate limiting and authentication

2. **Message Processing Pipeline**
   - **Redis Streams** for message queuing
   - **3-tier priority system**:
     - Realtime (importance ≥ 8): 5-min batches
     - Standard (importance 5-7): 15-min batches  
     - Archive (importance < 5): 60-min batches
   - **Smart batching** by time, volume, and context

3. **LLM Intelligence Layer**
   - **Multi-model support** (OpenAI GPT-4/3.5, Anthropic Claude)
   - **3 report types**:
     - Real-time alerts (urgent signals)
     - Hourly summaries (market overview)
     - Daily reports (comprehensive analysis)
   - **Token optimization** for cost efficiency
   - **Validation system** to prevent hallucinations

4. **Data Storage** (Supabase)
   - **Core tables**:
     - `messages`: Raw captured data
     - `message_batches`: Batch tracking
     - `reports`: Generated intelligence
     - `report_subscriptions`: Distribution config
   - **Optimized indexes** for ticker and time queries
   - **Vector embeddings** for semantic search

5. **Processing Workers** (Celery)
   - Async job processing
   - Parallel batch handling
   - Memory optimization
   - Failure recovery

6. **Monitoring & Observability**
   - Prometheus metrics collection
   - Queue depth monitoring
   - LLM token usage tracking
   - Report quality scoring

#### Technology Stack

**Frontend (Chrome Extension):**
- **Language:** TypeScript/JavaScript
- **Build:** Webpack with Chrome extension config
- **UI Framework:** Vanilla JS (content script), React (options)
- **Validation:** Zod schemas
- **HTTP Client:** Fetch API with retry wrapper
- **Crypto:** Web Crypto API for HMAC
- **Storage:** chrome.storage.local + chrome.storage.sync

**Backend (NEW):**
- **API Framework:** FastAPI (Python 3.11+)
- **Queue System:** Redis Streams + Celery workers
- **Database:** Supabase (PostgreSQL + pgvector)
- **LLM Providers:** OpenAI API, Anthropic Claude API
- **Monitoring:** Prometheus + Grafana
- **Deployment:** Docker + Kubernetes/Render
- **Testing:** pytest, Jest for extension

#### Permissions
```json
{
  "permissions": [
    "storage",
    "scripting",
    "activeTab",
    "alarms"
  ],
  "host_permissions": [
    "https://discord.com/*",
    "https://web.telegram.org/*"
  ]
}
```

---

## 4. User Journeys

### 4.1 First-Time Setup - Generic Web Chat
1. User installs extension from Chrome Web Store
2. Opens options page automatically
3. Navigates to their web-based chat platform
4. Clicks "Auto-Detect" button or manually configures selectors
5. Uses visual selector builder to click on message elements
6. Tests configuration and sees preview of parsed messages
7. Enters webhook URL and tests connection
8. Saves configuration
9. Receives first webhook within 30 seconds

### 4.2 First-Time Setup - Known Platform
1. User installs extension from Chrome Web Store
2. Opens options page automatically
3. Browses community selector library
4. Searches for their platform (e.g., "TradingView chat")
5. Imports pre-built configuration
6. Tests and adjusts if needed
7. Enters webhook URL
8. Starts receiving data immediately

### 4.3 Daily Usage
1. User opens their web-based chat platform
2. Extension automatically detects matching URL pattern
3. Loads appropriate selector configuration
4. Extension icon shows active status with message count
5. Messages stream automatically to webhook
6. User's systems receive structured data
7. User monitors multiple different chat platforms in tabs

### 4.4 Troubleshooting
1. User notices missed messages
2. Opens diagnostics panel
3. Sees delivery failures with error details
4. Adjusts webhook configuration
5. Tests new settings
6. Confirms successful delivery

---

## 5. Go-to-Market Strategy

### 5.1 Launch Timeline

#### Phase 1: MVP & Validation (Weeks 1-4)
- Build universal selector system
- Create visual selector builder
- Test with 5 different proprietary chat systems
- Build selector templates for common patterns
- Beta test with 10 users on various platforms
- Prepare Chrome Web Store listing

#### Phase 2: Soft Launch (Weeks 5-8)
- Release to 100 beta users across different platforms
- Create selector library with 20+ platform configs
- Launch on Product Hunt emphasizing "works with ANY chat"
- Target developer communities and legacy system users
- Collect testimonials from proprietary platform users

#### Phase 3: Growth (Weeks 9-12)
- Public launch with "Universal Chat Adapter" messaging
- Build selector marketplace
- Partner with companies using proprietary chat systems
- Community-driven selector contributions
- Target: 500 users, 100 paid

### 5.2 Marketing Channels

1. **Content Marketing**
   - "Extract Data from Any Web Chat" tutorials
   - "Monitor Proprietary Chat Systems" guides
   - "Legacy System Integration" case studies
   - "No API? No Problem" blog series
   - Platform-specific setup guides

2. **Developer Communities**
   - Stack Overflow answers for chat scraping
   - GitHub selector library repository
   - Dev.to articles on DOM observation
   - Hacker News launch

3. **Enterprise Outreach**
   - LinkedIn targeting legacy system managers
   - Webinars on proprietary system monitoring
   - Direct outreach to companies with custom chat
   - Partner with system integrators

### 5.3 Pricing Strategy

| Tier | Price/Month | Messages | Webhooks | Features |
|------|------------|----------|----------|----------|
| Free | $0 | 1,000 | 1 | Basic, 24hr retention |
| Starter | $19 | 10,000 | 3 | All platforms, 7-day retention |
| Pro | $49 | 100,000 | 10 | Priority support, 30-day retention |
| Business | $149 | 1,000,000 | Unlimited | API, 90-day retention |
| Enterprise | Custom | Unlimited | Unlimited | SLA, SSO, audit logs |

---

## 6. Success Criteria & KPIs

### 6.1 Launch Success (Month 1)
- [ ] 100+ installations
- [ ] 10+ paying customers
- [ ] 4.5+ star rating
- [ ] <5% uninstall rate
- [ ] 80%+ activation rate

### 6.2 Growth Metrics (Months 2-6)
- [ ] 30% MoM user growth
- [ ] $10K MRR by Month 6
- [ ] <5% monthly churn
- [ ] NPS score >50
- [ ] CAC < $50

### 6.3 Long-term Success (Year 1)
- [ ] 5,000 active users
- [ ] 1,500 paying customers
- [ ] $50K MRR
- [ ] 3+ platform integrations
- [ ] Enterprise customer acquisition

---

## 7. Risks & Mitigations

### 7.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Platform DOM changes | High | High | Versioned selectors, rapid updates, community contributions |
| Chrome API deprecation | High | Low | Stay current with MV3 changes, maintain update channel |
| Performance degradation | Medium | Low | Continuous profiling, optimization sprints |
| Data loss | High | Low | Persistent storage, retry mechanisms, monitoring |

### 7.2 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Platform ToS violation | High | Medium | Clear compliance guidelines, no automation |
| Competition from platforms | High | Low | Focus on cross-platform value, rapid innovation |
| Low conversion rate | Medium | Medium | Free tier optimization, better onboarding |
| Support overwhelm | Medium | Medium | Community support, comprehensive docs |

### 7.3 Legal & Compliance Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GDPR violations | High | Low | Privacy controls, data minimization |
| Security breach | High | Low | Security audit, minimal permissions |
| IP disputes | Medium | Low | Original code, clear licensing |

---

## 8. Development Roadmap

### 8.1 MVP (v1.0) - Completed
- [x] Universal selector system for ANY web chat
- [x] Trading intelligence analysis
- [x] Basic webhook delivery with HMAC
- [x] Message importance scoring
- [x] Enhanced author detection
- [x] Chrome extension functional

### 8.2 Backend Integration (v1.5) - ACTIVE (August 2025)
- [x] Message stacking architecture design
- [x] LLM batch processing pipeline design
- [x] Supabase schema design
- [ ] Webhook receiver implementation (Week 1)
- [ ] Redis queue setup (Week 1)
- [ ] LLM report generation (Week 2)
- [ ] Celery workers deployment (Week 2)
- [ ] Report distribution system (Week 2)

### 8.3 Growth (v2.0) - Months 4-6
- [ ] AI-powered selector suggestions
- [ ] Shadow DOM and iframe support
- [ ] Multi-profile management
- [ ] Team collaboration features
- [ ] Enterprise authentication options
- [ ] Selector marketplace

### 8.4 Platform (v3.0) - Months 7-12
- [ ] Browser plugin for Firefox/Edge
- [ ] Selector recommendation engine
- [ ] Custom transformation rules
- [ ] White-label solution
- [ ] Advanced compliance tools
- [ ] API for selector sharing

---

## 9. Team & Resources

### 9.1 Required Roles
- **Product Manager:** Strategy, requirements, stakeholder management
- **Frontend Developer:** Chrome extension, React UI
- **Backend Developer:** Webhook testing, infrastructure
- **UX Designer:** Options UI, user flows
- **QA Engineer:** Testing, automation
- **DevOps:** CI/CD, monitoring
- **Marketing:** Growth, content, partnerships

### 9.2 Budget Estimates
- **Development:** $50K (3 months, 2 developers)
- **Design:** $10K (UI/UX, branding)
- **Infrastructure:** $2K/month (servers, monitoring)
- **Marketing:** $20K (launch campaign, content)
- **Legal:** $5K (privacy policy, ToS)
- **Total Year 1:** ~$100K

---

## 10. Acceptance Criteria

### 10.1 Technical Acceptance
- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests successful
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] Chrome Web Store approved

### 10.2 Product Acceptance
- [ ] Captures ≥95% of messages on ANY web chat
- [ ] <5 minute setup for unknown platforms
- [ ] <1 minute setup with preset configs
- [ ] 99.9% webhook delivery rate
- [ ] Works on 10+ different chat platforms
- [ ] Visual selector builder functional
- [ ] 50+ platform configs in library
- [ ] Comprehensive documentation

### 10.3 Business Acceptance
- [ ] Positive user feedback (>4 stars)
- [ ] Target activation rate achieved
- [ ] Revenue targets on track
- [ ] Support load manageable
- [ ] Legal compliance verified

---

## 11. Appendices

### Appendix A: Technical Specifications
[Link to detailed technical architecture document]

### Appendix B: User Research
[Link to customer interview summaries]

### Appendix C: Competitive Analysis
[Link to detailed competitive research]

### Appendix D: Financial Model
[Link to revenue projections and unit economics]

### Appendix E: Legal Considerations
[Link to privacy policy and terms of service]

---

## 12. Approval & Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Manager | John | [Signed] | Aug 14, 2025 |
| Engineering Lead | | | |
| UX Lead | | | |
| Legal Counsel | | | |
| Executive Sponsor | | | |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Aug 14, 2025 | AI Assistant | Initial PRD from technical prompt |
| 2.0 | Aug 14, 2025 | John (PM) | Refined with market analysis and user stories |
| 2.1 | Aug 15, 2025 | AI Assistant | Added backend architecture and LLM pipeline design |

---

*This PRD is a living document and will be updated as we learn more from customers and technical implementation.*