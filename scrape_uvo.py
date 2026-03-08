#!/usr/bin/env python
"""Scrape UVO tender pages and enrich result PDFs with OpenAI."""

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

from scrape_josephine import (
    analyze_with_openai,
    clean_whitespace,
    collect_target_documents,
    download_file,
    extract_pdf_text_with_fallback,
    normalize_text,
    parse_cpv_entries,
    safe_filename,
    to_snake_case,
)


load_dotenv()


logger = logging.getLogger(__name__)

BASE_URL = "https://www.uvo.gov.sk"
UVO_ALLOWED_HOSTS = {"uvo.gov.sk", "www.uvo.gov.sk", "ww.uvo.gov.sk"}

DETAIL_FIELD_TRANSLATIONS = {
    "nazov zakazky": "subject_name",
    "obstaravatel": "buyer_organization_name",
    "datum vytvorenia": "info_date_created",
    "datum poslednej aktualizacie": "info_date_last_updated",
    "stav zakazky": "procurement_result",
    "cpv zakazky": "main_cpv",
    "nuts zakazky": "nuts",
    "druh zakazky": "procurement_type",
    "druh postupu": "procedure_type",
    "spolufinancovanie z fondov eu": "info_eu_funds_cofinancing",
    "obrana / bezpecnost": "info_defense_security",
    "datum zverejnenia": "info_date_published",
    "elektronicka aukcia": "electronic_auction",
}


def extract_tender_id_from_url(url: str) -> Optional[str]:
    """Extract UVO tender identifier from detail/documents URL."""
    match = re.search(
        r"/(?:vyhladavanie/vyhladavanie-zakaziek|vyhladavanie-zakaziek)/(?:detail(?:/dokumenty)?|dokumenty)/(\d+)",
        url,
    )
    if match:
        return match.group(1)
    return None


def normalize_uvo_tender_url(url: str) -> Optional[str]:
    """Normalize supported UVO tender URLs to canonical detail URL form."""
    if not url:
        return None

    raw = url.strip()
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return None

    host = (parsed.hostname or "").lower()
    if host not in UVO_ALLOWED_HOSTS:
        return None

    tender_id = extract_tender_id_from_url(raw)
    if not tender_id:
        return None

    canonical_path = f"/vyhladavanie/vyhladavanie-zakaziek/detail/{tender_id}"
    canonical_netloc = "www.uvo.gov.sk"
    canonical_scheme = parsed.scheme or "https"
    return urlunparse(
        (
            canonical_scheme,
            canonical_netloc,
            canonical_path,
            "",
            parsed.query,
            "",
        )
    )


