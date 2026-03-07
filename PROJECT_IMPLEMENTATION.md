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
