"""
Context builder for the chatbot.

Builds a scoped context string from the current ``FilterState`` and
``DataStore``, including provenance metadata. Implements a simple
in-memory LRU cache keyed by the filter hash to avoid recomputation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from ..engine import DataStore
from ..models import Contract, FilterState

logger = logging.getLogger(__name__)

# Maximum contracts to include in full detail
_FULL_DETAIL_THRESHOLD = 100
# Top-N contracts to include when summarising
_TOP_N = 20
# LRU cache max entries
_CACHE_MAX = 128


# ── Provenance document ──────────────────────────────────────────────


def _provenance_entry(c: Contract) -> Dict[str, str]:
    """Create a provenance metadata dict for a single contract."""
    return {
        "id": c.contract_id or "",
        "title": c.contract_title or "(untitled)",
        "source": c.contract_url or "",
        "date": c.published_date or "",
    }


# ── Cache ────────────────────────────────────────────────────────────


class _ContextCache:
    """Simple in-process LRU cache for context chunks."""

    def __init__(self, max_size: int = _CACHE_MAX):
        self._store: OrderedDict[str, Tuple[str, List[Dict[str, str]]]] = OrderedDict()
        self._max = max_size

    def _key(self, filters: FilterState) -> str:
        raw = json.dumps(filters.model_dump(), sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, filters: FilterState):
        key = self._key(filters)
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def put(self, filters: FilterState, context: str, provenance: List[Dict[str, str]]):
        key = self._key(filters)
        self._store[key] = (context, provenance)
        self._store.move_to_end(key)
        if len(self._store) > self._max:
            self._store.popitem(last=False)

    def clear(self):
        self._store.clear()


# Singleton cache
_cache = _ContextCache()


def get_context_cache() -> _ContextCache:
    """Return the module-level context cache (for testing)."""
    return _cache


# ── Context builder ──────────────────────────────────────────────────


def build_scoped_context(
    filters: FilterState,
    store: DataStore,
    top_n: int = _TOP_N,
    use_cache: bool = True,
) -> Tuple[str, List[Dict[str, str]]]:
    """Build a scoped context string and provenance docs from current filters.

    Strategy:
    - ``n ≤ 100`` → full filtered dataset in context
    - ``n > 100`` → top-N by value + category aggregates + compressed
      remainder summary

    Returns ``(context_string, provenance_list)``.
    """
    if use_cache:
        cached = _cache.get(filters)
        if cached is not None:
            logger.debug("Context cache hit for filters")
            return cached

    contracts = store.filter(filters)
    n = len(contracts)
    provenance: List[Dict[str, str]] = []

    if n == 0:
        context = "No contracts match the current filters."
        result = (context, provenance)
        if use_cache:
            _cache.put(filters, *result)
        return result

    # Aggregate stats
    agg = store.aggregate(contracts)
    stats_header = (
        f"Scope: {n} contracts | "
        f"Total spend: €{agg['total_spend']:,.2f} | "
        f"Average: €{agg['avg_value']:,.2f} | "
        f"Max: €{agg['max_value']:,.2f}"
    )

    if n <= _FULL_DETAIL_THRESHOLD:
        # Full detail mode
        lines = [stats_header, ""]
        for c in contracts:
            lines.append(_contract_line(c))
            provenance.append(_provenance_entry(c))
        context = "\n".join(lines)
    else:
        # Summary mode — top-N + aggregates
        sorted_by_value = sorted(
            contracts,
            key=lambda c: c.price_numeric_eur or 0.0,
            reverse=True,
        )
        top_contracts = sorted_by_value[:top_n]

        lines = [stats_header, ""]

        # Category breakdown
        groups = store.group_by("category", contracts)
        lines.append("Category breakdown:")
        for cat, cat_contracts in sorted(
            groups.items(), key=lambda x: len(x[1]), reverse=True
        ):
            cat_total = sum(c.price_numeric_eur or 0 for c in cat_contracts)
            lines.append(f"  {cat}: {len(cat_contracts)} contracts, €{cat_total:,.2f}")
        lines.append("")

        # Top contracts
        lines.append(f"Top {top_n} contracts by value:")
        for c in top_contracts:
            lines.append(_contract_line(c))
            provenance.append(_provenance_entry(c))
        lines.append("")

        # Remaining summary
        remaining = n - top_n
        remaining_total = sum(
            c.price_numeric_eur or 0 for c in sorted_by_value[top_n:]
        )
        lines.append(
            f"Plus {remaining} additional contracts "
            f"totalling €{remaining_total:,.2f}."
        )

        context = "\n".join(lines)

    result = (context, provenance)
    if use_cache:
        _cache.put(filters, *result)
    return result


def _contract_line(c: Contract) -> str:
    """Format a single contract as a context line."""
    parts = [
        f"[{c.contract_id or '?'}]",
        c.contract_title or "(untitled)",
        f"| {c.buyer or '?'} → {c.supplier or '?'}",
        f"| €{c.price_numeric_eur:,.2f}" if c.price_numeric_eur else "| €?",
        f"| {c.published_date or '?'}",
        f"| {c.category}",
    ]
    if c.pdf_text_summary and c.pdf_text_summary != "not_summarized":
        # Truncate long summaries
        summary = c.pdf_text_summary[:200]
        parts.append(f'| "{summary}"')
    return " ".join(parts)
