"""
Performance tests for Phase 8.

Tests verify that core operations complete within acceptable time
limits when processing large datasets (10k+ contracts).
"""

import os
import random
import string
import time
from datetime import datetime, timedelta

import pytest

from src.engine import DataStore
from src.models import Contract, FilterState

# ── Helpers ──────────────────────────────────────────────────────────

CATEGORIES = ["construction", "IT", "supplies", "services", "consulting", "healthcare", "education"]
AWARD_TYPES = ["direct_award", "open_tender", "restricted_tender", "unknown"]
BUYERS = [f"Institution_{i}" for i in range(50)]
SUPPLIERS = [f"Vendor_{i}" for i in range(200)]


def _random_date(start_year: int = 2020, end_year: int = 2025) -> str:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_day = start + timedelta(days=random.randint(0, delta.days))
    return random_day.strftime("%Y-%m-%d")


def _generate_contracts(n: int) -> list[dict]:
    """Generate n synthetic contract dicts."""
    records = []
    for i in range(n):
        records.append({
            "contract_id": str(10000 + i),
            "contract_title": f"Contract {''.join(random.choices(string.ascii_lowercase, k=8))} #{i}",
            "buyer": random.choice(BUYERS),
            "supplier": random.choice(SUPPLIERS),
            "price_numeric_eur": round(random.uniform(1000, 5_000_000), 2),
            "published_date": _random_date(),
            "category": random.choice(CATEGORIES),
            "award_type": random.choice(AWARD_TYPES),
            "pdf_text_summary": f"Summary text for contract {i} with some keywords",
            "contract_url": f"https://www.crz.gov.sk/zmluva/{10000 + i}/",
            "ico_buyer": f"{random.randint(10000000, 99999999):08d}",
            "ico_supplier": f"{random.randint(10000000, 99999999):08d}",
        })
    return records


@pytest.fixture(scope="module")
def large_store() -> DataStore:
    """DataStore with 10,000 synthetic contracts."""
    records = _generate_contracts(10_000)
    ds = DataStore()
    ds.load_from_list(records)
    return ds


@pytest.fixture(scope="module")
def very_large_store() -> DataStore:
    """DataStore with 50,000 synthetic contracts."""
    records = _generate_contracts(50_000)
    ds = DataStore()
    ds.load_from_list(records)
    return ds


# ── Tests ────────────────────────────────────────────────────────────


class TestFilterPerformance:
    """Filter operations on 10k+ contracts should complete under 200ms."""

    def test_filter_10k_contracts_under_200ms(self, large_store: DataStore):
        fs = FilterState(institutions=[BUYERS[0]])
        start = time.perf_counter()
        result = large_store.filter(fs)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Filter took {elapsed:.3f}s (limit: 0.200s)"
        assert len(result) > 0

    def test_filter_by_date_range_10k(self, large_store: DataStore):
        fs = FilterState(date_from="2023-01-01", date_to="2023-12-31")
        start = time.perf_counter()
        result = large_store.filter(fs)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Date-range filter took {elapsed:.3f}s"

    def test_filter_by_category_10k(self, large_store: DataStore):
        fs = FilterState(categories=["construction", "IT"])
        start = time.perf_counter()
        result = large_store.filter(fs)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Category filter took {elapsed:.3f}s"

    def test_filter_combined_10k(self, large_store: DataStore):
        fs = FilterState(
            institutions=[BUYERS[0], BUYERS[1]],
            categories=["construction"],
            date_from="2022-01-01",
            date_to="2024-12-31",
            value_min=10000,
            value_max=2_000_000,
        )
        start = time.perf_counter()
        result = large_store.filter(fs)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Combined filter took {elapsed:.3f}s"

    def test_text_search_10k(self, large_store: DataStore):
        fs = FilterState(text_search="contract")
        start = time.perf_counter()
        result = large_store.filter(fs)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.500, f"Text search took {elapsed:.3f}s (limit: 0.500s)"

    def test_filter_50k_contracts_under_500ms(self, very_large_store: DataStore):
        fs = FilterState(institutions=[BUYERS[0]])
        start = time.perf_counter()
        result = very_large_store.filter(fs)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.500, f"50k filter took {elapsed:.3f}s (limit: 0.500s)"


class TestAggregationPerformance:
    """Aggregation operations on 10k+ contracts should complete under 200ms."""

    def test_aggregation_10k_under_200ms(self, large_store: DataStore):
        all_contracts = large_store.filter(FilterState())
        start = time.perf_counter()
        result = large_store.aggregate(all_contracts)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Aggregation took {elapsed:.3f}s"
        assert result["contract_count"] == 10_000

    def test_group_by_aggregation_10k(self, large_store: DataStore):
        all_contracts = large_store.filter(FilterState())
        start = time.perf_counter()
        groups = large_store.aggregate_groups("category", all_contracts)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Group-by aggregation took {elapsed:.3f}s"
        assert len(groups) > 0

    def test_trend_10k(self, large_store: DataStore):
        all_contracts = large_store.filter(FilterState())
        start = time.perf_counter()
        trends = large_store.trend("month", all_contracts)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Trend computation took {elapsed:.3f}s"
        assert len(trends) > 0

    def test_rankings_10k(self, large_store: DataStore):
        start = time.perf_counter()
        rankings = large_store.rank_institutions("total_spend")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.500, f"Rankings took {elapsed:.3f}s (limit: 0.500s)"
        assert len(rankings) > 0


class TestSortPerformance:
    """Sort operations on 10k+ contracts should be fast."""

    def test_sort_10k_single_column(self, large_store: DataStore):
        all_contracts = large_store.filter(FilterState())
        start = time.perf_counter()
        sorted_list = large_store.sort_contracts(
            all_contracts, [("price_numeric_eur", "desc")]
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.200, f"Sort (single column) took {elapsed:.3f}s"
        assert len(sorted_list) == 10_000

    def test_sort_10k_multi_column(self, large_store: DataStore):
        all_contracts = large_store.filter(FilterState())
        start = time.perf_counter()
        sorted_list = large_store.sort_contracts(
            all_contracts, [("buyer", "asc"), ("price_numeric_eur", "desc")]
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.300, f"Sort (multi-column) took {elapsed:.3f}s"
        assert len(sorted_list) == 10_000


class TestLoadPerformance:
    """Data loading should be fast even for large datasets."""

    def test_load_10k_from_list_under_2s(self):
        records = _generate_contracts(10_000)
        start = time.perf_counter()
        ds = DataStore()
        ds.load_from_list(records)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Loading 10k records took {elapsed:.3f}s (limit: 2.0s)"
        assert len(ds.contracts) == 10_000

    def test_load_50k_from_list_under_10s(self):
        records = _generate_contracts(50_000)
        start = time.perf_counter()
        ds = DataStore()
        ds.load_from_list(records)
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Loading 50k records took {elapsed:.3f}s (limit: 10.0s)"
        assert len(ds.contracts) == 50_000
