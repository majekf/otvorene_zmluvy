"""
GovLens Condition Builder (Phase 4)

A no-code condition builder that lets users define custom rules
using field / operator / value combinations with AND/OR chaining.

Serialisable to/from JSON for persistence and URL-state embedding.
"""

from __future__ import annotations

import json
import operator
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..models import Contract


# ── Supported operators ──────────────────────────────────────────────

OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
    "contains": lambda a, b: (
        b.lower() in a.lower() if isinstance(a, str) and isinstance(b, str) else False
    ),
}

# Fields that may be referenced in conditions
CONDITION_FIELDS = frozenset({
    "price_numeric_eur",
    "published_date",
    "contract_title",
    "buyer",
    "supplier",
    "category",
    "award_type",
    "date_concluded",
    "date_published",
    "date_effective",
})


# ── Data classes ─────────────────────────────────────────────────────


@dataclass
class Condition:
    """A single field / operator / value comparison."""

    field: str
    operator: str  # one of OPERATORS keys
    value: Any

    def evaluate(self, contract: Contract) -> bool:
        """Return True if *contract* satisfies this condition."""
        actual = getattr(contract, self.field, None)
        if actual is None:
            return False

        op_fn = OPERATORS.get(self.operator)
        if op_fn is None:
            return False

        # Coerce value to match actual type
        target = self.value
        if isinstance(actual, float) and not isinstance(target, float):
            try:
                target = float(target)
            except (ValueError, TypeError):
                return False
        if isinstance(actual, int) and not isinstance(target, int):
            try:
                target = int(target)
            except (ValueError, TypeError):
                return False

        try:
            return op_fn(actual, target)
        except TypeError:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Condition":
        return cls(
            field=data["field"],
            operator=data["operator"],
            value=data["value"],
        )


@dataclass
class ConditionGroup:
    """
    A group of conditions combined with AND or OR logic.

    Serialize-friendly: ``to_dict`` / ``from_dict`` for JSON round-trip.
    """

    logic: str = "AND"  # "AND" or "OR"
    conditions: List[Condition] = field(default_factory=list)

    def evaluate(self, contract: Contract) -> bool:
        """Return True if *contract* satisfies the group's logic."""
        if not self.conditions:
            return True  # empty group matches everything

        if self.logic.upper() == "AND":
            return all(cond.evaluate(contract) for cond in self.conditions)
        else:  # OR
            return any(cond.evaluate(contract) for cond in self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "logic": self.logic,
            "conditions": [c.to_dict() for c in self.conditions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionGroup":
        return cls(
            logic=data.get("logic", "AND"),
            conditions=[
                Condition.from_dict(c) for c in data.get("conditions", [])
            ],
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ConditionGroup":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def filter_contracts(
        self, contracts: Sequence[Contract]
    ) -> List[Contract]:
        """Return contracts matching this condition group."""
        return [c for c in contracts if self.evaluate(c)]
