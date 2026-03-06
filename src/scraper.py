"""
CRZ (Central Register of Contracts) Web Scraper

Scrapes contract data from https://www.crz.gov.sk/ with:
- Pagination through contract listings
- Contract detail page extraction
- PDF download and text extraction
- Robust error handling and retries
"""

import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import pdfplumber

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# Configuration
BASE_URL = "https://www.crz.gov.sk"
LISTING_URL = f"{BASE_URL}/zmluvy/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 10
DEFAULT_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # exponential backoff multiplier

# Month name mapping (Slovak to number)
MONTH_MAP = {
    "január": 1, "február": 2, "marec": 3, "apríl": 4,
    "máj": 5, "jún": 6, "júl": 7, "august": 8,
    "september": 9, "október": 10, "november": 11, "december": 12,
}


def parse_price(price_str: str) -> Optional[float]:
    """
    Parse Slovak price format to float.
    Handles: "28 978,27 €", "0,00 €", "330 624,00 €"
    Returns: 28978.27, 0.0, 330624.0 respectively
    """
    if not price_str:
        return None
    
    # Remove € and whitespace
    price_str = price_str.replace("€", "").strip()
    
    # Handle non-breaking spaces and regular spaces
    price_str = price_str.replace("\u00a0", "").replace(" ", "")
    
    # Replace Slovak decimal comma with dot
    price_str = price_str.replace(",", ".")
    
    try:
        return float(price_str)
    except ValueError:
        logger.warning(f"Could not parse price: {price_str}")
        return None


def parse_slovak_date(day: str, month: str, year: str) -> Optional[str]:
    """Parse Slovak date parts to ISO format (YYYY-MM-DD)."""
    try:
        # Strip periods and whitespace from day (e.g., "1." or "28.")
        day_str = day.strip().rstrip(".")
        day_int = int(day_str)
        month_lower = month.strip().lower()
        month_int = MONTH_MAP.get(month_lower)
        year_int = int(year.strip())
        
        if not month_int:
            return None
        
        return f"{year_int:04d}-{month_int:02d}-{day_int:02d}"
    except (ValueError, AttributeError):
        return None


def parse_date_from_text(date_str: str) -> Optional[str]:
    """Parse date from text like '01.03.2026' to ISO format."""
    if not date_str or "neuvedený" in date_str.lower():
        return None
    
    try:
        parts = date_str.strip().split(".")
        if len(parts) != 3:
            return None
        day, month, year = parts
        return f"{year}-{month:0>2s}-{day:0>2s}"
    except (ValueError, IndexError):
        return None


