"""
Unit tests for Phase 1 — In-Memory Query & Aggregation Engine.

Tests cover: loading, filtering, grouping, aggregation, search,
benchmarking / comparison, trends, rankings, and edge cases.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.engine import DataStore, SORTABLE_FIELDS
from src.models import AggregationResult, FilterState

# ── Fixtures ────────────────────────────────────────────────────────

SAMPLE_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "test_data.json"
)


@pytest.fixture
def store() -> DataStore:
    """DataStore loaded with the sample contracts."""
    return DataStore(SAMPLE_DATA_PATH)


@pytest.fixture
def small_records():
    """Minimal contract records for controlled tests."""
    return [
        {
            "contract_title": "Oprava ciest",
            "buyer": "Mesto Bratislava",
            "supplier": "STRABAG s.r.o.",
            "price_numeric_eur": 1_000_000.0,
            "published_date": "2025-12-01",
            "category": "construction",
            "award_type": "direct_award",
            "pdf_text_summary": "road repair summary",
            "ico_buyer": "00001001",
            "ico_supplier": "00002001",
        },
        {
            "contract_title": "IT systém",
            "buyer": "Mesto Bratislava",
            "supplier": "T-Systems Slovakia s.r.o.",
            "price_numeric_eur": 500_000.0,
            "published_date": "2025-12-15",
            "category": "IT",
            "award_type": "open_tender",
            "pdf_text_summary": "IT system deployment",
            "ico_buyer": "00001001",
            "ico_supplier": "00002002",
        },
        {
            "contract_title": "Dodávka potravín",
            "buyer": "Mesto Košice",
            "supplier": "STRABAG s.r.o.",
            "price_numeric_eur": 200_000.0,
            "published_date": "2026-01-10",
            "category": "supplies",
            "award_type": "direct_award",
            "pdf_text_summary": "food supply for canteen",
            "ico_buyer": "00001002",
            "ico_supplier": "00002001",
        },
        {
            "contract_title": "Bezpečnostné služby",
            "buyer": "Ministerstvo vnútra SR",
            "supplier": "SecurCorp a.s.",
            "price_numeric_eur": 750_000.0,
            "published_date": "2026-01-20",
            "category": "services",
            "award_type": "open_tender",
            "pdf_text_summary": "security services contract",
            "ico_buyer": "00001003",
            "ico_supplier": "00002003",
        },
        {
            "contract_title": "Údržba budov",
            "buyer": "Mesto Košice",
            "supplier": "BuildCo s.r.o.",
            "price_numeric_eur": 300_000.0,
            "published_date": "2026-02-05",
            "category": "construction",
            "award_type": "direct_award",
            "pdf_text_summary": "building maintenance",
            "ico_buyer": "00001002",
            "ico_supplier": "00002004",
        },
    ]


@pytest.fixture
def small_store(small_records) -> DataStore:
    """DataStore loaded with a small set of controlled contracts."""
    ds = DataStore()
    ds.load_from_list(small_records)
    return ds


# ── 1. Loading ──────────────────────────────────────────────────────


class TestLoad:
    """Tests for loading contracts into the DataStore."""

    def test_load_contracts(self, store: DataStore):
        """DataStore loads sample JSON and reports correct count."""
        assert store.count == 29

    def test_load_from_json_file(self):
        """Load from a temporary JSON file works."""
        records = [
            {"contract_title": "Test", "buyer": "A", "price_numeric_eur": 10}
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(records, f)
            tmp_path = f.name

        try:
            ds = DataStore(tmp_path)
            assert ds.count == 1
            assert ds.contracts[0].contract_title == "Test"
        finally:
            os.unlink(tmp_path)

    def test_load_from_list(self, small_records):
        """load_from_list works with plain dicts."""
        ds = DataStore()
        count = ds.load_from_list(small_records)
        assert count == 5
        assert ds.count == 5

    def test_empty_store(self):
        """Empty DataStore has zero contracts."""
        ds = DataStore()
        assert ds.count == 0
        assert ds.contracts == []

    def test_contracts_are_contract_objects(self, store: DataStore):
        """Each loaded item is a Contract instance."""
        from src.models import Contract

        for c in store.contracts:
            assert isinstance(c, Contract)


# ── 2. Filtering ────────────────────────────────────────────────────


class TestFilter:
    """Tests for the filter() method."""

    def test_empty_filter_returns_all(self, store: DataStore):
        """No filters → all contracts returned."""
        result = store.filter(FilterState())
        assert len(result) == 29

    def test_filter_by_institution(self, small_store: DataStore):
        """Filter by institution returns only matching buyer."""
        f = FilterState(institutions=["Mesto Bratislava"])
        result = small_store.filter(f)
        assert len(result) == 2
        assert all(c.buyer == "Mesto Bratislava" for c in result)

    def test_filter_by_multiple_institutions(self, small_store: DataStore):
        """Filter by multiple institutions returns all matching."""
        f = FilterState(
            institutions=["Mesto Bratislava", "Mesto Košice"]
        )
        result = small_store.filter(f)
        assert len(result) == 4

    def test_filter_by_date_range(self, small_store: DataStore):
        """Date boundaries are inclusive."""
        f = FilterState(date_from="2026-01-01", date_to="2026-01-31")
        result = small_store.filter(f)
        assert len(result) == 2
        for c in result:
            assert c.published_date >= "2026-01-01"
            assert c.published_date <= "2026-01-31"

    def test_filter_by_date_from_only(self, small_store: DataStore):
        """date_from without date_to."""
        f = FilterState(date_from="2026-01-01")
        result = small_store.filter(f)
        assert len(result) == 3

    def test_filter_by_date_to_only(self, small_store: DataStore):
        """date_to without date_from."""
        f = FilterState(date_to="2025-12-31")
        result = small_store.filter(f)
        assert len(result) == 2

    def test_filter_by_value_range(self, small_store: DataStore):
        """Min/max EUR range filter."""
        f = FilterState(value_min=300_000, value_max=800_000)
        result = small_store.filter(f)
        # 500k (IT), 750k (security), 300k (maintenance)
        assert len(result) == 3
        for c in result:
            assert 300_000 <= c.price_numeric_eur <= 800_000

    def test_filter_by_value_min_only(self, small_store: DataStore):
        """value_min without value_max."""
        f = FilterState(value_min=500_000)
        result = small_store.filter(f)
        assert len(result) == 3  # 1M, 500k, 750k

    def test_filter_by_category(self, small_store: DataStore):
        """Filters on category field."""
        f = FilterState(categories=["construction"])
        result = small_store.filter(f)
        assert len(result) == 2
        assert all(c.category == "construction" for c in result)

    def test_filter_by_vendor(self, small_store: DataStore):
        """Filter by vendor (supplier)."""
        f = FilterState(vendors=["STRABAG s.r.o."])
        result = small_store.filter(f)
        assert len(result) == 2
        assert all(c.supplier == "STRABAG s.r.o." for c in result)

    def test_filter_by_award_type(self, small_store: DataStore):
        """Filter by award_type."""
        f = FilterState(award_types=["direct_award"])
        result = small_store.filter(f)
        assert len(result) == 3

    def test_filter_by_text_search(self, small_store: DataStore):
        """Text search matches title substring."""
        f = FilterState(text_search="systém")
        result = small_store.filter(f)
        assert len(result) == 1
        assert result[0].contract_title == "IT systém"

    def test_filter_by_text_search_in_summary(self, small_store: DataStore):
        """Text search matches pdf_text_summary substring."""
        f = FilterState(text_search="canteen")
        result = small_store.filter(f)
        assert len(result) == 1
        assert result[0].supplier == "STRABAG s.r.o."

    def test_filter_combined(self, small_store: DataStore):
        """Multiple filters applied together (AND)."""
        f = FilterState(
            institutions=["Mesto Bratislava"],
            value_min=400_000,
        )
        result = small_store.filter(f)
        assert len(result) == 2  # 1M (roads) + 500k (IT)

    def test_filter_no_match(self, small_store: DataStore):
        """Filter returning zero results."""
        f = FilterState(institutions=["Non-existent"])
        result = small_store.filter(f)
        assert len(result) == 0


# ── 3. Search ───────────────────────────────────────────────────────


class TestSearch:
    """Tests for the search() method."""

    def test_search_title(self, small_store: DataStore):
        """Search finds contract by title."""
        result = small_store.search("oprava")
        assert len(result) == 1
        assert result[0].contract_title == "Oprava ciest"

    def test_search_summary(self, small_store: DataStore):
        """Search finds contract by pdf_text_summary."""
        result = small_store.search("security")
        assert len(result) == 1

    def test_search_case_insensitive(self, small_store: DataStore):
        """Search is case-insensitive."""
        result = small_store.search("IT SYSTÉM")
        assert len(result) == 1

    def test_search_no_match(self, small_store: DataStore):
        """Search with no match returns empty list."""
        result = small_store.search("zxyzxyzxy")
        assert result == []


# ── 4. Group By ─────────────────────────────────────────────────────


class TestGroupBy:
    """Tests for the group_by() method."""

    def test_group_by_category(self, small_store: DataStore):
        """Returns correct groups by category."""
        groups = small_store.group_by("category")
        assert set(groups.keys()) == {"construction", "IT", "supplies", "services"}
        assert len(groups["construction"]) == 2

    def test_group_by_supplier(self, small_store: DataStore):
        """Groups by supplier name."""
        groups = small_store.group_by("supplier")
        assert "STRABAG s.r.o." in groups
        assert len(groups["STRABAG s.r.o."]) == 2

    def test_group_by_buyer(self, small_store: DataStore):
        """Groups by buyer."""
        groups = small_store.group_by("buyer")
        assert len(groups["Mesto Bratislava"]) == 2
        assert len(groups["Mesto Košice"]) == 2

    def test_group_by_month(self, small_store: DataStore):
        """Groups by YYYY-MM month key."""
        groups = small_store.group_by("month")
        assert "2025-12" in groups
        assert "2026-01" in groups
        assert "2026-02" in groups
        assert len(groups["2025-12"]) == 2

    def test_group_by_award_type(self, small_store: DataStore):
        """Groups by award_type."""
        groups = small_store.group_by("award_type")
        assert len(groups["direct_award"]) == 3
        assert len(groups["open_tender"]) == 2

    def test_group_by_with_filtered_contracts(self, small_store: DataStore):
        """group_by accepts a filtered subset."""
        filtered = small_store.filter(FilterState(institutions=["Mesto Bratislava"]))
        groups = small_store.group_by("category", contracts=filtered)
        assert set(groups.keys()) == {"construction", "IT"}

    def test_group_by_sample_data(self, store: DataStore):
        """Sample data all category='not_decided' → single group."""
        groups = store.group_by("category")
        assert "not_decided" in groups
        assert len(groups["not_decided"]) == 29


# ── 5. Aggregation ──────────────────────────────────────────────────


class TestAggregation:
    """Tests for aggregate() and related methods."""

    def test_aggregation_total_spend(self, small_store: DataStore):
        """Sum of price_numeric_eur."""
        stats = small_store.aggregate()
        expected = 1_000_000 + 500_000 + 200_000 + 750_000 + 300_000
        assert stats["total_spend"] == expected

    def test_aggregation_contract_count(self, small_store: DataStore):
        """Correct count."""
        stats = small_store.aggregate()
        assert stats["contract_count"] == 5

    def test_aggregation_avg_value(self, small_store: DataStore):
        """Average of all prices."""
        stats = small_store.aggregate()
        expected_avg = (1_000_000 + 500_000 + 200_000 + 750_000 + 300_000) / 5
        assert stats["avg_value"] == pytest.approx(expected_avg)

    def test_aggregation_max_value(self, small_store: DataStore):
        """Maximum price."""
        stats = small_store.aggregate()
        assert stats["max_value"] == 1_000_000

    def test_aggregation_empty_list(self, small_store: DataStore):
        """Aggregation of empty list."""
        stats = small_store.aggregate([])
        assert stats["total_spend"] == 0.0
        assert stats["contract_count"] == 0
        assert stats["avg_value"] == 0.0

    def test_aggregate_groups(self, small_store: DataStore):
        """aggregate_groups returns AggregationResult objects sorted by spend."""
        results = small_store.aggregate_groups("category")
        assert all(isinstance(r, AggregationResult) for r in results)
        # construction: 1M + 300k = 1.3M should be first
        assert results[0].group_value == "construction"
        assert results[0].total_spend == 1_300_000

    def test_top_n_vendors(self, small_store: DataStore):
        """top_n_vendors returns correct ranking."""
        top = small_store.top_n_vendors(n=2)
        assert len(top) == 2
        # STRABAG total: 1M + 200k = 1.2M → first
        assert top[0].name == "STRABAG s.r.o."
        assert top[0].total_spend == 1_200_000

    def test_direct_award_rate(self, small_store: DataStore):
        """3 out of 5 are direct awards."""
        rate = small_store.direct_award_rate()
        assert rate == pytest.approx(0.6)

    def test_direct_award_rate_empty(self):
        """Empty store → 0.0."""
        ds = DataStore()
        assert ds.direct_award_rate() == 0.0


# ── 6. Institutions & Vendors ───────────────────────────────────────


class TestInstitutionsVendors:
    """Tests for institutions() and vendors() listings."""

    def test_institutions_list(self, small_store: DataStore):
        """Lists all unique buyers with stats."""
        insts = small_store.institutions()
        names = [i.name for i in insts]
        assert "Mesto Bratislava" in names
        assert "Mesto Košice" in names
        assert "Ministerstvo vnútra SR" in names
        assert len(insts) == 3

    def test_institutions_sorted_by_spend(self, small_store: DataStore):
        """Institutions sorted descending by total_spend."""
        insts = small_store.institutions()
        spends = [i.total_spend for i in insts]
        assert spends == sorted(spends, reverse=True)

    def test_vendors_list(self, small_store: DataStore):
        """Lists all unique vendors."""
        vs = small_store.vendors()
        names = [v.name for v in vs]
        assert "STRABAG s.r.o." in names
        assert len(vs) == 4


# ── 7. Compare / Benchmark ──────────────────────────────────────────


class TestCompare:
    """Tests for the compare() method."""

    def test_compare_total_spend(self, small_store: DataStore):
        """Compare two institutions by total_spend."""
        result = small_store.compare(
            ["Mesto Bratislava", "Mesto Košice"], metric="total_spend"
        )
        assert len(result) == 2
        # Bratislava: 1.5M, Košice: 500k
        assert result[0]["institution"] == "Mesto Bratislava"
        assert result[0]["value"] == 1_500_000
        assert result[1]["institution"] == "Mesto Košice"
        assert result[1]["value"] == 500_000

    def test_compare_contract_count(self, small_store: DataStore):
        """Compare by contract_count."""
        result = small_store.compare(
            ["Mesto Bratislava", "Ministerstvo vnútra SR"],
            metric="contract_count",
        )
        assert result[0]["value"] == 2  # both have 2
        assert result[1]["value"] == 1

    def test_compare_direct_award_rate(self, small_store: DataStore):
        """Compare by direct_award_rate."""
        result = small_store.compare(
            ["Mesto Bratislava", "Mesto Košice"],
            metric="direct_award_rate",
        )
        # Bratislava: 1 direct / 2 = 0.5, Košice: 2 direct / 2 = 1.0
        assert result[0]["institution"] == "Mesto Košice"
        assert result[0]["value"] == pytest.approx(1.0)


# ── 8. Trends ───────────────────────────────────────────────────────


class TestTrends:
    """Tests for the trend() method."""

    def test_trend_monthly(self, small_store: DataStore):
        """Returns sorted monthly totals."""
        trend = small_store.trend(granularity="month")
        periods = [t["period"] for t in trend]
        assert periods == sorted(periods)
        assert "2025-12" in periods
        assert "2026-01" in periods
        assert "2026-02" in periods

    def test_trend_monthly_values(self, small_store: DataStore):
        """Monthly total_spend values are correct."""
        trend = small_store.trend(granularity="month", metric="total_spend")
        by_period = {t["period"]: t["value"] for t in trend}
        assert by_period["2025-12"] == 1_500_000  # 1M + 500k
        assert by_period["2026-01"] == 950_000  # 200k + 750k
        assert by_period["2026-02"] == 300_000

    def test_trend_quarterly(self, small_store: DataStore):
        """Quarterly aggregation works."""
        trend = small_store.trend(granularity="quarter")
        periods = [t["period"] for t in trend]
        assert "2025-Q4" in periods
        assert "2026-Q1" in periods

    def test_trend_yearly(self, small_store: DataStore):
        """Yearly aggregation works."""
        trend = small_store.trend(granularity="year")
        periods = [t["period"] for t in trend]
        assert "2025" in periods
        assert "2026" in periods

    def test_trend_contract_count(self, small_store: DataStore):
        """Trend by contract_count metric."""
        trend = small_store.trend(granularity="month", metric="contract_count")
        by_period = {t["period"]: t["value"] for t in trend}
        assert by_period["2025-12"] == 2
        assert by_period["2026-01"] == 2
        assert by_period["2026-02"] == 1

    def test_trend_with_filtered_contracts(self, small_store: DataStore):
        """Trend on a filtered subset."""
        filtered = small_store.filter(FilterState(institutions=["Mesto Bratislava"]))
        trend = small_store.trend(
            granularity="month", contracts=filtered, metric="total_spend"
        )
        assert len(trend) == 1
        assert trend[0]["period"] == "2025-12"
        assert trend[0]["value"] == 1_500_000


# ── 9. Rankings ─────────────────────────────────────────────────────


class TestRankings:
    """Tests for rank_institutions() and rank_vendors()."""

    def test_rank_institutions(self, small_store: DataStore):
        """Descending by total spend, with rank numbers."""
        ranked = small_store.rank_institutions(metric="total_spend")
        assert ranked[0]["rank"] == 1
        assert ranked[0]["institution"] == "Mesto Bratislava"
        assert ranked[0]["value"] == 1_500_000
        assert ranked[-1]["rank"] == 3

    def test_rank_institutions_by_count(self, small_store: DataStore):
        """Rank by contract_count."""
        ranked = small_store.rank_institutions(metric="contract_count")
        # All have at most 2 or 1
        assert ranked[0]["value"] >= ranked[1]["value"]

    def test_rank_vendors(self, small_store: DataStore):
        """Rank vendors by total_spend."""
        ranked = small_store.rank_vendors(metric="total_spend")
        assert ranked[0]["rank"] == 1
        assert ranked[0]["vendor"] == "STRABAG s.r.o."
        assert ranked[0]["value"] == 1_200_000

    def test_rank_vendors_by_count(self, small_store: DataStore):
        """Rank vendors by contract_count."""
        ranked = small_store.rank_vendors(metric="contract_count")
        assert ranked[0]["value"] >= ranked[-1]["value"]

    def test_rank_institutions_direct_award_rate(self, small_store: DataStore):
        """Rank institutions by direct_award_rate."""
        ranked = small_store.rank_institutions(metric="direct_award_rate")
        # Košice: 2/2=1.0, Bratislava: 1/2=0.5, Min: 0/1=0.0
        assert ranked[0]["institution"] == "Mesto Košice"
        assert ranked[0]["value"] == pytest.approx(1.0)


# ── 10. Sample-data smoke tests ─────────────────────────────────────


class TestSampleData:
    """Smoke tests using the real test_data.json."""

    def test_total_spend_positive(self, store: DataStore):
        """Total spend across all sample contracts is positive."""
        stats = store.aggregate()
        assert stats["total_spend"] > 0

    def test_institutions_non_empty(self, store: DataStore):
        """At least one institution exists."""
        assert len(store.institutions()) > 0

    def test_vendors_non_empty(self, store: DataStore):
        """At least one vendor exists."""
        assert len(store.vendors()) > 0

    def test_trend_monthly_sample(self, store: DataStore):
        """Monthly trend has at least one data point."""
        trend = store.trend(granularity="month")
        assert len(trend) > 0

    def test_rank_institutions_sample(self, store: DataStore):
        """Ranking sample data produces correct rank numbers."""
        ranked = store.rank_institutions()
        assert ranked[0]["rank"] == 1
        for i, item in enumerate(ranked, 1):
            assert item["rank"] == i

    def test_search_sample(self, store: DataStore):
        """Search in sample data returns results for a known word."""
        # 'dodávk' is a substring of 'dodávku' / 'Dodávka' which appears
        result = store.search("dodávk")
        assert len(result) > 0

    def test_filter_by_date_range_sample(self, store: DataStore):
        """Date range filter on sample data."""
        f = FilterState(date_from="2026-01-01", date_to="2026-01-31")
        result = store.filter(f)
        for c in result:
            assert c.published_date >= "2026-01-01"
            assert c.published_date <= "2026-01-31"


# ── 11. Edge cases ──────────────────────────────────────────────────


class TestEdgeCases:
    """Edge-case tests."""

    def test_filter_with_none_prices(self):
        """Contracts with missing prices handled gracefully."""
        ds = DataStore()
        ds.load_from_list(
            [
                {"contract_title": "A", "buyer": "X", "price_numeric_eur": None},
                {"contract_title": "B", "buyer": "X", "price_numeric_eur": 100},
            ]
        )
        result = ds.filter(FilterState(value_min=50))
        assert len(result) == 1
        assert result[0].contract_title == "B"

    def test_filter_with_none_dates(self):
        """Contracts with missing dates are excluded by date filter."""
        ds = DataStore()
        ds.load_from_list(
            [
                {"contract_title": "A", "buyer": "X", "published_date": None},
                {"contract_title": "B", "buyer": "X", "published_date": "2026-01-01"},
            ]
        )
        result = ds.filter(FilterState(date_from="2025-01-01"))
        assert len(result) == 1

    def test_group_by_month_missing_date(self):
        """Contracts without published_date are excluded from month grouping."""
        ds = DataStore()
        ds.load_from_list(
            [
                {"contract_title": "A", "buyer": "X", "published_date": None},
                {"contract_title": "B", "buyer": "X", "published_date": "2026-01-15"},
            ]
        )
        groups = ds.group_by("month")
        assert len(groups) == 1
        assert "2026-01" in groups

    def test_aggregate_no_prices(self):
        """Aggregation when no contracts have prices."""
        ds = DataStore()
        ds.load_from_list(
            [{"contract_title": "A", "buyer": "X"}]
        )
        stats = ds.aggregate()
        assert stats["total_spend"] == 0.0
        assert stats["avg_value"] == 0.0
        assert stats["contract_count"] == 1

    def test_reload_replaces_data(self, small_records):
        """Loading new data replaces old data completely."""
        ds = DataStore()
        ds.load_from_list(small_records)
        assert ds.count == 5
        ds.load_from_list(small_records[:2])
        assert ds.count == 2


# ── Sort fixture ────────────────────────────────────────────────────


@pytest.fixture
def sort_store() -> DataStore:
    """
    DataStore with data specifically designed for sort tests:
    - duplicate prices for tie-breaking
    - a None price to verify None-last behaviour
    - a lowercase title to verify case-insensitive string sort
    """
    ds = DataStore()
    ds.load_from_list([
        {
            "contract_title": "Alpha contract",
            "buyer": "Inst A",
            "supplier": "Vendor C",
            "price_numeric_eur": 500_000.0,
            "published_date": "2025-01-15",
            "category": "construction",
            "scanned_suggested_title": "Road maintenance",
            "scanned_service_type": "construction_services",
            "scanned_service_subtype": "bridges",
        },
        {
            "contract_title": "Beta contract",
            "buyer": "Inst A",
            "supplier": "vendor a",
            "price_numeric_eur": 500_000.0,  # same price as Alpha
            "published_date": "2025-06-01",   # later date
            "category": "IT",
            "scanned_suggested_title": "Airport support",
            "scanned_service_type": "air_transport",
            "scanned_service_subtype": "airfield",
        },
        {
            "contract_title": "Gamma contract",
            "buyer": "Inst B",
            "supplier": "Vendor D",
            "price_numeric_eur": 200_000.0,
            "published_date": "2025-03-20",
            "category": "services",
            "scanned_suggested_title": "Waste collection",
            "scanned_service_type": "waste_services",
            "scanned_service_subtype": "bins",
        },
        {
            "contract_title": "delta contract",  # intentional lowercase
            "buyer": "Inst B",
            "supplier": "Vendor B",
            "price_numeric_eur": 800_000.0,
            "published_date": "2025-09-10",
            "category": "supplies",
            "scanned_suggested_title": "Zoo cleaning",
            "scanned_service_type": "cleaning_services",
            "scanned_service_subtype": "zebra",
        },
        {
            "contract_title": "Epsilon contract",
            "buyer": "Inst C",
            "supplier": "Vendor E",
            "price_numeric_eur": None,          # None price
            "published_date": "2025-07-01",
            "category": "construction",
            "scanned_suggested_title": None,
            "scanned_service_type": None,
            "scanned_service_subtype": None,
        },
    ])
    return ds


# ── 12. Sort ────────────────────────────────────────────────────────


class TestSort:
    """Tests for sort_contracts() and the SORTABLE_FIELDS constant."""

    def test_sortable_fields_include_scanned_columns(self):
        """Scanned table columns are whitelisted for API/UI sort specs."""
        assert "scanned_suggested_title" in SORTABLE_FIELDS
        assert "scanned_service_type" in SORTABLE_FIELDS
        assert "scanned_service_subtype" in SORTABLE_FIELDS

    def test_sort_single_field_ascending(self, sort_store: DataStore):
        """price_numeric_eur sorted low → high; None last."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("price_numeric_eur", "asc")]
        )
        non_none = [c for c in result if c.price_numeric_eur is not None]
        assert non_none[0].price_numeric_eur == 200_000.0   # Gamma
        assert non_none[-1].price_numeric_eur == 800_000.0  # delta
        # None value (Epsilon) must be the last element
        assert result[-1].price_numeric_eur is None

    def test_sort_single_field_descending(self, sort_store: DataStore):
        """price_numeric_eur sorted high → low; None last."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("price_numeric_eur", "desc")]
        )
        assert result[0].price_numeric_eur == 800_000.0    # delta
        assert result[-1].price_numeric_eur is None         # Epsilon last

    def test_sort_multi_column_tie_breaking(self, sort_store: DataStore):
        """Equal-price contracts ordered by secondary field (published_date)."""
        spec = [("price_numeric_eur", "asc"), ("published_date", "asc")]
        result = sort_store.sort_contracts(sort_store.contracts, spec)
        # Non-None prices: 200k (Gamma), 500k (Alpha, Jan 15), 500k (Beta, Jun 1), 800k (delta)
        non_none = [c for c in result if c.price_numeric_eur is not None]
        assert non_none[0].contract_title == "Gamma contract"  # 200k
        assert non_none[1].contract_title == "Alpha contract"  # 500k, earlier date
        assert non_none[2].contract_title == "Beta contract"   # 500k, later date
        assert non_none[3].contract_title == "delta contract"  # 800k

    def test_sort_none_values_last_ascending(self, sort_store: DataStore):
        """None price is last even when sorting ascending."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("price_numeric_eur", "asc")]
        )
        assert result[-1].contract_title == "Epsilon contract"

    def test_sort_none_values_last_descending(self, sort_store: DataStore):
        """None price is last even when sorting descending."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("price_numeric_eur", "desc")]
        )
        assert result[-1].contract_title == "Epsilon contract"

    def test_sort_string_field(self, sort_store: DataStore):
        """contract_title sorted alphabetically, case-insensitive."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("contract_title", "asc")]
        )
        titles_lower = [c.contract_title.lower() for c in result]
        assert titles_lower == sorted(titles_lower)
        # 'delta contract' (lowercase) sorts between 'beta' and 'epsilon'
        assert result[2].contract_title == "delta contract"

    def test_sort_buyer_alphabetical(self, sort_store: DataStore):
        """buyer sorted alphabetically, case-insensitive."""
        result = sort_store.sort_contracts(sort_store.contracts, [("buyer", "asc")])
        buyers = [c.buyer for c in result]
        assert buyers[:2] == ["Inst A", "Inst A"]
        assert buyers[2:4] == ["Inst B", "Inst B"]
        assert buyers[4] == "Inst C"

    def test_sort_supplier_alphabetical(self, sort_store: DataStore):
        """supplier sorted alphabetically, case-insensitive."""
        result = sort_store.sort_contracts(sort_store.contracts, [("supplier", "asc")])
        suppliers = [c.supplier for c in result]
        assert suppliers == ["vendor a", "Vendor B", "Vendor C", "Vendor D", "Vendor E"]

    def test_sort_scanned_subject_alphabetical(self, sort_store: DataStore):
        """scanned_suggested_title sorts alphabetically with None values last."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("scanned_suggested_title", "asc")]
        )
        subjects = [sort_store._sort_field_value(c, "scanned_suggested_title") for c in result]
        assert subjects[:4] == [
            "Airport support",
            "Road maintenance",
            "Waste collection",
            "Zoo cleaning",
        ]
        assert subjects[4] is None

    def test_sort_scanned_type_alphabetical(self, sort_store: DataStore):
        """scanned_service_type sorts alphabetically with None values last."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("scanned_service_type", "asc")]
        )
        service_types = [sort_store._sort_field_value(c, "scanned_service_type") for c in result]
        assert service_types[:4] == [
            "air_transport",
            "cleaning_services",
            "construction_services",
            "waste_services",
        ]
        assert service_types[4] is None

    def test_sort_scanned_subtype_alphabetical(self, sort_store: DataStore):
        """scanned_service_subtype sorts alphabetically with None values last."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("scanned_service_subtype", "asc")]
        )
        service_subtypes = [sort_store._sort_field_value(c, "scanned_service_subtype") for c in result]
        assert service_subtypes[:4] == ["airfield", "bins", "bridges", "zebra"]
        assert service_subtypes[4] is None

    def test_sort_iso_date_string_ordering(self, sort_store: DataStore):
        """ISO date strings sort correctly as plain strings."""
        result = sort_store.sort_contracts(
            sort_store.contracts, [("published_date", "asc")]
        )
        dates = [c.published_date for c in result]
        assert dates == sorted(dates)
        assert dates[0] == "2025-01-15"   # Alpha
        assert dates[-1] == "2025-09-10"  # delta

    def test_sort_unknown_field_skipped(self, sort_store: DataStore):
        """An unrecognised field is silently ignored; no exception raised."""
        result = sort_store.sort_contracts(
            sort_store.contracts,
            [("nonexistent_field", "asc")],
        )
        assert len(result) == len(sort_store.contracts)

    def test_sort_empty_list(self, sort_store: DataStore):
        """Sorting an empty list returns an empty list."""
        result = sort_store.sort_contracts([], [("price_numeric_eur", "asc")])
        assert result == []

    def test_sort_single_item(self, sort_store: DataStore):
        """Sorting a one-element list returns that element unchanged."""
        single = sort_store.contracts[:1]
        result = sort_store.sort_contracts(single, [("price_numeric_eur", "desc")])
        assert len(result) == 1
        assert result[0].contract_title == single[0].contract_title

    def test_sort_preserves_filter_result(self, small_store: DataStore):
        """sort_contracts applied on filter() output; does not re-read the full store."""
        filtered = small_store.filter(FilterState(institutions=["Mesto Bratislava"]))
        assert len(filtered) == 2
        result = small_store.sort_contracts(filtered, [("price_numeric_eur", "desc")])
        assert len(result) == 2
        # Bratislava: 1M (Oprava ciest) and 500k (IT systém)
        assert result[0].price_numeric_eur == 1_000_000.0
        assert result[1].price_numeric_eur == 500_000.0


# ── Phase 6 — Investigation Mode helpers ─────────────────────────────


class TestVendorConcentrationScore:
    """Tests for DataStore.vendor_concentration_score (Phase 6)."""

    def test_concentration_with_dominant_vendor(self, small_store: DataStore):
        """When one vendor has most spend, concentration is high."""
        # STRABAG: 1M + 200k = 1.2M out of 2.75M total => top-1 ~ 43.6%
        score = small_store.vendor_concentration_score(top_n=1)
        assert 0.4 < score < 0.5

    def test_concentration_top_3(self, small_store: DataStore):
        """Top-3 vendors hold a significant share."""
        score = small_store.vendor_concentration_score(top_n=3)
        assert score > 0.8

    def test_concentration_empty(self):
        """Empty store returns 0."""
        ds = DataStore()
        assert ds.vendor_concentration_score() == 0.0

    def test_concentration_scoped_to_institution(self, small_store: DataStore):
        """Concentration computed on a filtered subset."""
        contracts = small_store.filter(FilterState(institutions=["Mesto Bratislava"]))
        score = small_store.vendor_concentration_score(contracts, top_n=1)
        # STRABAG: 1M out of 1.5M = 0.667
        assert abs(score - 1_000_000 / 1_500_000) < 0.01


class TestFragmentationScore:
    """Tests for DataStore.fragmentation_score (Phase 6)."""

    def test_fragmentation_returns_float(self, small_store: DataStore):
        """Fragmentation score is between 0 and 1."""
        score = small_store.fragmentation_score()
        assert 0.0 <= score <= 1.0

    def test_fragmentation_empty(self):
        """Empty store returns 0."""
        ds = DataStore()
        assert ds.fragmentation_score() == 0.0

    def test_fragmentation_single_contract(self):
        """Single contract has 0 fragmentation."""
        ds = DataStore()
        ds.load_from_list([{"price_numeric_eur": 100.0}])
        score = ds.fragmentation_score()
        assert score == 0.0


class TestCompareMultiMetric:
    """Tests for DataStore.compare_multi_metric (Phase 6)."""

    def test_multi_metric_comparison(self, small_store: DataStore):
        """Comparing two institutions on multiple metrics returns correct keys."""
        results = small_store.compare_multi_metric(
            ["Mesto Bratislava", "Mesto Košice"],
            ["total_spend", "contract_count", "direct_award_rate"],
        )
        assert len(results) == 2
        ba = next(r for r in results if r["institution"] == "Mesto Bratislava")
        assert ba["total_spend"] == 1_500_000
        assert ba["contract_count"] == 2
        assert ba["direct_award_rate"] == 0.5  # 1 of 2 is direct

    def test_multi_metric_with_concentration(self, small_store: DataStore):
        """Vendor concentration metric works in multi-metric."""
        results = small_store.compare_multi_metric(
            ["Mesto Bratislava"],
            ["vendor_concentration"],
        )
        assert "vendor_concentration" in results[0]
        assert 0.0 <= results[0]["vendor_concentration"] <= 1.0


class TestPeerGroup:
    """Tests for DataStore.peer_group (Phase 6)."""

    def test_peer_group_excludes_self(self, small_store: DataStore):
        """Target institution is not in its own peer group."""
        peers = small_store.peer_group("Mesto Bratislava", min_contracts=1)
        assert "Mesto Bratislava" not in peers

    def test_peer_group_min_contracts(self, small_store: DataStore):
        """min_contracts filters out institutions with fewer contracts."""
        peers = small_store.peer_group("Mesto Bratislava", min_contracts=2)
        # Only Mesto Košice has 2 contracts besides Bratislava
        assert "Mesto Košice" in peers
        assert "Ministerstvo vnútra SR" not in peers

    def test_peer_group_returns_all_eligible(self, small_store: DataStore):
        """With min_contracts=1, all other institutions are peers."""
        peers = small_store.peer_group("Mesto Bratislava", min_contracts=1)
        assert len(peers) == 2  # Košice + Ministerstvo


class TestTrendMultiMetric:
    """Tests for DataStore.trend_multi_metric (Phase 6)."""

    def test_multi_metric_trend(self, small_store: DataStore):
        """Multi-metric trend returns all requested metrics."""
        data = small_store.trend_multi_metric(
            granularity="month",
            metrics=["total_spend", "contract_count"],
        )
        assert len(data) > 0
        for point in data:
            assert "period" in point
            assert "total_spend" in point
            assert "contract_count" in point

    def test_multi_metric_trend_yearly(self, small_store: DataStore):
        """Yearly granularity produces year-level keys."""
        data = small_store.trend_multi_metric(
            granularity="year",
            metrics=["total_spend"],
        )
        for point in data:
            assert len(point["period"]) == 4  # YYYY

    def test_multi_metric_defaults_to_total_spend(self, small_store: DataStore):
        """Omitting metrics defaults to total_spend."""
        data = small_store.trend_multi_metric(granularity="month")
        for point in data:
            assert "total_spend" in point
