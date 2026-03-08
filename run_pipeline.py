#!/usr/bin/env python
"""Run full GovLens data pipeline in one command.

Pipeline steps:
1) Scrape CRZ contracts and PDFs (`scrape_crz.py`)
2) Migrate scraper output into `contracts.json` (`scripts/migrate_ndjson.py`)
3) Enrich contracts with OpenAI extracted scanned_* fields (`extract_api_chat.py`)
4) Expand subcontractors into dedicated dataset (`scripts/expand_subcontractors.py`)
5) Scrape JOSEPHINE tenders referenced by `public_procurement_url` (`scrape_josephine.py`)
6) Scrape UVO tenders referenced by `public_procurement_url` (`scrape_uvo.py`)
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
    parser.add_argument(
        "--ocr-workers",
        type=int,
        default=2,
        help="Background workers for PDF text extraction during scraping",
    )
    parser.add_argument("--log-level", type=str, default="INFO")

    # CRZ server-side filters (forwarded to scrape_crz.py)
    parser.add_argument("--crz-listing-url", type=str, default=None)
    parser.add_argument("--crz-art-zs2", type=str, default=None)
    parser.add_argument("--crz-art-predmet", type=str, default=None)
    parser.add_argument("--crz-art-ico", type=str, default=None)
    parser.add_argument("--crz-art-suma-spolu-od", type=str, default=None)
    parser.add_argument("--crz-art-suma-spolu-do", type=str, default=None)
    parser.add_argument("--crz-art-datum-zverejnene-od", type=str, default=None)
    parser.add_argument("--crz-art-datum-zverejnene-do", type=str, default=None)
    parser.add_argument("--crz-art-rezort", type=str, default=None)
    parser.add_argument("--crz-art-zs1", type=str, default=None)
    parser.add_argument("--crz-nazov", type=str, default=None)
    parser.add_argument("--crz-art-ico1", type=str, default=None)
    parser.add_argument("--crz-odoslat", type=str, default=None)
    parser.add_argument("--crz-id", type=str, default=None)
    parser.add_argument("--crz-frm-id-frm-filter-3", type=str, default=None)

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
    parser.add_argument(
        "--subcontractors-json",
        type=str,
        default="data/contracts_subcontractors.json",
        help="Expanded subcontractors JSON output path",
    )
    parser.add_argument(
        "--subcontractors-source-field",
        type=str,
        default="scanned_subcontractors",
        help="Contracts field used for subcontractor expansion",
    )
    parser.add_argument(
        "--skip-subcontractors",
        action="store_true",
        help="Skip subcontractor expansion step",
    )
    parser.add_argument(
        "--josephine-out",
        type=str,
        default="data/josephine_tenders.json",
        help="JOSEPHINE tenders output path",
    )
    parser.add_argument(
        "--josephine-pdf-dir",
        type=str,
        default="data/josephine_pdfs",
        help="Directory for JOSEPHINE result PDFs",
    )
    parser.add_argument(
        "--skip-josephine",
        action="store_true",
        help="Skip JOSEPHINE scraping step",
    )
    parser.add_argument(
        "--uvo-out",
        type=str,
        default="data/uvo_tenders.json",
        help="UVO tenders output path",
    )
    parser.add_argument(
        "--uvo-pdf-dir",
        type=str,
        default="data/uvo_pdfs",
        help="Directory for UVO result PDFs",
    )
    parser.add_argument(
        "--skip-uvo",
        action="store_true",
        help="Skip UVO scraping step",
    )

    # OpenAI analysis settings
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=5,
        help="Maximum number of concurrent OpenAI extraction requests",
    )
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
    subcontractors_script = root / "scripts" / "expand_subcontractors.py"
    josephine_script = root / "scrape_josephine.py"
    uvo_script = root / "scrape_uvo.py"

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
        "--ocr-workers",
        str(args.ocr_workers),
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
    if args.crz_listing_url:
        scrape_cmd.extend(["--crz-listing-url", args.crz_listing_url])

    crz_filter_args = {
        "--crz-art-zs2": args.crz_art_zs2,
        "--crz-art-predmet": args.crz_art_predmet,
        "--crz-art-ico": args.crz_art_ico,
        "--crz-art-suma-spolu-od": args.crz_art_suma_spolu_od,
        "--crz-art-suma-spolu-do": args.crz_art_suma_spolu_do,
        "--crz-art-datum-zverejnene-od": args.crz_art_datum_zverejnene_od,
        "--crz-art-datum-zverejnene-do": args.crz_art_datum_zverejnene_do,
        "--crz-art-rezort": args.crz_art_rezort,
        "--crz-art-zs1": args.crz_art_zs1,
        "--crz-nazov": args.crz_nazov,
        "--crz-art-ico1": args.crz_art_ico1,
        "--crz-odoslat": args.crz_odoslat,
        "--crz-id": args.crz_id,
        "--crz-frm-id-frm-filter-3": args.crz_frm_id_frm_filter_3,
    }
    for flag, value in crz_filter_args.items():
        if value is not None:
            scrape_cmd.extend([flag, value])

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
        "--max-concurrency",
        str(args.max_concurrency),
    ]
    if args.api_key:
        extract_cmd.extend(["--api-key", args.api_key])
    if args.no_skip_processed:
        extract_cmd.append("--no-skip-processed")
    if args.ignore_existing_pdf_text:
        extract_cmd.append("--ignore-existing-pdf-text")

    # Step 4: subcontractor expansion
    subcontractors_cmd = [
        python_exec,
        str(subcontractors_script),
        "--input",
        args.contracts_json,
        "--output",
        args.subcontractors_json,
        "--source-field",
        args.subcontractors_source_field,
    ]

    # Step 5: JOSEPHINE scraping from contracts public_procurement_url links
    josephine_cmd = [
        python_exec,
        str(josephine_script),
        "--contracts-json",
        args.contracts_json,
        "--out",
        args.josephine_out,
        "--pdf-dir",
        args.josephine_pdf_dir,
        "--openai-model",
        args.model,
        "--log-level",
        args.log_level,
    ]
    if args.api_key:
        josephine_cmd.extend(["--api-key", args.api_key])

    # Step 6: UVO scraping from contracts public_procurement_url links
    uvo_cmd = [
        python_exec,
        str(uvo_script),
        "--contracts-json",
        args.contracts_json,
        "--out",
        args.uvo_out,
        "--pdf-dir",
        args.uvo_pdf_dir,
        "--openai-model",
        args.model,
        "--log-level",
        args.log_level,
    ]
    if args.api_key:
        uvo_cmd.extend(["--api-key", args.api_key])

    try:
        _run_step("Step 1/6: Scrape CRZ", scrape_cmd)
        _run_step("Step 2/6: Migrate to contracts.json", migrate_cmd)
        _run_step("Step 3/6: OpenAI extraction", extract_cmd)
        if args.skip_subcontractors:
            print("\n=== Step 4/6: Subcontractor expansion (skipped) ===")
        else:
            _run_step("Step 4/6: Subcontractor expansion", subcontractors_cmd)
        if args.skip_josephine:
            print("\n=== Step 5/6: JOSEPHINE scraping (skipped) ===")
        else:
            _run_step("Step 5/6: JOSEPHINE scraping", josephine_cmd)
        if args.skip_uvo:
            print("\n=== Step 6/6: UVO scraping (skipped) ===")
        else:
            _run_step("Step 6/6: UVO scraping", uvo_cmd)
    except Exception as e:
        print(f"\n[PIPELINE ERROR] {e}", file=sys.stderr)
        return 1

    print("\n[PIPELINE SUCCESS] All steps completed.")
    print(f"Final dataset: {args.contracts_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
