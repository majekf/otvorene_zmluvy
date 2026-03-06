#!/usr/bin/env python
"""
CLI entry point for CRZ scraper.

Usage:
    python scrape_crz.py --start-page 1 --max-pages 3 --out out.ndjson
    python scrape_crz.py --start-page 1 --max-pages 100 --out contracts.ndjson --delay 1.0
"""

import argparse
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper import scrape_contracts


def main():
    parser = argparse.ArgumentParser(
        description="Scrape CRZ (Central Register of Contracts) from crz.gov.sk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_crz.py --start-page 1 --max-pages 3
  python scrape_crz.py --start-page 1 --max-pages 100 --out contracts.ndjson --delay 1.0
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
        "--out",
        type=str,
        default="out.ndjson",
        help="Output NDJSON file path (default: out.ndjson)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)"
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
    logger.info(f"  Output: {args.out}")
    logger.info(f"  Delay: {args.delay}s")
    logger.info(f"  PDF dir: {args.pdf_dir}")
    
    try:
        contracts_count = scrape_contracts(
            start_page=args.start_page,
            max_pages=args.max_pages,
            output_file=args.out,
            delay=args.delay,
            user_agent=args.user_agent,
            pdf_dir=args.pdf_dir,
        )
        
        logger.info(f"Success! Scraped {contracts_count} contracts to {args.out}")
        
        # Verify output file
        output_path = Path(args.out)
        if output_path.exists():
            lines = output_path.read_text(encoding="utf-8").strip().split("\n")
            logger.info(f"Output file contains {len(lines)} lines")
            if lines:
                logger.info(f"First contract: {lines[0][:100]}...")
        
        return 0
    
    except Exception as e:
        logger.exception(f"Scraping failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
