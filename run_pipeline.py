#!/usr/bin/env python
"""Run full GovLens data pipeline in one command.

Pipeline steps:
1) Scrape CRZ contracts and PDFs (`scrape_crz.py`)
2) Migrate scraper output into `contracts.json` (`scripts/migrate_ndjson.py`)
3) Enrich contracts with OpenAI extracted scanned_* fields (`extract_api_chat.py`)
"""

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List


def _run_step(step_name: str, args: List[str]) -> None:
    """Run one subprocess step, streaming output and failing fast on error."""
    printable = " ".join(shlex.quote(a) for a in args)
    print(f"\n=== {step_name} ===")
    print(f"$ {printable}")

    result = subprocess.run(args, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{step_name} failed with exit code {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run scraping + migration + OpenAI analysis in one script"
    )

    # Scraper settings
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument(
        "--max-contracts",
        type=int,
        default=None,
        help="Maximum number of contracts/files to scrape across all pages",
    )
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--min-price", type=float, default=None)
    parser.add_argument("--max-price", type=float, default=None)
    parser.add_argument("--user-agent", type=str, default=None)
    parser.add_argument("--pdf-dir", type=str, default="data/pdfs")
    parser.add_argument("--log-level", type=str, default="INFO")

    # Pipeline paths
    parser.add_argument(
        "--scrape-out",
        type=str,
        default="out.ndjson",
        help="Temporary output from scraper (JSON array supported)",
    )
    parser.add_argument(
        "--contracts-json",
        type=str,
        default="data/contracts.json",
        help="Final contracts JSON path after migration",
    )

    # OpenAI analysis settings
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument(
        "--no-skip-processed",
        action="store_true",
        help="Re-analyze already scanned contracts",
    )
    parser.add_argument(
        "--ignore-existing-pdf-text",
        action="store_true",
        help="Force extract_api_chat to re-read text from PDFs",
    )

    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    python_exec = sys.executable

    scrape_script = root / "scrape_crz.py"
    migrate_script = root / "scripts" / "migrate_ndjson.py"
    extract_script = root / "extract_api_chat.py"

    # Step 1: scrape
    scrape_cmd = [
        python_exec,
        str(scrape_script),
        "--start-page",
        str(args.start_page),
        "--max-pages",
        str(args.max_pages),
        "--out",
        args.scrape_out,
        "--delay",
        str(args.delay),
        "--pdf-dir",
        args.pdf_dir,
        "--log-level",
        args.log_level,
    ]
    if args.min_price is not None:
        scrape_cmd.extend(["--min-price", str(args.min_price)])
    if args.max_price is not None:
        scrape_cmd.extend(["--max-price", str(args.max_price)])
    if args.user_agent:
        scrape_cmd.extend(["--user-agent", args.user_agent])
    if args.max_contracts is not None:
        scrape_cmd.extend(["--max-contracts", str(args.max_contracts)])

    # Step 2: migrate
    migrate_cmd = [
        python_exec,
        str(migrate_script),
        "--input",
        args.scrape_out,
        "--output",
        args.contracts_json,
    ]

    # Step 3: OpenAI extraction
    extract_cmd = [
        python_exec,
        str(extract_script),
        "--input",
        args.contracts_json,
        "--pdf-dir",
        args.pdf_dir,
        "--model",
        args.model,
    ]
    if args.api_key:
        extract_cmd.extend(["--api-key", args.api_key])
    if args.no_skip_processed:
        extract_cmd.append("--no-skip-processed")
    if args.ignore_existing_pdf_text:
        extract_cmd.append("--ignore-existing-pdf-text")

    try:
        _run_step("Step 1/3: Scrape CRZ", scrape_cmd)
        _run_step("Step 2/3: Migrate to contracts.json", migrate_cmd)
        _run_step("Step 3/3: OpenAI extraction", extract_cmd)
    except Exception as e:
        print(f"\n[PIPELINE ERROR] {e}", file=sys.stderr)
        return 1

    print("\n[PIPELINE SUCCESS] All steps completed.")
    print(f"Final dataset: {args.contracts_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
