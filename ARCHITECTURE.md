# GovLens - Project Documentation

## Overview

GovLens is a full-stack application for exploring Slovak government contracts.

The backend scrapes three public procurement portals — the Central Register of Contracts (CRZ, https://www.crz.gov.sk/), the JOSEPHINE eProcurement platform (https://josephine.proebiz.com/), and the UVO tender portal (https://www.uvo.gov.sk/) — enriches the data with LLM-generated summaries and rule-based anomaly flags, and exposes everything through a FastAPI REST + WebSocket API.

The React/TypeScript frontend provides interactive dashboards, analytics views, a pattern-detection ("Red Flags") screen, a contracts-vs-subcontractors comparison view, and a WebSocket-backed contextual chatbot.

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

# 4. (Optional) Scrape contracts
python scrape_crz.py --start-page 1 --max-pages 3 --out contracts.ndjson
python scripts/migrate_ndjson.py -i contracts.ndjson -o data/contracts.json

# 5. Start backend
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# 6. Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

A **sample data file** (`data/sample_contracts.json`) ships with the repo so you can run the full UI without scraping first.

## Project Structure

```
crz_gov_scraping/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── scraper.py               # Core CRZ scraping logic + OCR helpers
│   ├── models.py                # Pydantic v2 data models
│   ├── engine.py                # In-memory query & aggregation engine
│   ├── api.py                   # FastAPI REST + WebSocket endpoints
│   ├── config.py                # Environment-variable config
│   ├── rules/                   # Pattern-detection rule engine (Phase 4)
│   │   ├── __init__.py
│   │   ├── engine.py            # 6 preset rules + RuleEngine class
│   │   └── builder.py           # No-code condition builder
│   └── chatbot/                 # LLM chatbot backend (Phase 5)
│       ├── __init__.py
│       ├── context.py           # Scoped context builder (LRU-cached)
│       ├── history.py           # Per-session chat history (in-memory)
│       ├── llm.py               # LLM client abstraction (Mock + OpenAI)
│       ├── protocol.py          # WebSocket frame models
│       ├── scope.py             # Out-of-scope query enforcement
│       └── usage.py             # Per-session token/cost accounting
├── frontend/                    # React + TypeScript + Vite
│   ├── src/
│   │   ├── types.ts             # TypeScript interfaces mirroring backend models
│   │   ├── api.ts               # API client (fetch wrappers for all endpoints)
│   │   ├── url-state.ts         # URL-state manager (parse/encode filters/sort/page)
│   │   ├── utils.ts             # Formatting utilities (EUR, compact, date)
│   │   ├── FilterContext.tsx    # Global filter state provider (React Context)
│   │   ├── App.tsx              # Root layout with react-router routes
│   │   ├── main.tsx             # Entry point with BrowserRouter
│   │   ├── components/          # Reusable UI components (17 total)
│   │   │   ├── AccordionContracts.tsx  # Lazy-loaded contracts per accordion group
│   │   │   ├── BarChart.tsx            # Recharts horizontal bar chart
│   │   │   ├── CategoryAccordion.tsx   # Expandable group rows with spend totals
│   │   │   ├── ChatBar.tsx             # Fixed-bottom WebSocket chatbot UI
│   │   │   ├── ClusteredBarChart.tsx   # Vertical clustered bar (contracts vs subcontractors)
│   │   │   ├── ConditionBuilder.tsx    # No-code custom rule UI
│   │   │   ├── ContractsTable.tsx      # Multi-column sortable table
│   │   │   ├── ErrorBoundary.tsx       # Error boundary with retry
│   │   │   ├── FilterBar.tsx           # Filter controls (institution, date, category, etc.)
│   │   │   ├── GroupByControl.tsx      # Group-by toggle buttons
│   │   │   ├── LoadingSkeleton.tsx     # Shimmer/pulse skeleton screens
│   │   │   ├── Pagination.tsx          # Page navigation
│   │   │   ├── RuleBadge.tsx           # Rule severity badge chip
│   │   │   ├── RulePanel.tsx           # Preset rules with param editors
│   │   │   ├── SeverityIndicator.tsx   # Visual severity bar
│   │   │   ├── TreemapChart.tsx        # D3 treemap with drill-down
│   │   │   └── WorkspaceToolbar.tsx    # Share/Save/CSV/PDF toolbar
│   │   └── pages/               # Route-level page components (10 total)
│   │       ├── AllContracts.tsx        # Flat contracts browser with full table
│   │       ├── BenchmarkView.tsx       # Institution benchmark comparison
│   │       ├── CompareView.tsx         # Contracts vs Subcontractors comparison
│   │       ├── ContractDetail.tsx      # Single contract detail
│   │       ├── Dashboard.tsx           # Home: filters + viz + accordion + chat
│   │       ├── GlobalView.tsx          # Global rankings table
│   │       ├── InstitutionProfile.tsx  # Institution stats + trend + vendors
│   │       ├── RedFlagsView.tsx        # Pattern-detection (rules + condition builder)
│   │       ├── TimeView.tsx            # Time trends with overlays
│   │       └── VendorProfile.tsx       # Vendor stats + trend + institutions
│   │   └── __tests__/           # 184+ frontend unit tests (vitest, 25 files)
│   ├── vite.config.ts           # Vite + Tailwind + vitest + proxy config
│   └── package.json             # Node.js dependencies
├── scripts/
│   ├── expand_subcontractors.py    # Explode contracts to one row per subcontractor
│   ├── migrate_jose_parts_once.py  # One-time Josephine parts migration
│   ├── migrate_ndjson.py           # NDJSON → JSON migration + field backfill
│   ├── start_dev.sh                # Unix dev startup script
│   └── start_dev.ps1               # Windows dev startup script
├── tests/
│   ├── __init__.py
│   ├── test_parser.py               # Unit tests for scraper parsing functions
│   ├── test_integration.py          # Integration tests for scraper
│   ├── test_models.py               # Model & sample-data tests
│   ├── test_migrate.py              # Migration script tests
│   ├── test_engine.py               # Engine tests (80+ tests)
│   ├── test_api.py                  # API endpoint tests (46+ tests)
│   ├── test_rules.py                # Rule engine & API tests (37 tests)
│   ├── test_chatbot.py              # Chatbot module tests (49 tests + 2 skipped)
│   ├── test_compare.py              # Contracts/subcontractors compare tests
│   ├── test_expand_subcontractors.py # expand_subcontractors.py tests
│   ├── test_josephine_scraper.py    # Josephine scraper tests
│   ├── test_uvo_scraper.py          # UVO scraper tests
│   ├── test_export.py               # CSV/PDF export tests (5 tests)
│   ├── test_workspace.py            # Workspace save/load tests (5 tests)
│   ├── test_url_state.py            # URL-state encoding tests (5 tests)
│   ├── test_e2e.py                  # E2E integration tests (15 tests)
│   └── test_performance.py          # Performance benchmarks (14 tests)
├── data/
│   ├── contracts.json               # Migrated contracts (generated)
│   ├── contracts_subcontractors.json # Subcontractor-expanded records (generated)
│   ├── tenders.json                 # Josephine/UVO tender records (generated)
│   └── pdfs/                        # Downloaded PDFs (auto-created)
├── scrape_crz.py                # CLI entry point for CRZ scraper
├── scrape_josephine.py          # Josephine procurement portal scraper
├── scrape_uvo.py                # UVO tender portal scraper
├── run_pipeline.py              # Orchestrates multi-source scraping pipeline
├── extract_api_chat.py          # CLI tool for chatbot context extraction
├── requirements.in              # Unpinned dependencies
├── requirements.txt             # Pinned Python dependencies
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.yml           # Docker Compose config
├── Makefile                     # Common dev commands
├── README.md                    # User documentation
├── ARCHITECTURE.md              # This file
└── .gitignore                   # Git ignore rules
```

## Architecture

### Core Components

#### 1. `src/scraper.py` — CRZ Scraper

**Key Functions:**

- **`parse_price(price_str)`**: Converts Slovak price format to float. Input: `"28 978,27 €"` → Output: `28978.27`
- **`parse_slovak_date(day, month, year)`**: Creates ISO date from Slovak parts (handles Slovak month names)
- **`parse_date_from_text(date_str)`**: Parses DD.MM.YYYY → ISO YYYY-MM-DD
- **`fetch_page(url, session)`**: Downloads page with exponential backoff, max 3 retries
- **`extract_listing_rows(html)`**: Extracts contracts from listing page (`table_list` CSS class)
- **`extract_contract_details(html, url)`**: Extracts contract metadata + PDF URLs from detail page
- **`extract_text_with_ocr(path)`**: PDF text extraction with OCR fallback using pypdfium2 + Pillow
- **`download_and_extract_pdf(pdf_url, pdf_dir, session)`**: Downloads PDF, extracts text (truncated at 50k chars)
- **`scrape_contracts(...)`**: Main orchestration — paginates, fetches details, downloads PDFs, writes NDJSON

#### 2. `scrape_crz.py` — CRZ CLI Interface

Entry point for scraping crz.gov.sk. Parses CLI arguments, configures logging, calls `scrape_contracts()`.

#### 3. `scrape_josephine.py` — Josephine Scraper (Phase 9)

Scrapes tender summaries from the JOSEPHINE eProcurement platform (https://josephine.proebiz.com/).

- Translates Slovak field names to English via lookup dictionaries
- Downloads result evaluation PDFs and enriches them with OpenAI GPT extraction
- Outputs structured tender records with buyer info, evaluation criteria, CPV codes, subcontractor data
- Reuses `extract_text_with_ocr` from `scraper.py`

#### 4. `scrape_uvo.py` — UVO Scraper (Phase 9)

Scrapes tender pages from the UVO procurement portal (https://www.uvo.gov.sk/).

- Normalises UVO tender URLs to canonical form
- Reuses helper functions from `scrape_josephine.py`
- Extracts detail fields and document links

#### 5. `src/models.py` — Pydantic Data Models

**Key Models:**

- **`Contract`**: Central record combining listing-page, detail-page, PDF, and GovLens enrichment fields.
  - Enrichment fields: `category` (default `"not_decided"`), `pdf_text_summary` (default `"not_summarized"`), `award_type` (default `"unknown"`)
  - `model_config = {"extra": "allow"}` — unknown keys pass through without error
- **`FilterState`**: Global filter with `institutions`, `date_from`/`date_to`, `categories`, `vendors`, `institution_icos`, `vendor_icos`, `icos`, `value_min`/`value_max`, `award_types`, `text_search`
- **`Institution`** / **`Vendor`**: Name, ICO, `contract_count`, `total_spend`
- **`AggregationResult`**: `group_key`, `group_value`, counts, spend stats

#### 6. `scripts/migrate_ndjson.py` — NDJSON Migration Tool

Converts scraper NDJSON output to a JSON array and backfills missing GovLens fields:

```bash
python scripts/migrate_ndjson.py -i out.ndjson -o data/contracts.json
```

Reads one JSON object per line, adds `category`/`pdf_text_summary`/`award_type` when missing, preserves existing values, and skips malformed lines with a warning.

#### 7. `scripts/expand_subcontractors.py` — Subcontractor Expansion (Phase 9)

Explodes each contract into one row per subcontractor:

```bash
python scripts/expand_subcontractors.py -i data/contracts.json -o data/contracts_subcontractors.json
```

- Handles subcontractor values as plain strings, dicts, JSON-encoded strings, or comma/semicolon-delimited lists
- Normalises subcontractor name and ICO from multiple possible key names
- Remaps `subcontractor`/`ico_subcontractor` → `supplier`/`ico_supplier` so the engine reuses vendor logic unmodified

#### 8. `src/engine.py` — In-Memory Query & Aggregation Engine

**Key Class: `DataStore`**

**Loading & Indexing:**
- `DataStore(data_path)` / `load_from_list(records)` — load JSON or list of dicts
- Auto-builds lookup indices for institution, category, date

**Filtering (`filter(FilterState)`):**
All filters are AND-combined; `None` means no filter.
Supports: institution name(s), institution/vendor ICOs, date range, categories, vendors, value range, award types, text search.

**Group By (`group_by(field, contracts?)`):**
Fields: `category`, `supplier`, `buyer`, `month`, `award_type`, `published_year` → `Dict[str, List[Contract]]`

**Aggregations:**
- `aggregate(contracts?)` → `{total_spend, contract_count, avg_value, max_value}`
- `aggregate_groups(field)` → `List[AggregationResult]` sorted by total_spend desc
- `top_n_vendors(n)` → `List[Vendor]`
- `direct_award_rate(contracts?)` → `float` (0.0–1.0)

**Benchmark / Compare:**
- `compare(institution_names, metric)` / `compare_multi_metric(institution_names, metrics)`
- `peer_group(institution_name, min_contracts)` — discover similar institutions

**Trends:**
- `trend(granularity, contracts?, metric)` — monthly/quarterly/yearly
- `trend_multi_metric(granularity, contracts, metrics)` — multi-metric

**Rankings:**
- `rank_institutions(metric)` / `rank_vendors(metric)` — with rank numbers
- `vendor_concentration_score(contracts, top_n)` — HHI-style
- `fragmentation_score(contracts)` — many-small-contracts score
- Metrics: `total_spend`, `contract_count`, `avg_value`, `max_value`, `direct_award_rate`, `vendor_concentration`, `fragmentation_score`

**Sort:**
- `sort_contracts(contracts, sort_spec)` — multi-column; `SORTABLE_FIELDS` whitelist; None values always last; strings case-insensitive

#### 9. `src/rules/` — Pattern-Detection Rule Engine (Phase 4)

**`src/rules/engine.py`** — `RuleEngine` class with 6 preset rules:

| Rule ID | Name | Description |
|---------|------|-------------|
| `threshold_proximity` | Threshold Proximity | Contracts within X% of a legal procurement threshold |
| `vendor_concentration` | Vendor Concentration | Top-N vendors hold > X% of institution spend |
| `fragmentation` | Fragmentation | Many small contracts to the same vendor |
| `overnight_turnaround` | Overnight Turnaround | Signed-to-published in < N hours |
| `new_vendor_large` | New Vendor Large Contract | First-time vendor with value above threshold |
| `round_number_clustering` | Round-Number Clustering | Statistical anomaly in round-number contract values |

Each rule produces `RuleFlag` objects with `rule_id`, `rule_name`, `severity` (0.0–1.0), `description`, and optional `contract_id`/`vendor`/`institution`.

`RuleResult` aggregates flags and provides `flags_for_contract(id)`, `flags_for_vendor(name)`, `severity_for_contract(id)`, `severity_for_vendor(name)`.

**`src/rules/builder.py`** — `ConditionGroup` class for no-code custom rules:

- Conditions: `field` / `operator` (`eq`, `ne`, `gt`, `ge`, `lt`, `le`, `contains`) / `value`
- Supported fields: `price_numeric_eur`, `published_date`, `contract_title`, `buyer`, `supplier`, `category`, `award_type`, `date_concluded`, `date_published`, `date_effective`
- Logic: `AND` or `OR` over a list of `Condition` objects; serialisable to/from JSON

#### 10. `src/chatbot/` — LLM Chatbot Backend (Phase 5)

**`llm.py`** — LLM client abstraction:
- `MockLLMClient` — deterministic template response, no API calls (CI/demo default)
- `OpenAIClient` — real OpenAI API with streaming + retry; activated by `LLM_PROVIDER=openai` + `OPENAI_API_KEY`
- Factory: `create_llm_client(provider, api_key, model, temperature)`

**`protocol.py`** — WebSocket frame models (Pydantic):
- `StartFrame` — generation started (provider, degraded flag)
- `TokenFrame` — single streamed token
- `PartialUsageFrame` — mid-stream token count update
- `DoneFrame` — complete response (content, provenance, scope_refusal, usage)
- `ErrorFrame` — error message
- `CancelFrame` — client → server abort signal

**`context.py`** — Context builder with LRU cache (128 entries):
- `build_scoped_context(store, filters)` — assembles a text prompt describing the current filtered contract set
- Uses `FIELD_LABEL_MAP` for human-friendly field names

**`scope.py`** — Out-of-scope query enforcement:
- `check_scope(message, filters, store)` — detects when the user mentions institutions/vendors outside the active filter
- Returns `ScopeRefusal` with structured suggestions

**`history.py`** — Per-session chat history:
- `InMemoryHistory` — default; LRU-eviction at 256 sessions
- Optional Redis/Postgres backends via feature flags
- API: `append(session_id, role, content)` / `get(session_id)` / `clear(session_id)`

**`usage.py`** — Token/cost accounting (active when `CHAT_COST_TRACKING=true`):
- Records `prompt_tokens`, `completion_tokens`, `total_cost_usd` per response per session

#### 11. `src/api.py` — Backend REST + WebSocket API

FastAPI application with two DataStore instances loaded at startup via lifespan handler.

**App Setup:**
- Primary DataStore from `GOVLENS_DATA_PATH`
- Optional subcontractors DataStore from `GOVLENS_SUBCONTRACTORS_DATA_PATH` (remaps `subcontractor` → `supplier` transparently)
- CORS middleware allowing all origins
- Dependency injection: `get_store()`, `get_sub_store()`, `parse_filters()`
- Filter params use **pipe-separated** values (e.g. `institutions=OrgA|OrgB`)

**Endpoints (27 total):**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/contracts` | GET | Paginated, filterable, sortable contract list |
| `/api/contracts/{id}` | GET | Single contract detail (404 if not found) |
| `/api/filter-options` | GET | Distinct slicer option lists with per-value counts |
| `/api/aggregations` | GET | Group-by + filters → aggregated stats |
| `/api/compare/aggregations` | GET | Contracts vs subcontractors side-by-side aggregations |
| `/api/treemap` | GET | Hierarchical data for D3 treemap |
| `/api/benchmark` | GET | Compare institutions by metric |
| `/api/benchmark/peers` | GET | Peer-group discovery |
| `/api/benchmark/compare` | GET | Multi-metric institution comparison |
| `/api/trends` | GET | Time-series by granularity, multi-metric, overlay dates |
| `/api/rankings` | GET | Ranked lists with pagination |
| `/api/institutions` | GET | All institutions with stats |
| `/api/institutions/{identifier}` | GET | Institution profile (by name or ICO) |
| `/api/vendors` | GET | All vendors with stats |
| `/api/vendors/{identifier}` | GET | Vendor profile (by name or ICO) |
| `/api/categories` | GET | Distinct category list |
| `/api/export/csv` | GET | Filtered CSV download |
| `/api/export/pdf` | GET | PDF report via ReportLab |
| `/api/workspace/save` | POST | Snapshot filters + UI state → base64 token |
| `/api/workspace/load` | GET | Restore workspace from base64 token |
| `/api/rules/presets` | GET | List the 6 preset rule definitions + default params |
| `/api/rules/evaluate` | POST | Evaluate selected rules against filtered contracts |
| `/api/rules/custom` | POST | Evaluate a custom `ConditionGroup` against filtered contracts |
| `/api/chat/status` | GET | Chat provider status (provider, degraded, active features) |
| `/api/chat/save` | POST | Export chat transcript + usage stats as JSON |
| `/api/chat` | WebSocket | Streaming contextual chatbot |
| `/api/filter-state` | GET | Debug: shows parsed/encoded filter state |

**Filter Query Parameters (shared across all filterable endpoints):**
- `institutions` — Pipe-separated buyer names
- `date_from` / `date_to` — Date range (YYYY-MM-DD)
- `categories` — Pipe-separated categories
- `vendors` — Pipe-separated supplier names
- `institution_icos` / `vendor_icos` — Pipe-separated IČO values
- `icos` — Pipe-separated IČO values (legacy alias)
- `value_min` / `value_max` — EUR value range
- `award_types` — Pipe-separated award types
- `text_search` — Full-text search query

**Running the server:**
```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

#### 12. `src/config.py` — Application Configuration

Loads settings from environment variables via `python-dotenv`. Key settings:

- `GOVLENS_HOST` / `GOVLENS_PORT` — Server binding (default: `0.0.0.0:8000`)
- `GOVLENS_DATA_PATH` — Primary contracts JSON (default: `data/sample_contracts.json`)
- `GOVLENS_SUBCONTRACTORS_DATA_PATH` — Subcontractors JSON (optional, empty = disabled)
- `LLM_PROVIDER` — `mock` (default) | `openai` | `anthropic`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — API credentials
- `OPENAI_MODEL` / `OPENAI_TEMPERATURE` — Model+temperature (default: `gpt-4.1-nano`, `0.2`)
- `CHAT_STREAMING`, `CHAT_HISTORY_BACKEND`, `CHAT_PROVENANCE`, `CHAT_COST_TRACKING`, `CHAT_OBSERVABILITY`, `CHAT_MAX_MESSAGE_LENGTH` — Chatbot feature flags
- `SCRAPER_PDF_DIR` / `SCRAPER_DELAY` — Scraper settings

Auto-forces `LLM_PROVIDER=mock` when the selected provider has no API key configured.

#### 13. `frontend/` — React Frontend

**Tech stack:**
- React 19 + TypeScript, Vite 7, Tailwind CSS v4 (`@tailwindcss/vite`), react-router-dom 7
- D3.js 7 (treemap), Recharts 3 (bar/line charts)
- vitest 3 + `@testing-library/react` — 184+ unit tests (25 test files)

**Global State (`FilterContext.tsx`):**
- `FilterProvider` wraps the app; exposes `filters`, `setFilters`, and pre-fetched dropdown option lists (institutions, vendors, categories, ICO maps, per-value counts)
- Fetches `/api/filter-options` once and caches it for the session lifetime
- Filters survive in-app navigation without re-encoding per page
- Seeds from URL on first mount for deep-link support

**Key Modules:**
- `types.ts` — TypeScript interfaces mirroring all backend models (all phases)
- `api.ts` — Thin fetch wrappers for all 27 REST endpoints + WebSocket URL helper; filter lists are pipe-joined
- `url-state.ts` — Parse/encode full UI state to/from URL query params (filters, sort, groupBy, page, mode)
- `utils.ts` — EUR formatting, compact numbers, date display

**Components (17):**
- `AccordionContracts` — Mounts only when a group is expanded; fetches contracts for that group on demand
- `BarChart` — Recharts horizontal bar chart
- `CategoryAccordion` — Expandable group rows, each embedding `AccordionContracts`
- `ChatBar` — Fixed bottom-bar WebSocket chatbot: streaming tokens, scope-refusal panel, source provenance, cancel, degraded-mode banner
- `ClusteredBarChart` — Vertical Recharts clustered bar (contracts vs subcontractors)
- `ConditionBuilder` — No-code custom rule UI, maps to `src/rules/builder.py`
- `ContractsTable` — Multi-column sortable table (Shift+click multi-sort, priority badges ①②③)
- `ErrorBoundary` — Wraps all routes; retry button + expandable error details
- `FilterBar` — Institution/ICO, date range, category, vendor/ICO, value range, award type, text search
- `GroupByControl` — Toggle between 5 group-by fields
- `LoadingSkeleton` — `TableSkeleton`, `ChartSkeleton`, `CardSkeleton`, `SummarySkeleton` variants
- `Pagination` — First/prev/next/last with page window
- `RuleBadge` — Severity chip (colour-coded)
- `RulePanel` — Lists preset rules with param sliders; evaluates and displays flags
- `SeverityIndicator` — Visual fill bar 0–100%
- `TreemapChart` — D3 treemap with drill-down on click
- `WorkspaceToolbar` — Share (clipboard URL), Save Workspace (JSON), Export CSV, Export PDF

**Pages (10):**
- `Dashboard` — Home: filters + treemap/bar + category accordion + contracts table + pagination + WorkspaceToolbar + ChatBar
- `AllContracts` — Flat contracts browser: FilterBar + ContractsTable + pagination (no chart/accordion layer)
- `ContractDetail` — Full contract info, PDF link, summary, category/award badges
- `InstitutionProfile` — Stats cards, spend trend line chart, top vendors bar chart, contracts table
- `VendorProfile` — Stats cards, revenue trend, institutions served bar chart, contracts table
- `BenchmarkView` — Institution benchmark comparison by metric
- `TimeView` — Time trends with overlay date markers
- `GlobalView` — Global rankings table (institutions or vendors)
- `CompareView` — Contracts vs Subcontractors: clustered bar comparison by group-by field and metric
- `RedFlagsView` — Pattern detection: `RulePanel` (preset rules) + `ConditionBuilder` (custom) side-by-side

**Routing:**

| Path | Page |
|------|------|
| `/` | Dashboard |
| `/contracts` | AllContracts |
| `/contract/:id` | ContractDetail |
| `/institution/:id` | InstitutionProfile |
| `/vendor/:id` | VendorProfile |
| `/benchmark` | BenchmarkView |
| `/time` | TimeView |
| `/rankings` | GlobalView |
| `/compare` | CompareView |
| `/red-flags` | RedFlagsView |

**ChatBar** is shown only on `/` (Dashboard). It opens a WebSocket to `/api/chat` and streams LLM tokens. It shows source provenance and scope-refusal suggestions when the LLM detects an out-of-scope query.

#### 14. Tests

**Backend (173+ passing, 18 test files):**
- `test_parser.py` — price/date parsing, edge cases
- `test_integration.py` — listing/detail extraction, full smoke test
- `test_models.py` — Contract defaults, validation, FilterState, AggregationResult
- `test_migrate.py` — field backfill, data preservation, edge cases
- `test_engine.py` (80+) — filtering, search, grouping, aggregation, trends, rankings, sort, sample-data smoke tests
- `test_api.py` (46+) — all endpoints, sort, pagination, benchmark, trends, rankings
- `test_rules.py` (37) — 6 preset rules, severity scoring, condition builder, rules API
- `test_chatbot.py` (49+2 skipped) — context builder, scope enforcement, LLM clients, history, protocol, usage, API, security
- `test_compare.py` — `/api/compare/aggregations` with and without sub-store
- `test_expand_subcontractors.py` — append-only expansion behavior
- `test_josephine_scraper.py` — Josephine HTML parsing, URL detection
- `test_uvo_scraper.py` — UVO detail fields, document table parsing, URL helpers
- `test_export.py` (5) — CSV/PDF export content, filter, sort
- `test_workspace.py` (5) — save/load round-trip, chat history, invalid token
- `test_url_state.py` (5) — encode/decode round-trip, edge cases
- `test_e2e.py` (15) — full workflow, chatbot, rule workflow
- `test_performance.py` (14) — filter/aggregation/sort at 10k and 50k contracts

**Frontend (184+ passing, 25 test files):** One test file per component/page covering rendering, interactions, API mocking, URL-state, and accessibility.

### Data Flow

```
CRZ / Josephine / UVO
  ↓ (scrapers)
scrape_crz.py / scrape_josephine.py / scrape_uvo.py
  └─ Write NDJSON output

         ↓

scripts/migrate_ndjson.py
  Read NDJSON → backfill fields → write data/contracts.json

scripts/expand_subcontractors.py  (optional)
  Explode subcontractors → data/contracts_subcontractors.json

         ↓

src/engine.py — DataStore (primary)
src/engine.py — DataStore (sub-store, optional)
  Load JSON → build indices → filter / group / aggregate / search / trend / rank

         ↓

src/api.py — FastAPI Application (27 endpoints + WebSocket)
  ├─ REST: GET /api/contracts, /api/aggregations, /api/treemap, etc.
  ├─ Rules: POST /api/rules/evaluate, /api/rules/custom
  ├─ Compare: GET /api/compare/aggregations (primary + sub-store)
  └─ Chat: WS /api/chat → src/chatbot/* → LLM → streaming tokens

         ↓

frontend/ — React SPA
  FilterContext → shared filter state across all 10 pages
  api.ts → fetch wrappers (27 endpoints) + WebSocket URL
  Pages: Dashboard / AllContracts / ContractDetail / ... / RedFlagsView
```

## Configuration

### Environment Variables

Configured via `src/config.py`, loaded through `python-dotenv`. Copy `.env.example` and fill in values:

**Server & Data**
- `GOVLENS_HOST` / `GOVLENS_PORT` — Server binding (default: `0.0.0.0:8000`)
- `GOVLENS_DATA_PATH` — Path to main contracts JSON (default: `data/contracts.json`)
- `GOVLENS_SUBCONTRACTORS_DATA_PATH` — Path to subcontractors JSON (optional, Phase 9)

**LLM / Chatbot (Phase 5)**
- `LLM_PROVIDER` — `openai` or `mock`; auto-forces `mock` when no API key set
- `OPENAI_API_KEY` — OpenAI credentials
- `OPENAI_MODEL` — Model identifier (default: `gpt-4.1-nano`)
- `OPENAI_TEMPERATURE` — Sampling temperature (default: `0.2`)
- `CHAT_STREAMING` — Stream tokens over WebSocket (default: `true`)
- `CHAT_HISTORY_BACKEND` — `memory` (default), `redis`, or `postgres`
- `CHAT_PROVENANCE` — Include contract citations in responses (default: `true`)
- `CHAT_COST_TRACKING` — Track token cost per session (default: `false`)
- `CHAT_OBSERVABILITY` — Enable observability/tracing hooks (default: `false`)
- `CHAT_DEBUG` — Verbose chatbot logging (default: `false`)
- `CHAT_MAX_MESSAGE_LENGTH` — Maximum user message length in chars (default: `4000`)

**Scraper**
- `SCRAPER_PDF_DIR` — PDF storage directory (default: `data/pdfs`)
- `SCRAPER_DELAY` — Delay between requests in seconds (default: `0.5`)

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

### Backend Tests (173+ tests across 18 files)

```bash
pytest tests/ -v --tb=short
```

| Test file | Phase | Approx tests | What it covers |
|-----------|-------|-------------|----------------|
| `test_parser.py` | 0 | ~10 | Slovak price/date parsing |
| `test_models.py` | 0 | ~12 | Contract, FilterState, AggregationResult, Institution, Vendor |
| `test_migrate.py` | 0 | ~8 | NDJSON migration field backfill, preservation, edge cases |
| `test_engine.py` | 1+6 | 95 | Filter, group-by, aggregate, trends, rankings, multi-column sort |
| `test_api.py` | 2+6+7 | 46 | All 27 REST endpoints, filter combos, pagination, exports |
| `test_workspace.py` | 7 | 5 | Save/load workspace round-trip, invalid tokens |
| `test_export.py` | 7 | 5 | CSV/PDF export content, filters, sort |
| `test_url_state.py` | 7 | 5 | URL-state encode/decode round-trip |
| `test_e2e.py` | 8 | 15 | Full workflow, benchmark, chatbot WebSocket, rules round-trip |
| `test_performance.py` | 8 | 14 | Filter/aggregation/sort/load performance benchmarks |
| `test_integration.py` | 0 | ~8 | HTML parsing, listing/detail extraction, smoke test |
| `test_rules.py` | 4 | 37 | All 6 preset rules, ConditionBuilder, severity scoring |
| `test_chatbot.py` | 5 | 49 | MockLLM, streaming protocol frames, scope check, history, usage |
| `test_compare.py` | 9 | ~10 | Compare aggregations, subcontractor store loading |
| `test_expand_subcontractors.py` | 9 | ~8 | Subcontractor expansion logic, field remapping |
| `test_josephine_scraper.py` | 9 | ~8 | Josephine portal scraping, PDF extraction |
| `test_uvo_scraper.py` | 9 | ~8 | UVO portal scraping, shared helpers |
| `test_data.json` | — | — | Seed test data (not a test runner file) |

### Frontend Tests (184+ tests across 25 files)

```bash
cd frontend && npm test
# or watch mode
npm run test:watch
```

All tests use **vitest** + `@testing-library/react`. Covers all 17 components and all 10 pages.

### Targeted Runs

```bash
# Single file
pytest tests/test_rules.py -v

# By phase marker (if using pytest marks)
pytest tests/ -k "chatbot" -v

# Coverage report
pytest --cov=src tests/
```

## Potential Future Enhancements

- **Async scraping**: `asyncio`/`httpx` parallel detail-page fetching for faster data collection
- **OCR for scanned PDFs**: `pytesseract` + wand for image-only PDFs
- **Redis/Postgres history**: Production-grade chatbot conversation history backends (stubs exist)
- **Observability**: OpenTelemetry tracing hooks (config flag exists, handlers not implemented)
- **Resume scraping**: Checkpoint to skip already-scraped contract IDs
- **Change detection**: Diff scraper output over time to surface new/updated contracts
- **More procurement portals**: Extend beyond CRZ, Josephine, UVO to other Slovak/EU portals
- **Alert subscriptions**: Email/webhook notifications on rules matches above a severity threshold

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

### Backend (Python — `requirements.txt`)

**Core:**
- `fastapi 0.135.1` — REST + WebSocket API framework
- `uvicorn[standard] 0.41.0` — ASGI server
- `pydantic 2.12.5` — Data models and validation
- `python-dotenv` — `.env` file support
- `httpx` — HTTP client (FastAPI TestClient)
- `websockets 16.0` — WebSocket client/server support

**Scraping & PDF:**
- `requests` — HTTP client for scrapers
- `beautifulsoup4` + `lxml` — HTML parsing
- `pypdfium2` — PDF rendering/text extraction (Phase 9)
- `pillow` — Image processing for PDF pages (Phase 9)

**AI / Chatbot:**
- `openai` — OpenAI API client (Phase 5); auto-disabled when no key set

**Export:**
- `reportlab` — PDF report generation

### Frontend (Node.js — `frontend/package.json`)

- `react 19.2` + `react-dom 19.2` — UI framework
- `react-router-dom 7.13` — Client-side routing
- `recharts 3.7` — Bar / line / area charts
- `d3 7.9` — Treemap visualization
- `tailwindcss v4` + `@tailwindcss/vite` — Utility-first CSS
- `vite 7.3` — Build tool with HMR, dev proxy
- `typescript ~5.9` — Type safety
- `vitest 3.2.4` — Test runner
- `@testing-library/react` + `@testing-library/jest-dom` — Component testing
- `@testing-library/user-event` — User interaction simulation

## Version History

### v2.0.0 — Phase 9: Compare View & Subcontractor Expansion

- `scrape_josephine.py` — Josephine procurement portal scraper with OpenAI-assisted PDF extraction
- `scrape_uvo.py` — UVO (Slovak Public Procurement Office) portal scraper
- `scripts/expand_subcontractors.py` — explodes contract rows into one-per-subcontractor, remaps fields
- `scripts/migrate_jose_parts_once.py` — one-time migration for Josephine parts data
- Dual `DataStore` in `src/api.py`: primary (contracts) + sub-store (subcontractors), remaps `subcontractor`→`supplier`
- New `CompareView` page — side-by-side contracts vs subcontractors aggregated by institution/vendor
- `ClusteredBarChart` — grouped bar chart for compare view
- `AccordionContracts` — collapsible contract list with inline summaries
- New API endpoints: `/api/compare/aggregations`, `/api/categories`, `/api/filter-options`
- New TypeScript types: `CompareAggregationRow`, `CompareAggregationsResponse`, `FilterOptionsResponse`
- `pypdfium2` + `pillow` added to Python dependencies

### v1.9.0 — Phase 8: Polish, Integration Testing, and Deployment

- 15 E2E integration tests (`test_e2e.py`), 14 performance benchmarks (`test_performance.py`)
- `ErrorBoundary.tsx` wrapping all routes with retry and error details
- `LoadingSkeleton.tsx` with Table/Chart/Card/Summary skeleton variants
- Accessibility: ARIA attributes, keyboard navigation, focus management across 6 components
- Multi-stage Dockerfile + docker-compose.yml
- Makefile + start_dev.sh + start_dev.ps1 dev scripts
- GitHub Actions CI pipeline (4 jobs: backend-tests, frontend-tests, lint, build)

### v1.8.0 — Phase 7: Workspace Persistence & Export

- `WorkspaceToolbar` component — Share (clipboard), Save Workspace (JSON), Export CSV, Export PDF
- `/api/workspace/save` + `/api/workspace/load` — base64-encoded snapshot tokens
- `/api/export/csv` + `/api/export/pdf` — filtered downloads; PDF uses ReportLab
- `url-state.ts` extended with `mode` field; filter encoding/decoding round-trips
- 15 new tests: `test_workspace.py`, `test_export.py`, `test_url_state.py`

### v1.7.0 — Phase 6: Investigation Modes

- BenchmarkView, TimeView, RankingsView pages
- Multi-metric compare: `/api/benchmark/compare`, `/api/benchmark/peers`
- Enhanced trends: `/api/trends` with multi-metric overlays
- Enhanced rankings with `vendor_concentration` and `fragmentation_score` metrics
- `LeaderboardTable`, `TrendChart`, `MetricSelector` components
- `FilterContext.tsx` — global filter state shared across all pages from `/api/filter-options`

### v1.6.0 — Phase 5: LLM Chatbot

- `src/chatbot/` package: `llm.py`, `protocol.py`, `context.py`, `scope.py`, `history.py`, `usage.py`
- WebSocket endpoint `ws://.../api/chat` with streaming token frames
- `MockLLMClient` (default) + `OpenAIClient` (activated by env)
- Scoped context builder with LRU cache; `ScopeRefusal` for out-of-scope queries
- `InMemoryHistory` with LRU-256 session cap; Redis/Postgres stubs behind feature flags
- Per-session cost tracking when `CHAT_COST_TRACKING=true`
- `ChatBar` component on Dashboard; `/api/chat/status`, `/api/chat/save`
- 49 new tests in `test_chatbot.py`

### v1.5.0 — Phase 4: Red-Flags Rules Engine

- `src/rules/` package: `engine.py`, `builder.py`
- 6 preset rules: `threshold_proximity`, `vendor_concentration`, `fragmentation`, `overnight_turnaround`, `new_vendor_large`, `round_number_clustering`
- `ConditionBuilder` — no-code custom rules with AND/OR logic, JSON-serialisable
- API endpoints: `/api/rules/presets`, `/api/rules/evaluate`, `/api/rules/custom`
- `RedFlagsView` page + `RulePanel` component
- 37 new tests in `test_rules.py`

### v1.4.0 — Phase 3: Frontend: Institution Lens UI

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

### v1.3.0 — Phase 2: Backend API (FastAPI) 

- FastAPI application in `src/api.py` with 17 REST endpoints
- `src/config.py` for environment-variable-based configuration
- CORS middleware, filter-state serialization, CSV export
- Institution and vendor profiles with lookup by name or ICO
- PDF export stub (deferred to Phase 7)
- Added `fastapi`, `uvicorn[standard]`, `httpx` to dependencies
- 33 new unit tests in `tests/test_api.py`

### v1.2.0 — Phase 1: In-Memory Query & Aggregation Engine 

- `DataStore` class in `src/engine.py` — loads JSON, holds Contract objects in RAM
- Filtering, grouping, aggregation, search, benchmarking, trends, rankings
- `sort_contracts(contracts, sort_spec)` — multi-column sort; `SORTABLE_FIELDS` whitelist; `None` values always last
- 95 unit tests in `tests/test_engine.py` (Phase 1 base + Phase 6 investigation modes)

### v1.1.0 — Phase 0: GovLens Data Foundation 

- Pydantic v2 data models (Contract, Institution, Vendor, FilterState, AggregationResult)
- Three new enrichment fields: category, pdf_text_summary, award_type
- NDJSON → JSON migration script
- Sample data seed file (30+ records)
- .env.example configuration template
- 39 new unit tests

### v1.0.0 

Initial release with:
- Pagination support
- Contract detail extraction
- PDF download and text extraction
- NDJSON output
- CLI interface
- Unit and integration tests
- Comprehensive documentation