def parse_table_rows_as_map(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract all table header/value pairs in main content area."""
    values: Dict[str, str] = {}
    for tr in soup.select("main table tr"):
        th = tr.find("th")
        td = tr.find("td")
        if th is None or td is None:
            continue

        label = clean_whitespace(th.get_text(" ", strip=True)).rstrip(":")
        value = clean_whitespace(td.get_text(" ", strip=True))
        if not label or not value:
            continue
        values[label] = value

    return values


def parse_uvo_tender_detail(html: str, source_url: str) -> Dict[str, Any]:
    """Extract base tender metadata from UVO detail page."""
    soup = BeautifulSoup(html, "html.parser")
    details_map = parse_table_rows_as_map(soup)

    title_tag = soup.find("title")
    page_title = clean_whitespace(title_tag.get_text(" ", strip=True)) if title_tag else None

    result: Dict[str, Any] = {
        "tender_url": source_url,
        "tender_id": extract_tender_id_from_url(source_url),
        "page_title": page_title,
        "documents": [],
    }

    for label, value in details_map.items():
        normalized_label = normalize_text(label)
        key = DETAIL_FIELD_TRANSLATIONS.get(normalized_label, f"info_{to_snake_case(label)}")
        result[key] = value

    # Keep CPV handling aligned with josephine output where additional CPVs are structured.
    if "main_cpv" in result:
        result["additional_cpv"] = parse_cpv_entries(str(result.get("main_cpv") or ""))

    return result


def extract_document_detail_url(tr: BeautifulSoup, source_url: str) -> Optional[str]:
    """Read document detail URL from row onclick handler."""
    onclick = tr.get("onclick") or ""
    match = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
    if not match:
        return None
    return urljoin(source_url, match.group(1))


def find_documents_table(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """Find UVO documents listing table by its known header label."""
    for table in soup.find_all("table"):
        headers = [
            normalize_text(th.get_text(" ", strip=True))
            for th in table.find_all("th")
        ]
        if any("druh dokumentu" in header for header in headers):
            return table
    return None


def parse_uvo_documents(html: str, source_url: str) -> List[Dict[str, Any]]:
    """Parse UVO documents listing rows into josephine-compatible shape."""
    soup = BeautifulSoup(html, "html.parser")
    table = find_documents_table(soup)
    if table is None:
        return []

    tbody = table.find("tbody")
    if tbody is None:
        return []

    rows: List[Dict[str, Any]] = []
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 4:
            continue

        document_type = clean_whitespace(tds[0].get_text(" ", strip=True))
        document_name = clean_whitespace(tds[1].get_text(" ", strip=True))
        uploaded_at = clean_whitespace(tds[3].get_text(" ", strip=True))
        detail_url = extract_document_detail_url(tr, source_url)

        rows.append(
            {
                "document_name": document_name,
                "document_title": document_name or None,
                "document_type": document_type,
                "file_size": None,
                "uploaded_at": uploaded_at,
                "link": detail_url,
                "is_external_link": False,
            }
        )

    return rows


def parse_document_file_metadata(cell: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract file metadata from 'Súbor' table cell in document detail."""
    parsed: Dict[str, Optional[str]] = {
        "document_title": None,
        "file_size": None,
        "download_link": None,
    }

    for text in cell.stripped_strings:
        cleaned = clean_whitespace(text)
        normalized = normalize_text(cleaned)

        if normalized.startswith("nazov suboru"):
            parsed["document_title"] = cleaned.split(":", 1)[-1].strip() or None
        elif normalized.startswith("velkost"):
            parsed["file_size"] = cleaned.split(":", 1)[-1].strip() or None

    link = cell.find("a", href=True)
    if link is not None:
        parsed["download_link"] = link.get("href")

    return parsed


def resolve_document_download_link(
    session: requests.Session,
    link_or_detail_url: str,
) -> Dict[str, Optional[str]]:
    """Resolve a UVO document listing link into direct download link and metadata."""
    if "/vyhladavanie/vyhladavanie-dokumentov/download/" in link_or_detail_url:
        return {
            "download_link": link_or_detail_url,
            "document_title": None,
            "file_size": None,
        }

    response = session.get(link_or_detail_url, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tr in soup.select("main table tr"):
        th = tr.find("th")
        td = tr.find("td")
        if th is None or td is None:
            continue

        if "subor" not in normalize_text(th.get_text(" ", strip=True)):
            continue

        parsed = parse_document_file_metadata(td)
        href = parsed.get("download_link")
        if href:
            parsed["download_link"] = urljoin(link_or_detail_url, href)
        return parsed

    return {
        "download_link": None,
        "document_title": None,
        "file_size": None,
    }


def to_documents_url(detail_url: str) -> str:
    """Convert a tender detail URL into its documents tab URL."""
    parsed = urlparse(detail_url)
    new_path = re.sub(
        r"/vyhladavanie/vyhladavanie-zakaziek/detail/(\d+)",
        r"/vyhladavanie/vyhladavanie-zakaziek/dokumenty/\1",
        parsed.path,
    )
    return urlunparse(parsed._replace(path=new_path))


def process_tender(
    url: str,
    session: requests.Session,
    pdf_dir: Path,
    min_chars: int,
    ocr_lang: str,
    openai_client: Optional[OpenAI],
    openai_model: str,
) -> Dict[str, Any]:
    """Scrape one UVO tender and enrich matching result documents."""
    response = session.get(url, timeout=60)
    response.raise_for_status()
    tender = parse_uvo_tender_detail(response.text, url)

    documents_url = to_documents_url(url)
    docs_response = session.get(documents_url, timeout=60)
    docs_response.raise_for_status()
    tender["documents"] = parse_uvo_documents(docs_response.text, documents_url)

    target_docs = collect_target_documents(tender.get("documents", []))
    tender["result_document_count"] = len(target_docs)
    tender["parts"] = []

    tender_id = tender.get("tender_id") or "unknown"
    for index, doc in enumerate(target_docs, start=1):
        part_payload: Dict[str, Any] = {
            "part_number": index,
            "document": doc,
        }

        detail_or_download_url = doc.get("link")
        if not detail_or_download_url:
            part_payload["error"] = "missing_document_link"
            tender["parts"].append(part_payload)
            continue

        try:
            resolved = resolve_document_download_link(session, str(detail_or_download_url))
        except Exception as exc:
            part_payload["error"] = f"resolve_document_link_failed: {exc}"
            tender["parts"].append(part_payload)
            continue

        direct_download_url = resolved.get("download_link")
        if resolved.get("document_title") and not doc.get("document_title"):
            doc["document_title"] = resolved["document_title"]
        if resolved.get("file_size") and not doc.get("file_size"):
            doc["file_size"] = resolved["file_size"]
        if direct_download_url:
            doc["link"] = direct_download_url

        if not direct_download_url:
            part_payload["error"] = "download_link_not_found"
            tender["parts"].append(part_payload)
            continue

        title_hint = str(doc.get("document_title") or doc.get("document_name") or "result")
        filename = safe_filename(f"{tender_id}_{index}_{title_hint}")
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        local_path = pdf_dir / filename

        if not download_file(session, str(direct_download_url), local_path):
            part_payload["error"] = "download_failed"
            part_payload["pdf_local_path"] = str(local_path)
            tender["parts"].append(part_payload)
            continue

        pdf_text = extract_pdf_text_with_fallback(
            local_path,
            min_chars=min_chars,
            ocr_lang=ocr_lang,
        )
        part_payload["pdf_local_path"] = str(local_path)
        part_payload["pdf_text"] = pdf_text

        if openai_client is not None and pdf_text.strip():
            try:
                ai_data = analyze_with_openai(
                    pdf_text,
                    client=openai_client,
                    model=openai_model,
                )
                ai_data.pop("tender_dates", None)
                part_payload.update(ai_data)
            except Exception as exc:
                part_payload["ai_extracted_error"] = str(exc)
        elif openai_client is None:
            part_payload["ai_extracted_error"] = "openai_disabled"
        else:
            part_payload["ai_extracted_error"] = "empty_pdf_text"

        tender["parts"].append(part_payload)

    return tender


def is_uvo_tender_url(url: str) -> bool:
    """Return True only for UVO tender detail links."""
    return normalize_uvo_tender_url(url) is not None


def load_uvo_urls_from_contracts(contracts_json_path: str) -> List[str]:
    """Load UVO public_procurement_url values from contracts JSON."""
    path = Path(contracts_json_path)
    if not path.exists():
        logger.warning("contracts_json file not found: %s", contracts_json_path)
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read contracts_json %s: %s", contracts_json_path, exc)
        return []

    if not isinstance(payload, list):
        logger.warning("contracts_json must contain a top-level list: %s", contracts_json_path)
        return []

    urls: List[str] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        value = row.get("public_procurement_url")
        if not isinstance(value, str):
            continue

        normalized = normalize_uvo_tender_url(value)
        if normalized:
            urls.append(normalized)

    return urls


def load_urls(args: argparse.Namespace) -> List[str]:
    """Load target URLs from CLI arguments and optional text file."""
    urls: List[str] = []
    if args.url:
        urls.extend(args.url)

    if args.urls_file:
        file_lines = Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        urls.extend(line.strip() for line in file_lines if line.strip())

    if args.contracts_json:
        urls.extend(load_uvo_urls_from_contracts(args.contracts_json))

    seen = set()
    unique_urls: List[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
    return unique_urls


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape UVO tenders and enrich result PDFs with OpenAI"
    )
    parser.add_argument(
        "--url",
        action="append",
        help="Tender detail URL (repeatable)",
    )
    parser.add_argument(
        "--urls-file",
        type=str,
        default=None,
        help="Text file containing one tender URL per line",
    )
    parser.add_argument(
        "--contracts-json",
        type=str,
        default=None,
        help=(
            "Contracts JSON path; UVO URLs are loaded from each "
            "record's public_procurement_url"
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default="data/uvo_tenders.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="data/uvo_pdfs",
        help="Directory where target result PDFs are downloaded",
    )
    parser.add_argument(
        "--ocr-min-chars",
        type=int,
        default=30,
        help="Minimum non-space chars before OCR fallback",
    )
    parser.add_argument(
        "--ocr-lang",
        type=str,
        default="slk+eng",
        help="Tesseract OCR language(s)",
    )
    parser.add_argument(
        "--openai-model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model for participant/date extraction",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key (default: OPENAI_API_KEY env)",
    )
    parser.add_argument(
        "--skip-openai",
        action="store_true",
        help="Skip OpenAI extraction and only scrape/OCR",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    urls = load_urls(args)
    if not urls:
        logger.warning("No UVO tender URLs found. Nothing to do.")
        return 0

    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    openai_client: Optional[OpenAI] = None
    if not args.skip_openai:
        if not api_key:
            logger.error("Missing OpenAI API key (set OPENAI_API_KEY or --api-key)")
            return 1
        openai_client = OpenAI(api_key=api_key)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        }
    )

    out_path = Path(args.out)
    existing_records: List[Dict[str, Any]] = []
    known_tender_urls = set()

    if out_path.exists():
        existing_text = out_path.read_text(encoding="utf-8").strip()
        if existing_text:
            loaded = json.loads(existing_text)
            if not isinstance(loaded, list):
                raise ValueError(
                    f"Existing output file {args.out} must contain a JSON array"
                )
            existing_records = loaded
            known_tender_urls = {
                str(item.get("tender_url"))
                for item in existing_records
                if isinstance(item, dict) and item.get("tender_url")
            }

    output_records: List[Dict[str, Any]] = list(existing_records)
    pdf_dir = Path(args.pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    for url in urls:
        if url in known_tender_urls:
            logger.info("Skipping already saved tender URL: %s", url)
            continue

        try:
            logger.info("Processing %s", url)
            tender = process_tender(
                url=url,
                session=session,
                pdf_dir=pdf_dir,
                min_chars=args.ocr_min_chars,
                ocr_lang=args.ocr_lang,
                openai_client=openai_client,
                openai_model=args.openai_model,
            )
            output_records.append(tender)
            known_tender_urls.add(url)
        except Exception as exc:
            logger.exception("Failed processing %s: %s", url, exc)
            output_records.append(
                {
                    "tender_url": url,
                    "error": str(exc),
                }
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Saved %d tenders to %s (existing=%d, added=%d)",
        len(output_records),
        out_path,
        len(existing_records),
        max(0, len(output_records) - len(existing_records)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
