#!/usr/bin/env python
"""
Migration script — Convert NDJSON scraper output to contracts.json
(JSON array) and backfill fields required by GovLens.

Usage:
    python scripts/migrate_ndjson.py -i out.ndjson -o data/contracts.json
    python scripts/migrate_ndjson.py -i out.ndjson              # default output: data/contracts.json
"""

import argparse
import json
import sys
from pathlib import Path

# Fields that must exist on every record with their default values
DEFAULT_FIELDS = {
    "category": "not_decided",
    "pdf_text_summary": "not_summarized",
    "award_type": "unknown",
}


def migrate_ndjson_to_json(input_path: str, output_path: str) -> int:
    """
    Read an NDJSON file (one JSON object per line), add any missing
    GovLens fields with sensible defaults, and write the result as a
    single JSON array.

    Args:
        input_path:  Path to the source NDJSON file.
        output_path: Path where the JSON array will be written.

    Returns:
        Number of records successfully processed.
    """
    records: list = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                # Backfill missing fields — keep existing values intact
                for field, default_value in DEFAULT_FIELDS.items():
                    if field not in record:
                        record[field] = default_value
                records.append(record)
            except json.JSONDecodeError as e:
                print(
                    f"Warning: Skipping line {line_num}: {e}",
                    file=sys.stderr,
                )

    # Ensure the output directory exists
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate NDJSON scraper output to GovLens contracts.json format. "
            "Adds missing fields (category, pdf_text_summary, award_type) with "
            "placeholder defaults and converts to a JSON array."
        ),
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Input NDJSON file path",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/contracts.json",
        help="Output JSON file path (default: data/contracts.json)",
    )

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    count = migrate_ndjson_to_json(args.input, args.output)
    print(f"Migrated {count} records → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
