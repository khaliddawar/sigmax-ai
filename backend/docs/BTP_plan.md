# Big Picture Trading Session Companion – MVP Plan
_Last updated: 2025-05-20_

<!-- NEW -->
## 📌 Objective (one-paragraph version)
> **Goal:** Within 10 minutes after any BPT Zoom session ends, every subscribed member receives an email “Quick-Sheet” and can ask a Slack bot natural-language questions about the session. The demo must work on one real recording and run on free-tier cloud resources.

## 🎯 Key deliverables (MVP demo)
- [ ] **End-to-end ingestion pipeline** triggered by Fireflies webhook
- [ ] **Quick-Sheet HTML email** with 120-word recap & trade table
- [ ] **Vector-indexed transcript** stored in Supabase pgvector
- [ ] **Slack slash command `/ask-bpt`** calling Retrieval-QA endpoint
- [ ] **Render deployment** (Docker) with `.env`-based secrets
- [ ] **Stopwatch latency log** proving < 10 min turnaround
<!-- /NEW -->

## 0. Goal
Deliver a **live demo** that:
1. Auto-ingests a recent Zoom/Fireflies session.
2. Emails a “Quick-Sheet” summary + trade table within 10 min.
3. Provides a Slack slash-command `/ask-bpt` that answers questions from the vector-indexed transcript.
Latency target for demo: ≤ 10 min end-to-end.

...

### 2.1  Project scaffolding (Day 1)
- [ ] **As a developer**, I can create the repo, licence, `README` so others can clone and run `make dev`.
  - [ ] `pyproject.toml` with FastAPI, langchain, openai, supabase-py, slack-bolt
  - [ ] `Dockerfile` builds & runs unit tests
  - [ ] `pre-commit` hooks (`ruff`, `black`)
  - **DoD:** `docker compose up` starts API on `localhost:8000/docs`

...

### 2.4  Email package & send (Day 4)
- [ ] **As a member**, I receive an HTML email containing the Quick-Sheet.
  - [ ] Jinja2 template `email_quicksheet.html`
  - [ ] SES sandbox credentials verified
  - **DoD:** Sending function returns 200 and email arrives in Gmail inbox.

...

## 4. Acceptance criteria
- [ ] Quick-Sheet arrives < 10 min after webhook (measured with stopwatch)
- [ ] `/ask-bpt "What is the stop on NVDA?"` returns correct answer ≤ 3 s
- [ ] Code passes `pytest -q` (≥ 5 unit tests)
