#!/usr/bin/env python
"""Scrape JOSEPHINE tender summaries and enrich result PDFs with OpenAI."""

import argparse
import json
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# Reuse CRZ OCR implementation.
sys.path.insert(0, str(Path(__file__).parent / "src"))
from scraper import extract_text_with_ocr  # type: ignore  # noqa: E402


# Align with existing pipeline scripts: load .env if present.
load_dotenv()


logger = logging.getLogger(__name__)

BASE_URL = "https://josephine.proebiz.com"
TARGET_DOC_TYPE = "informacia o vysledku vyhodnotenia ponuk"

INFO_FIELD_TRANSLATIONS = {
    "ID zákazky": "notice_id",
    "Názov predmetu": "subject_name",
    "Číslo spisu": "file_reference",
    "Číslo z vestníka VO": "bulletin_vo_number",
    "Číslo z vestníka EU": "bulletin_eu_number",
    "Druh postupu": "procedure_type",
    "Typ šablóny": "template_type",
    "Druh obstarávania": "procurement_type",
    "Výsledok obstarávania": "procurement_result",
    "Predpokladaná hodnota": "estimated_value",
    "Hlavný CPV": "main_cpv",
    "Doplňujúci CPV": "additional_cpv",
    "Obstarávanie sa delí na časti": "is_divided_into_parts",
    "Elektronická aukcia": "electronic_auction",
    "Centrálne obstarávanie": "central_procurement",
    "NUTS": "nuts",
    "Stručný opis": "short_description",
    "Kritérium na vyhodnotenie ponúk": "evaluation_criterion",
    "Na vyhodnotenie je určená cena": "evaluation_price_basis",
}

BUYER_FIELD_TRANSLATIONS = {
    "Názov organizácie": "buyer_organization_name",
    "Adresa": "buyer_address",
    "Procesný garant": "buyer_process_guarantor",
    "Internetový odkaz na profil obstarávateľa": "buyer_profile_url",
}

TERM_FIELD_TRANSLATIONS = {
    "Lehota na predkladanie ponúk": "offer_submission_deadline",
    "Plánované otváranie ponúk": "planned_opening_time",
}

DOCUMENT_FIELD_TRANSLATIONS = {
    "Názov dokumentu": "document_name",
    "Názov dokumentu (title)": "document_title",
    "Typ": "document_type",
    "Veľkosť": "file_size",
    "Nahrané": "uploaded_at",
}


