"""
Unit tests for Phase 2 — Backend API (FastAPI).

Tests cover: contracts CRUD, aggregations, treemap, benchmark,
trends, rankings, institutions, vendors, CSV export, and
filter-state round-trip.
"""

import csv
import io
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.api import app, encode_filter_state, get_store
from src.engine import DataStore
from src.models import FilterState

# ── Test data ────────────────────────────────────────────────────────

SMALL_RECORDS = [
    {
        "contract_id": "1001",
        "contract_title": "Oprava ciest",
        "buyer": "Mesto Bratislava",
        "supplier": "STRABAG s.r.o.",
        "price_numeric_eur": 1_000_000.0,
        "published_date": "2025-12-01",
        "category": "construction",
        "award_type": "direct_award",
        "pdf_text_summary": "road repair summary",
        "contract_url": "https://www.crz.gov.sk/zmluva/1001/",
        "ico_buyer": "00001001",
        "ico_supplier": "00002001",
    },
    {
        "contract_id": "1002",
        "contract_title": "IT systém",
        "buyer": "Mesto Bratislava",
        "supplier": "T-Systems Slovakia s.r.o.",
        "price_numeric_eur": 500_000.0,
        "published_date": "2025-12-15",
        "category": "IT",
        "award_type": "open_tender",
        "pdf_text_summary": "IT system deployment",
        "contract_url": "https://www.crz.gov.sk/zmluva/1002/",
        "ico_buyer": "00001001",
        "ico_supplier": "00002002",
    },
    {
        "contract_id": "1003",
        "contract_title": "Dodávka potravín",
        "buyer": "Mesto Košice",
        "supplier": "STRABAG s.r.o.",
        "price_numeric_eur": 200_000.0,
        "published_date": "2026-01-10",
        "category": "supplies",
        "award_type": "direct_award",
        "pdf_text_summary": "food supply for canteen",
        "contract_url": "https://www.crz.gov.sk/zmluva/1003/",
        "ico_buyer": "00001002",
        "ico_supplier": "00002001",
    },
    {
        "contract_id": "1004",
        "contract_title": "Bezpečnostné služby",
        "buyer": "Ministerstvo vnútra SR",
        "supplier": "SecurCorp a.s.",
        "price_numeric_eur": 750_000.0,
        "published_date": "2026-01-20",
        "category": "services",
        "award_type": "open_tender",
        "pdf_text_summary": "security services contract",
        "contract_url": "https://www.crz.gov.sk/zmluva/1004/",
        "ico_buyer": "00001003",
        "ico_supplier": "00002003",
    },
    {
        "contract_id": "1005",
        "contract_title": "Údržba budov",
        "buyer": "Mesto Košice",
        "supplier": "BuildCo s.r.o.",
        "price_numeric_eur": 300_000.0,
        "published_date": "2026-02-05",
        "category": "construction",
        "award_type": "direct_award",
        "pdf_text_summary": "building maintenance",
        "contract_url": "https://www.crz.gov.sk/zmluva/1005/",
        "ico_buyer": "00001002",
        "ico_supplier": "00002004",
    },
]


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def test_store():
    """DataStore loaded with small controlled data."""
    ds = DataStore()
    ds.load_from_list(SMALL_RECORDS)
    return ds


@pytest.fixture
def client(test_store):
    """FastAPI test client with dependency override."""
    app.dependency_overrides[get_store] = lambda: test_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Contracts ────────────────────────────────────────────────────────


