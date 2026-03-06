"""
GovLens In-Memory Query & Aggregation Engine (Phase 1)

Loads contracts from JSON into RAM and provides fast filtering,
grouping, aggregation, search, benchmarking, trends, and ranking.
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from .models import AggregationResult, Contract, FilterState, Institution, Vendor


# ── Sort support ─────────────────────────────────────────────────────

#: Fields that may be used in a sort_spec. Any field name not in this set
#: is silently ignored by sort_contracts().
SORTABLE_FIELDS: frozenset = frozenset({
    "price_numeric_eur",
    "published_date",
    "contract_title",
    "contract_number",
    "buyer",
    "supplier",
    "category",
    "award_type",
    "date_published",
    "date_concluded",
    "date_effective",
})


def _sort_key(field: str, descending: bool):
    """
    Return a key function that extracts *field* from a Contract.

    None values are always placed last regardless of sort direction:
    - ascending  (reverse=False): non-None → (0, val), None → (1, 0)
    - descending (reverse=True):  non-None → (1, val), None → (0, 0)

    Strings are lower-cased so the sort is case-insensitive.
    """
    def key(c: Contract) -> tuple:
        val = getattr(c, field, None)
        if val is None:
            return (0, 0) if descending else (1, 0)
        normalized = val.lower() if isinstance(val, str) else val
        return (1, normalized) if descending else (0, normalized)

    return key


class DataStore:
    """
    Central data store that loads contracts into memory and provides
    filtering, grouping, aggregation, search, benchmarking, trends,
    and ranking operations.
    """

    def __init__(self, data_path: Optional[str] = None):
        """
        Load contracts from a JSON file (array of objects).

        Args:
            data_path: Path to JSON file. If None, initialises empty.
        """
        self._contracts: List[Contract] = []
        self._institution_index: Dict[str, List[int]] = defaultdict(list)
        self._category_index: Dict[str, List[int]] = defaultdict(list)
        self._date_index: Dict[str, List[int]] = defaultdict(list)

        if data_path is not None:
            self.load(data_path)

    # ── Loading ──────────────────────────────────────────────────────

    def load(self, data_path: str) -> int:
        """
        Load contracts from a JSON file and rebuild indices.

        Returns:
            Number of contracts loaded.
        """
        path = Path(data_path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._contracts = [Contract(**r) for r in raw]
        self._rebuild_indices()
        return len(self._contracts)

    def load_from_list(self, records: List[dict]) -> int:
        """
        Load contracts from a list of dicts (useful for testing).

        Returns:
            Number of contracts loaded.
        """
        self._contracts = [Contract(**r) for r in records]
        self._rebuild_indices()
        return len(self._contracts)

    def _rebuild_indices(self) -> None:
        """Build lookup indices for frequently-filtered fields."""
        self._institution_index.clear()
        self._category_index.clear()
        self._date_index.clear()

        for idx, c in enumerate(self._contracts):
            if c.buyer:
                self._institution_index[c.buyer].append(idx)
            if c.category:
                self._category_index[c.category].append(idx)
            if c.published_date:
                self._date_index[c.published_date].append(idx)

    @property
    def contracts(self) -> List[Contract]:
        """Return all loaded contracts."""
        return list(self._contracts)

    @property
    def count(self) -> int:
        """Return total number of loaded contracts."""
        return len(self._contracts)

    # ── Filtering ────────────────────────────────────────────────────

    def filter(self, filters: FilterState) -> List[Contract]:
        """
        Apply shared global filters and return matching contracts.
        All filters are AND-combined; None means "no filter".
        """
        result = self._contracts

        if filters.institutions:
            inst_set = set(filters.institutions)
            result = [c for c in result if c.buyer in inst_set]

        if filters.date_from:
            result = [
                c
                for c in result
                if c.published_date and c.published_date >= filters.date_from
            ]

        if filters.date_to:
            result = [
                c
                for c in result
                if c.published_date and c.published_date <= filters.date_to
            ]

        if filters.categories:
            cat_set = set(filters.categories)
            result = [c for c in result if c.category in cat_set]

        if filters.vendors:
            vendor_set = set(filters.vendors)
            result = [c for c in result if c.supplier in vendor_set]

        if filters.value_min is not None:
            result = [
                c
                for c in result
                if c.price_numeric_eur is not None
                and c.price_numeric_eur >= filters.value_min
            ]

        if filters.value_max is not None:
            result = [
                c
                for c in result
                if c.price_numeric_eur is not None
                and c.price_numeric_eur <= filters.value_max
            ]

        if filters.award_types:
            at_set = set(filters.award_types)
            result = [c for c in result if c.award_type in at_set]

        if filters.text_search:
            result = self._text_filter(result, filters.text_search)

        return result

    def _text_filter(
        self, contracts: List[Contract], query: str
    ) -> List[Contract]:
        """Case-insensitive substring search over title and summary."""
        q = query.lower()
        return [
            c
            for c in contracts
            if (c.contract_title and q in c.contract_title.lower())
            or (c.pdf_text_summary and q in c.pdf_text_summary.lower())
        ]

    # ── Search ───────────────────────────────────────────────────────

    def search(self, query: str) -> List[Contract]:
        """
        Full-text search over contract_title and pdf_text_summary.
        Returns contracts matching the query (case-insensitive substring).
        """
        return self._text_filter(self._contracts, query)

    # ── Group By ─────────────────────────────────────────────────────

    def group_by(
        self,
        field: str,
        contracts: Optional[List[Contract]] = None,
    ) -> Dict[str, List[Contract]]:
        """
        Group contracts by a field name.

        Supported fields: 'category', 'supplier', 'buyer', 'month',
        'award_type', 'published_year'.

        Args:
            field: The field to group by.
            contracts: Subset to group; defaults to all contracts.

        Returns:
            Dict mapping group value → list of contracts.
        """
        if contracts is None:
            contracts = self._contracts

        groups: Dict[str, List[Contract]] = defaultdict(list)

        for c in contracts:
            key = self._extract_group_key(c, field)
            if key is not None:
                groups[key].append(c)

        return dict(groups)

    @staticmethod
    def _extract_group_key(contract: Contract, field: str) -> Optional[str]:
        """Extract the grouping key from a contract."""
        if field == "month":
            if contract.published_date:
                return contract.published_date[:7]  # YYYY-MM
            return None
        elif field == "supplier":
            return contract.supplier
        elif field == "buyer":
            return contract.buyer
        elif field == "category":
            return contract.category
        elif field == "award_type":
            return contract.award_type
        elif field == "published_year":
            return contract.published_year
        else:
            # Try generic attribute access
            val = getattr(contract, field, None)
            return str(val) if val is not None else None

    # ── Aggregations ─────────────────────────────────────────────────

    def aggregate(
        self,
        contracts: Optional[List[Contract]] = None,
    ) -> Dict[str, Any]:
        """
        Compute aggregate statistics for a set of contracts.

        Returns dict with keys: total_spend, contract_count,
        avg_value, max_value.
        """
        if contracts is None:
            contracts = self._contracts

        prices = [
            c.price_numeric_eur
            for c in contracts
            if c.price_numeric_eur is not None
        ]

        total = sum(prices) if prices else 0.0
        count = len(contracts)
        avg = mean(prices) if prices else 0.0
        mx = max(prices) if prices else 0.0

        return {
            "total_spend": total,
            "contract_count": count,
            "avg_value": avg,
            "max_value": mx,
        }

    def aggregate_groups(
        self,
        field: str,
        contracts: Optional[List[Contract]] = None,
    ) -> List[AggregationResult]:
        """
        Group by a field and compute aggregations for each group.

        Returns a list of AggregationResult sorted by total_spend descending.
        """
        groups = self.group_by(field, contracts)
        results: List[AggregationResult] = []

        for group_value, group_contracts in groups.items():
            stats = self.aggregate(group_contracts)
            results.append(
                AggregationResult(
                    group_key=field,
                    group_value=group_value,
                    contract_count=stats["contract_count"],
                    total_spend=stats["total_spend"],
                    avg_value=stats["avg_value"],
                    max_value=stats["max_value"],
                )
            )

        results.sort(key=lambda r: r.total_spend, reverse=True)
        return results

    def top_n_vendors(
        self,
        n: int = 10,
        contracts: Optional[List[Contract]] = None,
    ) -> List[Vendor]:
        """
        Return the top N vendors by total spend.
        """
        groups = self.group_by("supplier", contracts)
        vendors: List[Vendor] = []

        for name, group_contracts in groups.items():
            if name is None:
                continue
            stats = self.aggregate(group_contracts)
            # Try to find ICO from the first contract
            ico = None
            for c in group_contracts:
                if c.ico_supplier:
                    ico = c.ico_supplier
                    break
            vendors.append(
                Vendor(
                    name=name,
                    ico=ico,
                    contract_count=stats["contract_count"],
                    total_spend=stats["total_spend"],
                )
            )

        vendors.sort(key=lambda v: v.total_spend, reverse=True)
        return vendors[:n]

    def direct_award_rate(
        self, contracts: Optional[List[Contract]] = None
    ) -> float:
        """
        Compute the fraction of contracts that are direct awards.
        Returns a float between 0.0 and 1.0.
        """
        if contracts is None:
            contracts = self._contracts
        if not contracts:
            return 0.0

        direct = sum(1 for c in contracts if c.award_type == "direct_award")
        return direct / len(contracts)

    # ── Benchmark / Peer Comparison ──────────────────────────────────

    def institutions(self) -> List[Institution]:
        """
        Return a list of all unique institutions (buyers) with their
        contract counts and total spend.
        """
        groups = self.group_by("buyer")
        result: List[Institution] = []

        for name, group_contracts in groups.items():
            if name is None:
                continue
            stats = self.aggregate(group_contracts)
            ico = None
            for c in group_contracts:
                if c.ico_buyer:
                    ico = c.ico_buyer
                    break
            result.append(
                Institution(
                    name=name,
                    ico=ico,
                    contract_count=stats["contract_count"],
                    total_spend=stats["total_spend"],
                )
            )

        result.sort(key=lambda i: i.total_spend, reverse=True)
        return result

    def vendors(self) -> List[Vendor]:
        """
        Return a list of all unique vendors with their
        contract counts and total spend.
        """
        return self.top_n_vendors(n=len(self._contracts))

    def compare(
        self,
        institution_names: List[str],
        metric: str = "total_spend",
    ) -> List[Dict[str, Any]]:
        """
        Compare institutions on a metric.

        Args:
            institution_names: List of buyer names to compare.
            metric: One of 'total_spend', 'contract_count', 'avg_value',
                    'max_value', 'direct_award_rate'.

        Returns:
            List of dicts with 'institution', 'value' keys, sorted desc.
        """
        results: List[Dict[str, Any]] = []

        for name in institution_names:
            inst_contracts = [
                c for c in self._contracts if c.buyer == name
            ]
            if metric == "direct_award_rate":
                value = self.direct_award_rate(inst_contracts)
            else:
                stats = self.aggregate(inst_contracts)
                value = stats.get(metric, 0)

            results.append({"institution": name, "value": value})

        results.sort(key=lambda r: r["value"], reverse=True)
        return results

    # ── Time / Trend ─────────────────────────────────────────────────

    def trend(
        self,
        granularity: str = "month",
        contracts: Optional[List[Contract]] = None,
        metric: str = "total_spend",
    ) -> List[Dict[str, Any]]:
        """
        Compute a time-series trend.

        Args:
            granularity: 'month', 'quarter', or 'year'.
            contracts: Subset to analyse; defaults to all.
            metric: 'total_spend', 'contract_count', 'avg_value'.

        Returns:
            Sorted list of dicts with 'period' and 'value' keys.
        """
        if contracts is None:
            contracts = self._contracts

        buckets: Dict[str, List[Contract]] = defaultdict(list)

        for c in contracts:
            period = self._period_key(c, granularity)
            if period:
                buckets[period].append(c)

        result: List[Dict[str, Any]] = []
        for period in sorted(buckets.keys()):
            bucket = buckets[period]
            stats = self.aggregate(bucket)
            if metric in stats:
                value = stats[metric]
            else:
                value = stats.get("total_spend", 0)
            result.append({"period": period, "value": value})

        return result

    @staticmethod
    def _period_key(contract: Contract, granularity: str) -> Optional[str]:
        """Extract period key from a contract's published_date."""
        date_str = contract.published_date
        if not date_str:
            return None

        if granularity == "month":
            return date_str[:7]  # YYYY-MM
        elif granularity == "quarter":
            try:
                month = int(date_str[5:7])
                quarter = (month - 1) // 3 + 1
                return f"{date_str[:4]}-Q{quarter}"
            except (ValueError, IndexError):
                return None
        elif granularity == "year":
            return date_str[:4]
        else:
            return date_str[:7]

    # ── Rankings ──────────────────────────────────────────────────────

    def rank_institutions(
        self,
        metric: str = "total_spend",
    ) -> List[Dict[str, Any]]:
        """
        Rank all institutions by a metric.

        Args:
            metric: 'total_spend', 'contract_count', 'avg_value',
                    'max_value', 'direct_award_rate'.

        Returns:
            Sorted list of dicts with 'rank', 'institution', 'value'.
        """
        all_inst = self.institutions()
        ranked: List[Dict[str, Any]] = []

        for inst in all_inst:
            if metric == "total_spend":
                value = inst.total_spend
            elif metric == "contract_count":
                value = float(inst.contract_count)
            elif metric == "direct_award_rate":
                inst_contracts = [
                    c for c in self._contracts if c.buyer == inst.name
                ]
                value = self.direct_award_rate(inst_contracts)
            elif metric in ("avg_value", "max_value"):
                inst_contracts = [
                    c for c in self._contracts if c.buyer == inst.name
                ]
                stats = self.aggregate(inst_contracts)
                value = stats.get(metric, 0.0)
            else:
                value = inst.total_spend

            ranked.append({"institution": inst.name, "value": value})

        ranked.sort(key=lambda r: r["value"], reverse=True)
        for i, item in enumerate(ranked, 1):
            item["rank"] = i

        return ranked

    # ── Sorting ──────────────────────────────────────────────────────────────

    def sort_contracts(
        self,
        contracts: List[Contract],
        sort_spec: List[Tuple[str, str]],
    ) -> List[Contract]:
        """
        Sort a list of contracts by one or more fields.

        Args:
            contracts: Contracts to sort. The input list is not modified.
            sort_spec: Ordered list of (field, direction) tuples where
                       *field* is a key from SORTABLE_FIELDS and *direction*
                       is ``'asc'`` or ``'desc'``. Fields not in
                       SORTABLE_FIELDS are silently ignored.
                       None values are always placed last regardless of
                       direction.

        Returns:
            A new list in the requested sort order.
        """
        valid_spec = [
            (field, direction)
            for field, direction in sort_spec
            if field in SORTABLE_FIELDS
        ]

        if not valid_spec:
            return list(contracts)

        # Python's sort is stable — apply least-significant column first.
        result = list(contracts)
        for field, direction in reversed(valid_spec):
            descending = direction.lower() == "desc"
            result.sort(key=_sort_key(field, descending), reverse=descending)

        return result

    def rank_vendors(
        self,
        metric: str = "total_spend",
    ) -> List[Dict[str, Any]]:
        """
        Rank all vendors by a metric.

        Args:
            metric: 'total_spend', 'contract_count', 'avg_value',
                    'max_value'.

        Returns:
            Sorted list of dicts with 'rank', 'vendor', 'value'.
        """
        all_vendors = self.vendors()
        ranked: List[Dict[str, Any]] = []

        for v in all_vendors:
            if metric == "total_spend":
                value = v.total_spend
            elif metric == "contract_count":
                value = float(v.contract_count)
            elif metric in ("avg_value", "max_value"):
                v_contracts = [
                    c for c in self._contracts if c.supplier == v.name
                ]
                stats = self.aggregate(v_contracts)
                value = stats.get(metric, 0.0)
            else:
                value = v.total_spend

            ranked.append({"vendor": v.name, "value": value})

        ranked.sort(key=lambda r: r["value"], reverse=True)
        for i, item in enumerate(ranked, 1):
            item["rank"] = i

        return ranked

    # ── Phase 6 — Investigation Modes helpers ────────────────────────

    def vendor_concentration_score(
        self, contracts: Optional[List[Contract]] = None, top_n: int = 3
    ) -> float:
        """
        Compute Herfindahl-like vendor concentration score.

        Returns the share of total spend held by the top-N vendors (0.0–1.0).
        """
        if contracts is None:
            contracts = self._contracts
        if not contracts:
            return 0.0

        vendor_spend: Dict[str, float] = defaultdict(float)
        for c in contracts:
            if c.supplier and c.price_numeric_eur is not None:
                vendor_spend[c.supplier] += c.price_numeric_eur

        if not vendor_spend:
            return 0.0

        total = sum(vendor_spend.values())
        if total == 0:
            return 0.0

        sorted_spend = sorted(vendor_spend.values(), reverse=True)
        top_spend = sum(sorted_spend[:top_n])
        return top_spend / total

    def fragmentation_score(
        self, contracts: Optional[List[Contract]] = None
    ) -> float:
        """
        Compute a fragmentation score: ratio of contracts below the median value.

        Returns a float between 0.0 and 1.0; higher means more fragmented.
        """
        if contracts is None:
            contracts = self._contracts

        prices = sorted(
            c.price_numeric_eur
            for c in contracts
            if c.price_numeric_eur is not None
        )
        if not prices:
            return 0.0

        median = prices[len(prices) // 2]
        if median == 0:
            return 0.0

        below_median = sum(1 for p in prices if p < median)
        return below_median / len(prices)

    def compare_multi_metric(
        self,
        institution_names: List[str],
        metrics: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Compare institutions across multiple metrics.

        Args:
            institution_names: List of buyer names.
            metrics: List of metric names.

        Returns:
            List of dicts with 'institution' and a key per metric.
        """
        results: List[Dict[str, Any]] = []
        for name in institution_names:
            inst_contracts = [
                c for c in self._contracts if c.buyer == name
            ]
            stats = self.aggregate(inst_contracts)
            row: Dict[str, Any] = {"institution": name}
            for metric in metrics:
                if metric == "direct_award_rate":
                    row[metric] = self.direct_award_rate(inst_contracts)
                elif metric == "vendor_concentration":
                    row[metric] = self.vendor_concentration_score(inst_contracts)
                elif metric == "fragmentation_score":
                    row[metric] = self.fragmentation_score(inst_contracts)
                else:
                    row[metric] = stats.get(metric, 0)
            results.append(row)
        return results

    def peer_group(
        self,
        institution_name: str,
        min_contracts: int = 1,
    ) -> List[str]:
        """
        Build a peer group: institutions with at least ``min_contracts``.

        Returns names sorted by total spend, excluding the target institution.
        """
        all_inst = self.institutions()
        return [
            inst.name
            for inst in all_inst
            if inst.name != institution_name
            and inst.contract_count >= min_contracts
        ]

    def trend_multi_metric(
        self,
        granularity: str = "month",
        contracts: Optional[List[Contract]] = None,
        metrics: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute multi-metric time-series trend.

        Args:
            granularity: 'month', 'quarter', or 'year'.
            contracts: Subset to analyse; defaults to all.
            metrics: List of metric names (default: ['total_spend']).

        Returns:
            Sorted list of dicts with 'period' and a key per metric.
        """
        if contracts is None:
            contracts = self._contracts
        if not metrics:
            metrics = ["total_spend"]

        buckets: Dict[str, List[Contract]] = defaultdict(list)

        for c in contracts:
            period = self._period_key(c, granularity)
            if period:
                buckets[period].append(c)

        result: List[Dict[str, Any]] = []
        for period in sorted(buckets.keys()):
            bucket = buckets[period]
            stats = self.aggregate(bucket)
            row: Dict[str, Any] = {"period": period}
            for metric in metrics:
                if metric in stats:
                    row[metric] = stats[metric]
                else:
                    row[metric] = stats.get("total_spend", 0)
            result.append(row)

        return result
