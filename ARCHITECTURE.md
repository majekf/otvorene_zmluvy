# CRZ Scraper - Project Documentation

## Overview

This is a production-ready web scraper for the Central Register of Contracts (Centrálny register zmlúv) at https://www.crz.gov.sk/. It extracts contract data, downloads PDFs, and outputs structured data in NDJSON format.

## Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/arath/crz_gov_scraping.git
cd crz_gov_scraping

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run scraper
python scrape_crz.py --start-page 1 --max-pages 3 --out contracts.ndjson

# 5. View results
head -1 contracts.ndjson | jq .
```

## Project Structure

```
crz_gov_scraping/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── scraper.py               # Core scraping logic
│   ├── models.py                # Pydantic v2 data models (Phase 0)
│   ├── engine.py                # In-memory query & aggregation engine (Phase 1)
│   ├── api.py                   # FastAPI REST endpoints (Phase 2)
│   └── config.py                # Environment-variable config (Phase 2)
├── frontend/                    # React + TypeScript + Vite (Phase 3)
│   ├── src/
│   │   ├── types.ts             # TypeScript interfaces (mirrors backend models)
│   │   ├── api.ts               # API client (fetch wrappers for all endpoints)
│   │   ├── url-state.ts         # URL-state manager (parse/encode filters/sort/page)
│   │   ├── utils.ts             # Formatting utilities (EUR, compact, date)
│   │   ├── App.tsx              # Root layout with react-router routes
│   │   ├── main.tsx             # Entry point with BrowserRouter
│   │   ├── components/          # Reusable UI components
│   │   │   ├── FilterBar.tsx    # Filter controls (institution, date, category, etc.)
│   │   │   ├── GroupByControl.tsx # Group-by toggle buttons
│   │   │   ├── TreemapChart.tsx # D3 treemap visualization with drill-down
│   │   │   ├── BarChart.tsx     # Recharts horizontal bar chart
│   │   │   ├── CategoryAccordion.tsx # Expandable group rows
│   │   │   ├── ContractsTable.tsx # Multi-column sortable table
│   │   │   ├── Pagination.tsx   # Page navigation
│   │   │   ├── ErrorBoundary.tsx # Error boundary with retry (Phase 8)
│   │   │   └── LoadingSkeleton.tsx # Skeleton loading screens (Phase 8)
│   │   ├── pages/               # Route-level page components
│   │   │   ├── Dashboard.tsx    # Home: filters + viz + table + pagination
│   │   │   ├── ContractDetail.tsx # Contract info, PDF link, summary
│   │   │   ├── InstitutionProfile.tsx # Institution stats, trend, vendors
│   │   │   ├── VendorProfile.tsx # Vendor stats, trend, institutions
│   │   │   ├── BenchmarkView.tsx # Institution benchmark comparison (Phase 6)
│   │   │   ├── TimeView.tsx     # Time trends with overlays (Phase 6)
│   │   │   └── GlobalView.tsx   # Global rankings table (Phase 6)
│   │   └── __tests__/           # 135+ frontend unit tests (vitest)
│   ├── vite.config.ts           # Vite + Tailwind + vitest + proxy config
│   └── package.json             # Node.js dependencies
├── scripts/
│   ├── migrate_ndjson.py        # NDJSON → JSON migration (Phase 0)
│   ├── start_dev.sh             # Unix dev startup script (Phase 8)
│   └── start_dev.ps1            # Windows dev startup script (Phase 8)
├── tests/
│   ├── __init__.py
│   ├── test_parser.py           # Unit tests for parsing
│   ├── test_integration.py      # Integration tests
│   ├── test_models.py           # Model & sample-data tests (Phase 0)
│   ├── test_migrate.py          # Migration script tests (Phase 0)
│   ├── test_engine.py           # Engine tests (95 tests, Phase 1+6)
│   ├── test_api.py              # API endpoint tests (59 tests, Phase 2+6)
│   ├── test_e2e.py              # E2E integration tests (15 tests, Phase 8)
│   └── test_performance.py      # Performance benchmarks (14 tests, Phase 8)
├── data/
│   ├── sample_contracts.json    # 30+ seed contracts (Phase 0)
│   └── pdfs/                    # Downloaded PDFs (auto-created)
├── scrape_crz.py                # CLI entry point
├── requirements.in              # Unpinned dependencies
├── requirements.txt             # Pinned Python dependencies
├── .env.example                 # Environment config template (Phase 0)
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI pipeline (Phase 8)
├── Dockerfile                   # Multi-stage Docker build (Phase 8)
├── docker-compose.yml           # Docker Compose config (Phase 8)
├── Makefile                     # Common dev commands (Phase 8)
├── README.md                    # User documentation
├── ARCHITECTURE.md              # This file
├── setup.py                     # Setup validation script
├── init_git.py                  # Git initialization script
└── .gitignore                   # Git ignore rules
```

## Architecture

### Core Components

#### 1. `src/scraper.py` - Main Scraper Module

**Key Functions:**

- **`parse_price(price_str)`**: Converts Slovak price format to float
  - Input: "28 978,27 €"
  - Output: 28978.27
  
- **`parse_slovak_date(day, month, year)`**: Creates ISO date from Slovak parts
  - Handles Slovak month names (január, február, etc.)
  
- **`parse_date_from_text(date_str)`**: Parses DD.MM.YYYY format
  - Returns ISO format (YYYY-MM-DD)
  
- **`fetch_page(url, session)`**: Downloads page with retries
  - Exponential backoff on failure
  - Max 3 retries with delay
  
- **`extract_listing_rows(html)`**: Extracts contracts from listing page
  - Parses table with class `table_list`
  - Returns list of contract dicts
  
- **`extract_contract_details(html, url)`**: Extracts info from detail page
  - Finds "Identifikácia zmluvy" card
  - Finds "Dátum" card
  - Finds "Príloha" card (PDFs)
  
- **`download_and_extract_pdf(pdf_url, pdf_dir, session)`**: Downloads and processes PDF
  - Downloads to `data/pdfs/`
  - Extracts text with pdfplumber
  - Truncates to 50,000 chars
  
- **`scrape_contracts(...)`**: Main orchestration function
  - Paginates through listings
  - Fetches detail pages
  - Downloads PDFs
  - Writes NDJSON output

#### 2. `scrape_crz.py` - CLI Interface

**Responsibilities:**
- Parses command-line arguments
- Configures logging
- Calls main scraper function
- Reports results

#### 3. `src/models.py` — Pydantic Data Models (Phase 0)

**Key Models:**

- **`Contract`**: Central record for a government contract. Combines listing-page, detail-page, PDF, and GovLens enrichment fields. Three new enrichment fields:
  - `category` — LLM-assigned service category (default: `"not_decided"`)
  - `pdf_text_summary` — LLM-generated summary (default: `"not_summarized"`)
  - `award_type` — `tendered | direct_award | negotiated | unknown` (default: `"unknown"`)
  - Uses `model_config = {"extra": "allow"}` so unknown keys from the scraper pass through.

- **`Institution`**: Represents a buying institution (Objednávateľ) with `name`, `ico`, `contract_count`, `total_spend`.
- **`Vendor`**: Represents a supplier (Dodávateľ) with the same shape.
- **`FilterState`**: Encodes the shared global filter used across UI modes (date range, institutions, categories, vendors, value range, award types, text search).
- **`AggregationResult`**: Result of a group-by + aggregation operation (`group_key`, `group_value`, counts, spend stats).

#### 4. `scripts/migrate_ndjson.py` — Migration Tool (Phase 0)

Converts scraper NDJSON output to a JSON array and backfills missing GovLens fields:

```bash
python scripts/migrate_ndjson.py -i out.ndjson -o data/contracts.json
```

- Reads one JSON object per line
- Adds `category`, `pdf_text_summary`, `award_type` when missing
- Preserves existing values
- Skips malformed lines with a warning

#### 5. `data/sample_contracts.json` (Phase 0)

30+ realistic contract records with all fields populated, used as seed data for development and testing.

#### 6. `.env.example` (Phase 0)

Configuration template for future phases (LLM provider, API keys, server host/port, data paths).

#### 7. `src/engine.py` — In-Memory Query & Aggregation Engine (Phase 1)

**Key Class: `DataStore`**

Loads contracts from JSON into memory and provides fast querying.

**Loading & Indexing:**
- `DataStore(data_path)`: Load from JSON file at init
- `load_from_list(records)`: Load from list of dicts (for testing)
- Auto-builds lookup indices for institution, category, date

**Filtering (`filter(FilterState)`):**
- All filters are AND-combined; `None` means “no filter”
- Supported: institution(s), date_from/to, categories, vendors, value_min/max, award_types, text_search

**Search (`search(query)`):**
- Case-insensitive substring search over `contract_title` and `pdf_text_summary`

**Group By (`group_by(field, contracts?)`):**
- Fields: `category`, `supplier`, `buyer`, `month`, `award_type`, `published_year`
- Returns `Dict[str, List[Contract]]`

**Aggregations:**
- `aggregate(contracts?)` → `{total_spend, contract_count, avg_value, max_value}`
- `aggregate_groups(field)` → `List[AggregationResult]` sorted by total_spend desc
- `top_n_vendors(n)` → `List[Vendor]`
- `direct_award_rate(contracts?)` → `float` (0.0 – 1.0)

**Benchmark / Compare:**
- `institutions()` / `vendors()` — list all with stats
- `compare(institution_names, metric)` — side-by-side comparison
- `compare_multi_metric(institution_names, metrics)` — multi-metric comparison (Phase 6)
- `peer_group(institution_name, min_contracts)` — discover similar institutions (Phase 6)

**Trends:**
- `trend(granularity, contracts?, metric)` — time-series by month/quarter/year
- `trend_multi_metric(granularity, contracts, metrics)` — multi-metric trends (Phase 6)

**Rankings:**
- `rank_institutions(metric)` / `rank_vendors(metric)` — with rank numbers
- `vendor_concentration_score(contracts, top_n)` — HHI-style concentration (Phase 6)
- `fragmentation_score(contracts)` — many-small-contracts score (Phase 6)
- Metrics: `total_spend`, `contract_count`, `avg_value`, `max_value`, `direct_award_rate`, `vendor_concentration`, `fragmentation_score`

**Example:**
```bash
python scrape_crz.py \
  --start-page 1 \
  --max-pages 10 \
  --out contracts.ndjson \
  --delay 0.5 \
  --log-level INFO
