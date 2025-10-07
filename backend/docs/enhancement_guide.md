0 · Model choice (clear-up)
Default for production / cost-control: gpt-4o-mini

Override for high-fidelity runs or pilot demo: gpt-4o-mini (same response-format interface).

Implementation: add OPENAI_MODEL_NAME in settings.py or .env etc; every service uses that constant, so you can switch in one line without touching code.

1 · Create / replace app/services/transcript_processor.py
This file supersedes the old transcript_processor.py and the obsolete .srt pre-processor.

python
Copy
Edit
"""
TranscriptProcessor
• Accepts str, Path (.txt) or JSON payload (future Fireflies webhook)
• Splits into paragraphs
• Tags each paragraph with anchor topics
• Exposes helper: `bucketed_text()` for summary prompt
"""
from pathlib import Path
import json, re, typing as T, collections

ANCHOR_KEYWORDS = {
    # ------------- Equities / Indices / Crypto / Ccy / EM -------------
    "indices": [
        "s&p", "spx", "nasdaq", "ndx", "dow", "djia",
        "vix", "volatility",
        "bitcoin", "btc", "crypto",
        "dollar index", "dxy",
        "yen", "jpy", "euro", "eur", "gbp", "cad",
        "emerging market", "eem"
    ],
    # ------------- Commodities ----------------------------------------
    "commodities": [
        "gold", "silver", "crude", "oil", "nat gas",
        "uranium", "copper", "platinum", "palladium"
    ],
    # ------------- Trades / levels ------------------------------------
    "trades": ["long", "short", "buy", "sell",
               "entry", "target", "stop", "take profit"],
    # ------------- Q&A trigger ----------------------------------------
    "qa": ["question:", "q:", "answer:", "a:"]
}

def _load_raw(source: str | Path) -> str:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    else:
        text = source
    # future Fireflies JSON support
    if text.lstrip().startswith("{"):
        try:
            payload = json.loads(text)
            text = "\n".join(u["text"] for u in payload.get("utterances", []))
        except json.JSONDecodeError:
            pass
    # strip any stray .srt time-stamps
    return re.sub(r"\d+\n\d\d:\d\d:\d\d.\d+ --> .*", "", text).strip()

def _tag_paragraph(p: str) -> set[str]:
    low = p.lower()
    return {
        tag
        for tag, kw_list in ANCHOR_KEYWORDS.items()
        if any(k in low for k in kw_list)
    } or {"misc"}

def bucketed_text(source: str | Path) -> dict[str, str]:
    """Returns dict where key = topic tag, val = concatenated text."""
    raw = _load_raw(source)
    paras = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]
    buckets = collections.defaultdict(list)
    for p in paras:
        for tag in _tag_paragraph(p):
            buckets[tag].append(p)
    # concatenate & clip each bucket to 4000 chars (token safety)
    return {k: "\n".join(v)[:4000] for k, v in buckets.items()}
2 · Patch summary_service.py
2-A · Import processor & build prompt chunks (if not already in place)
python
Copy
Edit
from app.services.transcript_processor import bucketed_text

buckets = bucketed_text(transcript_source)          # Path or raw str
prompt_chunks = "\n\n".join(
    f"[{k.upper()}]\n{v}" for k, v in buckets.items()
)
2-B · Replace existing PROMPT string with JSON-schema prompt (see block below)
python
Copy
Edit
PROMPT_TEMPLATE = """
You are “BPT Session Summarizer,” a professional macro & trading analyst.
Return ONLY valid JSON. Use null where data absent.

JSON schema:
{
  "executive_snapshot": {...},
  "indices": [...],        // now includes BTC, major FX, EM
  "commodities": [...],
  ...
}

### TRANSCRIPT ###
{prompt_chunks}
### END ###
"""
2-C · Call OpenAI with enforced JSON output
python
Copy
Edit
resp = client.chat.completions.create(
    model=settings.OPENAI_MODEL_NAME,
    messages=[{"role": "system", "content": PROMPT_TEMPLATE.format(prompt_chunks=prompt_chunks)}],
    response_format={"type": "json_object"},
    temperature=0.2,
)
data = json.loads(resp.choices[0].message.content)
2-D · Empty-field retry (insert right after data = …)
python
Copy
Edit
missing = [k for k, v in data.items() if v in (None, [], "", {})]
if missing:
    retry_prompt = (
        "Fill ONLY the keys now null/empty: " + ", ".join(missing) +
        "\n### TRANSCRIPT ###\n" + prompt_chunks + "\n### END ###"
    )
    resp2 = client.chat.completions.create(
        model=settings.OPENAI_MODEL_NAME,
        messages=[{"role": "system", "content": retry_prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    patch = json.loads(resp2.choices[0].message.content)
    data.update({k: v for k, v in patch.items() if v not in (None, [], "", {})})
3 · Enhance trade_service.py (ticker seeding)
Locate extract_trades() and prepend:

python
Copy
Edit
TICKER = re.compile(r"\b[A-Z]{1,5}\b")
seed = [t for t in set(TICKER.findall(text)) if len(t) >= 2 and t.isupper()]
Then include seed in the LLM prompt as shown in previous message (“Given SEED tickers …”).

4 · Tighten HTML spacing in email_template.html
Global reset (top of file):

html
Copy
Edit
<style>
  body, table { margin:0; padding:0; font-family:Inter,Arial,sans-serif; }
  td { padding:4px 0; line-height:1.3em; vertical-align:top; }
  h2 { margin:18px 0 6px; }
  .section { margin-bottom:14px; }
</style>
Change every <td> tag to include no extra <p> wrappers; e.g.,

jinja
Copy
Edit
<td>{{ item.name }}</td>      <!-- GOOD -->
<td><p>{{ item.name }}</p></td> <!-- DELETE the <p> -->
5 · Adjust ingestion_service.py (future Fireflies webhook)
When webhook arrives:

python
Copy
Edit
from app.services.transcript_processor import _load_raw

payload_json = await request.json()
raw_text = json.dumps(payload_json)      # store full JSON
# save `raw_text` to S3 / DB for audit
Pass raw_text downstream—_load_raw already extracts utterances.

6 · settings.py or .env or where the model is mentioned
Add:

python
Copy
Edit
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
Now switching to gpt-4o-mini is one env-var tweak.

7 · Tests (very short)
python
Copy
Edit
def test_no_empty_fields(sample_transcript_txt):
    from app.services.summary_service import summarise
    data = summarise(sample_transcript_txt)
    assert all(v not in (None, [], "", {}) for v in data.values())
Deliver this checklist to your AI editor
Create / overwrite app/services/transcript_processor.py (Section 1).

Patch summary_service.py (2-A → 2-D).

Update trade_service.py ticker seeding (Section 3).

Fix email_template.html spacing (Section 4).

Add model constant to settings.py (Section 6).

(Optional) edit ingestion_service.py to store raw JSON (Section 5).

Add / update tests (Section 7).

Follow these steps sequentially; commit after each section to keep diffs atomic.
Result: cleaner emails, fully populated sections (indices now include Bitcoin, FX, EM), easy model switching, and future-proof ingest for Fireflies JSON.