#!/usr/bin/env python
"""
CLI entry point for CRZ scraper.

Usage:
    python scrape_crz.py --start-page 1 --max-pages 3 --out out.json
    python scrape_crz.py --start-page 1 --max-pages 100 --out contracts.json --delay 3.0
"""

import argparse
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper import enrich_json_with_ocr_text, scrape_contracts


def main():
    parser = argparse.ArgumentParser(
        description="Scrape CRZ (Central Register of Contracts) from crz.gov.sk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_crz.py --start-page 1 --max-pages 3
  python scrape_crz.py --start-page 1 --max-pages 100 --out contracts.json --delay 3.0
        """
    )
    
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Starting page number (1-indexed, default: 1)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Maximum number of pages to scrape (default: 1)"
    )

    parser.add_argument(
        "--max-contracts",
        type=int,
        default=None,
        help="Maximum number of contracts/files to scrape across all pages (optional)"
    )

    parser.add_argument(
        "--crz-listing-url",
        type=str,
        default=None,
        help="Custom CRZ listing URL (optional, default uses /zmluvy/)"
    )

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
    
    parser.add_argument(
        "--out",
        type=str,
        default="out.json",
        help="Output JSON file path (default: out.json)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Delay between requests in seconds (default: 3.0)"
    )

    parser.add_argument(
        "--min-price",
        type=float,
        default=None,
        help="Minimum contract price in EUR (inclusive, optional)"
    )

    parser.add_argument(
        "--max-price",
        type=float,
        default=None,
        help="Maximum contract price in EUR (inclusive, optional)"
    )
    
    parser.add_argument(
        "--user-agent",
        type=str,
        default=None,
        help="Custom User-Agent header (default: realistic browser UA)"
    )
    
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="data/pdfs",
        help="Directory to save PDFs (default: data/pdfs)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        "--ocr-json",
        type=str,
        default=None,
        help="Path to existing contracts JSON to enrich missing/unreadable pdf_text using OCR"
    )

    parser.add_argument(
        "--ocr-out",
        type=str,
        default=None,
        help="Output JSON path for OCR enrichment (default: overwrite --ocr-json file)"
    )

    parser.add_argument(
        "--ocr-min-chars",
        type=int,
        default=30,
        help="Minimum non-space chars required to consider pdf_text readable (default: 30)"
    )

    parser.add_argument(
        "--ocr-lang",
        type=str,
        default="slk+eng",
        help="Tesseract OCR language(s), e.g. 'slk+eng' (default: slk+eng)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting CRZ scraper")
    logger.info(f"  Start page: {args.start_page}")
    logger.info(f"  Max pages: {args.max_pages}")
    logger.info(f"  Max contracts: {args.max_contracts}")
    logger.info(f"  CRZ listing URL override: {args.crz_listing_url}")
    logger.info(f"  Output: {args.out}")
    logger.info(f"  Delay: {args.delay}s")
    logger.info(f"  Min price: {args.min_price}")
    logger.info(f"  Max price: {args.max_price}")
    logger.info(f"  PDF dir: {args.pdf_dir}")
    logger.info(f"  OCR JSON mode: {bool(args.ocr_json)}")
    
    try:
        crz_filters = {
            "art_zs2": args.crz_art_zs2,
            "art_predmet": args.crz_art_predmet,
            "art_ico": args.crz_art_ico,
            "art_suma_spolu_od": args.crz_art_suma_spolu_od,
            "art_suma_spolu_do": args.crz_art_suma_spolu_do,
            "art_datum_zverejnene_od": args.crz_art_datum_zverejnene_od,
            "art_datum_zverejnene_do": args.crz_art_datum_zverejnene_do,
            "art_rezort": args.crz_art_rezort,
            "art_zs1": args.crz_art_zs1,
            "nazov": args.crz_nazov,
            "art_ico1": args.crz_art_ico1,
            "odoslat": args.crz_odoslat,
            "ID": args.crz_id,
            "frm_id_frm_filter_3": args.crz_frm_id_frm_filter_3,
        }

        if args.ocr_json:
            stats = enrich_json_with_ocr_text(
                input_json_path=args.ocr_json,
                output_json_path=args.ocr_out,
                min_chars=args.ocr_min_chars,
                lang=args.ocr_lang,
            )
            output_target = args.ocr_out or args.ocr_json
            logger.info(
                "OCR JSON enrichment complete: total=%d, updated=%d, skipped=%d, output=%s",
                stats["total"],
                stats["updated"],
                stats["skipped"],
                output_target,
            )
            return 0

        contracts_count = scrape_contracts(
            start_page=args.start_page,
            max_pages=args.max_pages,
            max_contracts=args.max_contracts,
            listing_url=args.crz_listing_url or "https://www.crz.gov.sk/zmluvy/",
            crz_filters=crz_filters,
            output_file=args.out,
            delay=args.delay,
            min_price=args.min_price,
            max_price=args.max_price,
            user_agent=args.user_agent,
            pdf_dir=args.pdf_dir,
        )
        
        logger.info(f"Success! Scraped {contracts_count} contracts to {args.out}")
        
        # Verify output file
        output_path = Path(args.out)
        if output_path.exists():
            import json

            contracts = json.loads(output_path.read_text(encoding="utf-8"))
            logger.info(f"Output file contains {len(contracts)} contracts")
            if contracts:
                first_contract = json.dumps(contracts[0], ensure_ascii=False)
                logger.info(f"First contract: {first_contract[:100]}...")
        
        return 0
    
    except Exception as e:
        logger.exception(f"Scraping failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

