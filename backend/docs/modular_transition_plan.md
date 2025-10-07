# TubeVibe Chrome Extension – Modular Development Plan

> **Goal**: Build and test the modular system **completely separately** from the working production code (`content.ts`). The production extension remains untouched until modular is 100% ready.

---
## 📜 1. Core Principle: Parallel Development

**Production Path** (unchanged):
- `extension/simply/content.ts` - The working 4,000-line file
- Continues to serve all users normally
- **We do NOT modify this file at all**

**Development Path** (new):
- `extension/simply/.temp_modules/` - Already contains modular code
- Separate test harness for development/testing
- Completely isolated from production

---
## 🏗️ 2. Development Setup

### 2.1 Create Test Harness
Create a **separate content script** for testing only:

```typescript
// extension/simply/content-modular-test.ts
import type { PlasmoCSConfig } from "plasmo"

// Only runs on specific test URLs to avoid conflicts
export const config: PlasmoCSConfig = {
  matches: ["https://www.youtube.com/watch*"],
  all_frames: false,
  run_at: "document_idle",
  // Add URL parameter check to only run on test videos
  world: "MAIN"
}

// Only initialize if test mode is enabled
if (new URLSearchParams(window.location.search).get('tubevibe_test') === 'modular') {
  console.log('🧪 TubeVibe: Running MODULAR test version')
  import('./.temp_modules/content/index').then(mod => mod.initialize())
} else {
  // Do nothing - let production content.ts handle it
}
```

### 2.2 Testing Strategy

**Local Testing**:
1. Visit: `https://www.youtube.com/watch?v=VIDEO_ID&tubevibe_test=modular`
2. Modular version runs (production content.ts ignores this URL)
3. Compare results side-by-side with production

**Manifest During Development**:
```json
{
  "content_scripts": [
    {
      "matches": ["https://www.youtube.com/watch*"],
      "js": ["content.js"],  // Production (unchanged)
      "run_at": "document_idle"
    },
    {
      "matches": ["https://www.youtube.com/watch*"], 
      "js": ["content-modular-test.js"],  // Dev only
      "run_at": "document_idle"
    }
  ]
}
```

---
## 🗺️ 3. Existing Modular Code Map

The modular code **already exists** under `.temp_modules/content/**`:

| Production Method (`content.ts`) | Modular File | Status |
|----------------------------------|--------------|--------|
| `extractFromYouTubeDOMTranscript()` | `DomPanelExtractor.ts` | ✅ Implemented |
| `extractFromPlayerResponseFast()` | `PlayerResponseExtractor.ts` | ✅ Implemented |
| `extractFromYouTubeDOMTranscriptSafe()` | `DomSafeExtractor.ts` | ✅ Implemented |
| `extractFromTimedtext()` | `TimedTextExtractor.ts` | ✅ Implemented |
| `YouTubeTranscriptExtractor` class | `TranscriptExtractor.ts` | ✅ Orchestrator ready |

---
## 📋 4. Development Tasks

### Phase 1: Integration (Current)
- [ ] Create `.temp_modules/content/index.ts` entry point
- [ ] Wire up modular extractors to work together
- [ ] Add test harness (`content-modular-test.ts`)
- [ ] Implement UI injection (currently missing from modular)

### Phase 2: Feature Parity
- [ ] Port UI creation (`createPanel`, `setupUI`)
- [ ] Port message handlers (popup communication)
- [ ] Port metadata extraction
- [ ] Port auto-extraction logic
- [ ] Add CSS injection

### Phase 3: Testing & Validation
- [ ] Test matrix: 20 videos (different types)
- [ ] Compare extraction success rates
- [ ] Verify UI behavior matches production
- [ ] Performance benchmarks (should be faster)

### Phase 4: Production Preparation
- [ ] Remove test harness
- [ ] Create single `content-modular.ts` 
- [ ] Update manifest to use modular version
- [ ] Final testing round
- [ ] Deploy

---
## 🧪 5. Testing Approach

### A/B Testing in Development:
```bash
# Terminal 1 - Production
open "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Terminal 2 - Modular  
open "https://www.youtube.com/watch?v=dQw4w9WgXcQ&tubevibe_test=modular"
```

