"""
Unit tests for Phase 7 — CSV and PDF exports.

Tests cover: CSV content and headers, CSV with filters, and PDF export.
"""

import csv
import io

import pytest
from fastapi.testclient import TestClient

from src.api import app, get_store
from src.engine import DataStore


# ── Test data ────────────────────────────────────────────────────────

SMALL_RECORDS = [
    {
        "contract_id": "E001",
        "contract_title": "Oprava ciest",
        "buyer": "Mesto Bratislava",
        "supplier": "STRABAG s.r.o.",
        "price_numeric_eur": 1_000_000.0,
        "published_date": "2025-12-01",
        "category": "construction",
        "award_type": "direct_award",
        "contract_url": "https://www.crz.gov.sk/zmluva/E001/",
    },
    {
        "contract_id": "E002",
        "contract_title": "IT systém",
        "buyer": "Mesto Bratislava",
        "supplier": "T-Systems s.r.o.",
        "price_numeric_eur": 500_000.0,
        "published_date": "2025-12-15",
        "category": "IT",
        "award_type": "open_tender",
        "contract_url": "https://www.crz.gov.sk/zmluva/E002/",
    },
    {
        "contract_id": "E003",
        "contract_title": "Potraviny",
        "buyer": "Mesto Košice",
        "supplier": "FoodCo s.r.o.",
        "price_numeric_eur": 200_000.0,
        "published_date": "2026-01-10",
        "category": "supplies",
        "award_type": "direct_award",
        "contract_url": "https://www.crz.gov.sk/zmluva/E003/",
    },
]


@pytest.fixture
def test_store():
    ds = DataStore()
    ds.load_from_list(SMALL_RECORDS)
    return ds


@pytest.fixture
def client(test_store):
    app.dependency_overrides[get_store] = lambda: test_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── CSV export ───────────────────────────────────────────────────────


class TestCSVExport:
    """Tests for CSV export content and filtering."""

    def test_csv_export_content(self, client):
        """CSV has correct headers and row count."""
        r = client.get("/api/export/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        assert len(rows) == 3

        # Check expected headers
        expected_headers = {
            "contract_id", "contract_title", "buyer", "supplier",
            "price_numeric_eur", "published_date", "category",
            "award_type", "contract_url",
        }
        assert set(reader.fieldnames or []) == expected_headers

    def test_csv_export_respects_filters(self, client):
        """Only filtered contracts appear in CSV."""
        r = client.get(
            "/api/export/csv",
            params={"institutions": "Mesto Bratislava"},
        )
        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        assert len(rows) == 2
        assert all(row["buyer"] == "Mesto Bratislava" for row in rows)


# ── PDF export ───────────────────────────────────────────────────────


class TestPDFExport:
    """Tests for PDF export endpoint."""

    def test_pdf_export_returns_pdf(self, client):
        """Response Content-Type is application/pdf."""
        r = client.get("/api/export/pdf")
        assert r.status_code == 200
        assert "application/pdf" in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]
        # PDF magic bytes: %PDF-
        assert r.content[:5] == b"%PDF-"

    def test_pdf_export_respects_filters(self, client):
        """PDF export with filter succeeds and returns valid PDF."""
        r = client.get(
            "/api/export/pdf",
            params={"institutions": "Mesto Košice"},
        )
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        # The file should be non-trivially sized (has at least a header and table)
        assert len(r.content) > 500

    def test_pdf_export_with_sort(self, client):
        """PDF export with sort parameter succeeds."""
        r = client.get(
            "/api/export/pdf",
            params={"sort": "price_numeric_eur:desc"},
        )
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
