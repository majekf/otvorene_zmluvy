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
import shutil
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import pdfplumber
import pypdfium2 as pdfium
import requests
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
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
DEFAULT_DELAY = 3.0  # seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # exponential backoff multiplier

# Month name mapping (normalized Slovak month names to number)
MONTH_MAP = {
    "januar": 1,
    "februar": 2,
    "marec": 3,
    "april": 4,
    "maj": 5,
    "jun": 6,
    "jul": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}


class RequestThrottler:
    """Ensure a minimum delay between consecutive outbound HTTP requests."""

    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = max(0.0, delay_seconds)
        self._last_request_ts: Optional[float] = None

    def wait_for_slot(self) -> None:
        if self.delay_seconds <= 0:
            self._last_request_ts = time.monotonic()
            return

        now = time.monotonic()
        if self._last_request_ts is not None:
            elapsed = now - self._last_request_ts
            if elapsed < self.delay_seconds:
                time.sleep(self.delay_seconds - elapsed)

        self._last_request_ts = time.monotonic()


def normalize_text(value: Optional[str]) -> str:
    """Lowercase, strip accents, and trim text for tolerant matching."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_accents.strip().lower()


def extract_label_value(li: Any) -> Optional[Dict[str, Optional[str]]]:
    """Extract one label/value pair from the detail-page list item."""
    strong = li.find("strong")
    if not strong:
        return None

    raw_label = strong.get_text(" ", strip=True).strip()
    label = raw_label.rstrip(":").strip()
    if not label:
        return None

    span = li.find("span")
    if span:
        value = span.get_text(" ", strip=True).strip()
    else:
        full_text = li.get_text(" ", strip=True)
        value = full_text.replace(raw_label, "", 1).strip(" :")

    return {"label": label, "value": value or None}


def matches_price_filter(
    price: Optional[float],
    min_price: Optional[float],
    max_price: Optional[float],
) -> bool:
    """Return True when row price satisfies configured bounds."""
    if min_price is None and max_price is None:
        return True
    if price is None:
        return False
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    return True


def parse_price(price_str: str) -> Optional[float]:
    """
    Parse Slovak price format to float.
    Handles: "28 978,27 €", "0,00 €", "330 624,00 €"
    Returns: 28978.27, 0.0, 330624.0 respectively
    """
    if not price_str:
        return None

    # Remove euro sign and whitespace
    cleaned = price_str.replace("€", "").replace("â‚¬", "").strip()

    # Handle non-breaking spaces and regular spaces
    cleaned = cleaned.replace("\u00a0", "").replace(" ", "")

    # Replace Slovak decimal comma with dot
    cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        logger.warning(f"Could not parse price: {cleaned}")
        return None


def parse_slovak_date(day: str, month: str, year: str) -> Optional[str]:
    """Parse Slovak date parts to ISO format (YYYY-MM-DD)."""
    try:
        day_str = day.strip().rstrip(".")
        day_int = int(day_str)
        month_key = normalize_text(month)
        month_int = MONTH_MAP.get(month_key)
        year_int = int(year.strip())

        if not month_int:
            return None

        return f"{year_int:04d}-{month_int:02d}-{day_int:02d}"
    except (ValueError, AttributeError):
        return None


def parse_date_from_text(date_str: str) -> Optional[str]:
    """Parse date from text like '01.03.2026' to ISO format."""
    if not date_str or "neuvedeny" in normalize_text(date_str):
        return None

    try:
        parts = date_str.strip().split(".")
        if len(parts) != 3:
            return None
        day, month, year = parts
        return f"{year}-{month:0>2s}-{day:0>2s}"
    except (ValueError, IndexError):
        return None


def fetch_page(
    url: str,
    session: requests.Session,
    timeout: int = DEFAULT_TIMEOUT,
    throttler: Optional[RequestThrottler] = None,
) -> Optional[str]:
    """Fetch a page with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            if throttler:
                throttler.wait_for_slot()
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            wait_time = DEFAULT_DELAY * (RETRY_BACKOFF**attempt)
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    f"Fetch failed for {url}: {e}. Retrying in {wait_time:.1f}s..."
                )
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

        contract_number = None
        title_spans = title_cell.find_all("span")
        if title_spans:
            contract_number = title_spans[0].get_text(strip=True)

        # Cell 3: Price
        price_raw = cells[2].get_text(strip=True)
        price_numeric = parse_price(price_raw)

        # Cell 4/5: Parties
        supplier = cells[3].get_text(strip=True)
        buyer = cells[4].get_text(strip=True)

        contract_id = None
        if contract_url:
            match = re.search(r"/zmluva/(\d+)/", contract_url)
            if match:
                contract_id = match.group(1)

        published_date = parse_slovak_date(day, month, year)

        rows.append(
            {
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
            }
        )

    return rows