### Success Metrics:
- Same transcript extracted ✓
- Same UI appearance ✓
- Same or better performance ✓
- No console errors ✓

---
## 🚀 6. Migration (Only After 100% Ready)

**One-line change** in production:
```diff
// manifest.json or PlasmoCSConfig
- "js": ["content.js"]
+ "js": ["content-modular.js"]
```

**Rollback** is equally simple:
```diff
- "js": ["content-modular.js"]  
+ "js": ["content.js"]
```

---
## ⚠️ 7. What We DON'T Do

- ❌ No shadow mode in production
- ❌ No modifying `content.ts` 
- ❌ No complex bootstrap loaders
- ❌ No risk to current users
- ❌ No telemetry needed (test locally first)

---
## 📊 8. Current Status

**What's Ready**:
- ✅ All 4 extraction methods ported
- ✅ Orchestrator (`TranscriptExtractor`) ready
- ✅ Text processing utilities shared

**What's Missing**:
- ❌ UI injection (panel, buttons, styles)
- ❌ Message passing to popup
- ❌ Metadata extraction 
- ❌ Auto-extraction on page load
- ❌ Test harness setup

---
## 🛠️ 9. Detailed Implementation Steps

### Step 1: Create Modular Entry Point
**File**: `.temp_modules/content/index.ts`
```typescript
import { TranscriptExtractor } from './extraction/TranscriptExtractor'
import { MetadataExtractor } from './metadata/MetadataExtractor'
import { UIManager } from './ui/UIManager'

export class ModularController {
  private transcriptExtractor: TranscriptExtractor
  private metadataExtractor: MetadataExtractor
  private uiManager: UIManager
  
  constructor() {
    this.transcriptExtractor = new TranscriptExtractor()
    this.metadataExtractor = new MetadataExtractor()
    this.uiManager = new UIManager()
  }

  async initialize(): Promise<void> {
    // Same init flow as content.ts but modular
    await this.waitForYouTubeLoad()
    const metadata = await this.metadataExtractor.extractWithRetries()
    await this.uiManager.setupUI()
    await this.setupMessageHandlers()
    this.autoExtractTranscript()
  }
}
```

### Step 2: Port Metadata Extraction
**File**: `.temp_modules/content/metadata/MetadataExtractor.ts`
```typescript
// Copy these methods from content.ts:
// - extractMetadata()
// - extractMetadataWithRetries() 
// - fetchOEmbedMetadata()
// - getVideoDuration()
// - parseDurationToSeconds()

export class MetadataExtractor implements IMetadataExtractor {
  async extractMetadataWithRetries(): Promise<VideoMetadata> {
    // Exact same logic as content.ts
  }
  
  extractMetadata(): VideoMetadata {
    // Exact same logic as content.ts
  }
  
  // ... other methods
}
```

### Step 3: Port UI Management
**File**: `.temp_modules/content/ui/UIManager.ts`
```typescript
// Copy these methods from content.ts:
// - setupUI()
// - createPanel()
// - setupPanelEvents()
// - injectIntoYouTubeSidebar()
// - All CSS injection

export class UIManager {
  private panel: HTMLElement | null = null
  
  async setupUI(): Promise<void> {
    // Exact same UI creation as content.ts
    this.performComprehensiveCleanup()
    this.injectCSS()
    this.createPanel()
    this.injectIntoYouTubeSidebar()
    this.setupPanelEvents()
  }
  
  private injectCSS(): void {
    // Copy the massive CSS string from content.ts setupUI()
  }
  
  // ... all other UI methods
}
```

### Step 4: Port Message Handlers
**File**: `.temp_modules/content/messaging/MessageHandler.ts`
```typescript
// Copy these from content.ts:
// - chrome.runtime.onMessage.addListener
// - All message types: EXTRACT_CAPTIONS, GET_CURRENT_VIDEO_METADATA, etc.

export class MessageHandler {
  constructor(
    private transcriptExtractor: TranscriptExtractor,
    private metadataExtractor: MetadataExtractor
  ) {}
  
  setupMessageHandlers(): void {
    chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
      // Exact same message handling as content.ts
      if (message.type === 'EXTRACT_CAPTIONS') {
        // Use this.transcriptExtractor instead of YouTubeTranscriptExtractor.getInstance()
      }
      // ... all other message types
    })
  }
}
```