```

#### 8. `src/api.py` — Backend REST API (Phase 2)

FastAPI application exposing the DataStore engine over HTTP REST endpoints.

**App Setup:**
- Lifespan handler loads DataStore at startup (graceful fallback if file missing)
- CORS middleware allowing all origins (for frontend dev server)
- Dependency injection for DataStore (`get_store`) and filter parsing (`parse_filters`)
- Filter-state serialization utility (`encode_filter_state`)

**Endpoints (17 total):**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/contracts` | GET | Paginated, filterable contract list |
| `/api/contracts/{id}` | GET | Single contract detail (404 if not found) |
| `/api/aggregations` | GET | Group-by + filters → aggregated stats |
| `/api/treemap` | GET | Hierarchical data for D3 treemap visualization |
| `/api/benchmark` | GET | Compare institutions by metric (with min_contracts filter) |
| `/api/benchmark/peers` | GET | Peer-group discovery for an institution (Phase 6) |
| `/api/benchmark/compare` | GET | Multi-metric comparison across institutions (Phase 6) |
| `/api/trends` | GET | Time-series by granularity, multi-metric, overlay dates (Phase 6 enhanced) |
| `/api/rankings` | GET | Ranked list with filters, new metrics: vendor_concentration, fragmentation_score (Phase 6 enhanced) |
| `/api/institutions` | GET | All institutions with stats |
| `/api/institutions/{identifier}` | GET | Institution profile (by name or ICO) |
| `/api/vendors` | GET | All vendors with stats |
| `/api/vendors/{identifier}` | GET | Vendor profile (by name or ICO) |
| `/api/export/csv` | GET | Filtered CSV download |
| `/api/export/pdf` | GET | PDF export (ReportLab-generated report with summary stats + contract table) |
| `/api/workspace/save` | POST | Snapshot filters, sort, groupBy, mode, chart state, chat history → base64 token + JSON |
| `/api/workspace/load` | GET | Restore workspace from base64 token (`?token=...`) |
| `/api/filter-state` | GET | Debug: shows parsed/encoded filter state |

