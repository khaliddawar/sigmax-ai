
# PRD_Prompt.md
**Title:** Agentic Chrome Extension (MV3) to Capture Chatroom Discussions and Stream Structured JSON to a Backend Webhook

> Use this prompt **verbatim** to generate production-grade code with **zero hallucination**. If any required detail is missing, **stop and ask for that specific detail** instead of guessing. Comply strictly with each requirement. Prefer explicit, audited code over “magic” wrappers.

---

## 0) Objective (What to build)
Build a **Manifest V3** Chrome extension that:
1. **Observes a chatroom UI** (single-page or multi-page app) and **extracts messages in real time**.
2. **Normalizes messages → structured JSON** (ticker-aware text + attachments).
3. **Reliably delivers** batched events to a **configurable webhook** with **auth**, **retries**, and **idempotency**.
4. Provides a minimal **Options UI** to configure the site’s CSS selectors, webhook, and run-time controls.
5. **Never blocks or degrades** the website. Respect ToS (no automation of clicks, no login, no scraping behind paywalls).

Do **not** use Playwright/Puppeteer. This is a **browser extension** only.

---

## 1) Tech/Tooling (strict)
- **Manifest:** MV3 only (`manifest_version: 3`).
- **Language:** TypeScript for all extension scripts.
- **Build:** Vite or Rollup (choose one and wire a reproducible build).
- **Lint/Format:** ESLint + Prettier with standard configs.
- **State/Storage:** `chrome.storage.local` + `chrome.storage.sync` (small user prefs).
- **Background:** Service worker (MV3) for networking, batching, alarms, auth signing.
- **UI:** Options page (React + minimal Tailwind). Popup is optional.
- **No external UI frameworks** besides React and Tailwind. No heavy runtime (keep bundle small).
- **Dependencies (allowed):**
  - `zod` for schema validation of settings/payloads.
  - `axios` for HTTP; or `fetch` with retry wrapper.
  - `crypto-js` or Web Crypto API for HMAC signing.
  - Optional: `mutation-summary` or implement a small, robust `MutationObserver` wrapper yourself.
- **Permissions (minimal):**
  - `"storage"`, `"scripting"`, `"activeTab"`
  - `"alarms"` for retry/flush scheduling
  - `"host_permissions"` for the target domain(s) ONLY (use placeholders `https://example.com/*`)
- **Content Security Policy:** Strict defaults. No `unsafe-eval`.

---

## 2) Target data (what to capture)
The chatroom may render messages as dynamic DOM nodes. Capture **incremental changes** in real time via `MutationObserver` and **periodic snapshot** failsafe (every 60s) to avoid missed nodes.

### 2.1 Message fields (normalized)
Produce **one JSON object per message** with the following contract (**do not change field names**):
```json
{
  "msg_id": "ui-<stable-unique-from-dom-or-hash>",
  "ts_iso": "2025-08-14T14:05:01Z",
  "author": "Display Name",
  "channel": "room-or-thread-name",
  "text": "Raw text content without HTML",
  "html": "<p>...</p>",
  "images": ["https://.../img1.png"],
  "audios": ["https://.../note1.mp3"],
  "videos": ["https://.../clip1.mp4"],
  "links": ["https://..."],
  "permalink": "https://site/room/123#msg_456",
  "meta": {
    "edited": false,
    "deleted": false,
    "reply_count": 0,
    "reply_to_id": null,
    "reactions": [{"emoji":"👍","count":2}],
    "author_id": "optional if visible"
  },
  "source": {
    "url": "https://current/page/url",
    "selector_version": 1
  }
}
```
Rules:
- **`msg_id` must be stable**: derive from DOM attributes (data-id) or a **hash** of `(author + text + ts + channel)`.
- Prefer **UTC ISO-8601** times.
- **Collect attachments** from `<img>`, `<a>`, `<audio>`, `<video>` (extract `src`, `href`).
- If the site supports **message edits/deletes**, emit **update events** with `meta.edited=true` or `meta.deleted=true` and **same `msg_id`**.

### 2.2 Event envelope (batching)
Batch multiple messages in an envelope for the webhook:
```json
{
  "client": {
    "extension_version": "1.0.0",
    "installation_id": "<uuid-v4>",
    "browser": "Chrome",
    "tz": "Asia/Riyadh"
  },
  "source": {
    "origin": "https://example.com/chat",
    "page_title": "<document.title>",
    "selector_version": 1
  },
  "messages": [ /* array of message objects above */ ]
}
```

---

## 3) Site configuration (selectors)
Because each chat UI differs, implement a **selector-config** the user can edit in the Options page and store in `chrome.storage.sync`.

