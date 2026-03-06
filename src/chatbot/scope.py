"""
Scope enforcement for the chatbot.

Checks whether a user query references entities (institutions,
vendors, dates) that fall outside the active ``FilterState``.
When the query is out of scope, returns a structured ``ScopeRefusal``
with suggestions for how to change the filters.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..engine import DataStore
from ..models import FilterState

logger = logging.getLogger(__name__)

# Structured log for refused queries
_refusal_log: List[Dict[str, Any]] = []


@dataclass
class ScopeRefusal:
    """Structured refusal when a query is out of scope."""

    reason: str
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    hint_endpoint: str = ""


def get_refusal_log() -> List[Dict[str, Any]]:
    """Return the in-memory refusal log (for testing / inspection)."""
    return _refusal_log


def clear_refusal_log() -> None:
    """Clear the in-memory refusal log."""
    _refusal_log.clear()


def check_scope(
    message: str,
    filters: FilterState,
    store: DataStore,
) -> Optional[ScopeRefusal]:
    """Check whether *message* references entities outside the current filter scope.

    Returns ``None`` if the message is in-scope, or a ``ScopeRefusal``
    with suggestions if it is out-of-scope.
    """
    message_lower = message.lower()

    # Gather known entities from the store
    all_institutions = {
        inst.name.lower(): inst.name
        for inst in store.institutions()
    }
    all_vendors = {
        v.name.lower(): v.name for v in store.vendors()
    }

    # Active filter scope
    scoped_institutions = {
        name.lower() for name in (filters.institutions or [])
    }
    scoped_vendors = {name.lower() for name in (filters.vendors or [])}

    suggestions: List[Dict[str, Any]] = []
    reasons: List[str] = []

    # ── Check institution references ─────────────────────────────────
    for inst_lower, inst_name in all_institutions.items():
        if inst_lower in message_lower:
            # Institution is mentioned
            if scoped_institutions and inst_lower not in scoped_institutions:
                reasons.append(
                    f'Institution "{inst_name}" is not in the current filter scope.'
                )
                suggestions.append(
                    {
                        "label": f"Add {inst_name} to institution filter",
                        "action": "add_institution",
                        "value": inst_name,
                    }
                )

    # ── Check vendor references ──────────────────────────────────────
    for vendor_lower, vendor_name in all_vendors.items():
        if vendor_lower in message_lower:
            if scoped_vendors and vendor_lower not in scoped_vendors:
                reasons.append(
                    f'Vendor "{vendor_name}" is not in the current filter scope.'
                )
                suggestions.append(
                    {
                        "label": f"Add {vendor_name} to vendor filter",
                        "action": "add_vendor",
                        "value": vendor_name,
                    }
                )

    # ── Check date references ────────────────────────────────────────
    year_matches = re.findall(r"\b(20[12]\d)\b", message)
    if year_matches and (filters.date_from or filters.date_to):
        for year_str in year_matches:
            year = int(year_str)
            if filters.date_from:
                from_year = int(filters.date_from[:4])
                if year < from_year:
                    reasons.append(
                        f"Year {year} is before the filter start date ({filters.date_from})."
                    )
                    suggestions.append(
                        {
                            "label": f"Expand date range to include {year}",
                            "action": "set_date_from",
                            "value": f"{year}-01-01",
                        }
                    )
            if filters.date_to:
                to_year = int(filters.date_to[:4])
                if year > to_year:
                    reasons.append(
                        f"Year {year} is after the filter end date ({filters.date_to})."
                    )
                    suggestions.append(
                        {
                            "label": f"Expand date range to include {year}",
                            "action": "set_date_to",
                            "value": f"{year}-12-31",
                        }
                    )

    if not reasons:
        return None

    refusal = ScopeRefusal(
        reason=" ".join(reasons),
        suggestions=suggestions,
        hint_endpoint=f"/api/institutions?{_build_hint_qs(suggestions)}",
    )

    # Log the refusal
    log_entry = {
        "message": message,
        "filters": filters.model_dump(),
        "reason": refusal.reason,
        "suggestions_count": len(refusal.suggestions),
    }
    _refusal_log.append(log_entry)
    logger.info("Scope refusal: %s", json.dumps(log_entry))

    return refusal


def _build_hint_qs(suggestions: List[Dict[str, Any]]) -> str:
    """Build a query-string hint from suggestions."""
    parts = []
    for s in suggestions:
        if s.get("action") == "add_institution":
            parts.append(f"institutions={s['value']}")
        elif s.get("action") == "add_vendor":
            parts.append(f"vendors={s['value']}")
    return "&".join(parts)