**Filter Query Parameters (shared across filterable endpoints):**
- `institutions` — Comma-separated buyer names
- `date_from` / `date_to` — Date range (YYYY-MM-DD)
- `categories` — Comma-separated categories
- `vendors` — Comma-separated supplier names
- `value_min` / `value_max` — EUR value range
- `award_types` — Comma-separated award types
- `text_search` — Full-text search query

**Running the server:**
```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

#### 9. `src/config.py` — Application Configuration (Phase 2)

Loads settings from environment variables with defaults, using `python-dotenv` for `.env` file support.

**Settings:**
- `GOVLENS_HOST` / `GOVLENS_PORT` — Server binding (default: `0.0.0.0:8000`)
- `GOVLENS_DATA_PATH` — Path to contracts JSON (default: `data/sample_contracts.json`)
- `LLM_PROVIDER` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — LLM config (Phase 5)
- `SCRAPER_PDF_DIR` / `SCRAPER_DELAY` — Scraper settings

#### 10. `frontend/` — React Frontend (Phase 3)

Single-page application built with React 18, TypeScript, Vite, and Tailwind CSS v4.

**Tech stack:**
- **React 18** + TypeScript — component library and type safety
- **Vite** — build tool with HMR, proxy `(/api → localhost:8000)`
- **Tailwind CSS v4** — utility-first styling via `@tailwindcss/vite` plugin
- **react-router-dom** — client-side routing with URL-state
- **D3.js** — treemap visualization with drill-down
- **Recharts** — bar charts, line charts for trends
- **vitest** + `@testing-library/react` — 135 frontend unit tests

**Key modules:**
- `types.ts` — TypeScript interfaces mirroring all backend Pydantic models
- `api.ts` — Thin fetch wrappers for all 20 REST endpoints + `saveWorkspace()` / `loadWorkspace()`
- `url-state.ts` — Parse/encode full UI state to/from URL query params (includes `mode` field for Phase 7)
- `utils.ts` — EUR formatting, compact numbers, date display

**Components (8):**
- `FilterBar` — Institution, date range, category, vendor, value range, award type, text search
- `GroupByControl` — Toggle between 5 group-by dimensions
- `TreemapChart` — D3 treemap with drill-down on click
- `BarChart` — Recharts horizontal bar chart fallback
- `CategoryAccordion` — Expandable group rows with spend totals
- `ContractsTable` — Multi-column sortable table (click/Shift+click, direction arrows, priority badges)
- `Pagination` — First/prev/next/last with page window
- `WorkspaceToolbar` — Share (clipboard), Save Workspace (JSON download), Export CSV, Export PDF (Phase 7)
- `ErrorBoundary` — React error boundary wrapping all routes, with retry button and expandable error details (Phase 8)
- `LoadingSkeleton` — Shimmer/pulse skeleton screens with `TableSkeleton`, `ChartSkeleton`, `CardSkeleton`, `SummarySkeleton` variants (Phase 8)

**Pages (4):**
- `Dashboard` — Home: filters + viz + accordion + table + pagination + WorkspaceToolbar (Share/Save/CSV/PDF)
- `ContractDetail` — Full contract info, PDF link, summary, category/award badges
- `InstitutionProfile` — Stats cards, spend trend line chart, top vendors bar chart, contracts table
- `VendorProfile` — Stats cards, revenue trend, institutions served bar chart, contracts table

**Routing:**
- `/` → Dashboard
- `/contract/:id` → ContractDetail
- `/institution/:id` → InstitutionProfile
- `/vendor/:id` → VendorProfile

#### 3. Tests

**`tests/test_parser.py`**: Unit tests
- Price parsing with various formats
- Slovak date parsing
- Date text parsing

**`tests/test_integration.py`**: Integration tests
- Listing extraction
- Detail extraction
- Full smoke test
- Output format validation

**`tests/test_models.py`** (Phase 0): Model & sample-data tests
- Contract defaults for enrichment fields
- Validation and serialization round-trips
- FilterState, AggregationResult, Institution, Vendor
- Sample data file loading and contract validation

**`tests/test_migrate.py`** (Phase 0): Migration script tests
- Field backfill (category, pdf_text_summary, award_type)
- Existing data preservation
- Overwrite protection
- Edge cases (blank lines, invalid JSON, empty input)

**`tests/test_engine.py`** (Phase 1+6): Engine tests (95 tests)
- Loading from JSON and in-memory lists
- Filtering: institution, date range, value range, category, vendor, award type, text search, combined
- Search: title, summary, case-insensitive
- Group by: category, supplier, buyer, month, award_type
- Aggregations: total spend, count, avg, max, grouped, top-N vendors, direct award rate
- Institutions & vendors listing with stats
- Compare / benchmark institutions
- Trends: monthly, quarterly, yearly
- Rankings: institutions & vendors by multiple metrics
- Multi-column sort: ascending/descending, None-last, tie-breaking, case-insensitive strings, SORTABLE_FIELDS whitelist
- Sample-data smoke tests and edge cases

**`tests/test_api.py`** (Phase 2+6+7): API endpoint tests (46 tests)
- Contracts: list (200), filter by institution, pagination, date range, text search, detail, not found (404)
- Aggregations: group by category, with filter
- Treemap: data structure, sub-grouping
- Benchmark: peer comparison
- Trends: time-series, with filter
- Rankings: institutions, vendors
- Institutions: list, profile by name, by ICO, not found
- Vendors: list, profile, by ICO, not found
- Export: CSV, CSV with filter, PDF returns application/pdf
- Filter state: round-trip, empty encoding
- Sample data smoke tests: contracts, institutions, rankings, CSV

**`tests/test_workspace.py`** (Phase 7): Workspace save/load tests (5 tests)
- Save and load round-trip restores identical filter state
- Workspace snapshot includes chat history
- Invalid token returns 400
- Non-JSON base64 token returns 400
- Minimal payload round-trip

**`tests/test_export.py`** (Phase 7): Export tests (5 tests)
- CSV export content and headers
- CSV export respects filters
- PDF export returns application/pdf
- PDF export respects filters
- PDF export with sort

**`tests/test_url_state.py`** (Phase 7): URL-state encoding tests (5 tests)
- Full state encode/decode round-trip
- Empty FilterState returns empty dict
- Page=1 omitted from encoding
- Mode included when set
- Group-by included

**`tests/test_e2e.py`** (Phase 8): End-to-end integration tests (15 tests)
- Full workflow: load → filter → aggregate → export consistency
- Benchmark: institution comparison, treemap, rankings
- PDF export validation
- Chatbot: status, WebSocket session, save, scoped context
- Rules: preset discovery, evaluate all, custom conditions, severity scores, workspace round-trip

**`tests/test_performance.py`** (Phase 8): Performance benchmarks (14 tests)
- Filter performance: 10k contracts < 200ms, 50k contracts < 500ms
- Date range, category, combined, and text search filters
- Aggregation, group-by, trend, rankings performance
- Sort performance: single and multi-column
- Load performance: 10k < 2s, 50k < 10s

### Data Flow

```
CLI Args
  ↓