### Step 5: Create Test Harness
**File**: `extension/simply/content-modular-test.ts`
```typescript
import type { PlasmoCSConfig } from "plasmo"

export const config: PlasmoCSConfig = {
  matches: ["https://www.youtube.com/watch*"],
  all_frames: false,
  run_at: "document_idle"
}

// Only run if test parameter is present
if (new URLSearchParams(window.location.search).get('tubevibe_test') === 'modular') {
  console.log('🧪 TubeVibe: Running MODULAR test version')
  
  import('./.temp_modules/content/index').then(async ({ ModularController }) => {
    const controller = new ModularController()
    await controller.initialize()
  }).catch(error => {
    console.error('🧪 TubeVibe: Modular initialization failed:', error)
  })
}
```

### Step 6: Port Auto-Extraction
**File**: `.temp_modules/content/extraction/AutoExtractor.ts`
```typescript
// Copy these methods from content.ts:
// - autoExtractTranscript()
// - debouncedInitialize()
// - bootstrapSimply()

export class AutoExtractor {
  constructor(private transcriptExtractor: TranscriptExtractor) {}
  
  async autoExtractTranscript(): Promise<void> {
    // Same logic as content.ts
    const transcript = await this.transcriptExtractor.extractTranscript()
    // Send to background, update UI, etc.
  }
}
```

### Step 7: Backend Integration Points
**Key Integration Points to Maintain**:

1. **Popup Communication**:
   ```typescript
   // Keep these message types exactly the same:
   chrome.runtime.sendMessage({
     type: 'TRANSCRIPT_EXTRACTED',
     data: { metadata, transcript }
   })
   
   chrome.runtime.sendMessage({
     type: 'NEW_VIDEO_DETECTED', 
     data: { metadata }
   })
   ```

2. **Summary Generation**:
   ```typescript
   // Keep this exact API call:
   const response = await chrome.runtime.sendMessage({
     type: "PROCESS_TRANSCRIPT",
     data: {
       video_id: metadata?.videoId,
       title: metadata?.title,
       // ... same structure
     }
   })
   ```

3. **UI Event Handlers**:
   ```typescript
   // Keep same button behaviors:
   transcribeBtn.addEventListener('click', async () => {
     await this.handleTranscription(transcribeBtn)
   })
   
   summaryBtn.addEventListener('click', async () => {
     await this.handleSummaryGeneration(summaryBtn)
   })
   ```

### Step 8: Directory Structure After Implementation
```
.temp_modules/content/
├── index.ts                    # ModularController entry point
├── extraction/
│   ├── TranscriptExtractor.ts  # ✅ Already done
│   ├── DomPanelExtractor.ts    # ✅ Already done  
│   ├── PlayerResponseExtractor.ts # ✅ Already done
│   ├── DomSafeExtractor.ts     # ✅ Already done
│   ├── TimedTextExtractor.ts   # ✅ Already done
│   └── AutoExtractor.ts        # ❌ New - port from content.ts
├── metadata/
│   └── MetadataExtractor.ts    # ❌ New - port from content.ts
├── ui/
│   └── UIManager.ts            # ❌ New - port from content.ts
└── messaging/
    └── MessageHandler.ts       # ❌ New - port from content.ts
```

---
## 🎯 10. Implementation Priority Order

### Phase 1: Core Infrastructure (Week 1)
1. ✅ Create `ModularController` entry point
2. ✅ Port `MetadataExtractor` (copy from content.ts)
3. ✅ Create test harness (`content-modular-test.ts`)
4. ✅ Test basic loading with `?tubevibe_test=modular`

### Phase 2: UI System (Week 2)  
1. ✅ Port `UIManager` (copy all CSS + panel creation from content.ts)
2. ✅ Test UI appears correctly in modular version
3. ✅ Verify no conflicts with production content.ts

### Phase 3: Message Integration (Week 3)
1. ✅ Port `MessageHandler` (copy all chrome.runtime.onMessage logic)
2. ✅ Test popup communication works
3. ✅ Test backend integration (summary generation)

