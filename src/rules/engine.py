"""
GovLens Rule Engine (Phase 4)

Evaluates preset and custom rules against a set of contracts,
producing per-contract and per-vendor flags with severity scores.

Preset rules:
  1. Threshold Proximity — contracts within X% of a legal threshold
  2. Vendor Concentration — top-N vendors hold > X% of institution spend
  3. Fragmentation — many small contracts to same vendor
  4. Overnight Turnaround — signed-to-published in < N hours
  5. New-Vendor-Large-Contract — first-time vendor with value above threshold
  6. Round-Number Clustering — statistical anomaly in round-number values
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from math import sqrt
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence

from ..models import Contract


# ── Data classes ─────────────────────────────────────────────────────


@dataclass
class RuleFlag:
    """A single flag produced by a rule evaluation."""

    rule_id: str
    rule_name: str
    severity: float  # 0.0 – 1.0
    description: str
    contract_id: Optional[str] = None
    vendor: Optional[str] = None
    institution: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """Aggregated result from evaluating all rules."""

    flags: List[RuleFlag] = field(default_factory=list)

    # convenience maps built after evaluation
    _by_contract: Dict[str, List[RuleFlag]] = field(
        default_factory=lambda: defaultdict(list), repr=False
    )
    _by_vendor: Dict[str, List[RuleFlag]] = field(
        default_factory=lambda: defaultdict(list), repr=False
    )

    def add(self, flag: RuleFlag) -> None:
        self.flags.append(flag)
        if flag.contract_id:
            self._by_contract[flag.contract_id].append(flag)
        if flag.vendor:
            self._by_vendor[flag.vendor].append(flag)

    def flags_for_contract(self, contract_id: str) -> List[RuleFlag]:
        return self._by_contract.get(contract_id, [])

    def flags_for_vendor(self, vendor: str) -> List[RuleFlag]:
        return self._by_vendor.get(vendor, [])

    def severity_for_contract(self, contract_id: str) -> float:
        """Sum of severities capped at 1.0."""
        flags = self.flags_for_contract(contract_id)
        return min(1.0, sum(f.severity for f in flags))

    def severity_for_vendor(self, vendor: str) -> float:
        flags = self.flags_for_vendor(vendor)
        return min(1.0, sum(f.severity for f in flags))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_flags": len(self.flags),
            "flags": [
                {
                    "rule_id": f.rule_id,
                    "rule_name": f.rule_name,
                    "severity": f.severity,
                    "description": f.description,
                    "contract_id": f.contract_id,
                    "vendor": f.vendor,
                    "institution": f.institution,
                    "details": f.details,
                }
                for f in self.flags
            ],
        }


# ── Preset rules ─────────────────────────────────────────────────────

PRESET_RULES = [
    {
        "id": "threshold_proximity",
        "name": "Threshold Proximity",
        "description": "Flags contracts within X% of a legal threshold (e.g. direct-award limit).",
        "params": {"threshold_eur": 100_000, "proximity_pct": 10},
    },
    {
        "id": "vendor_concentration",
        "name": "Vendor Concentration",
        "description": "Flags when top-N vendors hold more than X% of an institution's spend.",
        "params": {"top_n": 1, "max_share_pct": 60},
    },
    {
        "id": "fragmentation",
        "name": "Fragmentation",
        "description": "Flags when many small contracts go to the same vendor, suggesting split procurement.",
        "params": {"min_contracts": 3, "max_value_eur": 50_000},
    },
    {
        "id": "overnight_turnaround",
        "name": "Overnight Turnaround",
        "description": "Flags contracts signed and published within less than N hours.",
        "params": {"max_hours": 24},
    },
    {
        "id": "new_vendor_large_contract",
        "name": "New-Vendor-Large-Contract",
        "description": "Flags first-time vendors receiving a contract above a value threshold.",
        "params": {"min_value_eur": 100_000},
    },
    {
        "id": "round_number_clustering",
        "name": "Round-Number Clustering",
        "description": "Flags a statistical anomaly of round-number contract values.",
        "params": {"round_modulus": 1000, "min_round_pct": 60, "min_contracts": 5},
    },
]


# ── Rule evaluation functions ────────────────────────────────────────


def _eval_threshold_proximity(
    contracts: Sequence[Contract],
    threshold_eur: float = 100_000,
    proximity_pct: float = 10,
) -> List[RuleFlag]:
    """Flag contracts within *proximity_pct* % below *threshold_eur*."""
    lower = threshold_eur * (1 - proximity_pct / 100)
    flags: List[RuleFlag] = []
    for c in contracts:
        if c.price_numeric_eur is None:
            continue
        if lower <= c.price_numeric_eur < threshold_eur:
            pct = (c.price_numeric_eur / threshold_eur) * 100
            flags.append(
                RuleFlag(
                    rule_id="threshold_proximity",
                    rule_name="Threshold Proximity",
                    severity=0.6,
                    description=(
                        f"Contract value {c.price_numeric_eur:,.2f} € is "
                        f"{pct:.1f}% of the {threshold_eur:,.0f} € threshold"
                    ),
                    contract_id=c.contract_id,
                    vendor=c.supplier,
                    institution=c.buyer,
                    details={
                        "value": c.price_numeric_eur,
                        "threshold": threshold_eur,
                        "pct_of_threshold": round(pct, 2),
                    },
                )
            )
    return flags


def _eval_vendor_concentration(
    contracts: Sequence[Contract],
    top_n: int = 1,
    max_share_pct: float = 60,
) -> List[RuleFlag]:
    """Flag when top-N vendors hold > *max_share_pct* % of an institution's spend."""
    # Group by buyer
    inst_spend: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    inst_total: Dict[str, float] = defaultdict(float)

    for c in contracts:
        if c.buyer and c.supplier and c.price_numeric_eur is not None:
            inst_spend[c.buyer][c.supplier] += c.price_numeric_eur
            inst_total[c.buyer] += c.price_numeric_eur

    flags: List[RuleFlag] = []
    for inst, vendors in inst_spend.items():
        total = inst_total[inst]
        if total <= 0:
            continue
        sorted_vendors = sorted(vendors.items(), key=lambda x: x[1], reverse=True)
        top_spend = sum(v for _, v in sorted_vendors[:top_n])
        share = (top_spend / total) * 100
        if share > max_share_pct:
            top_names = [name for name, _ in sorted_vendors[:top_n]]
            for vname in top_names:
                flags.append(
                    RuleFlag(
                        rule_id="vendor_concentration",
                        rule_name="Vendor Concentration",
                        severity=0.5,
                        description=(
                            f"Top-{top_n} vendor(s) hold {share:.1f}% of "
                            f"{inst}'s spend (threshold: {max_share_pct}%)"
                        ),
                        vendor=vname,
                        institution=inst,
                        details={
                            "top_n": top_n,
                            "share_pct": round(share, 2),
                            "max_share_pct": max_share_pct,
                            "vendor_spend": vendors[vname],
                            "institution_total": total,
                        },
                    )
                )
    return flags