scrape_crz.py (entry point)
  ↓
scraper.scrape_contracts()
  ├─ For each page:
  │   ├─ fetch_page(listing_url)
  │   ├─ extract_listing_rows(html)
  │   └─ For each contract:
  │       ├─ fetch_page(detail_url)
  │       ├─ extract_contract_details(html)
  │       ├─ For each PDF:
  │       │   └─ download_and_extract_pdf()
  │       ├─ Set category / pdf_text_summary / award_type defaults
  │       └─ Write to NDJSON
  └─ Return contract count

         ↓ (optional: Phase 0 migration)

scripts/migrate_ndjson.py
  Read NDJSON → backfill fields → write data/contracts.json

         ↓ (Phase 1: load into engine)

src/engine.py — DataStore
  Load JSON → build indices → filter / group / aggregate / search / trend / rank

         ↓ (Phase 2: REST API)

src/api.py — FastAPI Application
  DataStore loaded at startup → HTTP endpoints expose filter / aggregate / export
  Frontend or curl → GET /api/contracts?institutions=X&page=1 → JSON response
```

## Configuration

### Environment Variables

Configured via `.env.example` (Phase 0) and loaded by `src/config.py` (Phase 2):
- `LLM_PROVIDER`: Anthropic or OpenAI (for future chatbot)
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`: API credentials
- `GOVLENS_HOST` / `GOVLENS_PORT`: Server binding
- `GOVLENS_DATA_PATH`: Path to contracts JSON
- `SCRAPER_PDF_DIR`: PDF storage directory
- `SCRAPER_DELAY`: Default delay between requests

