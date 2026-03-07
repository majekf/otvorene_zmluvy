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


# Map backend JSON field names to human-readable labels used in prompt context.
# Add or override entries here to expose new fields without touching formatter logic.
FIELD_LABEL_MAP: Dict[str, str] = {
    "published_day": "Published day (raw)",
    "published_month": "Published month (raw)",
    "published_year": "Published year (raw)",
    "published_date": "Published date (normalized)",
    "contract_title": "Title",
    "contract_number": "Contract number",
    "price_raw": "Price (raw)",
    "price_numeric_eur": "Price in EUR (numeric)",
    "supplier": "Supplier",
    "buyer": "Buyer",
    "contract_url": "CRZ contract URL",
    "contract_id": "Contract ID",
    "scraped_at": "Scraped at",
    "contract_number_detail": "Contract number (detail page)",
    "contract_id_detail": "Contract ID (detail page)",
    "buyer_detail": "Buyer (detail page)",
    "supplier_detail": "Supplier (detail page)",
    "ico_buyer": "Buyer ICO",
    "ico_supplier": "Supplier ICO",
    "date_published": "CRZ published date",
    "date_concluded": "Signed date",
    "date_effective": "Effective from",
    "date_valid_until": "Valid until",
    "pdf_urls": "Attached PDF URLs",
    "pdf_url": "Primary PDF URL",
    "pdf_local_path": "Local PDF path",
    "pdf_text": "Extracted PDF text",
    "category": "Category",
    "pdf_text_summary": "PDF summary",
    "award_type": "Award type",
    "navrhovany_nazov": "Suggested title",
    "scanovane_ico_dodavatela": "Supplier ICO (scanned document)",
    "ico_supplier_scanned": "Supplier ICO (scanned document)",
    "ico_supplier_pdf": "Supplier ICO (PDF)",
    "mena_subdodavatelov": "Subcontractor names",
    "ico_subdodavatelov": "Subcontractor ICOs",
    "suma_sluzby": "Service amount",
    "typ_sluzby": "Service type",
    "typ_platby": "Payment type",
    "dovod_platby": "Payment reason",
    "suhrn": "Summary",
}


FILTER_LABEL_MAP: Dict[str, str] = {
    "institutions": "Institutions",
    "date_from": "Date from",
    "date_to": "Date to",
    "categories": "Categories",
    "vendors": "Vendors",
    "value_min": "Minimum value (EUR)",
    "value_max": "Maximum value (EUR)",
    "award_types": "Award types",
    "text_search": "Text search",
}


# ── Provenance document ──────────────────────────────────────────────


def _provenance_entry(c: Contract) -> Dict[str, str]:
    """Create a provenance metadata dict for a single contract."""
    return {
        "id": c.contract_id or "",
        "title": c.contract_title or "(untitled)",
        "source": c.contract_url or "",
        "date": c.published_date or "",
    }


def _humanize_field_name(field_name: str) -> str:
    """Resolve a field name to a human-readable label."""
    if field_name in FIELD_LABEL_MAP:
        return FIELD_LABEL_MAP[field_name]
    return field_name.replace("_", " ").strip().capitalize()


def _format_field_value(field_name: str, value: Any) -> str:
    """Render field values in a prompt-friendly, explicit way."""
    if value is None or value == "":
        return "not extracted"

    if isinstance(value, list):
        if not value:
            return "none"
        return ", ".join(str(v) for v in value)

    if isinstance(value, float):
        if field_name == "price_numeric_eur":
            return f"{value:,.2f} EUR"
        return f"{value}"

    if isinstance(value, bool):
        return "yes" if value else "no"

    return str(value)


def _filters_section(filters: FilterState) -> List[str]:
    """Build the ACTIVE FILTER section using actual GovLens filter keys."""
    lines = [
        "ACTIVE FILTERS (GovLens)",
        "",
    ]

    payload = filters.model_dump()
    for key in (
        "institutions",
        "date_from",
        "date_to",
        "categories",
        "vendors",
        "value_min",
        "value_max",
        "award_types",
        "text_search",
    ):
        raw_value = payload.get(key)
        label = FILTER_LABEL_MAP[key]
        lines.append(f"- {label}: {_format_field_value(key, raw_value)}")

    return lines


def _scope_summary_lines(contracts: List[Contract], agg: Dict[str, Any]) -> List[str]:
    """Build scope summary lines from filtered contracts."""
    dates = sorted([c.published_date for c in contracts if c.published_date])
    if dates:
        date_range = f"{dates[0]} to {dates[-1]}"
    else:
        date_range = "not available"

    return [
        "",
        "SCOPE SUMMARY",
        "",
        f"- Contracts in scope: {len(contracts)}",
        f"- Total value: {agg['total_spend']:,.2f} EUR",
        f"- Average value: {agg['avg_value']:,.2f} EUR",
        f"- Maximum value: {agg['max_value']:,.2f} EUR",
        f"- Date range in scope: {date_range}",
    ]