def normalize_text(value: Optional[str]) -> str:
    """Normalize text for accent-insensitive comparisons."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    no_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    return no_accents.strip().lower()


def clean_whitespace(value: str) -> str:
    """Collapse repeated whitespace in extracted text."""
    return re.sub(r"\s+", " ", value).strip()


def to_snake_case(value: str) -> str:
    """Convert arbitrary label to ASCII snake_case."""
    normalized = normalize_text(value)
    snake = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return snake or "field"


def parse_cpv_entries(value: Optional[str]) -> List[Dict[str, str]]:
    """Parse CPV text like '12345678-9 - Name 98765432-1 - Name' into objects."""
    if not value:
        return []

    text = clean_whitespace(value)
    matches = list(re.finditer(r"(\d{8}-\d)\s*-\s*(.*?)(?=\s+\d{8}-\d\s*-|$)", text))
    entries: List[Dict[str, str]] = []
    for match in matches:
        code = match.group(1).strip()
        name = clean_whitespace(match.group(2))
        if code and name:
            entries.append({"code": code, "name": name})
    return entries


def is_readable_text(text: Optional[str], min_chars: int = 30) -> bool:
    """Heuristic for deciding whether OCR fallback is needed."""
    if not text:
        return False
    return len("".join(text.split())) >= min_chars


def extract_json_object(raw: str) -> Dict[str, Any]:
    """Parse JSON response that might be wrapped in markdown or text."""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("OpenAI response did not contain JSON object")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI JSON payload is not an object")
    return parsed


def parse_dl_as_map(dl: Optional[BeautifulSoup]) -> Dict[str, str]:
    """Convert a JOSEPHINE <dl> list into a label->value map."""
    if dl is None:
        return {}

    result: Dict[str, str] = {}
    for dt in dl.find_all("dt"):
        label = clean_whitespace(dt.get_text(" ", strip=True))
        dd = dt.find_next_sibling("dd")
        if not label or dd is None:
            continue
        value = clean_whitespace(dd.get_text(" ", strip=True))
        result[label] = value
    return result


def find_section_dl(soup: BeautifulSoup, title: str) -> Optional[BeautifulSoup]:
    """Find <dl> immediately following a given section header."""
    wanted = normalize_text(title)
    for h2 in soup.find_all("h2"):
        if normalize_text(h2.get_text(" ", strip=True)) != wanted:
            continue

        current = h2
        while True:
            current = current.find_next_sibling()  # type: ignore[assignment]
            if current is None:
                return None
            if getattr(current, "name", None) == "dl":
                return current
            if getattr(current, "name", None) == "h2":
                return None
    return None


def find_documents_table(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """Find table under section 'Dokumenty'."""
    wanted = normalize_text("Dokumenty")
    for h2 in soup.find_all("h2"):
        if normalize_text(h2.get_text(" ", strip=True)) != wanted:
            continue

        current = h2
        while True:
            current = current.find_next_sibling()  # type: ignore[assignment]
            if current is None:
                return None
            if getattr(current, "name", None) == "table":
                return current
            if getattr(current, "name", None) == "h2":
                return None
    return None


def parse_documents(table: Optional[BeautifulSoup], source_url: str) -> List[Dict[str, Any]]:
    """Parse document table rows and keep all requested columns + link."""
    if table is None:
        return []

    rows: List[Dict[str, Any]] = []
    tbody = table.find("tbody")
    if tbody is None:
        return rows

    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 4:
            continue

        name_cell = tds[0]
        name_span = None
        for candidate in name_cell.find_all("span", title=True):
            classes = candidate.get("class", [])
            if any("file-icon" in cls for cls in classes):
                continue
            name_span = candidate
            break
        if name_span is None:
            name_span = name_cell.find("span", title=True)
        visible_name = clean_whitespace(name_cell.get_text(" ", strip=True))
        name_title = clean_whitespace(name_span["title"]) if name_span else ""

        action_link = tds[-1].find("a", href=True)
        link_url = urljoin(source_url, action_link["href"]) if action_link else None
        action_icon = ""
        if action_link:
            icon = action_link.find("span")
            if icon and icon.has_attr("class"):
                action_icon = " ".join(icon.get("class", []))

        rows.append(
            {
                "document_name": visible_name,
                "document_title": name_title or None,
                "document_type": clean_whitespace(tds[1].get_text(" ", strip=True)),
                "file_size": clean_whitespace(tds[2].get_text(" ", strip=True)),
                "uploaded_at": clean_whitespace(tds[3].get_text(" ", strip=True)),
                "link": link_url,
                "is_external_link": "external-link" in action_icon,
            }
        )

    return rows


def parse_tender_summary(html: str, source_url: str) -> Dict[str, Any]:
    """Extract requested sections and documents from one JOSEPHINE summary page."""
    soup = BeautifulSoup(html, "html.parser")

    tender_id_match = re.search(r"/tender/(\d+)/", source_url)
    tender_id = tender_id_match.group(1) if tender_id_match else None

    info = parse_dl_as_map(find_section_dl(soup, "Informácie"))
    buyer = parse_dl_as_map(find_section_dl(soup, "Verejný obstarávateľ"))
    terms = parse_dl_as_map(find_section_dl(soup, "Termíny"))
    docs = parse_documents(find_documents_table(soup), source_url)

    title_tag = soup.find("title")
    page_title = clean_whitespace(title_tag.get_text(" ", strip=True)) if title_tag else None

    result: Dict[str, Any] = {
        "tender_url": source_url,
        "tender_id": tender_id,
        "page_title": page_title,
        "documents": docs,
    }

    for key, value in info.items():
        result[INFO_FIELD_TRANSLATIONS.get(key, f"info_{to_snake_case(key)}")] = value

    for key, value in buyer.items():
        result[BUYER_FIELD_TRANSLATIONS.get(key, f"buyer_{to_snake_case(key)}")] = value

    for key, value in terms.items():
        result[TERM_FIELD_TRANSLATIONS.get(key, f"term_{to_snake_case(key)}")] = value

    # Emit additional CPV as structured entries for easier downstream usage.
    if "additional_cpv" in result:
        result["additional_cpv"] = parse_cpv_entries(str(result.get("additional_cpv") or ""))

    return result


def safe_filename(value: str) -> str:
    """Build a filesystem-safe file stem."""
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("._")
    return value or "document"


def download_file(session: requests.Session, url: str, output_path: Path) -> bool:
    """Download one file to disk."""
    try:
        response = session.get(url, timeout=90)
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return True
    except Exception as exc:
        logger.warning("File download failed %s: %s", url, exc)
        return False


def extract_pdf_text_with_fallback(
    pdf_path: Path,
    min_chars: int = 30,
    ocr_lang: str = "slk+eng",
) -> str:
    """Extract text with pdfplumber and OCR fallback when too short."""
    try:
        text_parts: List[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        text = "\n".join(text_parts).strip()
    except Exception as exc:
        logger.warning("pdfplumber extraction failed for %s: %s", pdf_path, exc)
        text = ""

    if is_readable_text(text, min_chars=min_chars):
        return text[:50000]

    logger.info("Using OCR fallback for %s", pdf_path)
    ocr_text = extract_text_with_ocr(str(pdf_path), lang=ocr_lang)
    if ocr_text:
        return ocr_text[:50000]
    return text[:50000]


def build_openai_prompt(pdf_text: str) -> str:
    """Create extraction prompt for participant data only."""
    snippet = pdf_text[:30000]
    return f"""