### Constants in `scraper.py`

```python
BASE_URL = "https://www.crz.gov.sk"
LISTING_URL = f"{BASE_URL}/zmluvy/"
DEFAULT_USER_AGENT = "Mozilla/5.0 ..."
DEFAULT_TIMEOUT = 10
DEFAULT_DELAY = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5
```

## Resilience & Error Handling

### Retry Strategy

- **Transient errors** (connection, timeout): Retry up to 3 times with exponential backoff
- **HTTP errors**: Log and skip contract, continue with next
- **Parsing errors**: Log warning, continue with default values
- **PDF errors**: Log error, mark as failed, continue

### Error Logging

- INFO: Pages fetched, contracts processed, PDFs downloaded
- WARNING: Failed fetches, unparseable prices
- ERROR: Critical failures

### Fallback Selectors

- Uses CSS class selectors primarily
- No XPath (too fragile with HTML changes)
- Tag-based fallbacks for robustness

## Data Output

### NDJSON Format

Each line is a complete JSON object (no pretty-printing):

```json
{"published_day": "1.", "published_month": "Marec", ..., "scraped_at": "2026-03-01T10:30:45Z"}
```

### Fields Reference

| Field | Source | Type | Example |
|-------|--------|------|---------|
| `published_day` | Listing | str | "1." |
| `published_month` | Listing | str | "Marec" |
| `published_year` | Listing | str | "2026" |
| `published_date` | Listing (computed) | str | "2026-03-01" |
| `contract_title` | Listing | str | "rámcová dohoda" |
| `contract_number` | Listing | str | "2026/22/E/CI" |
| `price_raw` | Listing | str | "28 978,27 €" |
| `price_numeric_eur` | Listing (computed) | float | 28978.27 |
| `supplier` | Listing | str | "Company Name" |
| `buyer` | Listing | str | "Organization Name" |
| `contract_url` | Listing | str | "https://..." |
| `contract_id` | Listing (computed) | str | "12048046" |
| `scraped_at` | Runtime | str | ISO datetime |
| `contract_number_detail` | Detail | str | "2026/22/E/CI" |
| `contract_id_detail` | Detail | str | "12048046" |
| `ico_buyer` | Detail | str | "17336163" |
| `ico_supplier` | Detail | str | "36394556" |
| `date_published` | Detail | str | "2026-03-01" |
| `date_concluded` | Detail | str | "2026-02-28" |
| `date_effective` | Detail | str | "2026-03-02" |
| `date_valid_until` | Detail | str/null | null if "neuvedený" |
| `pdf_urls` | Detail | list | ["https://..."] |
| `pdf_url` | PDF | str | "https://...pdf" |
| `pdf_local_path` | PDF | str | "data/pdfs/12345.pdf" |
| `pdf_text` | PDF (extracted) | str | "Contract text..." |
| `category` | GovLens (Phase 0) | str | "not_decided" |
| `pdf_text_summary` | GovLens (Phase 0) | str | "not_summarized" |
| `award_type` | GovLens (Phase 0) | str | "unknown" |

