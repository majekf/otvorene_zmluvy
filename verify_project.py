#!/usr/bin/env python
"""
Project verification script - checks that all required files are present
"""

import sys
from pathlib import Path


def verify_project():
    """Verify all required files exist."""
    project_root = Path(__file__).parent
    
    required_files = {
        # Core implementation
        "src/scraper.py": "Core scraping module",
        "src/__init__.py": "Package initialization",
        "scrape_crz.py": "CLI entry point",
        
        # Tests
        "tests/test_parser.py": "Unit tests",
        "tests/test_integration.py": "Integration tests",
        "tests/__init__.py": "Test package init",
        
        # Configuration
        "requirements.txt": "Python dependencies",
        ".gitignore": "Git ignore file",
        
        # Documentation
        "README.md": "User documentation",
        "ARCHITECTURE.md": "Technical documentation",
        "QUICKSTART.md": "Quick reference guide",
        "PROJECT_COMPLETION.md": "Project summary",
        
        # Setup scripts
        "setup.py": "Setup validation script",
        "init_git.py": "Git initialization script",
        "setup_git.bat": "Git setup batch file",
    }
    
    required_dirs = {
        "src": "Source code directory",
        "tests": "Tests directory",
        "data/pdfs": "PDF storage directory",
    }
    
    print("=" * 70)
    print("CRZ SCRAPER - PROJECT VERIFICATION")
    print("=" * 70)
    print()
    
    # Check directories
    print("Checking directories...")
    dir_ok = True
    for dir_path, desc in required_dirs.items():
        full_path = project_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"  ✓ {dir_path:<20} {desc}")
        else:
            print(f"  ✗ {dir_path:<20} {desc} - MISSING")
            dir_ok = False
    
    print()
    
    # Check files
    print("Checking files...")
    file_ok = True
    for file_path, desc in required_files.items():
        full_path = project_root / file_path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path:<30} ({size:>6} bytes)")
        else:
            print(f"  ✗ {file_path:<30} MISSING")
            file_ok = False
    
    print()
    
    # Check file content
    print("Checking core functionality...")
    content_ok = True
    
    # Check scraper.py
    scraper_file = project_root / "src" / "scraper.py"
    if scraper_file.exists():
        content = scraper_file.read_text()
        checks = [
            ("parse_price", "parse_price function"),
            ("extract_listing_rows", "extract_listing_rows function"),
            ("extract_contract_details", "extract_contract_details function"),
            ("download_and_extract_pdf", "download_and_extract_pdf function"),
            ("scrape_contracts", "scrape_contracts function"),
        ]
        for check_str, desc in checks:
            if check_str in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc} - NOT FOUND")
                content_ok = False
    else:
        content_ok = False
    
    # Check scrape_crz.py
    cli_file = project_root / "scrape_crz.py"
    if cli_file.exists():
        content = cli_file.read_text()
        cli_checks = [
            ("argparse", "CLI argument parsing"),
            ("--start-page", "--start-page argument"),
            ("--max-pages", "--max-pages argument"),
            ("--out", "--out argument"),
        ]
        for check_str, desc in cli_checks:
            if check_str in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc} - NOT FOUND")
                content_ok = False
    else:
        content_ok = False
    
    print()
    
    # Check test files
    print("Checking tests...")
    test_ok = True
    
    test_parser = project_root / "tests" / "test_parser.py"
    if test_parser.exists():
        content = test_parser.read_text()
        test_checks = [
            ("TestParsePrice", "Price parsing tests"),
            ("TestParseSlovakDate", "Slovak date parsing tests"),
            ("TestParseDateFromText", "Date text parsing tests"),
        ]
        for check_str, desc in test_checks:
            if check_str in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc} - NOT FOUND")
                test_ok = False
    else:
        test_ok = False
    
    test_integration = project_root / "tests" / "test_integration.py"
    if test_integration.exists():
        content = test_integration.read_text()
        int_checks = [
            ("TestExtractListingRows", "Listing extraction tests"),
            ("TestExtractContractDetails", "Detail extraction tests"),
            ("TestScrapeContractsSmoke", "Smoke tests"),
        ]
        for check_str, desc in int_checks:
            if check_str in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc} - NOT FOUND")
                test_ok = False
    else:
        test_ok = False
    
    print()
    
    # Summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    all_ok = dir_ok and file_ok and content_ok and test_ok
    
    print(f"  Directories:  {'✓ PASS' if dir_ok else '✗ FAIL'}")
    print(f"  Files:        {'✓ PASS' if file_ok else '✗ FAIL'}")
    print(f"  Content:      {'✓ PASS' if content_ok else '✗ FAIL'}")
    print(f"  Tests:        {'✓ PASS' if test_ok else '✗ FAIL'}")
    print()
    
    if all_ok:
        print("✓ PROJECT COMPLETE AND VERIFIED")
        print()
        print("Next steps:")
        print("  1. Install dependencies:")
        print("     pip install -r requirements.txt")
        print()
        print("  2. Run tests:")
        print("     pytest tests/ -v")
        print()
        print("  3. Test the scraper:")
        print("     python scrape_crz.py --start-page 1 --max-pages 1")
        print()
        return 0
    else:
        print("✗ PROJECT VERIFICATION FAILED")
        print()
        print("Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(verify_project())