def fetch_page(url: str, session: requests.Session, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """Fetch a page with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            wait_time = DEFAULT_DELAY * (RETRY_BACKOFF ** attempt)
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Fetch failed for {url}: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch {url} after {MAX_RETRIES} retries: {e}")
                return None
    return None


def extract_listing_rows(html: str) -> List[Dict[str, Any]]:
    """Extract contract rows from listing page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    
    table = soup.find("table", {"class": "table_list"})
    if not table:
        logger.warning("Could not find table with class 'table_list'")
        return rows
    
    tbody = table.find("tbody")
    if not tbody:
        return rows
    
    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue
        
        # Cell 1: Date (day, month, year)
        date_cell = cells[0]
        day_span = date_cell.find("span", class_="d-block")
        month_span = date_cell.find_all("span", class_="d-block")
        
        day = None
        month = None
        year = None
        
        spans = date_cell.find_all("span", class_="d-block")
        if len(spans) >= 3:
            day = spans[0].get_text(strip=True)
            month = spans[1].get_text(strip=True)
            year = spans[2].get_text(strip=True)
        
        # Cell 2: Title and contract number
        title_cell = cells[1]
        link = title_cell.find("a")
        contract_title = None
        contract_url = None
        if link:
            contract_title = link.get_text(strip=True)
            contract_url = link.get("href")
            if contract_url:
                contract_url = urljoin(BASE_URL, contract_url)
        
        # Contract number (in span after link)
        contract_number = None
        spans = title_cell.find_all("span")
        if spans:
            contract_number = spans[0].get_text(strip=True)
        
        # Cell 3: Price
        price_raw = cells[2].get_text(strip=True)
        price_numeric = parse_price(price_raw)
        
        # Cell 4: Supplier
        supplier = cells[3].get_text(strip=True)
        
        # Cell 5: Buyer
        buyer = cells[4].get_text(strip=True)
        
        # Extract contract ID from URL if present
        contract_id = None
        if contract_url:
            match = re.search(r'/zmluva/(\d+)/', contract_url)
            if match:
                contract_id = match.group(1)
        
        published_date = parse_slovak_date(day, month, year)
        
        rows.append({
            "published_day": day,
            "published_month": month,
            "published_year": year,
            "published_date": published_date,
            "contract_title": contract_title,
            "contract_number": contract_number,
            "price_raw": price_raw,
            "price_numeric_eur": price_numeric,
            "supplier": supplier,
            "buyer": buyer,
            "contract_url": contract_url,
            "contract_id": contract_id,
        })
    
    return rows


def extract_contract_details(html: str, contract_url: str) -> Dict[str, Any]:
    """Extract detailed contract information from detail page."""
    soup = BeautifulSoup(html, "html.parser")
    details = {}
    
    # Extract ID zmluvy
    all_text = soup.get_text()
    
    # Find all sections with key-value pairs
    cards = soup.find_all("div", {"class": "card"})
    
    for card in cards:
        header = card.find("h2", {"class": "card-header"})
        if not header:
            continue
        
        header_text = header.get_text(strip=True)
        body = card.find("div", {"class": "card-body"})
        if not body:
            continue
        
        if "Identifikácia" in header_text:
            # Extract identification fields
            list_items = body.find_all("li")
            last_entity = None  # Track if we're in buyer or supplier context
            for li in list_items:
                strong = li.find("strong")
                if strong:
                    label = strong.get_text(strip=True)
                    # Get value from span or following text
                    span = li.find("span")
                    if span:
                        value = span.get_text(strip=True)
                        
                        if "Č. zmluvy" in label:
                            details["contract_number_detail"] = value
                        elif "ID zmluvy" in label:
                            details["contract_id_detail"] = value
                        elif "Objednávateľ" in label:
                            details["buyer_detail"] = value
                            last_entity = "buyer"
                        elif "Dodávateľ" in label:
                            details["supplier_detail"] = value
                            last_entity = "supplier"
                        elif "IČO" in label:
                            # Assign to buyer or supplier based on context
                            if last_entity == "buyer":
                                details["ico_buyer"] = value
                            elif last_entity == "supplier":
                                details["ico_supplier"] = value
        
        elif "Dátum" in header_text:
            # Extract dates
            list_items = body.find_all("li")
            for li in list_items:
                strong = li.find("strong")
                span = li.find("span", {"class": "col-auto"})
                if strong and span:
                    label = strong.get_text(strip=True)
                    value = span.get_text(strip=True)
                    
                    if "Dátum zverejnenia" in label:
                        details["date_published"] = parse_date_from_text(value)
                    elif "Dátum uzavretia" in label:
                        details["date_concluded"] = parse_date_from_text(value)
                    elif "Dátum účinnosti" in label:
                        details["date_effective"] = parse_date_from_text(value)
                    elif "Dátum platnosti do" in label:
                        details["date_valid_until"] = parse_date_from_text(value)
        
        elif "Príloha" in header_text or "Příloha" in header_text:
            # Extract attachment/PDF links
            links = body.find_all("a")
            pdfs = []
            for link in links:
                href = link.get("href")
                if href and ".pdf" in href.lower():
                    pdf_url = urljoin(BASE_URL, href)
                    pdfs.append(pdf_url)
            
            if pdfs:
                details["pdf_urls"] = pdfs
    
    return details


def download_and_extract_pdf(pdf_url: str, pdf_dir: str, session: requests.Session) -> Dict[str, Any]:
    """Download PDF and extract text."""
    result = {
        "pdf_url": pdf_url,
        "pdf_local_path": None,
        "pdf_text": None,
    }
    
    try:
        # Parse filename from URL
        parsed = urlparse(pdf_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"contract_{int(time.time())}.pdf"
        
        pdf_path = os.path.join(pdf_dir, filename)
        
        # Create directory if it doesn't exist
        Path(pdf_dir).mkdir(parents=True, exist_ok=True)
        
        # Download PDF
        logger.info(f"Downloading PDF: {pdf_url}")
        response = session.get(pdf_url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        
        result["pdf_local_path"] = pdf_path
        
        # Extract text
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                full_text = "\n".join(text_parts)
                # Truncate to 50000 chars if very large
                if len(full_text) > 50000:
                    result["pdf_text"] = full_text[:50000]
                else:
                    result["pdf_text"] = full_text if full_text else None
                
                logger.info(f"Extracted {len(full_text)} chars from PDF")
        except Exception as e:
            logger.warning(f"Failed to extract text from PDF {pdf_path}: {e}")
    
    except Exception as e:
        logger.error(f"Failed to download/process PDF {pdf_url}: {e}")
    
    return result


def scrape_contracts(
    start_page: int = 1,
    max_pages: int = 1,
    output_file: str = "out.ndjson",
    delay: float = DEFAULT_DELAY,
    user_agent: str = DEFAULT_USER_AGENT,
    pdf_dir: str = "data/pdfs",
) -> int:
    """
    Main scraping function.
    
    Args:
        start_page: Starting page number (1-indexed)
        max_pages: Maximum number of pages to scrape
        output_file: Output NDJSON file path
        delay: Delay between requests in seconds
        user_agent: Custom User-Agent header
        pdf_dir: Directory to save PDFs
    
    Returns:
        Number of contracts scraped
    """
    import json
    
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    
    contracts_processed = 0
    pdfs_downloaded = 0
    
    try:
        with open(output_file, "w", encoding="utf-8") as out_f:
            for page_num in range(start_page, start_page + max_pages):
                # Convert 1-indexed to 0-indexed for URL
                url_page = page_num - 1
                page_url = f"{LISTING_URL}?page={url_page}"
                
                logger.info(f"Fetching page {page_num} (URL page={url_page})")
                html = fetch_page(page_url, session)
                
                if not html:
                    logger.warning(f"Skipping page {page_num}")
                    continue
                
                # Extract listing rows
                rows = extract_listing_rows(html)
                logger.info(f"Found {len(rows)} contracts on page {page_num}")
                
                for row in rows:
                    try:
                        contract_data = dict(row)
                        # Use timezone-aware UTC instead of deprecated utcnow()
                        contract_data["scraped_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

                        # GovLens enrichment fields (Phase 0) — placeholders
                        contract_data["category"] = "not_decided"
                        contract_data["pdf_text_summary"] = "not_summarized"
                        contract_data["award_type"] = "unknown"
                        
                        # Fetch detail page if we have a URL
                        if row.get("contract_url"):
                            time.sleep(delay)
                            detail_html = fetch_page(row["contract_url"], session)
                            
                            if detail_html:
                                details = extract_contract_details(detail_html, row["contract_url"])
                                contract_data.update(details)
                                
                                # Download PDFs if present
                                pdf_urls = details.get("pdf_urls", [])
                                for pdf_url in pdf_urls:
                                    time.sleep(delay)
                                    pdf_result = download_and_extract_pdf(pdf_url, pdf_dir, session)
                                    
                                    # Store first PDF info in main contract record
                                    if pdf_result["pdf_local_path"] and not contract_data.get("pdf_local_path"):
                                        contract_data.update(pdf_result)
                                        pdfs_downloaded += 1
                        
                        # Write to NDJSON
                        out_f.write(json.dumps(contract_data, ensure_ascii=False) + "\n")
                        contracts_processed += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing contract {row.get('contract_id')}: {e}")
                        continue
                
                # Delay before next page
                if page_num < start_page + max_pages - 1:
                    time.sleep(delay)
    
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    
    finally:
        session.close()
    
    logger.info(f"Scraping complete: {contracts_processed} contracts, {pdfs_downloaded} PDFs")
    return contracts_processed
