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
import threading
import time
import unicodedata
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

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

# pypdfium2/tesseract OCR fallback is not reliably thread-safe under high
# parallelism in this environment. Serialize OCR calls to avoid native crashes.
OCR_LOCK = threading.Lock()

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


def extract_public_procurement_id(public_procurement_url: Optional[str]) -> Optional[str]:
    """Extract procurement identifier from known external procurement URLs."""
    if not public_procurement_url:
        return None

    parsed = urlparse(public_procurement_url)
    path = parsed.path or ""

    # Josephine format: /sk/tender/<id>/summary
    tender_match = re.search(r"/tender/(\d+)(?:/|$)", path)
    if tender_match:
        return tender_match.group(1)

    # UVO format often includes /detail/<id>
    detail_match = re.search(r"/detail/(\d+)(?:/|$)", path)
    if detail_match:
        return detail_match.group(1)

    # Fallback: use the last numeric segment in path.
    numeric_parts = re.findall(r"\d+", path)
    if numeric_parts:
        return numeric_parts[-1]

    return None


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


def build_listing_page_url(
    listing_url: str,
    page_index: int,
    crz_filters: Optional[Dict[str, Optional[str]]] = None,
) -> str:
    """Build listing URL with page index and optional CRZ query filters."""
    parsed = urlparse(listing_url)
    query_map = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if crz_filters:
        for key, value in crz_filters.items():
            if value is None:
                continue
            query_map[key] = str(value)

    query_map["page"] = str(page_index)
    new_query = urlencode(query_map, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


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


def detect_canonical_listing_url(html: str, current_listing_url: str) -> Optional[str]:
    """Detect canonical CRZ listing URL from filter form action on landing pages."""
    soup = BeautifulSoup(html, "html.parser")

    filter_form = soup.find("form", id=re.compile(r"^frm_filter_"))
    if not filter_form:
        return None

    action = filter_form.get("action")
    if not action:
        return None

    candidate = urljoin(BASE_URL, action)
    if candidate.rstrip("/") == current_listing_url.rstrip("/"):
        return None

    return candidate


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

            for li in list_items:
                label_value = extract_label_value(li)
                if not label_value:
                    continue

                label = label_value["label"]
                value = label_value["value"]
                label_norm = normalize_text(label)

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
                elif "verejne obstaravanie" in label_norm:
                    # Some contracts include an external procurement portal link
                    # (for example UVO/Josephine). Keep both label and URL.
                    link = li.find("a", href=True)
                    if link:
                        details["public_procurement_url"] = urljoin(
                            BASE_URL,
                            link["href"],
                        )
                        details["public_procurement_id"] = extract_public_procurement_id(
                            details["public_procurement_url"]
                        )
                        details["public_procurement_portal"] = link.get_text(
                            " ",
                            strip=True,
                        )
                    elif value:
                        details["public_procurement_portal"] = value

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

        # Fallback: if the field exists outside expected section/card structure.
        if "public_procurement_url" not in details:
            for li in soup.find_all("li"):
                strong = li.find("strong")
                if not strong:
                    continue
                label_norm = normalize_text(strong.get_text(" ", strip=True))
                if "verejne obstaravanie" not in label_norm:
                    continue

                link = li.find("a", href=True)
                if link:
                    details["public_procurement_url"] = urljoin(BASE_URL, link["href"])
                    details["public_procurement_id"] = extract_public_procurement_id(
                        details["public_procurement_url"]
                    )
                    details["public_procurement_portal"] = link.get_text(" ", strip=True)
                    break
    return details


def download_and_extract_pdf(
    pdf_url: str,
    pdf_dir: str,
    session: requests.Session,
    agreement_context: Optional[str] = None,
    throttler: Optional[RequestThrottler] = None,
    ocr_executor: Optional[ThreadPoolExecutor] = None,
) -> Dict[str, Any]:
    """Download PDF and optionally run text extraction in background."""
    result = {
        "pdf_url": pdf_url,
        "pdf_local_path": None,
        "pdf_text": None,
        "text_future": None,
    }

    try:
        parsed = urlparse(pdf_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"contract_{int(time.time())}.pdf"

        pdf_path = os.path.join(pdf_dir, filename)
        Path(pdf_dir).mkdir(parents=True, exist_ok=True)

        if agreement_context:
            logger.info("Downloading PDF for %s: %s", agreement_context, pdf_url)
        else:
            logger.info("Downloading PDF: %s", pdf_url)
        if throttler:
            throttler.wait_for_slot()
        response = session.get(pdf_url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        with open(pdf_path, "wb") as f:
            f.write(response.content)

        result["pdf_local_path"] = pdf_path

        if ocr_executor:
            logger.info("Scheduling async PDF text extraction")
            result["text_future"] = ocr_executor.submit(
                _extract_pdf_text_with_fallback,
                pdf_path,
            )
        else:
            result["pdf_text"] = _extract_pdf_text_with_fallback(pdf_path)

    except Exception as e:
        logger.error(f"Failed to download/process PDF {pdf_url}: {e}")

    return result


def _is_readable_text(text: Optional[str], min_chars: int = 30) -> bool:
    """Heuristic: treat text as readable only if it has enough non-space chars."""
    if not text:
        return False
    return len("".join(text.split())) >= min_chars


def _extract_pdf_text_with_fallback(pdf_path: str) -> Optional[str]:
    """Extract text via pdfplumber, then OCR fallback for scanned PDFs."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            full_text = "\n".join(text_parts)
            text = full_text[:50000] if full_text else None
            logger.info("Extracted %d chars from PDF", len(full_text))

            if _is_readable_text(text):
                return text

            logger.info("Text extraction returned too little text, trying OCR fallback")
            ocr_text = _extract_text_with_ocr_threadsafe(pdf_path)
            if ocr_text:
                clipped = ocr_text[:50000]
                logger.info("OCR fallback extracted %d chars", len(clipped))
                return clipped
            return text
    except Exception as e:
        logger.warning("Failed to extract text from PDF %s: %s", pdf_path, e)
        ocr_text = _extract_text_with_ocr_threadsafe(pdf_path)
        if ocr_text:
            clipped = ocr_text[:50000]
            logger.info(
                "OCR fallback extracted %d chars after pdfplumber failure",
                len(clipped),
            )
            return clipped
    return None


def _extract_text_with_ocr_threadsafe(pdf_path: str) -> Optional[str]:
    """Run OCR fallback under a process-wide lock to avoid native crashes."""
    with OCR_LOCK:
        return extract_text_with_ocr(pdf_path)


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
    max_contracts: Optional[int] = None,
    listing_url: str = LISTING_URL,
    crz_filters: Optional[Dict[str, Optional[str]]] = None,
    output_file: str = "out.json",
    delay: float = DEFAULT_DELAY,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    user_agent: str = DEFAULT_USER_AGENT,
    pdf_dir: str = "data/pdfs",
    ocr_workers: int = 2,
) -> int:
    """
    Main scraping function.

    Args:
        start_page: Starting page number (1-indexed)
        max_pages: Maximum number of pages to scrape
        max_contracts: Optional hard limit on number of contracts to process
        listing_url: Listing URL to scrape (default CRZ /zmluvy/ listing)
        crz_filters: Optional CRZ server-side query filters, e.g. art_ico, art_predmet
        output_file: Output JSON file path
        delay: Delay between requests in seconds
        min_price: Minimum accepted contract value in EUR (inclusive)
        max_price: Maximum accepted contract value in EUR (inclusive)
        user_agent: Custom User-Agent header
        pdf_dir: Directory to save PDFs
        ocr_workers: Number of background workers for PDF text extraction
            (including OCR fallback when needed)

    Returns:
        Number of contracts scraped
    """
    import json

    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValueError("min_price cannot be greater than max_price")
    if max_contracts is not None and max_contracts <= 0:
        raise ValueError("max_contracts must be greater than 0")

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    throttler = RequestThrottler(delay)

    contracts_processed = 0
    pdfs_downloaded = 0
    scraped_contracts: List[Dict[str, Any]] = []
    pending_text_jobs: List[Dict[str, Any]] = []
    existing_contracts: List[Dict[str, Any]] = []
    known_contract_ids: set[str] = set()
    active_listing_url = listing_url

    output_path = Path(output_file)
    if output_path.exists():
        existing_text = output_path.read_text(encoding="utf-8").strip()
        if existing_text:
            loaded = json.loads(existing_text)
            if not isinstance(loaded, list):
                raise ValueError(
                    f"Existing output file {output_file} must contain a JSON array"
                )
            existing_contracts = loaded
            known_contract_ids = {
                str(item.get("contract_id"))
                for item in existing_contracts
                if isinstance(item, dict) and item.get("contract_id")
            }
            logger.info(
                "Loaded %d existing contracts (%d with contract_id) from %s",
                len(existing_contracts),
                len(known_contract_ids),
                output_file,
            )

    try:
        with ThreadPoolExecutor(max_workers=max(1, ocr_workers)) as ocr_executor:
            for page_num in range(start_page, start_page + max_pages):
                url_page = page_num - 1
                page_url = build_listing_page_url(
                    listing_url=active_listing_url,
                    page_index=url_page,
                    crz_filters=crz_filters,
                )

                logger.info(f"Fetching page {page_num} (URL page={url_page})")
                html = fetch_page(page_url, session, throttler=throttler)

                if not html:
                    logger.warning(f"Skipping page {page_num}")
                    continue

                rows = extract_listing_rows(html)

                if not rows:
                    canonical_listing_url = detect_canonical_listing_url(
                        html,
                        active_listing_url,
                    )
                    if canonical_listing_url:
                        logger.info(
                            "Detected canonical CRZ listing URL from filter action: %s",
                            canonical_listing_url,
                        )
                        active_listing_url = canonical_listing_url
                        retry_page_url = build_listing_page_url(
                            listing_url=active_listing_url,
                            page_index=url_page,
                            crz_filters=crz_filters,
                        )
                        logger.info(
                            "Retrying page %d using canonical listing URL",
                            page_num,
                        )
                        retry_html = fetch_page(
                            retry_page_url,
                            session,
                            throttler=throttler,
                        )
                        if retry_html:
                            rows = extract_listing_rows(retry_html)

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
                    if max_contracts is not None and contracts_processed >= max_contracts:
                        logger.info(
                            "Reached max_contracts=%d, stopping scrape", max_contracts
                        )
                        break

                    row_contract_id = row.get("contract_id")
                    if row_contract_id and row_contract_id in known_contract_ids:
                        logger.info(
                            "Skipping already present contract_id=%s",
                            row_contract_id,
                        )
                        continue

                    try:
                        contract_data = dict(row)
                        agreement_context = (
                            "row=%d page=%d contract_id=%s title=%s"
                            % (
                                contracts_processed + 1,
                                page_num,
                                row.get("contract_id") or "unknown",
                                row.get("contract_title") or "unknown",
                            )
                        )
                        logger.info("Processing agreement %s", agreement_context)

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
                                if pdf_urls:
                                    # Keep all attachment links in `pdf_urls`, but only
                                    # download/extract the primary attachment used downstream.
                                    primary_pdf_url = pdf_urls[0]
                                    pdf_result = download_and_extract_pdf(
                                        primary_pdf_url,
                                        pdf_dir,
                                        session,
                                        agreement_context=agreement_context,
                                        throttler=throttler,
                                        ocr_executor=ocr_executor,
                                    )

                                    text_future = pdf_result.pop("text_future", None)

                                    if pdf_result["pdf_local_path"]:
                                        contract_data.update(pdf_result)
                                        pdfs_downloaded += 1

                                    if isinstance(text_future, Future):
                                        pending_text_jobs.append(
                                            {
                                                "future": text_future,
                                                "contract_data": contract_data,
                                                "agreement_context": agreement_context,
                                            }
                                        )

                                    skipped_attachments = max(0, len(pdf_urls) - 1)
                                    if skipped_attachments:
                                        logger.info(
                                            "Skipping %d additional PDF attachments for %s; links retained in pdf_urls",
                                            skipped_attachments,
                                            agreement_context,
                                        )

                        scraped_contracts.append(contract_data)
                        contracts_processed += 1
                        if row_contract_id:
                            known_contract_ids.add(row_contract_id)

                    except Exception as e:
                        logger.error(
                            f"Error processing contract {row.get('contract_id')}: {e}"
                        )
                        continue

                if max_contracts is not None and contracts_processed >= max_contracts:
                    break

            if pending_text_jobs:
                logger.info(
                    "Waiting for %d background text extraction jobs to finish",
                    len(pending_text_jobs),
                )

            for text_job in pending_text_jobs:
                try:
                    extracted_text = text_job["future"].result()
                    if extracted_text:
                        text_job["contract_data"]["pdf_text"] = extracted_text[:50000]
                        logger.info(
                            "Text extraction finished for %s: %d chars",
                            text_job["agreement_context"],
                            len(text_job["contract_data"]["pdf_text"]),
                        )
                except Exception as text_error:
                    logger.warning(
                        "Background text extraction failed for %s: %s",
                        text_job["agreement_context"],
                        text_error,
                    )

        combined_contracts = existing_contracts + scraped_contracts
        with open(output_file, "w", encoding="utf-8") as out_f:
            out_f.write(json.dumps(combined_contracts, ensure_ascii=False, indent=2))
            out_f.write("\n")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")

    finally:
        session.close()

    logger.info(
        f"Scraping complete: {contracts_processed} contracts, {pdfs_downloaded} PDFs"
    )
    return contracts_processed