def _eval_fragmentation(
    contracts: Sequence[Contract],
    min_contracts: int = 3,
    max_value_eur: float = 50_000,
) -> List[RuleFlag]:
    """Flag many small contracts to the same vendor (split procurement)."""
    # Group by (buyer, supplier)
    pair_contracts: Dict[tuple, List[Contract]] = defaultdict(list)
    for c in contracts:
        if c.buyer and c.supplier and c.price_numeric_eur is not None:
            if c.price_numeric_eur <= max_value_eur:
                pair_contracts[(c.buyer, c.supplier)].append(c)

    flags: List[RuleFlag] = []
    for (inst, vendor), clist in pair_contracts.items():
        if len(clist) >= min_contracts:
            total = sum(c.price_numeric_eur for c in clist if c.price_numeric_eur is not None)
            for c in clist:
                flags.append(
                    RuleFlag(
                        rule_id="fragmentation",
                        rule_name="Fragmentation",
                        severity=0.4,
                        description=(
                            f"{len(clist)} small contracts (≤{max_value_eur:,.0f} €) "
                            f"from {inst} to {vendor}, total {total:,.2f} €"
                        ),
                        contract_id=c.contract_id,
                        vendor=vendor,
                        institution=inst,
                        details={
                            "contract_count": len(clist),
                            "max_value_eur": max_value_eur,
                            "total_value": total,
                        },
                    )
                )
    return flags


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date or datetime string, returning None on failure."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _eval_overnight_turnaround(
    contracts: Sequence[Contract],
    max_hours: float = 24,
) -> List[RuleFlag]:
    """Flag contracts signed and published within *max_hours* hours."""
    flags: List[RuleFlag] = []
    for c in contracts:
        concluded = _parse_date(c.date_concluded)
        published = _parse_date(c.date_published)
        if concluded and published:
            delta = published - concluded
            hours = delta.total_seconds() / 3600
            if 0 <= hours < max_hours:
                flags.append(
                    RuleFlag(
                        rule_id="overnight_turnaround",
                        rule_name="Overnight Turnaround",
                        severity=0.3,
                        description=(
                            f"Contract concluded on {c.date_concluded} and "
                            f"published on {c.date_published} "
                            f"({hours:.1f}h turnaround, limit {max_hours}h)"
                        ),
                        contract_id=c.contract_id,
                        vendor=c.supplier,
                        institution=c.buyer,
                        details={
                            "hours": round(hours, 2),
                            "max_hours": max_hours,
                            "date_concluded": c.date_concluded,
                            "date_published": c.date_published,
                        },
                    )
                )
    return flags


