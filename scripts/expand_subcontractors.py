#!/usr/bin/env python
"""Expand contracts into one row per subcontractor.

Example:
- 1 contract with 2 subcontractors -> 2 output records
- Adds `subcontractor` and `ico_subcontractor` fields to each output record
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_subcontractor_item(item: Any) -> Optional[Dict[str, Optional[str]]]:
    """Normalize one subcontractor item to {subcontractor, ico_subcontractor}."""
    if isinstance(item, str):
        name = item.strip()
        if not name:
            return None
        return {"subcontractor": name, "ico_subcontractor": None}

    if not isinstance(item, dict):
        return None

    name_keys = ["name", "subcontractor", "nazov", "company", "supplier"]
    ico_keys = [
        "ico",
        "ico_subcontractor",
        "ico_subdodavatela",
        "subcontractor_ico",
        "IČO",
        "ICO",
    ]

    name: Optional[str] = None
    ico: Optional[str] = None

    for key in name_keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            name = value.strip()
            break

    for key in ico_keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            ico = value.strip()
            break
        if isinstance(value, int):
            ico = str(value)
            break

    if not name and not ico:
        return None

    return {"subcontractor": name, "ico_subcontractor": ico}


def _extract_subcontractors(value: Any) -> List[Dict[str, Optional[str]]]:
    """Extract subcontractor entries from the source field value."""
    if value is None:
        return []

    if isinstance(value, list):
        out: List[Dict[str, Optional[str]]] = []
        for item in value:
            normalized = _normalize_subcontractor_item(item)
            if normalized:
                out.append(normalized)
        return out

    if isinstance(value, dict):
        normalized = _normalize_subcontractor_item(value)
        return [normalized] if normalized else []

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []

        # Try JSON first for values like '[{"name":...,"ico":...}]'.
        if text.startswith("[") or text.startswith("{"):
            try:
                parsed = json.loads(text)
                return _extract_subcontractors(parsed)
            except json.JSONDecodeError:
                pass

        # Fallback: split by line/semicolon/comma into names only.
        parts = [p.strip() for p in text.replace("\n", ";").split(";")]
        if len(parts) == 1:
            parts = [p.strip() for p in text.split(",")]

        out = []
        for part in parts:
            if part:
                out.append({"subcontractor": part, "ico_subcontractor": None})
        return out

    return []


def expand_contracts_by_subcontractors(
    input_path: str,
    output_path: str,
    source_field: str = "scanned_subcontractors",
) -> Dict[str, int]:
    """Create expanded JSON where each subcontractor gets its own agreement row."""
    in_file = Path(input_path)
    if not in_file.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_path}")

    contracts = json.loads(in_file.read_text(encoding="utf-8"))
    if not isinstance(contracts, list):
        raise ValueError("Input JSON must contain a top-level list")

    expanded: List[Dict[str, Any]] = []
    contracts_with_subcontractors = 0

    for contract in contracts:
        if not isinstance(contract, dict):
            continue

        subs = _extract_subcontractors(contract.get(source_field))
        if not subs:
            continue

        contracts_with_subcontractors += 1
        for sub in subs:
            row = dict(contract)
            row["subcontractor"] = sub.get("subcontractor")
            row["ico_subcontractor"] = sub.get("ico_subcontractor")
            expanded.append(row)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        json.dumps(expanded, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "contracts_total": len(contracts),
        "contracts_with_subcontractors": contracts_with_subcontractors,
        "rows_written": len(expanded),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Expand agreements with subcontractors into one agreement row per "
            "subcontractor and add subcontractor/ico_subcontractor fields"
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="data/contracts.json",
        help="Input contracts JSON (default: data/contracts.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/contracts_subcontractors.json",
        help="Output expanded JSON (default: data/contracts_subcontractors.json)",
    )
    parser.add_argument(
        "--source-field",
        type=str,
        default="scanned_subcontractors",
        help="Field containing subcontractor data (default: scanned_subcontractors)",
    )

    args = parser.parse_args()

    stats = expand_contracts_by_subcontractors(
        input_path=args.input,
        output_path=args.output,
        source_field=args.source_field,
    )

    print(
        "Expanded subcontractor dataset created: "
        f"contracts_total={stats['contracts_total']}, "
        f"contracts_with_subcontractors={stats['contracts_with_subcontractors']}, "
        f"rows_written={stats['rows_written']}, "
        f"output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
