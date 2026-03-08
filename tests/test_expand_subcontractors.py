import json
from pathlib import Path

from scripts.expand_subcontractors import expand_contracts_by_subcontractors


def test_expand_subcontractors_appends_only_new_rows(tmp_path):
    input_path = tmp_path / "contracts.json"
    output_path = tmp_path / "contracts_subcontractors.json"

    input_payload = [
        {
            "contract_id": "A1",
            "scanned_subcontractors": [{"name": "Sub One", "ico": "12345678"}],
        },
        {
            "contract_id": "A2",
            "scanned_subcontractors": [{"name": "Sub Two", "ico": "87654321"}],
        },
    ]
    input_path.write_text(json.dumps(input_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    existing_payload = [
        {
            "contract_id": "A1",
            "subcontractor": "Sub One",
            "ico_subcontractor": "12345678",
        }
    ]
    output_path.write_text(
        json.dumps(existing_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    stats = expand_contracts_by_subcontractors(
        input_path=str(input_path),
        output_path=str(output_path),
        source_field="scanned_subcontractors",
    )

    assert stats["rows_existing"] == 1
    assert stats["rows_added"] == 1
    assert stats["rows_written"] == 2

    rows = json.loads(Path(output_path).read_text(encoding="utf-8"))
    assert len(rows) == 2
    assert rows[0]["contract_id"] == "A1"
    assert rows[1]["contract_id"] == "A2"
