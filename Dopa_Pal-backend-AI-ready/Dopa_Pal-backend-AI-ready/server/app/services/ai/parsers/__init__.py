"""Deterministic, rule-based parsers used by the ingestion pipeline.

Each parser takes raw text and returns a best-effort structured value plus
a confidence score. None of these depend on an LLM - that's the whole point
of the deterministic-first architecture described in the README.
"""