def _eval_new_vendor_large_contract(
    contracts: Sequence[Contract],
    min_value_eur: float = 100_000,
) -> List[RuleFlag]:
    """Flag vendors appearing for the first time with a large contract.

    "First time" is determined by the earliest *published_date* per vendor
    within the supplied contract set.
    """
    # Group contracts by vendor, sort by date
    vendor_contracts: Dict[str, List[Contract]] = defaultdict(list)
    for c in contracts:
        if c.supplier:
            vendor_contracts[c.supplier].append(c)

    flags: List[RuleFlag] = []
    for vendor, clist in vendor_contracts.items():
        dated = sorted(
            [c for c in clist if c.published_date],
            key=lambda c: c.published_date,  # type: ignore[arg-type]
        )
        if not dated:
            continue
        first = dated[0]
        if (
            first.price_numeric_eur is not None
            and first.price_numeric_eur >= min_value_eur
        ):
            flags.append(
                RuleFlag(
                    rule_id="new_vendor_large_contract",
                    rule_name="New-Vendor-Large-Contract",
                    severity=0.5,
                    description=(
                        f"Vendor '{vendor}' first appeared with a "
                        f"{first.price_numeric_eur:,.2f} € contract "
                        f"(threshold {min_value_eur:,.0f} €)"
                    ),
                    contract_id=first.contract_id,
                    vendor=vendor,
                    institution=first.buyer,
                    details={
                        "value": first.price_numeric_eur,
                        "min_value_eur": min_value_eur,
                        "first_date": first.published_date,
                    },
                )
            )
    return flags


def _eval_round_number_clustering(
    contracts: Sequence[Contract],
    round_modulus: int = 1000,
    min_round_pct: float = 60,
    min_contracts: int = 5,
) -> List[RuleFlag]:
    """Flag statistical anomaly of round-number contract values.

    A "round number" is defined as a value divisible by *round_modulus*.
    If the proportion of round values exceeds *min_round_pct* and there
    are at least *min_contracts*, a flag is raised for each round contract.
    """
    priced = [
        c for c in contracts
        if c.price_numeric_eur is not None and c.price_numeric_eur > 0
    ]

    if len(priced) < min_contracts:
        return []

    round_contracts = [
        c for c in priced
        if c.price_numeric_eur is not None
        and c.price_numeric_eur % round_modulus == 0
    ]

    round_pct = (len(round_contracts) / len(priced)) * 100
    if round_pct < min_round_pct:
        return []

    flags: List[RuleFlag] = []
    for c in round_contracts:
        flags.append(
            RuleFlag(
                rule_id="round_number_clustering",
                rule_name="Round-Number Clustering",
                severity=0.3,
                description=(
                    f"{round_pct:.0f}% of contracts have round values "
                    f"(divisible by {round_modulus})"
                ),
                contract_id=c.contract_id,
                vendor=c.supplier,
                institution=c.buyer,
                details={
                    "round_pct": round(round_pct, 2),
                    "round_modulus": round_modulus,
                    "value": c.price_numeric_eur,
                    "total_priced": len(priced),
                    "total_round": len(round_contracts),
                },
            )
        )
    return flags


# ── Rule Engine ──────────────────────────────────────────────────────


# Map rule IDs → evaluation functions
_RULE_EVALUATORS = {
    "threshold_proximity": _eval_threshold_proximity,
    "vendor_concentration": _eval_vendor_concentration,
    "fragmentation": _eval_fragmentation,
    "overnight_turnaround": _eval_overnight_turnaround,
    "new_vendor_large_contract": _eval_new_vendor_large_contract,
    "round_number_clustering": _eval_round_number_clustering,
}


class RuleEngine:
    """
    Evaluates a set of rules against contracts and produces flags.

    Usage::

        engine = RuleEngine()
        result = engine.evaluate(contracts, rules=[
            {"id": "threshold_proximity", "params": {"threshold_eur": 50000}},
        ])
    """

    def evaluate(
        self,
        contracts: Sequence[Contract],
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> RuleResult:
        """
        Evaluate rules against the given contracts.

        Args:
            contracts: The contracts to evaluate.
            rules: List of rule configs (``{"id": ..., "params": {...}}``).
                   If *None*, all preset rules with default params are used.

        Returns:
            A RuleResult containing all flags.
        """
        result = RuleResult()

        if rules is None:
            rules = [{"id": r["id"], "params": dict(r["params"])} for r in PRESET_RULES]

        for rule_cfg in rules:
            rule_id = rule_cfg.get("id", "")
            params = rule_cfg.get("params", {})
            evaluator = _RULE_EVALUATORS.get(rule_id)
            if evaluator is None:
                continue
            flags = evaluator(contracts, **params)
            for flag in flags:
                result.add(flag)

        return result

    @staticmethod
    def preset_rules() -> List[Dict[str, Any]]:
        """Return the list of available preset rules with default params."""
        return [dict(r) for r in PRESET_RULES]
