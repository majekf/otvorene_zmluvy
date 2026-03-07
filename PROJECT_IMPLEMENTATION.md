# Project Implementation Changes

## 2026-03-07 - OCR Support for Non-Readable PDFs

### Problem
Some CRZ PDF attachments are scanned/image-based documents. For these files, direct text extraction can return empty or near-empty output (`pdf_text` missing or unreadable).

### What Changed

1. Added OCR fallback in `src/scraper.py`.
- New helper `_is_readable_text(...)` checks whether extracted text has enough non-space characters.
- New helper `extract_text_with_ocr(...)` renders PDF pages to images via `pypdfium2` and runs `tesseract` OCR.
- `download_and_extract_pdf(...)` now:
  - Uses `pdfplumber` first.
  - Automatically runs OCR fallback if extracted text is too short.
  - Also attempts OCR if `pdfplumber` extraction raises an exception.

2. Added JSON OCR backfill function in `src/scraper.py`.
- New function `enrich_json_with_ocr_text(...)` reads a contracts JSON array and fills missing/unreadable `pdf_text` using `pdf_local_path`.
- Supports both absolute and relative `pdf_local_path` values.

3. Extended CLI in `scrape_crz.py`.
- Added flags:
  - `--ocr-json`
  - `--ocr-out`
  - `--ocr-min-chars`
  - `--ocr-lang`
- Running with `--ocr-json` enables OCR enrichment mode for existing JSON files.

### Usage

```bash
python scrape_crz.py --ocr-json data/contracts.json --ocr-out data/contracts_ocr.json
```

Optional:

```bash
python scrape_crz.py --ocr-json data/contracts.json --ocr-min-chars 30 --ocr-lang slk+eng
```

### Operational Note
OCR fallback requires `tesseract` binary available in system `PATH`. If not installed, scraper continues without OCR and logs a warning.

## 2026-03-07 - Async PDF Text Extraction + OCR Stability

### Problem
After adding OCR fallback, scraping still waited for PDF text extraction to finish per contract. During higher parallelism, OCR fallback could also trigger native crashes (`exit code -11`) in Step 1/3.

### What Changed

1. Made PDF text extraction asynchronous during scraping in `src/scraper.py`.
- `download_and_extract_pdf(...)` now schedules background extraction jobs when workers are enabled.
- New helper `_extract_pdf_text_with_fallback(...)` centralizes extraction flow:
  - Try `pdfplumber` first.
  - If text is unreadable, run OCR fallback.
  - If `pdfplumber` fails, run OCR fallback.
- `scrape_contracts(...)` now keeps scraping while text extraction runs in background workers.
- Scraper waits for all background extraction jobs at the end, then writes finalized `pdf_text` values.

2. Added worker control for scraping text extraction.
- New argument in `scrape_contracts(...)`: `ocr_workers`.
- New CLI flag in `scrape_crz.py`: `--ocr-workers`.
- New pipeline flag in `run_pipeline.py`: `--ocr-workers` (forwarded to `scrape_crz.py`).

3. Hardened OCR fallback against parallel native crashes.
- Added a process-wide OCR lock in `src/scraper.py`.
- OCR fallback is now executed via `_extract_text_with_ocr_threadsafe(...)`, which serializes OCR calls.
- This keeps asynchronous PDF extraction benefits while avoiding OCR thread-safety crashes.

### Usage

Scraper only:

```bash
python scrape_crz.py --start-page 1 --max-pages 3 --ocr-workers 4 --out out.json
```

Full pipeline:

```bash
python run_pipeline.py --start-page 11 --max-pages 10 --ocr-workers 4 --max-concurrency 8
```

### Validation
- `py_compile` passed for updated files.
- Smoke tests passed for:
  - `scrape_crz.py` with async extraction enabled.
  - `run_pipeline.py` with `--ocr-workers` forwarding.
  - Filtered slice that previously crashed now completes successfully.
