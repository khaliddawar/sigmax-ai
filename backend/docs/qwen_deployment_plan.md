# Qwen Summary Generation Deployment Plan

## 1. Objectives

* **Reduce inference cost** by switching the _summary‐only_ stage from OpenAI GPT-4o(128k) to **Qwen-Max / Qwen-Flash** while keeping existing GPT models for embeddings / RAG retrieval.
* **Handle very long transcripts** (6–12 h videos) using Qwen’s ≥128 k-token context window.
* **Zero regression** for existing pipelines: embeddings, vector search, QA, payment flow, Chrome extension.

---

## 2. Model Options & Costs

| Model | Context Window | Price (1 K tokens) | Speed | Notes |
|-------|----------------|--------------------|-------|-------|
| GPT-4o-128k | 128 k | $5.00 in / $15.00 out | 1× | Baseline (current) |
| **Qwen-Flash** | 128 k | **$0.30** in / **$0.60** out | 1.2× | Cheaper drop-in window match |
| **Qwen-Max**  | 200 k | $0.50 in / $1.00 out | 1× | Extra head-room for 12 h video |
| Qwen-2.5-Turbo-1M | 1 M | $5.00 in / $10.00 out | 0.6× | Only for enterprise, GPU-heavy |

We will default to **Qwen-Max** and allow **Qwen-Flash** as a cost-saving tier via env-var.

---

## 3. High-Level Architecture Impact

```
┌─────────┐   ┌─────────────┐   ┌───────────┐
│Chrome ex│→ │/api/yt_sum  │→ │SummarySvc │──► Qwen-Max  (NEW)
└─────────┘   └─────────────┘   └───────────┘
                                       ▲
                                   GPT Emb   (UNCHANGED)
```
* **Unaffected components:**  EmbeddingService, RetrievalQAService, vector DB, Chrome extension.
* **Changed component:**      `SummaryService` (and `SemanticChunker` size logic).

---

## 4. Code Changes

### 4.1 Dependencies

*Add to `requirements.txt`*
```text
# Qwen provider
openai>=1.12.0   # via OpenRouter compatible endpoint
# OR for native:
dashscope>=1.14.0
```

### 4.2 Settings

*Modify* `app/settings.py`
```python
class Settings(BaseSettings):
    SUMMARY_MODEL_PROVIDER: Literal["openai", "anthropic", "qwen"] = "openai"
    SUMMARY_MODEL: str = "qwen-max"
    QWEN_API_KEY: str | None = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
```
Expose in **`.env`**:
```dotenv
SUMMARY_MODEL_PROVIDER=qwen
SUMMARY_MODEL=qwen-max   # or qwen-flash
QWEN_API_KEY=sk-qwen-...
```

### 4.3 Service Layer

*Refactor* `app/services/summary_service.py`
1. Add an `LLMProvider` Enum.
2. Extract provider factory `_get_llm_client(settings)` returning a callable.
3. Replace direct OpenAI calls with `self.call_llm(prompt, history)`.

### 4.4 Chunking Logic

*Update* `app/services/semantic_chunker.py`
```python
DEFAULT_CHUNK_SIZE = 2_048  # tokens (GPT)
QWEN_CHUNK_SIZE = 8_000     # tokens

chunk_size = QWEN_CHUNK_SIZE if settings.SUMMARY_MODEL_PROVIDER == "qwen" else DEFAULT_CHUNK_SIZE
```
No changes to embedding chunking.

### 4.5 Prompt Adjustments

Qwen tends to respond in Chinese unless instructed:
```python
SYSTEM_MSG = (
    "You are TubeVibe-AI summariser. Answer in English. Output sections: TL;DR, Key-Insights, Timestamps."
)
```

### 4.6 Feature Flag

Add to `app/utils/feature_flags.py`:
```python
def use_qwen_summary() -> bool:
    return os.getenv("SUMMARY_MODEL_PROVIDER", "openai") == "qwen"
```
The Chrome extension keeps calling the same endpoint; backend switches provider.

### 4.7 Tests

*`tests/test_qwen_summary.py`*
```python
@pytest.mark.asyncio
@mock.patch.dict(os.environ, {"SUMMARY_MODEL_PROVIDER": "qwen", "QWEN_API_KEY": "test"})
async def test_qwen_summary(monkeypatch):
    async def _fake_llm(prompt, history):
        return "Summary: ..."
    monkeypatch.setattr(summary_service, "_get_llm_client", lambda s: _fake_llm)
    txt = "word " * 150_000
    res = await SummaryService(Settings()).generate_summary([txt])
    assert res.startswith("Summary")
```

---

## 5. Deployment

### 5.1 Dockerfile
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
ENV SUMMARY_MODEL_PROVIDER=qwen
ENV SUMMARY_MODEL=qwen-max
ENV QWEN_API_KEY=$QWEN_API_KEY
```

### 5.2 Render / Railway Secrets
* Add `QWEN_API_KEY`.
* If using OpenRouter: set `OPENAI_API_KEY` to the OpenRouter key and model name to `qwen-max`.

### 5.3 Roll-out Strategy
| Stage | Traffic % | Env settings |
|-------|-----------|--------------|
| Canary | 5 % power-users | `SUMMARY_MODEL_PROVIDER=qwen` |
| Ramp   | 25 % | increase flag in feature_flags |
| Full   | 100 % | remove legacy code path after 2 w |

Monitor **`summary_service`** latency & error rate via existing structured logs.

---

## 6. Cost Projection

| Volume | GPT-4o 128k | Qwen-Max 200k | **Savings** |
|--------|-------------|---------------|-------------|
| 100 M tokens / mo | $2 000 | $500 | **75 % ↓** |

---

## 7. Fallback & Failure Modes
1. If Qwen times-out > 30 s → auto-retry with GPT-4o.
2. If Qwen returns non-English summary → fallback prompt & retry once.
3. Log provider in DB for each summary for post-mortem.

---

## 8. Timeline
| Day | Task |
|-----|------|
| 1   | Add deps, env-vars, feature flag |
| 2   | Implement provider factory & tests |
| 3   | Container build, staging deploy |
| 4-5 | Canary traffic 5 %, monitor |
| 6   | Ramp to 25 % |
| 10  | Full switch, remove GPT path in v2 |

---

## 9. Owners
* **Backend:** `@dev_backend`
* **Ops / DevOps:** `@devops`
* **QA:** `@qa_team`

> **Outcome:** TubeVibe can summarise 12-hour videos at one-quarter the current cost without touching embeddings, retrieval or the Chrome extension.
