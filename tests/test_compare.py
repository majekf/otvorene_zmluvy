"""
Unit tests for Phase 9 — Compare endpoint (Contracts vs Subcontractors).

Tests cover: /api/compare/aggregations endpoint (merged response shape,
filter pass-through, missing sub_store graceful fallback, grouping options).
"""

import pytest
from fastapi.testclient import TestClient

from src.api import app, get_store, get_sub_store
from src.engine import DataStore

# ── Test data ────────────────────────────────────────────────────────

CONTRACT_RECORDS = [
    {
        "contract_id": "C1",
        "contract_title": "Oprava ciest",
        "buyer": "Mesto Bratislava",
        "supplier": "STRABAG s.r.o.",
        "price_numeric_eur": 1_000_000.0,
        "published_date": "2025-12-01",
        "scanned_service_type": "construction",
        "award_type": "direct_award",
        "ico_buyer": "00001001",
        "ico_supplier": "00002001",
    },
    {
        "contract_id": "C2",
        "contract_title": "IT systém",
        "buyer": "Mesto Bratislava",
        "supplier": "T-Systems Slovakia s.r.o.",
        "price_numeric_eur": 500_000.0,
        "published_date": "2025-12-15",
        "scanned_service_type": "IT",
        "award_type": "open_tender",
        "ico_buyer": "00001001",
        "ico_supplier": "00002002",
    },
    {
        "contract_id": "C3",
        "contract_title": "Dodávka potravín",
        "buyer": "Mesto Košice",
        "supplier": "FoodCorp s.r.o.",
        "price_numeric_eur": 200_000.0,
        "published_date": "2026-01-10",
        "scanned_service_type": "construction",
        "award_type": "direct_award",
        "ico_buyer": "00001002",
        "ico_supplier": "00002003",
    },
]

# Subcontractor records: same structure but with subcontractor→supplier remapping
SUBCONTRACTOR_RECORDS = [
    {
        "contract_id": "C1",
        "contract_title": "Oprava ciest",
        "buyer": "Mesto Bratislava",
        "supplier": "SubCompany A s.r.o.",  # Already remapped
        "price_numeric_eur": 600_000.0,
        "published_date": "2025-12-01",
        "scanned_service_type": "construction",
        "award_type": "direct_award",
        "ico_buyer": "00001001",
        "ico_supplier": "00003001",
    },
    {
        "contract_id": "C2",
        "contract_title": "IT systém",
        "buyer": "Mesto Bratislava",
        "supplier": "SubCompany B s.r.o.",  # Already remapped
        "price_numeric_eur": 300_000.0,
        "published_date": "2025-12-15",
        "scanned_service_type": "IT",
        "award_type": "open_tender",
        "ico_buyer": "00001001",
        "ico_supplier": "00003002",
    },
]


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def contract_store():
    ds = DataStore()
    ds.load_from_list(CONTRACT_RECORDS)
    return ds


@pytest.fixture
def sub_store():
    ds = DataStore()
    ds.load_from_list(SUBCONTRACTOR_RECORDS)
    return ds


@pytest.fixture
def client_with_sub(contract_store, sub_store):
    """FastAPI test client with both stores."""
    app.dependency_overrides[get_store] = lambda: contract_store
    app.dependency_overrides[get_sub_store] = lambda: sub_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_sub(contract_store):
    """FastAPI test client without subcontractor store."""
    app.dependency_overrides[get_store] = lambda: contract_store
    app.dependency_overrides[get_sub_store] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Tests ────────────────────────────────────────────────────────────


