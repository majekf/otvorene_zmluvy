"""
Unit tests for the NDJSON → JSON migration script (Phase 0 — task 0.4).
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Make the scripts/ package importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from migrate_ndjson import migrate_ndjson_to_json  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────

SAMPLE_RECORDS = [
    {
        "contract_id": "12048046",
        "contract_title": "rámcová dohoda",
        "price_numeric_eur": 28978.27,
        "supplier": "Liptovské pekárne",
        "buyer": "Liptovská nemocnica",
        "contract_url": "https://www.crz.gov.sk/zmluva/12048046/",
        "scraped_at": "2026-03-01T10:30:45Z",
    },
    {
        "contract_id": "12048044",
        "contract_title": "Zmluva o spolupráci",
        "price_numeric_eur": 0.0,
        "supplier": "PD Hrušov",
        "buyer": "Obec Báb",
        "contract_url": "https://www.crz.gov.sk/zmluva/12048044/",
        "scraped_at": "2026-03-01T10:30:46Z",
    },
]


def _write_ndjson(path: str, records=None):
    """Write records as NDJSON."""
    if records is None:
        records = SAMPLE_RECORDS
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ── Tests ────────────────────────────────────────────────────────────


class TestMigrateAddsFields:
    """Migration must backfill category, pdf_text_summary, award_type."""

    def test_adds_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            for rec in data:
                assert rec["category"] == "not_decided"

    def test_adds_pdf_text_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            for rec in data:
                assert rec["pdf_text_summary"] == "not_summarized"

    def test_adds_award_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            for rec in data:
                assert rec["award_type"] == "unknown"


class TestMigratePreservesData:
    """Existing fields must survive migration unchanged."""

    def test_preserves_contract_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            assert data[0]["contract_id"] == "12048046"
            assert data[1]["contract_id"] == "12048044"

    def test_preserves_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            assert data[0]["price_numeric_eur"] == 28978.27
            assert data[1]["price_numeric_eur"] == 0.0

    def test_preserves_supplier_and_buyer(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            assert data[0]["supplier"] == "Liptovské pekárne"
            assert data[1]["buyer"] == "Obec Báb"


class TestMigrateDoesNotOverwrite:
    """If new fields already exist in source, keep the original values."""

    def test_preserves_existing_category(self):
        records = [{"contract_id": "1", "category": "construction"}]
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp, records)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            assert data[0]["category"] == "construction"

    def test_preserves_existing_award_type(self):
        records = [{"contract_id": "2", "award_type": "tendered"}]
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp, records)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            assert data[0]["award_type"] == "tendered"

    def test_preserves_existing_summary(self):
        records = [
            {
                "contract_id": "3",
                "pdf_text_summary": "A building contract for a hospital.",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp, records)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            assert data[0]["pdf_text_summary"] == "A building contract for a hospital."


class TestMigrateOutputFormat:
    """Output must be a proper JSON array file."""

    def test_output_is_json_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            data = json.loads(Path(out).read_text("utf-8"))
            assert isinstance(data, list)

    def test_correct_record_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            _write_ndjson(inp)
            count = migrate_ndjson_to_json(inp, out)
            assert count == 2
            data = json.loads(Path(out).read_text("utf-8"))
            assert len(data) == 2

    def test_empty_input_produces_empty_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            Path(inp).write_text("")
            count = migrate_ndjson_to_json(inp, out)
            assert count == 0
            data = json.loads(Path(out).read_text("utf-8"))
            assert data == []


class TestMigrateEdgeCases:

    def test_skips_invalid_json_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            with open(inp, "w") as f:
                f.write('{"valid": true}\n')
                f.write("NOT VALID JSON\n")
                f.write('{"also_valid": true}\n')
            count = migrate_ndjson_to_json(inp, out)
            assert count == 2

    def test_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "out.json")
            with open(inp, "w") as f:
                f.write('{"a": 1}\n')
                f.write("\n")
                f.write("   \n")
                f.write('{"b": 2}\n')
            count = migrate_ndjson_to_json(inp, out)
            assert count == 2

    def test_creates_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = str(Path(tmp) / "in.ndjson")
            out = str(Path(tmp) / "sub" / "deep" / "out.json")
            _write_ndjson(inp)
            migrate_ndjson_to_json(inp, out)
            assert Path(out).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