## Performance

### Typical Performance

- **Listing page load**: 1-2 seconds (with retry/delay)
- **Contract detail fetch**: 1-2 seconds each
- **PDF download**: 2-10 seconds (depends on size)
- **PDF text extraction**: 0.5-2 seconds

### For 100 pages with ~20 contracts each (2000 contracts):

- Listing pages: ~100 × 2s = 200s
- Detail pages: ~2000 × 1.5s = 3000s
- PDFs (10% have attachments): ~200 × 5s = 1000s
- **Total: ~4200s (~70 minutes)**

With `--delay 0.5`, this would be the dominant time.

### Optimization Options

1. **Reduce delay** (not recommended for website health)
2. **Skip PDF processing** (modify scraper)
3. **Parallelize detail fetches** (requires thread pool)
4. **Resume from checkpoint** (requires modification)

## Testing

### Unit Tests

```bash
pytest tests/test_parser.py tests/test_models.py tests/test_migrate.py -v
```

Tests cover:
- Slovak price parsing
- Slovak date parsing
- ISO date parsing
- Error cases
- Contract model defaults and validation (Phase 0)
- FilterState, AggregationResult, Institution, Vendor (Phase 0)
- Sample data loading (Phase 0)
- Migration field backfill and preservation (Phase 0)

### Integration Tests

