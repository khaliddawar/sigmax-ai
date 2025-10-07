"""Generic Decision Extraction Service

This module introduces a domain-agnostic replacement for the former
TradeExtractionService.  It follows the project's new architecture in
which *all* domain-specific pieces (prompt wording, model selection,
JSON schema, post-processing) live outside application code so the same
Python logic can be reused for finance, healthcare, legal, etc.

Key design points
-----------------
1. Domain specific knowledge lives in:
   • config/domains/<domain>.yaml  – model, max_tokens, misc switches
   • config/prompts/<domain>/extraction.prompt – LLM prompt template
   • app/post_processors/<domain>.py            – result-parsing helpers
2. The service itself only:
   • Counts tokens (tiktoken)
   • Decides whether to chunk (SemanticChunker)
   • Calls OpenAI
   • Delegates parsing to the per-domain post-processor if present.
3. Backwards-compat: TradeExtractionService becomes a *thin* subclass
   that merely sets domain_type="financial".
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from importlib import import_module
from typing import Any, Dict, List, Optional

import openai  # type: ignore
import tiktoken  # type: ignore
import yaml  # type: ignore

from .semantic_chunker import SemanticChunker

logger = logging.getLogger("decision-extraction-service")

# ---------------------------------------------------------------------------
# Generic data structure -----------------------------------------------------
# ---------------------------------------------------------------------------

@dataclass
class Decision:
    """Generic representation of an actionable decision/recommendation."""

    action: str  # e.g. "buy", "prescribe", "approve", etc.
    subject: str  # ticker, medicine name, law article, …
    confidence: float = 0.5
    reasoning: str = ""
    timestamp: Optional[str] = None  # optional – when the statement was made
    extra: Dict[str, Any] = None  # domain-specific key-value pairs

    # Convenience to go back to plain dict (useful for JSON responses)
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Service class --------------------------------------------------------------
# ---------------------------------------------------------------------------

class DecisionExtractionService:
    """Domain-agnostic extraction of actionable decisions from transcripts."""

    DEFAULT_MODEL = "gpt-3.5-turbo-0125"
    DEFAULT_MAX_TOKENS = 16000  # sensible default if domain YAML missing
    PROMPT_OVERHEAD = 1000      # safety reserve for system + response

    def __init__(self, *, domain_type: str = "generic"):
        self.domain_type = domain_type or "generic"

        # ---- load domain configuration ------------------------------------
        domain_cfg_path = Path("config") / "domains" / f"{self.domain_type}.yaml"
        if domain_cfg_path.exists():
            with domain_cfg_path.open("r", encoding="utf-8") as fh:
                domain_cfg = yaml.safe_load(fh)
        else:
            logger.warning("Domain config %s not found – falling back to defaults", domain_cfg_path)
            domain_cfg = {}

        self.model: str = domain_cfg.get("model", self.DEFAULT_MODEL)
        self.max_context_tokens: int = domain_cfg.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self.max_safe_tokens: int = self.max_context_tokens - self.PROMPT_OVERHEAD

        # ---- prompt template ---------------------------------------------
        prompt_path = Path("config") / "prompts" / self.domain_type / "extraction.prompt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
        self.prompt_template = prompt_path.read_text(encoding="utf-8")

        # ---- helpers ------------------------------------------------------
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.chunker = SemanticChunker(domain_type=self.domain_type)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract_decisions(self, transcript_text: str) -> List[Decision]:
        """Main entry – return a list of domain-specific decisions."""
        if self._count_tokens(transcript_text) <= self.max_safe_tokens:
            raw = self._call_llm(self._build_prompt(transcript_text))
            return self._parse(raw)

        # Otherwise chunk & aggregate
        decisions: List[Decision] = []
        chunks = self.chunker.chunk_text(transcript_text, max_chunk_size=self.max_safe_tokens)
        for chunk in chunks:
            raw = self._call_llm(self._build_prompt(chunk.text))
            decisions.extend(self._parse(raw))
        return decisions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_prompt(self, text: str) -> str:
        return self.prompt_template.replace("{text}", text)

    def _call_llm(self, prompt: str) -> str:
        """Thin wrapper around openai.ChatCompletion.create."""
        logger.debug("Calling OpenAI model %s (tokens≈%s)", self.model, self._count_tokens(prompt))
        resp = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        return resp.choices[0].message.content  # type: ignore[attr-defined]

    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    # ------------------------------------------------------------------
    # Parsing (delegates to domain adapter if present)
    # ------------------------------------------------------------------
    def _parse(self, raw: str) -> List[Decision]:
        adapter_mod_name = f"app.post_processors.{self.domain_type}"
        try:
            adapter = import_module(adapter_mod_name)
            if hasattr(adapter, "parse"):
                return adapter.parse(raw)  # type: ignore[return-value]
            logger.warning("parse() not found in %s – falling back to generic JSON parser", adapter_mod_name)
        except ModuleNotFoundError:
            logger.info("No domain adapter %s – using generic parser", adapter_mod_name)
        return self._generic_json_parse(raw)

    def _generic_json_parse(self, raw: str) -> List[Decision]:
        """A very forgiving JSON parser for generic use-cases."""
        raw = raw.strip()
        # try to locate a JSON array / object in raw
        import re
        json_match = re.search(r"\[.*\]", raw, re.DOTALL) or re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # quick fixes
            raw = raw.replace("'", '"')
            raw = re.sub(r"(\w+):", r'"\1":', raw)
            data = json.loads(raw)

        decisions: List[Decision] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    decisions.append(Decision(**{k: item.get(k) for k in Decision.__annotations__}))
        elif isinstance(data, dict):
            decisions.append(Decision(**{k: data.get(k) for k in Decision.__annotations__}))
        return decisions 