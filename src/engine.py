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
    "scanned_suggested_title",
    "scanned_service_type",
    "scanned_service_subtype",
    "award_type",
    "date_published",
    "date_concluded",
    "date_effective",
    "red_flag_type",
    "red_flag_name",
    "red_flag_severity",
})


def _sort_key(value_getter, descending: bool):
    """
    Return a key function that extracts a sort value from a Contract.

    None values are always placed last regardless of sort direction:
    - ascending  (reverse=False): non-None → (0, val), None → (1, 0)
    - descending (reverse=True):  non-None → (1, val), None → (0, 0)

    Strings are lower-cased so the sort is case-insensitive.
    """
    def key(c: Contract) -> tuple:
        val = value_getter(c)
        if isinstance(val, str):
            val = val.strip()
            if not val:
                val = None
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

    def merge_red_flags(self, dataset: dict) -> int:
        """
        Merge red flag occurrences into the contracts list.

        For each flag in the dataset, find the matching contract by
        contract_id and create a copy with red flag fields populated.
        A single contract may appear multiple times if it has multiple
        flags. Contracts without flags are kept unchanged.

        Also enriches flag data with contract details (price, dates, etc.)
        when the flag itself has empty/null values for those fields.

        Returns:
            Number of red flag entries merged.
        """
        flags = dataset.get("flags", [])
        dataset_name = dataset.get("dataset_name", "unknown")
        if not flags:
            return 0

        # Build lookup: contract_id → contract
        contract_map: Dict[str, Contract] = {}
        for c in self._contracts:
            if c.contract_id:
                contract_map[c.contract_id] = c

        # First, remove any previously merged flags from this dataset
        self._contracts = [
            c for c in self._contracts if c.red_flag_dataset != dataset_name
        ]

        merged_count = 0
        for flag in flags:
            cid = flag.get("contract_id")
            base = contract_map.get(cid)
            if base:
                # Create a copy of the existing contract with red flag fields added
                data = base.model_dump()
            else:
                # Contract not in our data — create a minimal entry from the flag
                data = {
                    "contract_id": cid,
                    "contract_title": flag.get("contract_title", ""),
                    "buyer": flag.get("institution", ""),
                    "supplier": flag.get("vendor", ""),
                    "price_numeric_eur": flag.get("price_numeric_eur"),
                    "ico_buyer": flag.get("ico_buyer"),
                    "ico_supplier": flag.get("ico_supplier"),
                    "date_published": flag.get("date_published"),
                    "published_date": flag.get("date_published"),
                    "category": flag.get("category", "not_decided"),
                    "award_type": flag.get("award_type", "unknown"),
                }

            # Overlay red flag fields
            data["red_flag_type"] = flag.get("red_flag_type")
            data["red_flag_name"] = flag.get("red_flag_name")
            data["red_flag_severity"] = flag.get("severity")
            data["red_flag_description"] = flag.get("description")
            data["red_flag_dataset"] = dataset_name

            # Enrich flag with contract details if the flag has empty values
            if base:
                if not flag.get("institution") and base.buyer:
                    data["buyer"] = base.buyer
                if not flag.get("vendor") and base.supplier:
                    data["supplier"] = base.supplier
                if flag.get("price_numeric_eur") is None and base.price_numeric_eur is not None:
                    data["price_numeric_eur"] = base.price_numeric_eur
                if not flag.get("date_published") and base.published_date:
                    data["date_published"] = base.published_date
                    data["published_date"] = base.published_date

            self._contracts.append(Contract(**data))
            merged_count += 1

        self._rebuild_indices()
        self._compute_red_flag_associations()
        return merged_count

    def remove_red_flag_dataset(self, dataset_name: str) -> int:
        """
        Remove all contracts that were merged from a specific red flag dataset.

        Returns:
            Number of entries removed.
        """
        before = len(self._contracts)
        self._contracts = [
            c for c in self._contracts if c.red_flag_dataset != dataset_name
        ]
        removed = before - len(self._contracts)
        if removed > 0:
            self._rebuild_indices()
        self._compute_red_flag_associations()
        return removed

    # ── Red-flag association helper ──────────────────────────────────

    def _compute_red_flag_associations(self) -> None:
        """Mark every contract whose vendor or institution appears in any RF dataset.

        After merge/remove, this walks all contracts and builds a
        mapping of {dataset → flagged_vendors, flagged_institutions}.
        Then every contract (including non-flagged ones) gets its
        ``red_flag_associated_datasets`` set to the list of datasets
        where its supplier or buyer was involved in at least one flag.
        """
        # Collect flagged entities per dataset
        flagged_vendors: Dict[str, set] = defaultdict(set)
        flagged_institutions: Dict[str, set] = defaultdict(set)

        for c in self._contracts:
            if c.red_flag_dataset:
                if c.supplier:
                    flagged_vendors[c.red_flag_dataset].add(c.supplier)
                if c.buyer:
                    flagged_institutions[c.red_flag_dataset].add(c.buyer)

        all_datasets = set(flagged_vendors.keys()) | set(flagged_institutions.keys())

        if not all_datasets:
            # No flags at all – clear the helper field on every contract
            for c in self._contracts:
                object.__setattr__(c, "red_flag_associated_datasets", None)
            return

        # For each contract, determine which datasets its vendor/institution
        # appears in.
        for c in self._contracts:
            associated: List[str] = []
            for ds in all_datasets:
                vendor_flagged = (
                    c.supplier is not None
                    and c.supplier in flagged_vendors.get(ds, set())
                )
                institution_flagged = (
                    c.buyer is not None
                    and c.buyer in flagged_institutions.get(ds, set())
                )
                if vendor_flagged or institution_flagged:
                    associated.append(ds)
            object.__setattr__(
                c,
                "red_flag_associated_datasets",
                sorted(associated) if associated else None,
            )

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

    @staticmethod
    def _category_label(contract: Contract) -> str:
        """Resolve category label with robust fallback to raw JSON fields."""
        data = contract.model_dump()
        lookup = {str(k).lower(): v for k, v in data.items()}
        for key in ("rezort", "resort", "category"):
            val = lookup.get(key)
            if val is None:
                continue
            text = str(val).strip()
            if text and text != "not_decided":
                return text
        return ""

    @staticmethod
    def _scanned_service_type(contract: Contract) -> str:
        """Resolve scanned service type from raw JSON fields."""
        data = contract.model_dump()
        lookup = {str(k).lower(): v for k, v in data.items()}
        for key in ("scanned_service_type", "service_type"):
            val = lookup.get(key)
            if val is None:
                continue
            text = str(val).strip()
            if text:
                return text
        return ""

    @staticmethod
    def _scanned_service_subtype(contract: Contract) -> str:
        """Resolve scanned service subtype from raw JSON fields."""
        data = contract.model_dump()
        lookup = {str(k).lower(): v for k, v in data.items()}
        for key in ("scanned_service_subtype", "service_subtype"):
            val = lookup.get(key)
            if val is None:
                continue
            text = str(val).strip()
            if text:
                return text
        return ""

    def _sort_field_value(self, contract: Contract, field: str):
        """Resolve the canonical value used for sorting a given field."""
        if field == "category":
            return self._category_label(contract) or None
        if field == "scanned_service_type":
            return self._scanned_service_type(contract) or None
        if field == "scanned_service_subtype":
            return self._scanned_service_subtype(contract) or None
        if field == "scanned_suggested_title":
            val = getattr(contract, "scanned_suggested_title", None)
            if val is None:
                val = contract.model_dump().get("scanned_suggested_title")
            return val
        return getattr(contract, field, None)

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
            result = [
                c
                for c in result
                if self._category_label(c) in cat_set
            ]

        if filters.scanned_service_types:
            type_set = set(filters.scanned_service_types)
            include_unassigned = "Nezaradené" in type_set
            type_set.discard("Nezaradené")
            result = [
                c
                for c in result
                if (self._scanned_service_type(c) in type_set)
                or (include_unassigned and not self._scanned_service_type(c))
            ]

        if filters.scanned_service_subtypes:
            subtype_set = set(filters.scanned_service_subtypes)
            result = [
                c
                for c in result
                if self._scanned_service_subtype(c) in subtype_set
            ]

        if filters.vendors:
            vendor_set = set(filters.vendors)
            result = [c for c in result if c.supplier in vendor_set]

        if filters.institution_icos:
            inst_ico_set = set(filters.institution_icos)
            result = [
                c
                for c in result
                if c.ico_buyer and c.ico_buyer in inst_ico_set
            ]

        if filters.vendor_icos:
            vendor_ico_set = set(filters.vendor_icos)
            result = [
                c
                for c in result
                if c.ico_supplier and c.ico_supplier in vendor_ico_set
            ]

        if filters.icos:
            ico_set = set(filters.icos)
            result = [
                c
                for c in result
                if (c.ico_buyer and c.ico_buyer in ico_set)
                or (c.ico_supplier and c.ico_supplier in ico_set)
            ]

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

        if filters.red_flag_types:
            rf_set = set(filters.red_flag_types)
            result = [
                c for c in result
                if (c.red_flag_type and c.red_flag_type in rf_set)
                or (c.red_flag_name and c.red_flag_name in rf_set)
            ]

        if filters.red_flag_datasets:
            ds_set = set(filters.red_flag_datasets)
            result = [
                c for c in result
                if c.red_flag_associated_datasets
                and ds_set.intersection(c.red_flag_associated_datasets)
            ]

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

    def _extract_group_key(self, contract: Contract, field: str) -> Optional[str]:
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
            # "Category" charts/grouping should follow scanned service categories only.
            return self._scanned_service_type(contract) or "Nezaradené"
        elif field == "award_type":
            return contract.award_type
        elif field == "published_year":
            return contract.published_year
        elif field == "red_flag_type":
            return contract.red_flag_name or contract.red_flag_type
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

    def institutions(
        self, contracts: Optional[List[Contract]] = None,
    ) -> List[Institution]:
        """
        Return a list of all unique institutions (buyers) with their
        contract counts and total spend.

        Args:
            contracts: Subset to analyse; defaults to all.
        """
        groups = self.group_by("buyer", contracts)
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
        contracts: Optional[List[Contract]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compare institutions on a metric.

        Args:
            institution_names: List of buyer names to compare.
            metric: One of 'total_spend', 'contract_count', 'avg_value',
                    'max_value', 'direct_award_rate'.
            contracts: Subset to analyse; defaults to all.

        Returns:
            List of dicts with 'institution', 'value' keys, sorted desc.
        """
        pool = contracts if contracts is not None else self._contracts
        results: List[Dict[str, Any]] = []

        for name in institution_names:
            inst_contracts = [
                c for c in pool if c.buyer == name
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
            result.sort(
                key=_sort_key(lambda c, f=field: self._sort_field_value(c, f), descending),
                reverse=descending,
            )

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
        contracts: Optional[List[Contract]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compare institutions across multiple metrics.

        Args:
            institution_names: List of buyer names.
            metrics: List of metric names.
            contracts: Subset to analyse; defaults to all.

        Returns:
            List of dicts with 'institution' and a key per metric.
        """
        pool = contracts if contracts is not None else self._contracts
        results: List[Dict[str, Any]] = []
        for name in institution_names:
            inst_contracts = [
                c for c in pool if c.buyer == name
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
        contracts: Optional[List[Contract]] = None,
    ) -> List[str]:
        """
        Build a peer group: institutions with at least ``min_contracts``.

        Args:
            contracts: Subset to analyse; defaults to all.

        Returns names sorted by total spend, excluding the target institution.
        """
        if contracts is not None:
            # Build institution stats from the given contract subset
            groups: Dict[str, List[Contract]] = defaultdict(list)
            for c in contracts:
                if c.buyer:
                    groups[c.buyer].append(c)
            result: List[Tuple[str, float]] = []
            for name, grp in groups.items():
                if name == institution_name:
                    continue
                if len(grp) >= min_contracts:
                    stats = self.aggregate(grp)
                    result.append((name, stats["total_spend"]))
            result.sort(key=lambda t: t[1], reverse=True)
            return [name for name, _ in result]
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