```bash
pytest tests/test_integration.py -v
```

Tests cover:
- HTML parsing
- Listing extraction
- Detail extraction
- PDF URL extraction
- End-to-end scraping (mocked)

### Running All Tests

```bash
pytest tests/ -v --tb=short
```

### Test Coverage (Future)

```bash
pytest --cov=src tests/
```

## Future Enhancements

### High Priority

1. **Resume capability**: Save progress, skip already-scraped contracts
2. **Async fetching**: Use asyncio for parallel detail page fetches
3. **Database output**: Option to store in SQLite instead of NDJSON
4. **Filtering**: Only scrape contracts matching certain criteria

### Medium Priority

1. **OCR for scanned PDFs**: Add pytesseract support
2. **Change detection**: Track and report only new/updated contracts
3. **Configuration file**: YAML/JSON config instead of CLI args
4. **Email alerts**: Notify on new contracts matching criteria

### Low Priority

1. **Web UI**: Simple Flask dashboard for browsing results
2. **Caching**: Store HTML to reduce re-fetches
3. **Analytics**: Statistics on contract distribution, trends
4. **API endpoint**: REST API to query scraped data

## Troubleshooting

### Common Issues

**Issue: "429 Too Many Requests"**
- Solution: Increase `--delay` to 2.0 or higher
- Check robots.txt compliance

**Issue: "PDF text extraction returns empty"**
- Cause: PDF is a scanned image without OCR
- Solution: Use OCR library (pytesseract + wand)

**Issue: "Missing fields in output"**
- Cause: Website HTML structure changed
- Solution: Update selectors in `extract_*` functions

**Issue: Script hangs on PDF download**
- Cause: Large PDF or slow connection
- Solution: Increase `DEFAULT_TIMEOUT` in scraper.py

### Debug Mode

```bash
python scrape_crz.py --start-page 1 --max-pages 1 --log-level DEBUG
```

## Contributing

### Code Style

- Follow PEP 8
- Use type hints where practical
- Comment complex logic
- Keep functions under 50 lines

### Testing Requirements

- Unit tests for new parsing functions
- Integration test for new extraction
- Manual test on actual website

### Pull Request Process

1. Fork the repo
2. Create feature branch
3. Add tests
4. Update documentation
5. Submit PR with description

## Legal & Ethics

### Respect the Website

- Don't scrape faster than `--delay` allows
- Check website Terms of Service
- Respect robots.txt (even if not enforced)
- Don't overload the server

### Usage Rights

- Czech/Slovak law: Check local regulations
- GDPR: Personal data should not be shared
- License: MIT (see LICENSE file)

## Performance Tips

1. **Batch processing**: Don't scrape the entire site at once
2. **Caching**: Save HTML to avoid re-fetching
3. **Database**: Use SQLite for large datasets
4. **Filtering**: Scrape only needed pages/contracts
5. **Scheduling**: Run at off-peak hours

## Dependencies

### Required