class TestCompareAggregations:
    """Tests for /api/compare/aggregations endpoint."""

    def test_returns_200(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations")
        assert r.status_code == 200

    def test_response_shape(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations")
        data = r.json()
        assert "group_by" in data
        assert "data" in data
        assert "contracts_summary" in data
        assert "subcontractors_summary" in data
        assert "has_subcontractors" in data
        assert data["has_subcontractors"] is True

    def test_default_group_by_category(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations")
        data = r.json()
        assert data["group_by"] == "category"

    def test_merged_data_has_both_columns(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations")
        data = r.json()
        rows = data["data"]
        assert len(rows) > 0
        row = rows[0]
        assert "group_value" in row
        assert "contracts_total_spend" in row
        assert "subcontractors_total_spend" in row
        assert "contracts_contract_count" in row
        assert "subcontractors_contract_count" in row
        assert "contracts_avg_value" in row
        assert "subcontractors_avg_value" in row

    def test_contracts_summary_totals(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations")
        data = r.json()
        cs = data["contracts_summary"]
        assert cs["contract_count"] == 3
        assert cs["total_spend"] == pytest.approx(1_700_000.0)

    def test_subcontractors_summary_totals(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations")
        data = r.json()
        ss = data["subcontractors_summary"]
        assert ss["contract_count"] == 2
        assert ss["total_spend"] == pytest.approx(900_000.0)

    def test_group_by_supplier(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations?group_by=supplier")
        data = r.json()
        assert data["group_by"] == "supplier"
        rows = data["data"]
        # Should have distinct supplier names from both stores
        names = [row["group_value"] for row in rows]
        assert len(names) > 0

    def test_group_by_buyer(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations?group_by=buyer")
        data = r.json()
        assert data["group_by"] == "buyer"
        rows = data["data"]
        buyers = [row["group_value"] for row in rows]
        assert "Mesto Bratislava" in buyers

    def test_filter_pass_through(self, client_with_sub):
        """Filters should apply to both stores."""
        r = client_with_sub.get("/api/compare/aggregations?scanned_service_types=IT")
        data = r.json()
        cs = data["contracts_summary"]
        ss = data["subcontractors_summary"]
        # Only IT category contracts
        assert cs["contract_count"] == 1
        assert cs["total_spend"] == pytest.approx(500_000.0)
        assert ss["contract_count"] == 1
        assert ss["total_spend"] == pytest.approx(300_000.0)

    def test_date_filter_pass_through(self, client_with_sub):
        """Date filters should restrict both stores."""
        r = client_with_sub.get("/api/compare/aggregations?date_from=2026-01-01")
        data = r.json()
        cs = data["contracts_summary"]
        # Only one contract from Jan 2026
        assert cs["contract_count"] == 1

    def test_sorted_by_contracts_total_spend(self, client_with_sub):
        r = client_with_sub.get("/api/compare/aggregations")
        data = r.json()
        rows = data["data"]
        if len(rows) >= 2:
            assert rows[0]["contracts_total_spend"] >= rows[1]["contracts_total_spend"]

    def test_groups_include_subcontractor_only(self, client_with_sub):
        """Groups that only exist in subcontractors should still appear."""
        # Both stores have construction and IT, so all should be present
        r = client_with_sub.get("/api/compare/aggregations")
        data = r.json()
        values = {row["group_value"] for row in data["data"]}
        assert "construction" in values
        assert "IT" in values


class TestCompareNoSubStore:
    """Tests when subcontractors data is not loaded."""

    def test_returns_200_without_sub_store(self, client_no_sub):
        r = client_no_sub.get("/api/compare/aggregations")
        assert r.status_code == 200

    def test_has_subcontractors_false(self, client_no_sub):
        r = client_no_sub.get("/api/compare/aggregations")
        data = r.json()
        assert data["has_subcontractors"] is False

    def test_subcontractors_summary_zeroed(self, client_no_sub):
        r = client_no_sub.get("/api/compare/aggregations")
        data = r.json()
        ss = data["subcontractors_summary"]
        assert ss["total_spend"] == 0
        assert ss["contract_count"] == 0

    def test_contracts_data_still_present(self, client_no_sub):
        r = client_no_sub.get("/api/compare/aggregations")
        data = r.json()
        assert len(data["data"]) > 0
        # Only contract values populated
        for row in data["data"]:
            assert row["subcontractors_total_spend"] == 0
            assert row["contracts_total_spend"] >= 0


class TestSubStoreDataTransformation:
    """Test that subcontractor→supplier field remapping works correctly."""

    def test_remap_subcontractor_fields(self):
        """Simulate the lifespan data transformation logic."""
        raw_records = [
            {
                "contract_id": "X1",
                "buyer": "Test Buyer",
                "supplier": "Original Supplier",
                "ico_supplier": "ORIG_ICO",
                "subcontractor": "SubCo Ltd",
                "ico_subcontractor": "SUB_ICO",
                "price_numeric_eur": 100_000.0,
                "published_date": "2025-06-01",
                "scanned_service_type": "construction",
            }
        ]
        # Apply the same transformation as in lifespan
        for record in raw_records:
            if "subcontractor" in record:
                record["supplier"] = record["subcontractor"]
            if "ico_subcontractor" in record:
                record["ico_supplier"] = record["ico_subcontractor"]

        ds = DataStore()
        ds.load_from_list(raw_records)

        # Verify the DataStore now sees SubCo as the "supplier"
        assert ds.count == 1
        contract = ds.contracts[0]
        assert contract.supplier == "SubCo Ltd"
        assert contract.ico_supplier == "SUB_ICO"

    def test_remap_preserves_other_fields(self):
        """Other fields like buyer, price, etc. should be untouched."""
        raw_records = [
            {
                "contract_id": "X2",
                "buyer": "Test Buyer",
                "supplier": "Original Supplier",
                "subcontractor": "SubCo Ltd",
                "ico_subcontractor": "SUB_ICO",
                "price_numeric_eur": 250_000.0,
                "published_date": "2025-07-01",
                "scanned_service_type": "IT",
            }
        ]
        for record in raw_records:
            if "subcontractor" in record:
                record["supplier"] = record["subcontractor"]
            if "ico_subcontractor" in record:
                record["ico_supplier"] = record["ico_subcontractor"]

        ds = DataStore()
        ds.load_from_list(raw_records)
        contract = ds.contracts[0]
        assert contract.buyer == "Test Buyer"
        assert contract.price_numeric_eur == 250_000.0
        assert getattr(contract, "scanned_service_type", None) == "IT"

    def test_engine_aggregation_uses_remapped_vendor(self):
        """Aggregation by supplier should use the remapped subcontractor name."""
        records = [
            {
                "contract_id": "X3",
                "buyer": "Buyer A",
                "supplier": "SubCo Alpha",
                "ico_supplier": "ICO_A",
                "price_numeric_eur": 100_000.0,
                "published_date": "2025-06-01",
                "scanned_service_type": "construction",
            },
            {
                "contract_id": "X4",
                "buyer": "Buyer A",
                "supplier": "SubCo Alpha",
                "ico_supplier": "ICO_A",
                "price_numeric_eur": 200_000.0,
                "published_date": "2025-07-01",
                "scanned_service_type": "construction",
            },
            {
                "contract_id": "X5",
                "buyer": "Buyer B",
                "supplier": "SubCo Beta",
                "ico_supplier": "ICO_B",
                "price_numeric_eur": 50_000.0,
                "published_date": "2025-08-01",
                "scanned_service_type": "IT",
            },
        ]
        ds = DataStore()
        ds.load_from_list(records)

        groups = ds.group_by("supplier")
        assert "SubCo Alpha" in groups
        assert "SubCo Beta" in groups
        assert len(groups["SubCo Alpha"]) == 2
        assert len(groups["SubCo Beta"]) == 1

        vendors = ds.vendors()
        vendor_names = [v.name for v in vendors]
        assert "SubCo Alpha" in vendor_names
        assert "SubCo Beta" in vendor_names
