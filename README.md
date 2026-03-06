# CRZ (Central Register of Contracts) Web Scraper

A robust Python scraper for the Slovak government contracts website (https://www.crz.gov.sk/).

## Features

- **Pagination support**: Scrape multiple pages of contract listings
- **Contract details**: Extract structured information from individual contract pages
- **PDF handling**: Download PDFs and extract text using `pdfplumber`
- **Polite scraping**: Configurable delays, User-Agent headers, and retry logic
- **Resilient parsing**: Fallback selectors and error handling for HTML variations
- **NDJSON output**: Newline-delimited JSON format for easy streaming and processing
- **Comprehensive logging**: Track progress at INFO level
- **CLI interface**: Easy-to-use command-line arguments
- **Pydantic data models**: Validated `Contract`, `Institution`, `Vendor`, `FilterState`, and `AggregationResult` models (Phase 0)
- **Migration tooling**: Convert NDJSON scraper output to JSON array with backfilled GovLens fields
- **Sample data**: 29 realistic contract records in `data/sample_contracts.json`
- **Environment config**: `.env.example` template for future LLM and server settings
- **In-memory query engine**: `DataStore` class for filtering, grouping, aggregation, search, trends, and rankings (Phase 1)
- **Benchmarking & comparison**: Compare institutions by spend, contract count, or direct-award rate (Phase 1)
- **Time-series trends**: Monthly, quarterly, and yearly spend/count trends (Phase 1)
- **REST API**: 20 FastAPI endpoints for contracts, aggregations, treemap, benchmark, trends, rankings, institutions, vendors, CSV export, PDF export, workspace save/load (Phase 2+6+7)
- **Filter-state serialization**: Encode/decode filter state to/from URL query parameters (Phase 2)
- **Application config**: Environment-variable-based configuration via `src/config.py` (Phase 2)
- **React Frontend**: Institution Lens UI with React 18 + TypeScript + Vite (Phase 3)
- **Interactive Visualizations**: D3 treemap with drill-down, Recharts bar/line charts (Phase 3)
- **URL-Driven State**: All filters, sort, group-by, and pagination encoded in URL for bookmarkable views (Phase 3)
- **Multi-Column Sort**: Click/Shift+click table headers with direction arrows and priority badges (Phase 3)
- **Entity Profiles**: Institution and Vendor profile pages with trend charts and contract breakdowns (Phase 3)
- **Responsive Design**: Desktop-first layout with Tailwind CSS v4, usable mobile fallback (Phase 3)
- **WorkspaceToolbar**: Share (clipboard), Save Workspace (JSON download), Export CSV, Export PDF on every page (Phase 7)
- **PDF Export**: ReportLab-generated PDF report with summary stats and contract table (Phase 7)
- **Workspace Save/Load**: Base64-encoded workspace snapshots including filters, sort, mode, chat history (Phase 7)
- **URL-State Mode**: `mode` parameter encoding for bookmarkable view switching (Phase 7)
- **Error Boundaries**: React ErrorBoundary component wrapping all routes with retry and error details (Phase 8)
- **Loading Skeletons**: Shimmer/pulse skeleton screens (Table, Chart, Card, Summary variants) for async loading states (Phase 8)
- **Accessibility**: ARIA attributes, keyboard navigation, focus management across all interactive components (Phase 8)
- **E2E Tests**: 15 end-to-end integration tests covering full workflows (filter→aggregate→export, chatbot, rules) (Phase 8)
- **Performance Tests**: 14 performance benchmarks validating sub-second query times on 10k–50k contracts (Phase 8)
- **Docker**: Multi-stage Dockerfile and docker-compose.yml for containerized deployment (Phase 8)
- **CI/CD**: GitHub Actions pipeline with backend tests, frontend tests, lint, and build jobs (Phase 8)
- **Dev Scripts**: Makefile, start_dev.sh, and start_dev.ps1 for streamlined development workflow (Phase 8)

## Installation

### Prerequisites
- Python 3.8+
- pip or virtual environment

### Setup

1. Clone the repository:
```bash
git clone https://github.com/arath/crz_gov_scraping.git
cd crz_gov_scraping
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Scrape the first 3 pages and save to `out.ndjson`:
```bash
python scrape_crz.py --start-page 1 --max-pages 3 --out out.ndjson
```

### Advanced Options

```bash
python scrape_crz.py \
  --start-page 1 \
  --max-pages 100 \
  --out contracts.ndjson \
  --delay 1.0 \
  --pdf-dir data/pdfs \
  --log-level INFO
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--start-page` | int | 1 | Starting page number (1-indexed) |
| `--max-pages` | int | 1 | Maximum number of pages to scrape |
| `--out` | str | out.ndjson | Output NDJSON file path |
| `--delay` | float | 0.5 | Delay between requests in seconds |
| `--user-agent` | str | (realistic) | Custom User-Agent header |
| `--pdf-dir` | str | data/pdfs | Directory to save PDFs |
| `--log-level` | str | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |

## Output Format

Each line in the output NDJSON file is a JSON object with the following fields:

### Listing Page Fields
- `published_day`: Day of publication
- `published_month`: Month name (Slovak)
- `published_year`: Year of publication
- `published_date`: ISO format date (YYYY-MM-DD)
- `contract_title`: Contract title
- `contract_number`: Contract number (from listing)
- `price_raw`: Price as string (original format)
- `price_numeric_eur`: Price as float in EUR
- `supplier`: Supplier name
- `buyer`: Buyer name
- `contract_url`: Absolute URL to contract detail page
- `contract_id`: Numeric contract ID (extracted from URL)
- `scraped_at`: ISO datetime when contract was scraped

### Detail Page Fields (if available)
- `contract_number_detail`: Contract number from detail page
- `contract_id_detail`: Contract ID from detail page
- `buyer_detail`: Detailed buyer information
- `supplier_detail`: Detailed supplier information
- `ico_buyer`: ICO (company ID) of buyer
- `ico_supplier`: ICO (company ID) of supplier
- `date_published`: Publication date (ISO format)
- `date_concluded`: Contract conclusion date (ISO format)
- `date_effective`: Effective date (ISO format)
- `date_valid_until`: Validity end date (ISO format, if available)

### PDF Fields (if available)
- `pdf_urls`: List of PDF URLs found on detail page
- `pdf_url`: First PDF URL (absolute)
- `pdf_local_path`: Local path where PDF was downloaded
- `pdf_text`: Extracted text from PDF (truncated to 50,000 characters)

### GovLens Enrichment Fields (Phase 0)
- `category`: LLM-assigned service category (default: `"not_decided"`)
- `pdf_text_summary`: LLM-generated summary of PDF text (default: `"not_summarized"`)
- `award_type`: Award mechanism — `tendered` | `direct_award` | `negotiated` | `unknown` (default: `"unknown"`)

## Example Output

```json
{
  "published_day": "1.",
  "published_month": "Marec",
  "published_year": "2026",
  "published_date": "2026-03-01",
  "contract_title": "rámcová dohoda",
  "contract_number": "2026/22/E/CI",
  "price_raw": "28 978,27 €",
  "price_numeric_eur": 28978.27,
  "supplier": "Liptovské pekárne a cukrárne VČELA – Lippek k.s.",
  "buyer": "Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš",
  "contract_url": "https://www.crz.gov.sk/zmluva/12048046/",
  "contract_id": "12048046",
  "scraped_at": "2026-03-01T10:30:45.123456Z",
  "contract_number_detail": "2026/22/E/CI",
  "contract_id_detail": "12048046",
  "ico_buyer": "17336163",
  "ico_supplier": "36394556",
  "date_published": "2026-03-01",
  "date_concluded": "2026-02-28",
  "date_effective": "2026-03-02",
  "date_valid_until": null,
  "pdf_url": "https://www.crz.gov.sk/data/att/6568046.pdf",
  "pdf_local_path": "data/pdfs/6568046.pdf",
  "pdf_text": "...",
  "category": "not_decided",
  "pdf_text_summary": "not_summarized",
  "award_type": "unknown"
}
```

## Configuration

### Delay and Rate Limiting

The scraper includes polite scraping features:

- **Default delay**: 0.5 seconds between requests
- **Exponential backoff**: Failed requests retry with increasing delay
- **Max retries**: 3 attempts per request
- **Realistic User-Agent**: Browser-like header by default

To be more aggressive (use with caution):
```bash
python scrape_crz.py --start-page 1 --max-pages 100 --delay 0.1
```

To be more conservative:
```bash
python scrape_crz.py --start-page 1 --max-pages 10 --delay 2.0
```

## Testing

### Run Unit Tests

```bash
pytest tests/test_parser.py -v
```

Tests include:
- Price parsing (Slovak format with thousands separator and decimal comma)
- Slovak date parsing
- Date text parsing (DD.MM.YYYY format)

### Run Data Model & Migration Tests (Phase 0)

```bash
pytest tests/test_models.py tests/test_migrate.py -v
```

Phase 0 tests cover:
- Contract model defaults (`category`, `pdf_text_summary`, `award_type`)
- Validation, serialization, and JSON round-trip
- `FilterState`, `AggregationResult`, `Institution`, `Vendor` models
- Sample data file loading and validation
- Migration script: field backfill, data preservation, edge cases

### Run Engine Tests (Phase 1)

```bash
pytest tests/test_engine.py -v
```

Phase 1 tests cover (80 tests):
- Loading from JSON file and in-memory lists
- Filtering: institution, date range, value range, category, vendor, award type, text search, combined
- Search: title, summary, case-insensitive, no-match
- Group by: category, supplier, buyer, month, award_type, filtered subsets
- Aggregations: total spend, count, avg, max, grouped aggregation, top-N vendors, direct award rate
- Institutions & vendors listing
- Compare / benchmark institutions
- Trends: monthly, quarterly, yearly, by metric, on filtered data
- Rankings: institutions and vendors by spend, count, direct-award rate
- Multi-column sort: ascending/descending, None-last, tie-breaking, case-insensitive strings, SORTABLE_FIELDS whitelist
- Sample-data smoke tests and edge cases

### Run API Tests (Phase 2)

```bash
pytest tests/test_api.py -v
```

Phase 2 tests cover (33 tests):
- Contract list: pagination, filtering by institution/date/text, detail, 404
- Aggregations: group by category, with filters
- Treemap: data structure, sub-grouping
- Benchmark: peer comparison
- Trends: time-series, filtered
- Rankings: institutions, vendors
- Institutions: list, profile by name/ICO, not found
- Vendors: list, profile, by ICO, not found
- Export: CSV, CSV with filter, PDF export (ReportLab)
- Workspace: save/load round-trip, chat history inclusion, invalid token handling
- URL-state: full encode/decode round-trip, mode/groupBy encoding
- Filter state: round-trip encoding, empty state
- Sample data smoke tests: contracts, institutions, rankings, CSV

### Run Integration Tests

```bash
pytest tests/test_integration.py -v
```

Smoke test verifies:
- Listing row extraction
- Contract detail extraction
- PDF URL extraction
- Output NDJSON format

### Run E2E Tests (Phase 8)

```bash
pytest tests/test_e2e.py -v
```

Phase 8 E2E tests cover (15 tests):
- Full workflow: load → filter → aggregate → export consistency
- Benchmark: institution comparison with metric verification
- Treemap, rankings, and PDF export validation
- Chatbot: status, WebSocket session, save endpoint, scoped context
- Rules: preset discovery, evaluate all, custom conditions, severity scores, workspace round-trip

### Run Performance Tests (Phase 8)

```bash
pytest tests/test_performance.py -v
```

Phase 8 performance tests cover (14 tests):
- Filter performance: 10k contracts < 200ms, 50k contracts < 500ms
- Date range, category, combined, and text search filters
- Aggregation, group-by, trend, rankings performance
- Sort performance: single and multi-column
- Load performance: 10k contracts < 2s, 50k contracts < 10s

### Run Frontend Tests (Phase 3)

```bash
cd frontend && npx vitest run
```

Phase 3 tests cover (71 tests across 13 test files):
- URL-state: parse/encode round-trip for all filter/sort/groupBy/page fields
- Utilities: formatEur, formatCompact, formatDate with edge cases
- FilterBar: renders all controls, form submit triggers onChange
- GroupByControl: renders options, highlights active, fires onChange
- TreemapChart: SVG rendering, empty data handling
- BarChart: renders with data and empty data
- CategoryAccordion: expand/collapse, controlled state, toggle callback
- ContractsTable: empty state, sort click, direction toggle, shift+click secondary sort, priority badges, row click
- Pagination: single page hidden, multi-page navigation, disabled buttons, active page highlight
- ContractDetail: loading/error/success states, PDF link, summary display
- InstitutionProfile: loading/error/success, stats/chart/vendor rendering
- VendorProfile: loading/error/success, stats/chart/institution rendering
- App routing: all routes render correct page, header/footer present

### Run All Tests

```bash
# Backend (all tests including E2E and performance)
pytest tests/ -v

# Frontend
cd frontend && npx vitest run

# Or use the Makefile
make test
```

## Known Issues & Limitations

### PDFs from Scanned Documents

Some PDFs are scanned images without OCR. `pdfplumber` extracts text only from text-based PDFs.

**Solution**: If you need OCR, add `pytesseract` and `wand`:
```bash
pip install pytesseract wand
```

Then modify the PDF extraction code to use OCR for images.

### Pagination

The website uses `?page=0` for page 1, `?page=1` for page 2, etc. The scraper handles this conversion automatically.

### 429 Too Many Requests

If you receive HTTP 429 errors:
1. Increase the delay: `--delay 2.0` or higher
2. Reduce max pages: `--max-pages 10`
3. Wait before retrying

### Handling robots.txt

The scraper does not automatically parse `robots.txt`, but it respects polite scraping conventions:
- Realistic User-Agent
- Configurable delays
- Automatic retries with backoff

If the website requests no scraping, respect the request and do not use this tool.

## Docker

### Quick Start with Docker

```bash
# Build and run
docker compose up --build

# Or use Makefile
make docker

# Access the app
# http://localhost:8000        — API
# http://localhost:8000/docs   — Swagger docs
```

### Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `govlens` | 8000 | Backend API + static frontend |
| `frontend-dev` | 5173 | Vite dev server (optional, `--profile dev`) |

### Development Scripts

```bash
# Unix/macOS
./scripts/start_dev.sh

# Windows PowerShell
.\scripts\start_dev.ps1

# Makefile shortcuts
make dev          # Start backend + frontend dev servers
make test         # Run all backend + frontend tests
make lint         # Lint frontend
make build        # Build frontend for production
make clean        # Remove caches and build artifacts
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push/PR to `main`/`master`:

| Job | Description |
|-----|-------------|
| `backend-tests` | Python 3.11 + 3.12 matrix, pytest |
| `frontend-tests` | Node 22, vitest |
| `frontend-lint` | ESLint |
| `frontend-build` | Vite production build |

## Development

### Project Structure

```
crz_gov_scraping/
├── src/
│   ├── __init__.py          # Package init
│   ├── scraper.py           # Core scraping logic
│   ├── models.py            # Pydantic v2 data models (Phase 0)
│   ├── engine.py            # In-memory query & aggregation engine (Phase 1)
│   ├── api.py               # FastAPI REST endpoints (Phase 2)
│   ├── config.py            # Environment-variable config (Phase 2)
│   ├── chatbot/             # LLM chatbot module (Phase 5)
│   └── rules/               # Rule engine module (Phase 4)
├── frontend/                # React + TypeScript + Vite (Phase 3)
│   ├── src/
│   │   ├── types.ts         # TypeScript type definitions
│   │   ├── api.ts           # API client (fetch wrappers)
│   │   ├── url-state.ts     # URL-state manager
│   │   ├── utils.ts         # Formatting utilities
│   │   ├── App.tsx          # Root layout with react-router + ErrorBoundary
│   │   ├── main.tsx         # Entry point with BrowserRouter
│   │   ├── components/      # Reusable UI components
│   │   │   ├── FilterBar.tsx
│   │   │   ├── GroupByControl.tsx
│   │   │   ├── TreemapChart.tsx
│   │   │   ├── BarChart.tsx
│   │   │   ├── CategoryAccordion.tsx
│   │   │   ├── ContractsTable.tsx
│   │   │   ├── Pagination.tsx
│   │   │   ├── ErrorBoundary.tsx   # Error boundary with retry (Phase 8)
│   │   │   └── LoadingSkeleton.tsx  # Skeleton loading screens (Phase 8)
│   │   ├── pages/           # Route-level page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── ContractDetail.tsx
│   │   │   ├── InstitutionProfile.tsx
│   │   │   ├── VendorProfile.tsx
│   │   │   ├── BenchmarkView.tsx
│   │   │   ├── TimeView.tsx
│   │   │   └── GlobalView.tsx
│   │   └── __tests__/       # Frontend unit tests (vitest)
│   ├── vite.config.ts       # Vite + Tailwind + vitest config
│   └── package.json         # Node.js dependencies
├── scripts/
│   ├── migrate_ndjson.py    # NDJSON → JSON migration tool (Phase 0)
│   ├── start_dev.sh         # Unix dev startup script (Phase 8)
│   └── start_dev.ps1        # Windows dev startup script (Phase 8)
├── tests/
│   ├── test_parser.py       # Unit tests for parsing functions
│   ├── test_integration.py  # Integration tests
│   ├── test_models.py       # Model & sample-data tests (Phase 0)
│   ├── test_migrate.py      # Migration script tests (Phase 0)
│   ├── test_engine.py       # Engine tests (Phase 1)
│   ├── test_api.py          # API endpoint tests (Phase 2)
│   ├── test_e2e.py          # E2E integration tests (15 tests, Phase 8)
│   └── test_performance.py  # Performance benchmarks (14 tests, Phase 8)
├── data/
│   ├── sample_contracts.json # 30+ seed contracts (Phase 0)
│   └── pdfs/                # Downloaded PDFs (created on first run)
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI pipeline (Phase 8)
├── Dockerfile               # Multi-stage Docker build (Phase 8)
├── docker-compose.yml       # Docker Compose config (Phase 8)
├── Makefile                 # Common dev commands (Phase 8)
├── scrape_crz.py            # CLI entry point
├── requirements.in          # Unpinned dependencies
├── requirements.txt         # Pinned dependencies
├── .env.example             # Environment config template (Phase 0)
├── IMPLEMENTATION_PLAN.md   # Phase-by-phase development plan
└── README.md                # This file
```

### Adding Features

To extend the scraper:

1. **Add new fields**: Modify `extract_listing_rows()` or `extract_contract_details()` in `src/scraper.py`
2. **Change delay strategy**: Modify `DEFAULT_DELAY` or `RETRY_BACKOFF` constants
3. **Custom output format**: Modify the JSON serialization in `scrape_contracts()`

### Logging

Adjust logging level for debugging:
```bash
python scrape_crz.py --start-page 1 --max-pages 1 --log-level DEBUG
```

## Legal Notice

This tool is provided for educational and research purposes. Ensure you:

1. Comply with the website's Terms of Service
2. Respect the site's `robots.txt` file
3. Use reasonable request rates to avoid overloading the server
4. Check local laws regarding web scraping in your jurisdiction

The authors are not responsible for misuse of this tool.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For issues, questions, or suggestions:
- Create an issue on GitHub
- Include logs from `--log-level DEBUG`
- Describe the problem and expected behavior

## Changelog

### v1.9.0 — Phase 8: Polish, Integration Testing, and Deployment (2026-03-06)
- **E2E Tests**: 15 end-to-end integration tests (`tests/test_e2e.py`) covering full workflows, chatbot, and rule engine
- **Performance Tests**: 14 performance benchmarks (`tests/test_performance.py`) validating sub-second query times on 10k–50k synthetic contracts
- **Error Boundary**: `ErrorBoundary.tsx` React component wrapping all routes with retry button and expandable error details
- **Loading Skeletons**: `LoadingSkeleton.tsx` with `TableSkeleton`, `ChartSkeleton`, `CardSkeleton`, `SummarySkeleton` variants; integrated into Dashboard, BenchmarkView, TimeView, GlobalView
- **Accessibility Fixes**: ARIA attributes (`aria-sort`, `aria-expanded`, `aria-controls`, `aria-pressed`, `role` attributes), keyboard navigation (Enter/Space on table headers and rows), focus ring styles across ContractsTable, CategoryAccordion, GroupByControl, TreemapChart, FilterBar
- **Docker**: Multi-stage `Dockerfile` (python:3.12-slim + node:22-slim build + final image); `docker-compose.yml` with `govlens` service (port 8000) and optional `frontend-dev` service (port 5173)
- **Dev Scripts**: `Makefile` with 12 targets (install, dev, test, lint, build, docker, clean); `scripts/start_dev.sh` (Bash) and `scripts/start_dev.ps1` (PowerShell)
- **CI Pipeline**: `.github/workflows/ci.yml` with 4 jobs: backend-tests (Python 3.11+3.12 matrix), frontend-tests, frontend-lint, frontend-build

### v1.8.0 — Phase 7: State, Sharing, and Export (2026-03-06)
- `GET /api/export/pdf` — ReportLab-generated PDF report with title, summary stats, timestamp, and contract table (up to 500 rows)
- `POST /api/workspace/save` — snapshot filters, sort, groupBy, page, mode, chart state, and chat history → base64 token + JSON
- `GET /api/workspace/load?token=...` — restore workspace from base64-encoded snapshot
- Extended `encode_filter_state()` with `group_by`, `mode`, `page` parameters
- `WorkspaceToolbar` component: Share (clipboard), Save Workspace (JSON download), Export CSV, Export PDF buttons
- WorkspaceToolbar integrated into Dashboard, BenchmarkView, TimeView, and GlobalView
- `url-state.ts` extended with `AppMode` type and `mode` field for bookmarkable view switching
- Added `WorkspaceSnapshot`, `WorkspaceSaveResponse`, `WorkspaceLoadResponse` TypeScript types
- Added `pdfExportUrl()`, `saveWorkspace()`, `loadWorkspace()` API client functions
- Added `reportlab==4.4.10` to Python dependencies
- 15 new backend tests: `test_workspace.py` (5), `test_export.py` (5), `test_url_state.py` (5)
- 8 new frontend tests: `WorkspaceToolbar.test.tsx` (5), `url-state.test.ts` (3 new)
- Total: 312 backend tests (+ 1 skipped), 135 frontend tests

### v1.4.0 — Phase 3: Frontend: Institution Lens UI (2026-03-03)
- React 18 + TypeScript + Vite frontend in `frontend/`
- Tailwind CSS v4 via `@tailwindcss/vite` plugin
- react-router-dom for client-side routing with URL-state
- D3.js treemap visualization with drill-down
- Recharts horizontal bar charts and line charts for trends
- Components: FilterBar, GroupByControl, TreemapChart, BarChart, CategoryAccordion, ContractsTable, Pagination
- Pages: Dashboard (home), ContractDetail, InstitutionProfile, VendorProfile
- Multi-column sort with Shift+click, direction arrows (↑/↓), priority badges (①②③)
- URL-state manager: all filters, sort, group-by, pagination in URL query params
- API client wrapping all 14+ backend endpoints
- Global layout with header, breadcrumbs, footer
- Zero dead-ends: all entity names are clickable links
- Responsive design (desktop-first, mobile-usable via Tailwind)
- Vite proxy `/api` → `localhost:8000` for development
- 71 unit tests across 13 test files (vitest + @testing-library/react)

### v1.3.0 — Phase 2: Backend API (FastAPI) (2026-03-03)
- FastAPI application in `src/api.py` with 14 REST endpoints
- `src/config.py` for environment-variable-based configuration
- CORS middleware for frontend dev server
- Contract endpoints: paginated list with filtering, detail by ID
- Aggregation endpoints: group-by, treemap, benchmark, trends, rankings
- Entity endpoints: institution list/profile, vendor list/profile (lookup by name or ICO)
- CSV export with all active filters applied
- PDF export endpoint (stub, deferred to Phase 7)
- Filter-state serialization: encode/decode FilterState ↔ URL query params
- Added `fastapi`, `uvicorn[standard]`, `httpx` to dependencies
- 33 new unit tests in `tests/test_api.py`

### v1.2.0 — Phase 1: In-Memory Query & Aggregation Engine (2026-03-03)
- `DataStore` class in `src/engine.py` — loads JSON, holds Contract objects in RAM
- Shared global filters: institution(s), date range, category, vendor, value range, award type, text search
- `group_by(field)` for category, supplier, buyer, month, award_type
- Aggregations: total_spend, contract_count, avg_value, max_value, top_n_vendors, direct_award_rate
- `search(query)` — case-insensitive substring search over title and summary
- `compare(institutions, metric)` — benchmark institutions side-by-side
- `trend(granularity, metric)` — time-series by month/quarter/year
- `rank_institutions(metric)` / `rank_vendors(metric)` — global rankings
- Index structures for frequently-filtered fields (institution, category, date)
- `sort_contracts(contracts, sort_spec)` — multi-column sort with `SORTABLE_FIELDS` whitelist; `None` values always last regardless of direction
- 80 unit tests in `tests/test_engine.py` (11 new `TestSort` tests added)

### v1.1.0 — Phase 0: GovLens Data Foundation (2026-03-03)
- Pydantic v2 data models (`Contract`, `Institution`, `Vendor`, `FilterState`, `AggregationResult`)
- Three new enrichment fields on every contract: `category`, `pdf_text_summary`, `award_type`
- NDJSON → JSON migration script (`scripts/migrate_ndjson.py`)
- Sample data seed file (`data/sample_contracts.json`, 30+ records)
- `.env.example` configuration template
- Updated `requirements.in` with `pydantic` and `python-dotenv`
- 39 new unit tests across `test_models.py` and `test_migrate.py`

### v1.0.0 (2026-03-01)
- Initial release
- Contract listing pagination
- Contract detail extraction
- PDF download and text extraction
- NDJSON output format
- CLI with argparse
- Unit and integration tests