Extract data from a Slovak tender result document.

Return strict JSON object with this exact schema:
{{
  "participants": [
    {{
      "ico": "string or null",
      "name": "string or null",
      "proposed_sum": "string or null",
      "proposed_sum_eur": 0.0
    }}
  ],
  "notes": "string or null"
}}

Rules:
- Use only information explicitly present in the document.
- Keep participant ordering as in source.
- If value is unknown use null.
- ICO should be exactly 8 digits when present.
- proposed_sum keeps original textual amount (e.g. "1 234 567,89 EUR").
- proposed_sum_eur must be number when clear, else null.
- Return only JSON, no markdown.

DOCUMENT TEXT:
---
{snippet}
---
"""


def analyze_with_openai(
    text: str,
    client: OpenAI,
    model: str,
) -> Dict[str, Any]:
    """Request structured participant extraction from OpenAI."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": build_openai_prompt(text)}],
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    return extract_json_object(content)


def collect_target_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Select documents with type 'Informácia o výsledku vyhodnotenia ponúk'."""
    matches: List[Dict[str, Any]] = []
    for doc in documents:
        doc_type = normalize_text(str(doc.get("document_type") or ""))
        if TARGET_DOC_TYPE in doc_type:
            matches.append(doc)
    return matches


def process_tender(
    url: str,
    session: requests.Session,
    pdf_dir: Path,
    min_chars: int,
    ocr_lang: str,
    openai_client: Optional[OpenAI],
    openai_model: str,
) -> Dict[str, Any]:
    """Scrape one tender page and enrich all matching result documents."""
    response = session.get(url, timeout=60)
    response.raise_for_status()
    tender = parse_tender_summary(response.text, url)

    target_docs = collect_target_documents(tender.get("documents", []))
    tender["result_document_count"] = len(target_docs)
    tender["parts"] = []

    tender_id = tender.get("tender_id") or "unknown"
    for index, doc in enumerate(target_docs, start=1):
        part_payload: Dict[str, Any] = {
            "part_number": index,
            "document": doc,
        }

        link = doc.get("link")
        if not link:
            part_payload["error"] = "missing_document_link"
            tender["parts"].append(part_payload)
            continue

        title_hint = str(doc.get("document_title") or doc.get("document_name") or "result")
        filename = safe_filename(f"{tender_id}_{index}_{title_hint}")
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        local_path = pdf_dir / filename

        if not download_file(session, str(link), local_path):
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
                # Keep output stable even if model returns extra keys.
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


def load_urls(args: argparse.Namespace) -> List[str]:
    """Load target URLs from CLI arguments and optional text file."""
    urls: List[str] = []
    if args.url:
        urls.extend(args.url)

    if args.urls_file:
        file_lines = Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        urls.extend(line.strip() for line in file_lines if line.strip())

    if args.contracts_json:
        urls.extend(load_josephine_urls_from_contracts(args.contracts_json))

    seen = set()
    unique_urls: List[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        unique_urls.append(u)
    return unique_urls


def is_josephine_tender_url(url: str) -> bool:
    """Return True only for JOSEPHINE tender summary links."""
    if not url:
        return False
    return bool(
        re.match(
            r"^https?://josephine\.proebiz\.com/.*/tender/\d+/summary/?$",
            url.strip(),
            flags=re.IGNORECASE,
        )
    )


def load_josephine_urls_from_contracts(contracts_json_path: str) -> List[str]:
    """Load JOSEPHINE public_procurement_url values from contracts JSON."""
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
        if isinstance(value, str) and is_josephine_tender_url(value):
            urls.append(value.strip())

    return urls


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape JOSEPHINE tenders and enrich result PDFs with OpenAI"
    )
    parser.add_argument(
        "--url",
        action="append",
        help="Tender summary URL (repeatable)",
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
            "Contracts JSON path; JOSEPHINE URLs are loaded from each "
            "record's public_procurement_url"
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default="data/josephine_tenders.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="data/josephine_pdfs",
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
        logger.warning("No JOSEPHINE tender URLs found. Nothing to do.")
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