def extract_contract_details(html: str, contract_url: str) -> Dict[str, Any]:
    """Extract detailed contract information from detail page."""
    del contract_url  # kept for backwards-compatible signature

    soup = BeautifulSoup(html, "html.parser")
    details: Dict[str, Any] = {}

    cards = soup.find_all("div", {"class": "card"})

    for card in cards:
        header = card.find("h2", {"class": "card-header"})
        if not header:
            continue

        header_text = header.get_text(strip=True)
        header_norm = normalize_text(header_text)
        body = card.find("div", {"class": "card-body"})
        if not body:
            continue

        if "identifik" in header_norm:
            list_items = body.find_all("li")
            last_entity = None  # buyer/supplier/rezort context for repeated ICO labels
            identification_items: List[Dict[str, Optional[str]]] = []
            identification_fields: Dict[str, Any] = {}

            for li in list_items:
                label_value = extract_label_value(li)
                if not label_value:
                    continue

                label = label_value["label"]
                value = label_value["value"]
                label_norm = normalize_text(label)

                identification_items.append({"label": label, "value": value})

                if label in identification_fields:
                    existing = identification_fields[label]
                    if isinstance(existing, list):
                        existing.append(value)
                    else:
                        identification_fields[label] = [existing, value]
                else:
                    identification_fields[label] = value

                if "c. zmluvy" in label_norm or "cislo zmluvy" in label_norm:
                    details["contract_number_detail"] = value
                elif "id zmluvy" in label_norm:
                    details["contract_id_detail"] = value
                elif "objednavatel" in label_norm:
                    details["buyer_detail"] = value
                    last_entity = "buyer"
                elif "dodavatel" in label_norm:
                    details["supplier_detail"] = value
                    last_entity = "supplier"
                elif "rezort" in label_norm:
                    details["rezort"] = value
                    last_entity = "rezort"
                elif label_norm == "typ":
                    details["contract_type"] = value
                elif label_norm == "ico":
                    if last_entity == "buyer":
                        details["ico_buyer"] = value
                    elif last_entity == "supplier":
                        details["ico_supplier"] = value
                    elif last_entity == "rezort":
                        details["ico_rezort"] = value

            if identification_items:
                details["identification_section_items"] = identification_items
            if identification_fields:
                details["identification_fields"] = identification_fields

        elif "datum" in header_norm:
            list_items = body.find_all("li")
            for li in list_items:
                strong = li.find("strong")
                span = li.find("span", {"class": "col-auto"})
                if strong and span:
                    label = strong.get_text(strip=True)
                    value = span.get_text(strip=True)
                    label_norm = normalize_text(label)

                    if "datum zverejnenia" in label_norm:
                        details["date_published"] = parse_date_from_text(value)
                    elif "datum uzavretia" in label_norm:
                        details["date_concluded"] = parse_date_from_text(value)
                    elif "datum ucinnosti" in label_norm:
                        details["date_effective"] = parse_date_from_text(value)
                    elif "datum platnosti do" in label_norm:
                        details["date_valid_until"] = parse_date_from_text(value)

        elif "priloha" in header_norm:
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


