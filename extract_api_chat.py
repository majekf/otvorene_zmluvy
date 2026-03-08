#!/usr/bin/env python
"""Analyze contract text with OpenAI and write scanned_* fields back to JSON."""

import asyncio
import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
import requests
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from tqdm import tqdm

# Load environment variables from .env (if present) for OPENAI_API_KEY.
load_dotenv()

INPUT_FILE = "data/contracts.json"
PDF_DIR = "data/pdfs"
MODEL_NAME = "gpt-4o-mini"
DEBUG_PRINT_FULL_TEXT = False
DEBUG_TEXT_PREVIEW = 1500


def download_pdf(url: str, contract_id: str, pdf_dir: str) -> Optional[Path]:
    """Download PDF to local cache; reuse existing file when present."""
    try:
        pdf_path = Path(pdf_dir) / f"{contract_id}.pdf"

        if pdf_path.exists():
            return pdf_path

        response = requests.get(url, timeout=90)
        response.raise_for_status()

        with open(pdf_path, "wb") as f:
            f.write(response.content)

        return pdf_path

    except Exception as e:
        print(f"[ERROR] PDF download failed for {contract_id}: {e}")
        return None


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text using pdfplumber (no OCR in this stage)."""
    all_text = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        return "\n".join(all_text)

    except Exception as e:
        print(f"[ERROR] PDF extraction failed for {pdf_path}: {e}")
        return ""


def clean_extracted_text(text: str) -> str:
    """Normalize whitespace before sending text to LLM."""
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(\b\w)\s+(?=\w\b)", r"\1", text)
    return text.strip()


def debug_print_text(contract_id: str, text: str) -> None:
    """Optional debug output showing extracted text length and preview."""
    print(f"\n[DEBUG] Contract ID: {contract_id}")
    print(f"[DEBUG] Extracted text length: {len(text)}")

    if DEBUG_PRINT_FULL_TEXT:
        print(f"[DEBUG] Full text:\n{text}\n")
    else:
        print(f"[DEBUG] Preview:\n{text[:DEBUG_TEXT_PREVIEW]}\n")


def clean_json_response(content: str) -> Dict[str, Any]:
    """Handle plain JSON and JSON wrapped in markdown/text."""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Invalid JSON from model")


def _build_contract_prompt(text: str) -> str:
    """Build extraction prompt from contract text."""
    """Ask OpenAI to extract normalized contract metadata as JSON."""
    snippet = text[:22000]
    return f"""
Extract structured data from Slovak public procurement contract.

Return JSON:

{{
  "service_type": "...",
  "suggested_title": "...",
  "related_contract_number": "...",
  "supplier_ico": "...",
  "contract_value": null,
  "payment_reason": "...",
  "contract_type": "konecna | ciastkova | ramcova | dodatok",
  "summary": "...",
  "subcontractors": null
}}

Rules:
- Only explicit data
- Missing -> null
- ICO = 8 digits