### Phase 4: Auto-Extraction (Week 4)
1. ✅ Port `AutoExtractor` (copy auto-transcript logic)
2. ✅ Test extraction happens automatically on page load
3. ✅ Test YouTube SPA navigation handling

### Phase 5: Final Testing (Week 5)
1. ✅ Side-by-side comparison (production vs modular)
2. ✅ Test matrix: 20 videos, different types
3. ✅ Performance benchmarks
4. ✅ Production deployment preparation

---
## 📋 11. Testing Checklist

### UI Verification:
- [ ] Panel appears in same location as production
- [ ] All buttons work (Transcribe, Summary, Chat)
- [ ] Tabs switch correctly (Transcript, Summary, Chat)
- [ ] CSS styles match production exactly
- [ ] No console errors in UI injection

### Backend Integration:
- [ ] Popup receives transcript data
- [ ] Summary generation works
- [ ] Email summaries sent correctly
- [ ] All message types handled

### Extraction Verification:
- [ ] Same transcript extracted as production
- [ ] All 4 extraction methods work
- [ ] Fallback order respected
- [ ] Auto-extraction on page load

### Performance:
- [ ] Faster initial load (due to modular chunks)
- [ ] Same or better extraction speed
- [ ] No memory leaks
- [ ] Proper cleanup on navigation

---
## 🎯 12. Success Criteria

**Ready for Production When**:
1. ✅ Modular version extracts same transcripts as production
2. ✅ UI behavior is identical to production  
3. ✅ All backend integrations work
4. ✅ Performance is same or better
5. ✅ No console errors
6. ✅ Test matrix passes 100%

**Then**: Update manifest.json to use modular version, remove content.ts

---
## 📜 1. Terminology
| Term | Meaning |
|------|---------|
| **Legacy** | Current monolithic `extension/simply/content.ts`. |
| **Modular** | New code under `.temp_modules/content/**`.  Orchestrator = `TranscriptExtractor`. |
| **Bootstrap** | Tiny content-script that decides whether to use Modular or fall back to Legacy. |
| **Shadow mode** | Phase where Modular runs first; on failure Legacy is lazy-loaded. |

---
## 🚧 2. High-Level Phases
| Phase | Objective | Exit Criteria |
|-------|-----------|---------------|
| P0 | Baseline – Legacy only (status-quo) | Current prod is stable |
| P1 | **Introduce Modular & Bootstrap** in dev build | Unit tests pass, manual smoke on 10+ videos |
| P2 | Shadow mode in **beta channel** (5 % users) | ≥ 95 % Modular success, no regressions reported |
| P3 | Shadow mode **wide** (100 %) | ≥ 99 % success for 7 days, ≤ 0.1 % fallback invocations |
| P4 | Remove Legacy, Bootstrap now imports Modular directly | Chrome Web Store publish |

---
## 📝 3. Task List

### 3.1 Code Tasks
1. **Create `bootstrap.ts`**
   * Declared as **sole** content-script in `PlasmoCSConfig`.
   * `import('./modular/entry').then(run)`; on error/invalid => `import('./content')`.
2. **Expose Modular entry point**
   * File: `.temp_modules/content/extraction/ModularEntry.ts`.
   * `export async function run(): Promise<boolean>` returns *true* if transcript extracted & validated.
3. **Instrument success / fallback**
   * `chrome.runtime.sendMessage({type:"MODULAR_OK"})` etc.
   * Background script counts & persists.
4. **Feature flag** `ENABLE_LEGACY_FALLBACK` inside bootstrap.
5. **Chunk naming** comments so bundler produces:
   * `bootstrap.js` (very small)
   * `modular-extractor.js` (lazy)
   * `legacy-content.js` (lazy, only if needed)
6. **CSS namespace**
   * Wrap modular styles in `#tubevibe-modular` to avoid collisions when Legacy also injects.
7. **Global isolation**
   * Put any globals on `window.TubeVibeMod`.

### 3.2 Telemetry Tasks
1. Background script accumulates counts in memory; flush to `chrome.storage.local` every hour.
2. Add keyboard shortcut in popup **Dev tab** to view counts.
3. Optional: daily `fetch()` to internal API endpoint for central dashboard.