def download_and_extract_pdf(
    pdf_url: str,
    pdf_dir: str,
    session: requests.Session,
    throttler: Optional[RequestThrottler] = None,
) -> Dict[str, Any]:
    """Download PDF and extract text."""
    result = {
        "pdf_url": pdf_url,
        "pdf_local_path": None,
        "pdf_text": None,
    }

    try:
        parsed = urlparse(pdf_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"contract_{int(time.time())}.pdf"

        pdf_path = os.path.join(pdf_dir, filename)
        Path(pdf_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading PDF: {pdf_url}")
        if throttler:
            throttler.wait_for_slot()
        response = session.get(pdf_url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        with open(pdf_path, "wb") as f:
            f.write(response.content)

        result["pdf_local_path"] = pdf_path

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                full_text = "\n".join(text_parts)
                result["pdf_text"] = full_text[:50000] if full_text else None

                logger.info(f"Extracted {len(full_text)} chars from PDF")

                if not _is_readable_text(result["pdf_text"]):
                    logger.info(
                        "Text extraction returned too little text, trying OCR fallback"
                    )
                    ocr_text = extract_text_with_ocr(pdf_path)
                    if ocr_text:
                        result["pdf_text"] = ocr_text[:50000]
                        logger.info(
                            "OCR fallback extracted %d chars", len(result["pdf_text"])
                        )
        except Exception as e:
            logger.warning(f"Failed to extract text from PDF {pdf_path}: {e}")
            ocr_text = extract_text_with_ocr(pdf_path)
            if ocr_text:
                result["pdf_text"] = ocr_text[:50000]
                logger.info(
                    "OCR fallback extracted %d chars after pdfplumber failure",
                    len(result["pdf_text"]),
                )

    except Exception as e:
        logger.error(f"Failed to download/process PDF {pdf_url}: {e}")

    return result


def _is_readable_text(text: Optional[str], min_chars: int = 30) -> bool:
    """Heuristic: treat text as readable only if it has enough non-space chars."""
    if not text:
        return False
    return len("".join(text.split())) >= min_chars


def extract_text_with_ocr(
    pdf_path: str,
    max_chars: int = 50000,
    lang: str = "slk+eng",
    dpi: int = 220,
) -> Optional[str]:
    """
    OCR text extraction fallback for scanned PDFs.

    Requires `tesseract` binary available in PATH.
    """
    if not shutil.which("tesseract"):
        logger.warning("OCR fallback skipped: 'tesseract' binary not found in PATH")
        return None

    try:
        pdf = pdfium.PdfDocument(pdf_path)
    except Exception as e:
        logger.warning("OCR fallback failed to open PDF %s: %s", pdf_path, e)
        return None

    try:
        text_parts: List[str] = []
        with TemporaryDirectory(prefix="crz_ocr_") as temp_dir:
            total_pages = len(pdf)
            for page_index in range(total_pages):
                try:
                    page = pdf[page_index]
                    bitmap = page.render(scale=dpi / 72)
                    pil_image = bitmap.to_pil()

                    image_path = Path(temp_dir) / f"page_{page_index + 1:04d}.png"
                    pil_image.save(image_path, format="PNG")

                    cmd = [
                        "tesseract",
                        str(image_path),
                        "stdout",
                        "-l",
                        lang,
                        "--dpi",
                        str(dpi),
                    ]
                    proc = subprocess.run(
                        cmd,
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    if proc.returncode != 0:
                        logger.warning(
                            "OCR failed on %s page %d: %s",
                            pdf_path,
                            page_index + 1,
                            proc.stderr.strip() or "unknown tesseract error",
                        )
                        continue

                    page_text = proc.stdout.strip()
                    if page_text:
                        text_parts.append(page_text)

                    joined = "\n".join(text_parts)
                    if len(joined) >= max_chars:
                        return joined[:max_chars]

                except Exception as page_error:
                    logger.warning(
                        "OCR page render/process failed for %s page %d: %s",
                        pdf_path,
                        page_index + 1,
                        page_error,
                    )
                    continue

        full_text = "\n".join(text_parts).strip()
        return full_text[:max_chars] if full_text else None
    finally:
        pdf.close()


def enrich_json_with_ocr_text(
    input_json_path: str,
    output_json_path: Optional[str] = None,
    min_chars: int = 30,
    lang: str = "slk+eng",
) -> Dict[str, int]:
    """
    Fill missing/unreadable `pdf_text` in contracts JSON using OCR.

    Processes records where `pdf_local_path` exists and current `pdf_text` is empty
    or shorter than `min_chars` non-space characters.
    """
    import json

    in_path = Path(input_json_path)
    out_path = Path(output_json_path) if output_json_path else in_path

    if not in_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {in_path}")

    records = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Input JSON must contain a top-level list of contracts")

    updated = 0
    skipped = 0

    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            continue

        current_text = record.get("pdf_text")
        if _is_readable_text(current_text, min_chars=min_chars):
            skipped += 1
            continue

        local_path = record.get("pdf_local_path")
        if not local_path:
            skipped += 1
            continue

        pdf_path = Path(local_path)
        if not pdf_path.is_absolute():
            # Prefer path relative to current working directory, then to JSON file.
            cwd_path = Path.cwd() / pdf_path
            json_relative_path = in_path.parent / pdf_path
            if cwd_path.exists():
                pdf_path = cwd_path
            else:
                pdf_path = json_relative_path

        if not pdf_path.exists():
            skipped += 1
            continue

        ocr_text = extract_text_with_ocr(str(pdf_path), lang=lang)
        if ocr_text:
            record["pdf_text"] = ocr_text
            updated += 1
        else:
            skipped += 1

    out_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "total": len(records),
        "updated": updated,
        "skipped": skipped,
    }


def scrape_contracts(
    start_page: int = 1,
    max_pages: int = 1,
    output_file: str = "out.json",
    delay: float = DEFAULT_DELAY,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    user_agent: str = DEFAULT_USER_AGENT,
    pdf_dir: str = "data/pdfs",
) -> int:
    """
    Main scraping function.

    Args:
        start_page: Starting page number (1-indexed)
        max_pages: Maximum number of pages to scrape
        output_file: Output JSON file path
        delay: Delay between requests in seconds
        min_price: Minimum accepted contract value in EUR (inclusive)
        max_price: Maximum accepted contract value in EUR (inclusive)
        user_agent: Custom User-Agent header
        pdf_dir: Directory to save PDFs

    Returns:
        Number of contracts scraped
    """
    import json

    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValueError("min_price cannot be greater than max_price")

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    throttler = RequestThrottler(delay)

    contracts_processed = 0
    pdfs_downloaded = 0

    try:
        with open(output_file, "w", encoding="utf-8") as out_f:
            out_f.write("[\n")
            first_record = True
            for page_num in range(start_page, start_page + max_pages):
                url_page = page_num - 1
                page_url = f"{LISTING_URL}?page={url_page}"

                logger.info(f"Fetching page {page_num} (URL page={url_page})")
                html = fetch_page(page_url, session, throttler=throttler)

                if not html:
                    logger.warning(f"Skipping page {page_num}")
                    continue

                rows = extract_listing_rows(html)
                logger.info(f"Found {len(rows)} contracts on page {page_num}")

                if min_price is not None or max_price is not None:
                    rows = [
                        row
                        for row in rows
                        if matches_price_filter(
                            row.get("price_numeric_eur"),
                            min_price=min_price,
                            max_price=max_price,
                        )
                    ]
                    logger.info(
                        "After price filter (min=%s, max=%s): %d contracts",
                        min_price,
                        max_price,
                        len(rows),
                    )

                for row in rows:
                    try:
                        contract_data = dict(row)
                        contract_data["scraped_at"] = (
                            datetime.now(timezone.utc)
                            .isoformat()
                            .replace("+00:00", "Z")
                        )

                        # GovLens enrichment fields (Phase 0) - placeholders
                        contract_data["category"] = "not_decided"
                        contract_data["pdf_text_summary"] = "not_summarized"
                        contract_data["award_type"] = "unknown"

                        if row.get("contract_url"):
                            detail_html = fetch_page(
                                row["contract_url"],
                                session,
                                throttler=throttler,
                            )

                            if detail_html:
                                details = extract_contract_details(
                                    detail_html,
                                    row["contract_url"],
                                )
                                contract_data.update(details)

                                pdf_urls = details.get("pdf_urls", [])
                                for pdf_url in pdf_urls:
                                    pdf_result = download_and_extract_pdf(
                                        pdf_url,
                                        pdf_dir,
                                        session,
                                        throttler=throttler,
                                    )

                                    if (
                                        pdf_result["pdf_local_path"]
                                        and not contract_data.get("pdf_local_path")
                                    ):
                                        contract_data.update(pdf_result)
                                        pdfs_downloaded += 1

                        if not first_record:
                            out_f.write(",\n")
                        out_f.write(json.dumps(contract_data, ensure_ascii=False))
                        first_record = False
                        contracts_processed += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing contract {row.get('contract_id')}: {e}"
                        )
                        continue

            out_f.write("\n]\n")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")

    finally:
        session.close()

    logger.info(
        f"Scraping complete: {contracts_processed} contracts, {pdfs_downloaded} PDFs"
    )
    return contracts_processed