**Model (Zod schema):**
```ts
const SelectorConfig = z.object({
  version: z.number().int().default(1),
  siteName: z.string(),
  matchUrls: z.array(z.string()),          // e.g., ["https://example.com/chat/*"]
  containerSelector: z.string(),           // scroll container of messages
  messageSelector: z.string(),             // each message root node
  authorSelector: z.string(),
  timestampSelector: z.string().optional(),
  textSelector: z.string(),
  htmlSelector: z.string().optional(),
  imageSelector: z.string().optional(),    // within a message
  audioSelector: z.string().optional(),
  videoSelector: z.string().optional(),
  linkSelector: z.string().optional(),
  permalinkSelector: z.string().optional(),
  replyCountSelector: z.string().optional(),
  reactionSelector: z.string().optional(),
  deletedPredicate: z.string().optional(), // CSS class indicating deletion
  editedPredicate: z.string().optional(),  // CSS class indicating edited
  dedupeKey: z.enum(["data-id","hash","auto"]).default("auto"),
  throttleMs: z.number().int().default(250),
  snapshotIntervalMs: z.number().int().default(60000)
});
```
Implement **validation + helpful error messages** in Options UI. Provide a **Test** button to run the selectors on the current tab and preview parsed JSON.

---

## 4) Content script (DOM observer)
Implement `src/content/index.ts`:
- On pages matching `matchUrls`, load config, then:
  - **Initial snapshot**: parse existing messages → push to a local queue (dedupe).
  - **MutationObserver** on `containerSelector`: on added/changed/removed `messageSelector` nodes, parse and enqueue delta items.
  - **Debounce** with `throttleMs` to avoid spamming.
  - **Periodic snapshot** every `snapshotIntervalMs` as a safety net.
- **Parser strategy** per message:
  - Read author, timestamp, text (prefers visible text only), innerHTML (optional).
  - Extract attachments from descendant selectors.
  - Compute `msg_id` per config (DOM `data-id` or SHA-256 hash of `(author|text|ts|channel)`).
  - Detect edited/deleted via predicates/classes.
- **Send** messages to background via `chrome.runtime.sendMessage` in **small batches** (e.g., up to 20).

**Reliability features:**
- **Dedupe** by `msg_id` in content script before sending.
- **Backpressure**: if background replies with `busy`, queue and retry with exponential backoff.
- **Visibility change**: on tab hidden → keep observing; on unload → flush queue.

---

## 5) Background service worker (networking & batching)
Implement `src/background/index.ts`:
- Maintain an **outbox** in `chrome.storage.local`:
  - Keyed by `batch_id` (uuid) → envelope payload.
- **Batching policy:**
  - Send when **≥ N messages** or **≥ T ms** elapsed (configurable).
  - If network fails, **retry with exponential backoff** (`1s, 2s, 4s, 8s, max 5m`).
  - Use `chrome.alarms` to wake and flush.
- **Idempotency & auth:**
  - Add headers:
    - `X-Installation-Id: <uuid>`
    - `X-Timestamp: <epoch_ms>`
    - `X-Idempotency-Key: <batch_id>`
    - `X-Signature: HMAC-SHA256(<body>, SHARED_SECRET)`
  - **Do not embed secrets in code.** Options UI allows entering a shared secret; store in `chrome.storage.local` **encrypted** with `chrome.runtime.getURL` Web Crypto (derive key from `chrome.storage.session` seed). If encryption is not feasible, store plaintext with a clear warning in UI.
- **Response handling:**
  - On HTTP `2xx`, delete batch from outbox.
  - On `409` or `429`, retry with backoff (respect `Retry-After`).
  - On `4xx` other than 409/429, log and pause sending; show badge warning.

---

## 6) Options page (settings UI)
Implement `src/options/index.tsx` (React + Tailwind):
- Sections:
  1. **Webhook**: URL (required), method (POST), headers (key/value), **Auth** (shared secret for HMAC).
  2. **Selectors**: full `SelectorConfig` with validation; **Test Selectors** on active tab (via `chrome.scripting.executeScript`) and render a **Preview Table** of parsed messages.
  3. **Batching & Retry**: `maxBatchSize`, `maxBatchIntervalMs`, `maxRetries`, `backoffCeilMs`.
  4. **Privacy & Scope**: toggle to **exclude** private DMs, or restrict to listed channels if recognizable in URL/DOM.
  5. **Diagnostics**: toggle verbose logs; “Flush Now” button; clear storage; export/import settings (JSON file).
- Be defensive: show inline error messages and a **status badge** (Connected / Errors / Idle).

---

## 7) Security, Privacy, ToS
- **Never** automate logins or bypass paywalls/DRM.
- **Process only visible DOM** on permitted hosts.
- **Minimize PII**: collect only fields listed above.
- **User consent**: first-run modal in Options: “Only capture on allowed domains.”
- **CORS**: background worker performs cross-origin POST (requires `host_permissions` for webhook domain or use `no-cors` + server-side CORS allowlist).

---

## 8) Performance & Resilience
- Use a **single** `MutationObserver` on the container; filter to `messageSelector` nodes.
- Debounce parse calls; avoid layout thrashing (no measurements that force reflow).
- Limit memory by trimming outbox size (e.g., 5MB cap). If exceeded, pause and notify user.
- On **tab reload/navigation**, re-init gracefully and avoid duplicate observers.