class TestContracts:
    """Tests for /api/contracts endpoints."""

    def test_get_contracts_returns_200(self, client):
        """Basic contracts endpoint returns 200 with all records."""
        r = client.get("/api/contracts")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["contracts"]) == 5

    def test_get_contracts_filter_institution(self, client):
        """Filtering by institution returns only matching buyer."""
        r = client.get(
            "/api/contracts",
            params={"institutions": "Mesto Bratislava"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert all(
            c["buyer"] == "Mesto Bratislava" for c in data["contracts"]
        )

    def test_get_contracts_pagination(self, client):
        """Pagination slices results correctly."""
        r = client.get(
            "/api/contracts",
            params={"page": 1, "page_size": 2},
        )
        data = r.json()
        assert len(data["contracts"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3

    def test_get_contracts_filter_date_range(self, client):
        """Date-range filter returns contracts within range."""
        r = client.get(
            "/api/contracts",
            params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        )
        data = r.json()
        assert data["total"] == 2
        for c in data["contracts"]:
            assert c["published_date"] >= "2026-01-01"
            assert c["published_date"] <= "2026-01-31"

    def test_get_contracts_filter_text_search(self, client):
        """Text search matches contract title."""
        r = client.get(
            "/api/contracts", params={"text_search": "systém"}
        )
        data = r.json()
        assert data["total"] == 1
        assert data["contracts"][0]["contract_id"] == "1002"

    def test_get_contract_detail(self, client):
        """Single contract by ID returns correct record."""
        r = client.get("/api/contracts/1001")
        assert r.status_code == 200
        data = r.json()
        assert data["contract_id"] == "1001"
        assert data["contract_title"] == "Oprava ciest"
        assert data["buyer"] == "Mesto Bratislava"

    def test_get_contract_not_found(self, client):
        """Missing contract ID returns 404."""
        r = client.get("/api/contracts/9999")
        assert r.status_code == 404


# ── Aggregations ─────────────────────────────────────────────────────


class TestAggregations:
    """Tests for /api/aggregations endpoint."""

    def test_aggregations_group_by_category(self, client):
        """Grouped aggregation returns correct structure."""
        r = client.get(
            "/api/aggregations", params={"group_by": "category"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["group_by"] == "category"
        assert "results" in data
        assert "summary" in data
        # construction: 1M + 300k = 1.3M
        groups = {g["group_value"]: g for g in data["results"]}
        assert "construction" in groups
        assert groups["construction"]["total_spend"] == 1_300_000

    def test_aggregations_with_filter(self, client):
        """Aggregation respects filters."""
        r = client.get(
            "/api/aggregations",
            params={
                "group_by": "category",
                "institutions": "Mesto Bratislava",
            },
        )
        data = r.json()
        assert data["summary"]["contract_count"] == 2
        assert data["summary"]["total_spend"] == 1_500_000


# ── Treemap ──────────────────────────────────────────────────────────


class TestTreemap:
    """Tests for /api/treemap endpoint."""

    def test_treemap_data_structure(self, client):
        """Treemap returns hierarchical JSON with name, value, children."""
        r = client.get(
            "/api/treemap", params={"group_by": "category"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "root"
        assert "value" in data
        assert "children" in data
        assert len(data["children"]) == 4  # 4 categories

        # Children have required fields
        for child in data["children"]:
            assert "name" in child
            assert "value" in child
            assert "contract_count" in child

    def test_treemap_with_sub_group(self, client):
        """Treemap with sub-grouping has nested children."""
        r = client.get(
            "/api/treemap",
            params={"group_by": "category", "sub_group_by": "supplier"},
        )
        data = r.json()
        # construction group should have children by supplier
        construction = next(
            (c for c in data["children"] if c["name"] == "construction"),
            None,
        )
        assert construction is not None
        assert "children" in construction
        assert len(construction["children"]) == 2  # STRABAG + BuildCo


# ── Benchmark ────────────────────────────────────────────────────────


class TestBenchmark:
    """Tests for /api/benchmark endpoint."""

    def test_benchmark_endpoint(self, client):
        """Benchmark returns peer comparison."""
        r = client.get(
            "/api/benchmark",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice",
                "metric": "total_spend",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["metric"] == "total_spend"
        assert len(data["results"]) == 2
        # Bratislava: 1.5M > Košice: 500k → sorted desc
        assert data["results"][0]["institution"] == "Mesto Bratislava"
        assert data["results"][0]["value"] == 1_500_000


# ── Trends ───────────────────────────────────────────────────────────


class TestTrends:
    """Tests for /api/trends endpoint."""

    def test_trends_endpoint(self, client):
        """Trends returns time-series array."""
        r = client.get(
            "/api/trends",
            params={"granularity": "month", "metric": "total_spend"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["granularity"] == "month"
        assert data["metric"] == "total_spend"
        assert "data" in data
        periods = [d["period"] for d in data["data"]]
        assert periods == sorted(periods)

    def test_trends_with_filter(self, client):
        """Trends respects filters."""
        r = client.get(
            "/api/trends",
            params={
                "granularity": "month",
                "institutions": "Mesto Bratislava",
            },
        )
        data = r.json()
        # Only Dec 2025 for Bratislava
        assert len(data["data"]) == 1
        assert data["data"][0]["period"] == "2025-12"


# ── Rankings ─────────────────────────────────────────────────────────


class TestRankings:
    """Tests for /api/rankings endpoint."""

    def test_rankings_endpoint(self, client):
        """Institution rankings returns sorted list with rank numbers."""
        r = client.get(
            "/api/rankings",
            params={"entity": "institutions", "metric": "total_spend"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["entity"] == "institutions"
        assert data["rankings"][0]["rank"] == 1
        assert data["rankings"][0]["institution"] == "Mesto Bratislava"

    def test_rankings_vendors(self, client):
        """Vendor rankings works."""
        r = client.get(
            "/api/rankings",
            params={"entity": "vendors", "metric": "total_spend"},
        )
        data = r.json()
        assert data["entity"] == "vendors"
        assert data["rankings"][0]["rank"] == 1
        assert data["rankings"][0]["vendor"] == "STRABAG s.r.o."


class TestRankingsPagination:
    """Tests for pagination support on /api/rankings endpoint."""

    def test_rankings_response_has_pagination_metadata(self, client):
        """Response includes total, page, page_size, total_pages fields."""
        r = client.get("/api/rankings", params={"entity": "institutions"})
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_rankings_pagination_limits_results(self, client):
        """page_size=2 returns only 2 records on page 1."""
        r = client.get(
            "/api/rankings",
            params={"entity": "institutions", "metric": "total_spend", "page_size": 2},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["rankings"]) == 2
        assert data["total"] == 3  # 3 institutions in test fixture
        assert data["page_size"] == 2
        assert data["total_pages"] == 2
        # First page still returns rank 1
        assert data["rankings"][0]["rank"] == 1

    def test_rankings_pagination_page_2(self, client):
        """page=2 with page_size=2 returns the 3rd institution."""
        r = client.get(
            "/api/rankings",
            params={"entity": "institutions", "metric": "total_spend", "page_size": 2, "page": 2},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["rankings"]) == 1
        assert data["page"] == 2
        # Rank numbers are global (rank 3 is on page 2)
        assert data["rankings"][0]["rank"] == 3

    def test_rankings_pagination_beyond_last_page_returns_empty(self, client):
        """Requesting a page beyond the last returns empty rankings."""
        r = client.get(
            "/api/rankings",
            params={"entity": "institutions", "page": 99, "page_size": 20},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["rankings"] == []
        assert data["total"] == 3

    def test_rankings_default_page_size_is_20(self, client):
        """Default page_size is 20 — all 3 test-fixture institutions fit on page 1."""
        r = client.get("/api/rankings", params={"entity": "institutions"})
        data = r.json()
        assert data["page_size"] == 20
        assert len(data["rankings"]) == 3  # all 3 fit


# ── Institutions ─────────────────────────────────────────────────────


class TestInstitutions:
    """Tests for /api/institutions endpoints."""

    def test_institutions_list(self, client):
        """Lists unique buyers with stats."""
        r = client.get("/api/institutions")
        assert r.status_code == 200
        data = r.json()
        names = [i["name"] for i in data["institutions"]]
        assert "Mesto Bratislava" in names
        assert "Mesto Košice" in names
        assert "Ministerstvo vnútra SR" in names
        assert len(data["institutions"]) == 3

    def test_institution_profile_by_name(self, client):
        """Institution profile by name returns full data."""
        r = client.get(
            f"/api/institutions/{quote('Mesto Bratislava', safe='')}"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Mesto Bratislava"
        assert data["ico"] == "00001001"
        assert data["contract_count"] == 2
        assert data["total_spend"] == 1_500_000
        assert "top_vendors" in data
        assert "trend" in data
        assert "contracts" in data

    def test_institution_profile_by_ico(self, client):
        """Institution profile by ICO works."""
        r = client.get("/api/institutions/00001002")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Mesto Košice"

    def test_institution_not_found(self, client):
        """Unknown institution returns 404."""
        r = client.get(
            f"/api/institutions/{quote('Unknown', safe='')}"
        )
        assert r.status_code == 404


# ── Vendors ──────────────────────────────────────────────────────────


class TestVendors:
    """Tests for /api/vendors endpoints."""

    def test_vendors_list(self, client):
        """Lists unique vendors with stats."""
        r = client.get("/api/vendors")
        assert r.status_code == 200
        data = r.json()
        names = [v["name"] for v in data["vendors"]]
        assert "STRABAG s.r.o." in names
        assert len(data["vendors"]) == 4

    def test_vendor_profile(self, client):
        """Vendor profile returns full data with institutions served."""
        r = client.get(
            f"/api/vendors/{quote('STRABAG s.r.o.', safe='')}"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "STRABAG s.r.o."
        assert data["ico"] == "00002001"
        assert data["contract_count"] == 2
        assert data["total_spend"] == 1_200_000
        assert "institutions_served" in data
        assert "trend" in data
        assert "contracts" in data

    def test_vendor_profile_by_ico(self, client):
        """Vendor profile by ICO works."""
        r = client.get("/api/vendors/00002003")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "SecurCorp a.s."

    def test_vendor_not_found(self, client):
        """Unknown vendor returns 404."""
        r = client.get(
            f"/api/vendors/{quote('Unknown', safe='')}"
        )
        assert r.status_code == 404


# ── Export ────────────────────────────────────────────────────────────


class TestExport:
    """Tests for /api/export endpoints."""

    def test_export_csv(self, client):
        """CSV export returns correct content-type and data."""
        r = client.get("/api/export/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]

        # Parse CSV content
        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        assert len(rows) == 5
        assert rows[0]["contract_id"] == "1001"

    def test_export_csv_with_filter(self, client):
        """CSV export respects filters."""
        r = client.get(
            "/api/export/csv",
            params={"institutions": "Mesto Bratislava"},
        )
        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        assert len(rows) == 2
        assert all(row["buyer"] == "Mesto Bratislava" for row in rows)

    def test_export_pdf_not_implemented(self, client):
        """PDF export returns a valid PDF (Phase 7)."""
        r = client.get("/api/export/pdf")
        assert r.status_code == 200
        assert "application/pdf" in r.headers["content-type"]


# ── Filter-state round-trip ──────────────────────────────────────────


class TestFilterState:
    """Tests for filter-state serialisation."""

    def test_filter_state_round_trip(self, client):
        """Encode → decode preserves all filter fields."""
        original = FilterState(
            institutions=["Mesto Bratislava", "Mesto Košice"],
            date_from="2025-01-01",
            date_to="2026-12-31",
            categories=["construction"],
            value_min=100_000,
            value_max=5_000_000,
            award_types=["direct_award"],
            text_search="cesty",
        )
        encoded = encode_filter_state(original)

        r = client.get("/api/filter-state", params=encoded)
        assert r.status_code == 200
        parsed = r.json()["parsed"]

        assert parsed["institutions"] == original.institutions
        assert parsed["date_from"] == original.date_from
        assert parsed["date_to"] == original.date_to
        assert parsed["categories"] == original.categories
        assert parsed["value_min"] == original.value_min
        assert parsed["value_max"] == original.value_max
        assert parsed["award_types"] == original.award_types
        assert parsed["text_search"] == original.text_search

    def test_empty_filter_encodes_to_empty(self):
        """Empty FilterState encodes to empty dict."""
        fs = FilterState()
        encoded = encode_filter_state(fs)
        assert encoded == {}

    def test_values_with_commas_survive_round_trip(self, client):
        """Values containing commas are preserved through encode→parse cycle."""
        original = FilterState(
            categories=["IT, consulting", "legal"],
            vendors=["Smith, Jones & Co"],
            institutions=["Ministry of Finance, SR"],
        )
        encoded = encode_filter_state(original)
        r = client.get("/api/filter-state", params=encoded)
        assert r.status_code == 200
        parsed = r.json()["parsed"]
        assert parsed["categories"] == ["IT, consulting", "legal"]
        assert parsed["vendors"] == ["Smith, Jones & Co"]
        assert parsed["institutions"] == ["Ministry of Finance, SR"]


# ── Sample-data smoke tests ──────────────────────────────────────────


class TestSampleDataSmoke:
    """Smoke tests using the real test_data.json."""

    @pytest.fixture
    def sample_client(self):
        """Client backed by the actual sample data."""
        import os

        data_path = os.path.join(
            os.path.dirname(__file__),
            "test_data.json",
        )
        ds = DataStore(data_path)
        app.dependency_overrides[get_store] = lambda: ds
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def test_contracts_endpoint(self, sample_client):
        """Contracts endpoint works with sample data."""
        r = sample_client.get("/api/contracts")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 29
        assert len(data["contracts"]) == 20  # default page_size

    def test_institutions_endpoint(self, sample_client):
        """Institutions endpoint returns results."""
        r = sample_client.get("/api/institutions")
        assert r.status_code == 200
        data = r.json()
        assert len(data["institutions"]) > 0

    def test_rankings_endpoint(self, sample_client):
        """Rankings endpoint works with sample data."""
        r = sample_client.get("/api/rankings")
        assert r.status_code == 200
        data = r.json()
        assert data["rankings"][0]["rank"] == 1

    def test_csv_export_sample(self, sample_client):
        """CSV export works with sample data."""
        r = sample_client.get("/api/export/csv")
        assert r.status_code == 200
        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        assert len(rows) == 29


# ── Contracts Sort ────────────────────────────────────────────────────


class TestContractsSort:
    """Tests for multi-column sort on GET /api/contracts and CSV export (Tasks 2.18–2.20)."""

    # Records with a deliberate price tie to exercise secondary sort
    TIE_RECORDS = [
        {
            "contract_id": "T001",
            "contract_title": "Alpha contract",
            "scanned_suggested_title": "Zeta support",
            "scanned_service_type": "water_services",
            "scanned_service_subtype": "zoning",
            "buyer": "Org A",
            "supplier": "Vendor X",
            "price_numeric_eur": 1_000_000.0,
            "published_date": "2025-03-01",
            "category": "construction",
            "award_type": "open_tender",
        },
        {
            "contract_id": "T002",
            "contract_title": "Beta contract",
            "scanned_suggested_title": "Alpha support",
            "scanned_service_type": "airport_services",
            "scanned_service_subtype": "airfield",
            "buyer": "Org A",
            "supplier": "Vendor Y",
            "price_numeric_eur": 500_000.0,
            "published_date": "2025-01-01",
            "category": "IT",
            "award_type": "direct_award",
        },
        {
            "contract_id": "T003",
            "contract_title": "Gamma contract",
            "scanned_suggested_title": "Beta support",
            "scanned_service_type": "building_services",
            "scanned_service_subtype": "bridges",
            "buyer": "Org B",
            "supplier": "Vendor Z",
            "price_numeric_eur": 500_000.0,
            "published_date": "2025-06-01",
            "category": "services",
            "award_type": "open_tender",
        },
    ]

    @pytest.fixture
    def tie_store(self):
        """DataStore with price ties for multi-column sort tests."""
        ds = DataStore()
        ds.load_from_list(self.TIE_RECORDS)
        return ds

    @pytest.fixture
    def tie_client(self, tie_store):
        """FastAPI test client backed by TIE_RECORDS."""
        app.dependency_overrides[get_store] = lambda: tie_store
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def test_sort_by_price_descending(self, client):
        """First contract in response has the highest price_numeric_eur."""
        r = client.get(
            "/api/contracts",
            params={"sort": "price_numeric_eur:desc"},
        )
        assert r.status_code == 200
        contracts = r.json()["contracts"]
        prices = [c["price_numeric_eur"] for c in contracts]
        assert prices == sorted(prices, reverse=True)
        assert prices[0] == 1_000_000.0  # contract 1001

    def test_sort_by_price_ascending(self, client):
        """First contract has the lowest price_numeric_eur."""
        r = client.get(
            "/api/contracts",
            params={"sort": "price_numeric_eur:asc"},
        )
        assert r.status_code == 200
        contracts = r.json()["contracts"]
        prices = [c["price_numeric_eur"] for c in contracts]
        assert prices == sorted(prices)
        assert prices[0] == 200_000.0  # contract 1003

    def test_sort_multi_column_applied(self, tie_client):
        """Two-column spec correctly orders equal-price contracts by secondary field."""
        r = tie_client.get(
            "/api/contracts",
            params={"sort": "price_numeric_eur:desc,published_date:asc"},
        )
        assert r.status_code == 200
        contracts = r.json()["contracts"]
        assert len(contracts) == 3
        # T001 (1M) first; then T002 (500k, Jan 2025) before T003 (500k, Jun 2025)
        assert contracts[0]["contract_id"] == "T001"
        assert contracts[1]["contract_id"] == "T002"
        assert contracts[2]["contract_id"] == "T003"

    def test_sort_by_scanned_subject_alphabetical(self, tie_client):
        """Scanned subject column supports alphabetical sort."""
        r = tie_client.get(
            "/api/contracts",
            params={"sort": "scanned_suggested_title:asc"},
        )
        assert r.status_code == 200
        contracts = r.json()["contracts"]
        assert [c["contract_id"] for c in contracts] == ["T002", "T003", "T001"]

    def test_sort_combined_with_filter(self, client):
        """Filter reduces the set; sort is applied to the filtered subset only."""
        r = client.get(
            "/api/contracts",
            params={
                "institutions": "Mesto Bratislava",
                "sort": "price_numeric_eur:desc",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        contracts = data["contracts"]
        assert contracts[0]["contract_id"] == "1001"  # 1 000 000
        assert contracts[1]["contract_id"] == "1002"  # 500 000

    def test_sort_pagination_stability(self, client):
        """Page 2 continues the same globally-sorted order — slicing happens after sort."""
        # Expected desc order: 1001(1M), 1004(750k), 1002(500k), 1005(300k), 1003(200k)
        r1 = client.get(
            "/api/contracts",
            params={"sort": "price_numeric_eur:desc", "page": 1, "page_size": 2},
        )
        r2 = client.get(
            "/api/contracts",
            params={"sort": "price_numeric_eur:desc", "page": 2, "page_size": 2},
        )
        page1_ids = [c["contract_id"] for c in r1.json()["contracts"]]
        page2_ids = [c["contract_id"] for c in r2.json()["contracts"]]
        assert page1_ids == ["1001", "1004"]
        assert page2_ids == ["1002", "1005"]

    def test_csv_export_respects_sort(self, client):
        """CSV rows arrive in the same order as the equivalent API response."""
        sort_param = "price_numeric_eur:desc"
        api_r = client.get("/api/contracts", params={"sort": sort_param})
        csv_r = client.get("/api/export/csv", params={"sort": sort_param})
        assert csv_r.status_code == 200
        api_ids = [c["contract_id"] for c in api_r.json()["contracts"]]
        csv_reader = csv.DictReader(io.StringIO(csv_r.text))
        csv_ids = [row["contract_id"] for row in csv_reader]
        assert api_ids == csv_ids

    def test_sort_invalid_field_ignored(self, client):
        """Unrecognised sort field does not cause 4xx/5xx; valid fields still applied."""
        r = client.get(
            "/api/contracts",
            params={"sort": "nonexistent_field:desc,price_numeric_eur:asc"},
        )
        assert r.status_code == 200
        contracts = r.json()["contracts"]
        prices = [c["price_numeric_eur"] for c in contracts]
        # Valid part of the spec (price asc) is still applied
        assert prices == sorted(prices)

    def test_sort_missing_param_deterministic(self, client):
        """Omitting sort returns a stable order across two successive identical requests."""
        r1 = client.get("/api/contracts")
        r2 = client.get("/api/contracts")
        ids1 = [c["contract_id"] for c in r1.json()["contracts"]]
        ids2 = [c["contract_id"] for c in r2.json()["contracts"]]
        assert ids1 == ids2

    def test_encode_filter_state_includes_sort(self):
        """encode_filter_state(fs, sort_spec=...) round-trips sort spec through URL params."""
        fs = FilterState(institutions=["Mesto Bratislava"])
        sort_spec = [("price_numeric_eur", "desc"), ("published_date", "asc")]
        encoded = encode_filter_state(fs, sort_spec=sort_spec)

        assert "sort" in encoded
        assert encoded["sort"] == "price_numeric_eur:desc,published_date:asc"
        assert encoded["institutions"] == "Mesto Bratislava"

        # parse_sort must be able to decode it back
        decoded: list = []
        for token in encoded["sort"].split(","):
            field, direction = token.split(":")
            decoded.append((field, direction))
        assert decoded == sort_spec


# ── Phase 6: Investigation Modes ─────────────────────────────────────


class TestBenchmarkPeerGroup:
    """Tests for Phase 6 benchmark peer-group endpoint."""

    def test_peers_excludes_self(self, client):
        """Peer group for Mesto Bratislava does not include itself."""
        r = client.get(
            "/api/benchmark/peers",
            params={"institution": "Mesto Bratislava", "min_contracts": 1},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["institution"] == "Mesto Bratislava"
        assert "Mesto Bratislava" not in data["peers"]
        assert len(data["peers"]) == 2

    def test_peers_min_contracts_filter(self, client):
        """min_contracts=2 excludes institutions with fewer contracts."""
        r = client.get(
            "/api/benchmark/peers",
            params={"institution": "Mesto Bratislava", "min_contracts": 2},
        )
        data = r.json()
        assert "Mesto Košice" in data["peers"]
        assert "Ministerstvo vnútra SR" not in data["peers"]

    def test_benchmark_min_contracts_filter(self, client):
        """Benchmark endpoint with min_contracts filters results."""
        r = client.get(
            "/api/benchmark",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice|Ministerstvo vnútra SR",
                "metric": "total_spend",
                "min_contracts": 2,
            },
        )
        assert r.status_code == 200
        data = r.json()
        names = [r["institution"] for r in data["results"]]
        assert "Ministerstvo vnútra SR" not in names
        assert "Mesto Bratislava" in names


class TestBenchmarkMultiMetric:
    """Tests for Phase 6 multi-metric benchmark comparison."""

    def test_multi_metric_compare(self, client):
        """Multi-metric comparison returns all requested metrics."""
        r = client.get(
            "/api/benchmark/compare",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice",
                "metrics": "total_spend,contract_count,direct_award_rate",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) == 2
        assert data["metrics"] == ["total_spend", "contract_count", "direct_award_rate"]
        ba = next(r for r in data["results"] if r["institution"] == "Mesto Bratislava")
        assert ba["total_spend"] == 1_500_000
        assert ba["contract_count"] == 2

    def test_multi_metric_comparison_metrics(self, client):
        """Comparison includes standard and advanced metrics."""
        r = client.get(
            "/api/benchmark/compare",
            params={
                "institutions": "Mesto Bratislava",
                "metrics": "total_spend,vendor_concentration,fragmentation_score",
            },
        )
        assert r.status_code == 200
        data = r.json()
        result = data["results"][0]
        assert "vendor_concentration" in result
        assert "fragmentation_score" in result


class TestTrendsEnhanced:
    """Tests for Phase 6 enhanced trends endpoint."""

    def test_trends_with_overlay(self, client):
        """Trends with overlay=true includes overlay dates."""
        r = client.get(
            "/api/trends",
            params={"granularity": "month", "metric": "total_spend", "overlay": "true"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "overlays" in data
        assert len(data["overlays"]) > 0
        assert "date" in data["overlays"][0]
        assert "label" in data["overlays"][0]

    def test_trends_without_overlay(self, client):
        """Trends without overlay param does not include overlays."""
        r = client.get(
            "/api/trends",
            params={"granularity": "month", "metric": "total_spend"},
        )
        data = r.json()
        assert "overlays" not in data

    def test_trends_quarterly(self, client):
        """Quarterly granularity returns Q-format periods."""
        r = client.get(
            "/api/trends",
            params={"granularity": "quarter"},
        )
        data = r.json()
        assert data["granularity"] == "quarter"
        for point in data["data"]:
            assert "-Q" in point["period"]


class TestRankingsEnhanced:
    """Tests for Phase 6 enhanced rankings endpoint."""

    def test_rankings_direct_award_rate(self, client):
        """Rankings by direct_award_rate works."""
        r = client.get(
            "/api/rankings",
            params={"entity": "institutions", "metric": "direct_award_rate"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["metric"] == "direct_award_rate"
        assert data["rankings"][0]["rank"] == 1
        values = [item["value"] for item in data["rankings"]]
        assert values == sorted(values, reverse=True)

    def test_rankings_vendor_concentration(self, client):
        """Rankings by vendor_concentration returns Herfindahl-type metric."""
        r = client.get(
            "/api/rankings",
            params={"entity": "institutions", "metric": "vendor_concentration"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["metric"] == "vendor_concentration"
        for item in data["rankings"]:
            assert 0.0 <= item["value"] <= 1.0

    def test_rankings_fragmentation_score(self, client):
        """Rankings by fragmentation_score works."""
        r = client.get(
            "/api/rankings",
            params={"entity": "institutions", "metric": "fragmentation_score"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["metric"] == "fragmentation_score"
        assert all(0.0 <= item["value"] <= 1.0 for item in data["rankings"])

    def test_rankings_with_filter(self, client):
        """Rankings respect filters."""
        r = client.get(
            "/api/rankings",
            params={
                "entity": "institutions",
                "metric": "total_spend",
                "categories": "construction",
            },
        )
        assert r.status_code == 200
        data = r.json()
        # Only institutions with construction contracts appear
        institutions = [item["institution"] for item in data["rankings"]]
        # Mestro Bratislava has construction, Mesto Košice has construction,
        # Ministerstvo vnútra SR has only services
        assert "Ministerstvo vnútra SR" not in institutions

    def test_rankings_vendors_with_filter(self, client):
        """Vendor rankings respect filters."""
        r = client.get(
            "/api/rankings",
            params={
                "entity": "vendors",
                "metric": "total_spend",
                "institutions": "Mesto Bratislava",
            },
        )
        assert r.status_code == 200
        data = r.json()
        vendors = [item["vendor"] for item in data["rankings"]]
        assert "STRABAG s.r.o." in vendors
        assert "T-Systems Slovakia s.r.o." in vendors
        # SecurCorp only serves Ministerstvo
        assert "SecurCorp a.s." not in vendors


class TestBenchmarkWithFilters:
    """Tests for benchmark endpoints with global filter support."""

    def test_benchmark_compare_with_date_filter(self, client):
        """Benchmark compare respects date_from filter."""
        # Only contracts from 2026 onward (1003=200k Košice, 1004=750k Ministerstvo, 1005=300k Košice)
        r = client.get(
            "/api/benchmark/compare",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice",
                "metrics": "total_spend,contract_count",
                "date_from": "2026-01-01",
            },
        )
        assert r.status_code == 200
        data = r.json()
        ba = next(r for r in data["results"] if r["institution"] == "Mesto Bratislava")
        ke = next(r for r in data["results"] if r["institution"] == "Mesto Košice")
        # Bratislava has no contracts from 2026 onward
        assert ba["total_spend"] == 0
        assert ba["contract_count"] == 0
        # Košice has 1003 + 1005
        assert ke["total_spend"] == 500_000
        assert ke["contract_count"] == 2

    def test_benchmark_compare_with_category_filter(self, client):
        """Benchmark compare respects category filter."""
        r = client.get(
            "/api/benchmark/compare",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice",
                "metrics": "total_spend",
                "categories": "construction",
            },
        )
        assert r.status_code == 200
        data = r.json()
        ba = next(r for r in data["results"] if r["institution"] == "Mesto Bratislava")
        ke = next(r for r in data["results"] if r["institution"] == "Mesto Košice")
        # Bratislava has 1 construction contract (1001=1M)
        assert ba["total_spend"] == 1_000_000
        # Košice has 1 construction contract (1005=300k)
        assert ke["total_spend"] == 300_000

    def test_benchmark_compare_without_filter(self, client):
        """Benchmark compare without filters uses all contracts (backwards compatible)."""
        r = client.get(
            "/api/benchmark/compare",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice",
                "metrics": "total_spend",
            },
        )
        assert r.status_code == 200
        data = r.json()
        ba = next(r for r in data["results"] if r["institution"] == "Mesto Bratislava")
        assert ba["total_spend"] == 1_500_000

    def test_benchmark_endpoint_with_category_filter(self, client):
        """Single-metric benchmark endpoint respects category filter."""
        r = client.get(
            "/api/benchmark",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice",
                "metric": "total_spend",
                "categories": "construction",
            },
        )
        assert r.status_code == 200
        data = r.json()
        ba = next(r for r in data["results"] if r["institution"] == "Mesto Bratislava")
        assert ba["value"] == 1_000_000

    def test_benchmark_peers_with_date_filter(self, client):
        """Peer group respects date filter."""
        # Only 2026 contracts: Košice has 2, Ministerstvo has 1
        r = client.get(
            "/api/benchmark/peers",
            params={
                "institution": "Mesto Košice",
                "min_contracts": 1,
                "date_from": "2026-01-01",
            },
        )
        assert r.status_code == 200
        data = r.json()
        # Ministerstvo has 1 contract in 2026
        assert "Ministerstvo vnútra SR" in data["peers"]
        # Bratislava has 0 contracts in 2026
        assert "Mesto Bratislava" not in data["peers"]

    def test_benchmark_peers_with_category_filter(self, client):
        """Peer group respects category filter."""
        r = client.get(
            "/api/benchmark/peers",
            params={
                "institution": "Mesto Bratislava",
                "min_contracts": 1,
                "categories": "construction",
            },
        )
        assert r.status_code == 200
        data = r.json()
        # Košice has construction contract (1005)
        assert "Mesto Košice" in data["peers"]
        # Ministerstvo has no construction contracts
        assert "Ministerstvo vnútra SR" not in data["peers"]

    def test_benchmark_compare_with_value_range_filter(self, client):
        """Benchmark compare respects value_min and value_max filters."""
        # Only contracts >= 500k: 1001=1M, 1002=500k, 1004=750k
        r = client.get(
            "/api/benchmark/compare",
            params={
                "institutions": "Mesto Bratislava|Mesto Košice",
                "metrics": "total_spend,contract_count",
                "value_min": "500000",
            },
        )
        assert r.status_code == 200
        data = r.json()
        ba = next(r for r in data["results"] if r["institution"] == "Mesto Bratislava")
        ke = next(r for r in data["results"] if r["institution"] == "Mesto Košice")
        # Bratislava: 1001(1M) + 1002(500k)
        assert ba["total_spend"] == 1_500_000
        assert ba["contract_count"] == 2
        # Košice: no contracts >= 500k
        assert ke["total_spend"] == 0
        assert ke["contract_count"] == 0