### 3.3 QA Tasks
* Regression matrix (20 public videos, 5 languages, 2 with no captions, 3 age-restricted).
* Confirm UI panel, summary, popup flows unchanged.
* Verify that on modular failure the Legacy UI still appears within ≤ 1.5 s.

### 3.4 Release Management
1. **Beta channel** upload with `ENABLE_LEGACY_FALLBACK=true`.
2. Monitor telemetry and user feedback.
3. If critical bug – flip flag remotely via `chrome.storage.sync` value check in bootstrap.
4. When criteria met → build with `ENABLE_LEGACY_FALLBACK=false` and delete `content.ts`.

---
## ⏳ 4. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Modular JS parse error | Captions broken | Shadow mode fallback. |
| CSS collision | UI glitch | Namespace via `#tubevibe-modular`. |
| Bundler tree-shakes Legacy accidentally | Cannot fallback | Mark `/* webpackChunkName: "legacy-content" */` and reference in code to keep chunk. |
| New Chrome manifest permission required | Store rejection | No new permissions – dynamic `import()` allowed. |

---
## ✅ 5. Done Definition
* [ ] Shadow mode success rate ≥ 99 % across ≥ 1 000 sessions.
* [ ] Telemetry shows < 0.1 % fallback use for 7 consecutive days.
* [ ] No new console errors in Sentry for content-script.
* [ ] QA regression matrix passes.
* [ ] Legacy bundle physically removed, extension size ↓ >200 KB.

---
## 📌 6. Next Steps
1. Implement bootstrap + modular entry (Tasks 3.1-1 & 3.1-2).  
2. Update manifest / Plasmo config.  
3. Ship internal build; run automated Cypress tests.  
4. Proceed through phases per telemetry.

---
## 🗺️ 2.1  Existing Modular Code Map
The modular extractor **already lives in the repo** under `.temp_modules/content/**`, but is **not wired in**.  The table below shows exactly which logic in `content.ts` is implemented by which modular file/class:

| Area / Method in `content.ts` | Modular Replacement File | Exported Class / Function | Notes |
|-------------------------------|--------------------------|---------------------------|-------|
| `extractFromYouTubeDOMTranscript()` (stealth panel-open) | `.temp_modules/content/extraction/DomPanelExtractor.ts` | `DomPanelExtractor` | Preserves hide-CSS, multi-close strategy, 1s wait. |
| `extractFromPlayerResponseFast()` | `.temp_modules/content/extraction/PlayerResponseExtractor.ts` | `PlayerResponseExtractor` | Caption-track selection, lang preference, auth fetch. |
| `extractFromYouTubeDOMTranscriptSafe()` | `.temp_modules/content/extraction/DomSafeExtractor.ts` | `DomSafeExtractor` |    No-panel safe scan + engagement-panel fallback. |
| `extractFromTimedtext()` | `.temp_modules/content/extraction/TimedTextExtractor.ts` | `TimedTextExtractor` | 4 endpoint loop, 5-second timeout, XML/VTT parsing. |
| Text clean/validate helpers | `.temp_modules/shared/utils/TextProcessor.ts` | `TextProcessor` | Already shared across extension. |
| VTT / XML / JSON caption parsing | `.temp_modules/content/extraction/CaptionParser` (inlined in `TranscriptExtractor`) | `CaptionParser` | Mirrors `parseVTTorXML` & `parseCaptionXML`. |
| Overall orchestration (`extractCaptionsDirectly` fallback order) | `.temp_modules/content/extraction/TranscriptExtractor.ts` | `TranscriptExtractor` | Orchestrates the four extractors in same priority order. |

### Call-flow in the Modular World
```
bootstrap.ts              // content-script declared in manifest
  └─ import('./ModularEntry').then(run)
        ModularEntry.run() // re-exports TranscriptExtractor
            └─ new TranscriptExtractor()
                    ├─ DomPanelExtractor.extractTranscript()
                    ├─ PlayerResponseExtractor.extractTranscript()
                    ├─ DomSafeExtractor.extractTranscript()
                    └─ TimedTextExtractor.extractTranscript()
```
If **all four** return `success=false`, bootstrap falls back to legacy `content.ts` (shadow-mode).

---
**Maintainer:** `@TubeVibe/extension-core`

Last updated: <!--YYYY-MM-DD will be auto-updated by CI script--> 