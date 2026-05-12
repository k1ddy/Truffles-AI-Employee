"""Corpus tooling for Policy-Core v3 shadow-run.

Status: PoC tooling. Not in runtime hot path.
Spec: SPECS/SHADOW_RUN_V3.md (Phase B.3).

This package owns:
- CorpusTurn / CorpusDialog typed schema and JSONL loader.
- Oracle/drift mock LLM that produces v3 responses from fixture data.
- Aggregator that turns ComparisonRecord JSONL into a histogram report.

It does NOT touch the runtime. The corpus runner script orchestrates this
package against `run_shadow`.
"""

from .aggregator import (
    CorpusAggregateReport,
    aggregate_records,
    aggregate_jsonl_file,
    format_report_text,
)
from .intent_vocabulary import normalize_legacy_intent, semantic_match
from .oracle_llm import (
    OracleLLMConfig,
    OracleLLMMode,
    build_oracle_llm,
)
from .runner import run_corpus
from .schema import CorpusDialog, CorpusTurn, load_corpus_jsonl

__all__ = [
    "CorpusAggregateReport",
    "CorpusDialog",
    "CorpusTurn",
    "OracleLLMConfig",
    "OracleLLMMode",
    "aggregate_jsonl_file",
    "aggregate_records",
    "build_oracle_llm",
    "format_report_text",
    "load_corpus_jsonl",
    "normalize_legacy_intent",
    "run_corpus",
    "semantic_match",
]