CONTRACT TEXT:
---
{snippet}
---
"""


def analyze_contract(text: str, client: OpenAI, model_name: str) -> Dict[str, Any]:
    """Synchronous OpenAI extraction helper (kept for compatibility)."""
    prompt = _build_contract_prompt(text)
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    return clean_json_response(content)


async def analyze_contract_async(
    text: str,
    client: AsyncOpenAI,
    model_name: str,
) -> Dict[str, Any]:
    """Asynchronous OpenAI extraction for one contract text."""
    prompt = _build_contract_prompt(text)
    response = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    return clean_json_response(content)


async def analyze_contracts_batch_async(
    work_items: List[Tuple[int, str, str]],
    api_key: str,
    model_name: str,
    max_concurrency: int,
) -> List[Tuple[int, str, Optional[Dict[str, Any]], Optional[str]]]:
    """Run OpenAI extraction concurrently and return per-item results."""
    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async def _worker(
        contract_index: int,
        contract_id: str,
        text: str,
    ) -> Tuple[int, str, Optional[Dict[str, Any]], Optional[str]]:
        try:
            async with semaphore:
                ai_data = await analyze_contract_async(
                    text,
                    client=client,
                    model_name=model_name,
                )
            return contract_index, contract_id, ai_data, None
        except Exception as e:
            return contract_index, contract_id, None, str(e)

    tasks = [
        _worker(contract_index, contract_id, text)
        for contract_index, contract_id, text in work_items
    ]
    return await asyncio.gather(*tasks)


def add_scanned_fields(contract: Dict[str, Any], ai_data: Dict[str, Any]) -> None:
    """Map AI extraction output to persistent scanned_* fields."""
    contract["scanned_service_type"] = ai_data.get("service_type")
    contract["scanned_suggested_title"] = ai_data.get("suggested_title")
    contract["scanned_related_contract_number"] = ai_data.get("related_contract_number")
    contract["scanned_supplier_ico"] = ai_data.get("supplier_ico")
    contract["scanned_contract_value"] = ai_data.get("contract_value")
    contract["scanned_payment_reason"] = ai_data.get("payment_reason")
    contract["scanned_contract_type"] = ai_data.get("contract_type")
    contract["scanned_summary"] = ai_data.get("summary")
    contract["scanned_subcontractors"] = ai_data.get("subcontractors")


def process_contracts_file(
    input_file: str = INPUT_FILE,
    pdf_dir: str = PDF_DIR,
    model_name: str = MODEL_NAME,
    api_key: Optional[str] = None,
    skip_processed: bool = True,
    prefer_existing_pdf_text: bool = True,
    max_concurrency: int = 5,
) -> Dict[str, int]:
    """Analyze contracts and persist scanned_* fields back to input JSON file."""
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_api_key:
        raise ValueError("OPENAI_API_KEY is not set and no --api-key was provided")

    Path(pdf_dir).mkdir(parents=True, exist_ok=True)
    if max_concurrency <= 0:
        raise ValueError("max_concurrency must be greater than 0")

    with open(input_path, "r", encoding="utf-8") as f:
        contracts = json.load(f)

    if not isinstance(contracts, list):
        raise ValueError("Input JSON must be a top-level array")

    stats = {
        "total": len(contracts),
        "processed": 0,
        "skipped": 0,
        "failed": 0,
    }
    work_items: List[Tuple[int, str, str]] = []

    for contract_index, contract in enumerate(tqdm(contracts)):
        if not isinstance(contract, dict):
            stats["skipped"] += 1
            continue

        contract_id = str(contract.get("contract_id", "unknown"))

        if skip_processed and contract.get("scanned_service_type"):
            stats["skipped"] += 1
            continue

        raw_text = ""
        if prefer_existing_pdf_text:
            raw_text = str(contract.get("pdf_text") or "")

        if not raw_text.strip():
            pdf_url = contract.get("pdf_url")
            if not pdf_url:
                print(f"[WARN] Missing pdf_url and no pdf_text: {contract_id}")
                stats["skipped"] += 1
                continue

            pdf_path = download_pdf(str(pdf_url), contract_id, pdf_dir)
            if not pdf_path:
                stats["failed"] += 1
                continue

            raw_text = extract_pdf_text(pdf_path)

        if not raw_text.strip():
            print(f"[WARN] Empty text: {contract_id}")
            stats["skipped"] += 1
            continue

        text = clean_extracted_text(raw_text)
        debug_print_text(contract_id, text)

        work_items.append((contract_index, contract_id, text))

    if work_items:
        results = asyncio.run(
            analyze_contracts_batch_async(
                work_items=work_items,
                api_key=resolved_api_key,
                model_name=model_name,
                max_concurrency=max_concurrency,
            )
        )

        for contract_index, contract_id, ai_data, error_text in results:
            if error_text:
                print(f"[ERROR] AI failed for {contract_id}: {error_text}")
                stats["failed"] += 1
                continue

            if ai_data is None:
                stats["failed"] += 1
                continue

            add_scanned_fields(contracts[contract_index], ai_data)
            stats["processed"] += 1

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(contracts, f, ensure_ascii=False, indent=2)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze contracts JSON with OpenAI and write scanned_* fields"
    )
    parser.add_argument("--input", type=str, default=INPUT_FILE)
    parser.add_argument("--pdf-dir", type=str, default=PDF_DIR)
    parser.add_argument("--model", type=str, default=MODEL_NAME)
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
        help="Re-analyze records even when scanned_* fields already exist",
    )
    parser.add_argument(
        "--ignore-existing-pdf-text",
        action="store_true",
        help="Always re-read text from PDF instead of using existing pdf_text field",
    )

    args = parser.parse_args()

    stats = process_contracts_file(
        input_file=args.input,
        pdf_dir=args.pdf_dir,
        model_name=args.model,
        api_key=args.api_key,
        skip_processed=not args.no_skip_processed,
        prefer_existing_pdf_text=not args.ignore_existing_pdf_text,
        max_concurrency=args.max_concurrency,
    )

    print(
        "[SUCCESS] AI analysis complete: "
        f"total={stats['total']}, processed={stats['processed']}, "
        f"skipped={stats['skipped']}, failed={stats['failed']}"
    )


if __name__ == "__main__":
    main()
