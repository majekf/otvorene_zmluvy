"""
Unit tests for GovLens Pydantic data models (Phase 0).
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import (  # noqa: E402
    AggregationResult,
    Contract,
    FilterState,
    Institution,
    Vendor,
)


# ── Contract ────────────────────────────────────────────────────────


class TestContractModelDefaults:
    """Task 0.1 / 0.5 — Contract default values for new GovLens fields."""

    def test_defaults_category(self):
        contract = Contract()
        assert contract.category == "not_decided"

    def test_defaults_pdf_text_summary(self):
        contract = Contract()
        assert contract.pdf_text_summary == "not_summarized"

    def test_defaults_award_type(self):
        contract = Contract()
        assert contract.award_type == "unknown"

    def test_all_optional_fields_are_none(self):
        """Every non-enrichment field defaults to None."""
        contract = Contract()
        assert contract.published_date is None
        assert contract.contract_title is None
        assert contract.price_numeric_eur is None
        assert contract.supplier is None
        assert contract.buyer is None
        assert contract.contract_url is None
        assert contract.ico_buyer is None
        assert contract.pdf_text is None


class TestContractModelValidation:
    """Task 0.1 — input validation."""

    def test_invalid_price_type_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Contract(price_numeric_eur="not_a_number")

    def test_valid_price_accepted(self):
        c = Contract(price_numeric_eur=28978.27)
        assert c.price_numeric_eur == 28978.27

    def test_extra_fields_allowed(self):
        """model_config extra='allow' lets unknown keys pass through."""
        c = Contract(unknown_future_field="hello")
        assert c.unknown_future_field == "hello"  # type: ignore[attr-defined]


class TestContractSerialization:
    """Round-trip through dict and JSON."""

    def test_model_dump_contains_new_fields(self):
        c = Contract(contract_id="123")
        data = c.model_dump()
        assert isinstance(data, dict)
        assert data["contract_id"] == "123"
        assert data["category"] == "not_decided"
        assert data["pdf_text_summary"] == "not_summarized"
        assert data["award_type"] == "unknown"

    def test_json_round_trip(self):
        c = Contract(contract_id="456", category="legal_services")
        json_str = c.model_dump_json()
        data = json.loads(json_str)
        c2 = Contract(**data)
        assert c2.contract_id == "456"
        assert c2.category == "legal_services"


class TestContractFromScraperDict:
    """Create a Contract from a dict shaped like scraper NDJSON output."""

    SCRAPER_ROW = {
        "published_day": "1.",
        "published_month": "Marec",
        "published_year": "2026",
        "published_date": "2026-03-01",
        "contract_title": "rámcová dohoda",
        "contract_number": "2026/22/E/CI",
        "price_raw": "28 978,27 €",
        "price_numeric_eur": 28978.27,
        "supplier": "Test Supplier",
        "buyer": "Test Buyer",
        "contract_url": "https://www.crz.gov.sk/zmluva/12048046/",
        "contract_id": "12048046",
        "scraped_at": "2026-03-01T10:30:45Z",
        "category": "not_decided",
        "pdf_text_summary": "not_summarized",
        "award_type": "unknown",
    }

    def test_from_scraper_dict(self):
        c = Contract(**self.SCRAPER_ROW)
        assert c.published_date == "2026-03-01"
        assert c.price_numeric_eur == 28978.27
        assert c.category == "not_decided"

    def test_overridden_category(self):
        row = {**self.SCRAPER_ROW, "category": "construction"}
        c = Contract(**row)
        assert c.category == "construction"


# ── FilterState ─────────────────────────────────────────────────────


class TestFilterStateDefaults:
    """Task 0.5 — FilterState default behaviour."""

    def test_all_none_by_default(self):
        fs = FilterState()
        assert fs.institutions is None
        assert fs.date_from is None
        assert fs.date_to is None
        assert fs.categories is None
        assert fs.vendors is None
        assert fs.icos is None
        assert fs.value_min is None
        assert fs.value_max is None
        assert fs.award_types is None
        assert fs.text_search is None

    def test_with_populated_values(self):
        fs = FilterState(
            institutions=["Mesto Bratislava"],
            date_from="2024-01-01",
            date_to="2026-12-31",
            value_min=1000.0,
            value_max=500000.0,
        )
        assert fs.institutions == ["Mesto Bratislava"]
        assert fs.value_min == 1000.0

    def test_serialization_round_trip(self):
        fs = FilterState(
            institutions=["A", "B"],
            text_search="construction",
        )
        data = fs.model_dump()
        fs2 = FilterState(**data)
        assert fs2.institutions == ["A", "B"]
        assert fs2.text_search == "construction"


# ── AggregationResult ───────────────────────────────────────────────


class TestAggregationResult:

    def test_defaults(self):
        r = AggregationResult(group_key="category", group_value="legal")
        assert r.contract_count == 0
        assert r.total_spend == 0.0
        assert r.avg_value == 0.0
        assert r.max_value == 0.0

    def test_with_values(self):
        r = AggregationResult(
            group_key="vendor",
            group_value="STRABAG s.r.o.",
            contract_count=15,
            total_spend=5_000_000.0,
            avg_value=333_333.33,
            max_value=1_000_000.0,
        )
        assert r.contract_count == 15
        assert r.total_spend == 5_000_000.0


# ── Institution / Vendor ────────────────────────────────────────────


class TestInstitutionModel:

    def test_defaults(self):
        i = Institution(name="Mesto Bratislava")
        assert i.contract_count == 0
        assert i.total_spend == 0.0
        assert i.ico is None

    def test_with_data(self):
        i = Institution(
            name="Mesto Bratislava",
            ico="00603481",
            contract_count=150,
            total_spend=25_000_000.0,
        )
        assert i.name == "Mesto Bratislava"
        assert i.ico == "00603481"


class TestVendorModel:

    def test_defaults(self):
        v = Vendor(name="STRABAG s.r.o.")
        assert v.contract_count == 0
        assert v.total_spend == 0.0

    def test_with_data(self):
        v = Vendor(
            name="STRABAG s.r.o.",
            ico="31355315",
            contract_count=50,
            total_spend=15_000_000.0,
        )
        assert v.ico == "31355315"


# ── Sample data file ────────────────────────────────────────────────


class TestSampleContractsFile:
    """Validate that data/sample_contracts.json is well-formed."""

    SAMPLE_PATH = Path(__file__).parent.parent / "data" / "sample_contracts.json"

    def test_file_exists(self):
        assert self.SAMPLE_PATH.exists(), f"{self.SAMPLE_PATH} not found"

    def test_loads_as_json_array(self):
        data = json.loads(self.SAMPLE_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 20, "Expected at least 20 seed records"

    def test_records_validate_as_contracts(self):
        data = json.loads(self.SAMPLE_PATH.read_text(encoding="utf-8"))
        for i, record in enumerate(data):
            c = Contract(**record)
            assert c.category is not None, f"Record {i} missing category"
            assert c.pdf_text_summary is not None, f"Record {i} missing pdf_text_summary"
            assert c.award_type is not None, f"Record {i} missing award_type"

    def test_records_have_required_fields(self):
        data = json.loads(self.SAMPLE_PATH.read_text(encoding="utf-8"))
        for i, record in enumerate(data):
            assert "contract_id" in record, f"Record {i} missing contract_id"
            assert "buyer" in record or "buyer_detail" in record, (
                f"Record {i} missing buyer"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