def _rules_section() -> List[str]:
    """Core response rules embedded into model context."""
    return [
        "",
        "RULES",
        "",
        "- Answer strictly from the contracts in this context.",
        "- Do not invent missing values.",
        "- If a field is 'not extracted', explicitly state that it is unavailable.",
        "- When referencing one contract, identify it by contract number + supplier + buyer.",
        "- If supplier ICO values from different sources conflict, proactively flag the mismatch.",
        "- You may compute totals, comparisons, trends, counts, and outliers.",
        "- Respond in the same language as the user message (Slovak, Czech, or English).",
    ]


def _contract_block(c: Contract, idx: int, total: int) -> str:
    """Render one full contract record with human labels and JSON key reference."""
    lines: List[str] = [
        f"--- CONTRACT {idx} / {total} ---",
    ]

    record = c.model_dump(exclude_none=False)

    supplier_ico = record.get("ico_supplier")
    scanned_ico = (
        record.get("scanovane_ico_dodavatela")
        or record.get("ico_supplier_scanned")
        or record.get("ico_supplier_pdf")
    )
    if supplier_ico and scanned_ico and str(supplier_ico).strip() != str(scanned_ico).strip():
        lines.append(
            "WARNING [ico_mismatch]: "
            f"website supplier ICO={supplier_ico}, scanned supplier ICO={scanned_ico}"
        )

    for key, value in record.items():
        label = _humanize_field_name(key)
        rendered = _format_field_value(key, value)
        lines.append(f"{label} [{key}]: {rendered}")

    return "\n".join(lines)


def _contract_reference_line(c: Contract) -> str:
    """Compact line used in summary mode top-N list."""
    number = c.contract_number or c.contract_id or "?"
    supplier = c.supplier or "?"
    buyer = c.buyer or "?"
    value = f"{(c.price_numeric_eur or 0.0):,.2f} EUR"
    return f"- {number} | {supplier} | {buyer} | {value}"


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
    header = [
        "You are an intelligent assistant for GovLens, an open-data platform for Slovak public procurement analysis.",
        "Use only the contracts included below.",
        "",
        *_filters_section(filters),
        *_scope_summary_lines(contracts, agg),
        *_rules_section(),
        "",
        "FIELD LABEL MAP (json_key -> human label)",
        "",
    ]
    for key in sorted(FIELD_LABEL_MAP.keys()):
        header.append(f"- {key} -> {FIELD_LABEL_MAP[key]}")

    if n <= _FULL_DETAIL_THRESHOLD:
        # Full detail mode: include all fields for every in-scope contract.
        lines = [
            *header,
            "",
            "CONTRACTS",
            "",
        ]
        for idx, c in enumerate(contracts, start=1):
            lines.append(_contract_block(c, idx, n))
            lines.append("")
            provenance.append(_provenance_entry(c))
        context = "\n".join(lines)
    else:
        # Summary mode — top-N full blocks + aggregate breakdown for the remainder.
        sorted_by_value = sorted(
            contracts,
            key=lambda c: c.price_numeric_eur or 0.0,
            reverse=True,
        )
        top_contracts = sorted_by_value[:top_n]

        lines = [
            *header,
            "",
            "CONTRACTS (summary mode)",
            "",
            f"Showing full details for top {top_n} contracts by value.",
            f"Remaining contracts in scope: {n - top_n}.",
            "",
        ]

        # Category breakdown
        groups = store.group_by("category", contracts)
        lines.append("Category breakdown:")
        for cat, cat_contracts in sorted(
            groups.items(), key=lambda x: len(x[1]), reverse=True
        ):
            cat_total = sum(c.price_numeric_eur or 0 for c in cat_contracts)
            lines.append(f"  {cat}: {len(cat_contracts)} contracts, {cat_total:,.2f} EUR")
        lines.append("")

        # Top contracts (full details)
        lines.append(f"Top {top_n} contracts by value:")
        for idx, c in enumerate(top_contracts, start=1):
            lines.append(_contract_block(c, idx, top_n))
            lines.append("")
            provenance.append(_provenance_entry(c))

        # Remaining summary
        remaining = n - top_n
        remaining_total = sum(
            c.price_numeric_eur or 0 for c in sorted_by_value[top_n:]
        )
        lines.append(f"Remaining contracts total: {remaining_total:,.2f} EUR")
        lines.append("Remaining contracts (compact reference):")
        for c in sorted_by_value[top_n:top_n + 50]:
            lines.append(_contract_reference_line(c))

        context = "\n".join(lines)

    result = (context, provenance)
    if use_cache:
        _cache.put(filters, *result)
    return result