---

## 9) Testing & Acceptance Criteria (must pass)
### 9.1 Unit/E2E dev tests
- Selector tester returns **≥95%** of visible messages on a sample chat page.
- Duplicate messages (copy/pastes) do **not** create duplicate `msg_id`.
- Edited/deleted messages send **update events** with same `msg_id`.
- Outbox retries until success; respects `Retry-After`; stops after `maxRetries` with clear UI error.
- HMAC signature matches test server.
- Options export/import round trips perfectly.

### 9.2 Manual test script
1. Configure webhook to a local test server (provide `curl` alternative).
2. Load a sample chat page, scroll to add messages.
3. Verify Options → Test Selectors preview.
4. Toggle verbose logs and observe batches sent.
5. Simulate network failure → verify retries/backoff.
6. Edit/delete a message (if UI allows) → verify update event.
7. Export then import settings → same behavior.

**Only ship if all checks pass.**

---

## 10) Deliverables (from the LLM/codegen)
- `manifest.json` (MV3) with minimal permissions and correct routes.
- `src/content/index.ts` (observer + parser + batching to background).
- `src/background/index.ts` (outbox, networking, alarms, HMAC, retries).
- `src/options/index.tsx` with complete form, validation, test-run, preview, import/export.
- `src/shared/` utilities: logger, hash (SHA-256), zod schemas, storage API, idempotency keys, HMAC signer.
- `vite.config.ts` (or rollup), `tsconfig.json`, `.eslintrc.cjs`, `.prettierrc`.
- `README.md` with build/install instructions, permission rationale, and a **selector authoring guide**.
- A **sample `selectors.example.json`** prefilled with neutral placeholders.

---

## 11) Sample code skeletons (generate full code from these outlines)

### 11.1 Content script (outline)
```ts
// src/content/index.ts
import { getSettings, sendBatchToBackground, parseNode, hash, dedupe } from "../shared";
const observedIds = new Set<string>();
let queue: any[] = [];
let timer: number | undefined;

function scheduleFlush(throttleMs: number) {
  if (timer) return;
  timer = window.setTimeout(() => {
    const batch = queue.splice(0, queue.length);
    timer = undefined;
    if (batch.length) sendBatchToBackground(batch);
  }, throttleMs);
}

function initObserver(cfg: SelectorConfig) {
  const container = document.querySelector(cfg.containerSelector);
  if (!container) return console.warn("[Ext] container not found");
  const parseAll = () => {
    const nodes = container.querySelectorAll(cfg.messageSelector);
    nodes.forEach(n => {
      const msg = parseNode(n as HTMLElement, cfg);
      if (!msg) return;
      if (observedIds.has(msg.msg_id)) return;
      observedIds.add(msg.msg_id);
      queue.push(msg);
    });
    scheduleFlush(cfg.throttleMs);
  };
  parseAll();
  const mo = new MutationObserver(() => parseAll());
  mo.observe(container, { childList: true, subtree: true });
  setInterval(parseAll, cfg.snapshotIntervalMs);
}
```

### 11.2 Background (outline)
```ts
// src/background/index.ts
chrome.runtime.onMessage.addListener(async (msg, sender, sendResponse) => {
  if (msg?.type === "BATCH_MESSAGES") {
    await outbox.enqueue(msg.payload);
    await tryFlush();
    sendResponse({ ok: true });
  }
});

async function tryFlush() {
  // batch by size/time, HMAC sign, POST, handle retries with alarms
}
```

### 11.3 Options page (outline)
```tsx
// src/options/index.tsx
export default function Options() {
  // React form for webhook + selectors + buttons: Test, Save, Export/Import
  // On Test: execute script in active tab to run parser and show preview table
}
```

---

## 12) Configuration & Build
- `npm run dev` for HMR on options page and reloading service worker.
- `npm run build` outputs the MV3 bundle to `dist/`.
- Include instructions for **loading unpacked extension** in Chrome and granting host permissions.

---

## 13) Non-goals (explicit)
- No login automation, no bypass of paywalls/DRM, no network interception of request bodies.
- Do not download audio/video; **only capture URLs/metadata** from DOM nodes (backend will ingest media).

---

## 14) Nice-to-haves (if time permits)
- Popup with quick status (connected, batches queued, last send time).
- Optional **regex-based field extraction** hints (e.g., `[A-Z]{1,5}` tickers) for preview only.
- Lightweight “channel filter” if channel is discoverable in DOM/URL.

---

## 15) Hand-off checklist (must include)
- Working extension in `dist/`.
- Example selector config JSON for a typical chat layout.
- Postman/cURL collection to verify webhook and signature.
- Screenshots/gif of Options page, Test preview, and network logs.

> **Reminder:** If any selector cannot be determined at runtime, the code must **surface a clear error** in Options and refuse to run rather than guessing.