- `requests`: HTTP client with built-in retry
- `beautifulsoup4`: HTML parsing
- `lxml`: XML/HTML parser for BeautifulSoup
- `pdfplumber`: PDF text extraction
- `pydantic>=2.0`: Data models and validation (Phase 0)
- `python-dotenv`: Environment configuration (Phase 0)
- `fastapi`: REST API framework (Phase 2)
- `uvicorn[standard]`: ASGI server for FastAPI (Phase 2)
- `httpx`: HTTP client for FastAPI TestClient (Phase 2)

### Optional (Future)

- `pytesseract`: OCR for scanned PDFs
- `Pillow` / `wand`: Image processing
- `sqlite3`: Database (built-in)
- `pandas`: Data analysis
- `sqlalchemy`: ORM layer

### Frontend (Node.js / npm)

- `react` + `react-dom`: UI framework (Phase 3)
- `react-router-dom`: Client-side routing (Phase 3)
- `d3`: Treemap visualization (Phase 3)
- `recharts`: Bar/line charts (Phase 3)
- `tailwindcss` + `@tailwindcss/vite`: Utility CSS (Phase 3)
- `vitest`: Test runner (Phase 3, dev)
- `@testing-library/react` + `@testing-library/jest-dom`: Component testing (Phase 3, dev)

## Version History

### v1.9.0 — Phase 8: Polish, Integration Testing, and Deployment (2026-03-06)

- 15 E2E integration tests (`test_e2e.py`), 14 performance benchmarks (`test_performance.py`)
- `ErrorBoundary.tsx` wrapping all routes with retry and error details
- `LoadingSkeleton.tsx` with Table/Chart/Card/Summary skeleton variants
- Accessibility: ARIA attributes, keyboard navigation, focus management across 6 components
- Multi-stage Dockerfile + docker-compose.yml
- Makefile + start_dev.sh + start_dev.ps1 dev scripts
- GitHub Actions CI pipeline (4 jobs: backend-tests, frontend-tests, lint, build)

### v1.4.0 — Phase 3: Frontend: Institution Lens UI (2026-03-03)

- React 18 + TypeScript + Vite frontend in `frontend/`
- Tailwind CSS v4 via `@tailwindcss/vite` plugin
- react-router-dom for client-side routing with full URL-state
- D3.js treemap, Recharts bar/line charts
- 7 reusable components: FilterBar, GroupByControl, TreemapChart, BarChart, CategoryAccordion, ContractsTable, Pagination
- 4 pages: Dashboard, ContractDetail, InstitutionProfile, VendorProfile
- Multi-column sort with Shift+click, priority badges (①②③)
- URL-state manager: all filters, sort, group-by, page in query params
- API client for all backend endpoints
- 71 unit tests in 13 test files (vitest + @testing-library/react)

### v1.3.0 — Phase 2: Backend API (FastAPI) (2026-03-03)

- FastAPI application in `src/api.py` with 17 REST endpoints
- `src/config.py` for environment-variable-based configuration
- CORS middleware, filter-state serialization, CSV export
- Institution and vendor profiles with lookup by name or ICO
- PDF export stub (deferred to Phase 7)
- Added `fastapi`, `uvicorn[standard]`, `httpx` to dependencies
- 33 new unit tests in `tests/test_api.py`

### v1.2.0 — Phase 1: In-Memory Query & Aggregation Engine (2026-03-03)

- `DataStore` class in `src/engine.py` — loads JSON, holds Contract objects in RAM
- Filtering, grouping, aggregation, search, benchmarking, trends, rankings
- `sort_contracts(contracts, sort_spec)` — multi-column sort; `SORTABLE_FIELDS` whitelist; `None` values always last
- 95 unit tests in `tests/test_engine.py` (Phase 1 base + Phase 6 investigation modes)

### v1.1.0 — Phase 0: GovLens Data Foundation (2026-03-03)

- Pydantic v2 data models (Contract, Institution, Vendor, FilterState, AggregationResult)
- Three new enrichment fields: category, pdf_text_summary, award_type
- NDJSON → JSON migration script
- Sample data seed file (30+ records)
- .env.example configuration template
- 39 new unit tests

### v1.0.0 (2026-03-01)

Initial release with:
- Pagination support
- Contract detail extraction
- PDF download and text extraction
- NDJSON output
- CLI interface
- Unit and integration tests
- Comprehensive documentation
