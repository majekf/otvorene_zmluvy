# CRZ Scraper - Project Index

## 📍 Quick Navigation

### For Users
- **[QUICKSTART.md](QUICKSTART.md)** - Start here! Quick commands and examples
- **[README.md](README.md)** - Complete user guide and documentation

### For Developers
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical design and implementation details
- **[src/scraper.py](src/scraper.py)** - Core scraper implementation (~1000 LOC)

### Project Info
- **[PROJECT_COMPLETION.md](PROJECT_COMPLETION.md)** - What was built and acceptance criteria
- **[verify_project.py](verify_project.py)** - Run to verify project integrity

## 🚀 Getting Started

### 1. Installation (2 minutes)

```bash
cd crz_gov_scraping
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Verify Setup (1 minute)

```bash
python verify_project.py
pytest tests/ -v
```

### 3. Test Run (5 minutes)

```bash
python scrape_crz.py --start-page 1 --max-pages 1 --out test.ndjson
head -1 test.ndjson | python -m json.tool
```

## 📚 Documentation Structure

```
README.md                   ← Installation & basic usage
├─ Features
├─ Installation
├─ Usage
├─ Output Format
└─ Troubleshooting

QUICKSTART.md              ← Command reference & examples
├─ Installation
├─ Basic usage
├─ Output verification
├─ Common tasks
└─ Examples

ARCHITECTURE.md            ← Technical documentation
├─ Project structure
├─ Core components
├─ Data flow
├─ Performance analysis
├─ Configuration
├─ Error handling
└─ Future enhancements

PROJECT_COMPLETION.md      ← What was delivered
├─ Features implemented
├─ Acceptance criteria
├─ Test coverage
└─ File inventory
```

## 🔧 Project Structure

```
src/
├─ scraper.py             Main scraping logic (1000+ LOC)
│  ├─ parse_price()       Convert Slovak price to float
│  ├─ parse_slovak_date() Parse day/month/year to ISO
│  ├─ extract_listing_rows() Parse contract listings
│  ├─ extract_contract_details() Get detail page data
│  ├─ download_and_extract_pdf() Process PDFs
│  └─ scrape_contracts()  Main orchestrator
├─ models.py              Pydantic v2 data models (Phase 0)
│  ├─ Contract            Central contract record
│  ├─ Institution         Buyer entity
│  ├─ Vendor              Supplier entity
│  ├─ FilterState         Shared global filter
│  └─ AggregationResult   Group-by result
├─ engine.py              In-memory query engine (Phase 1)
│  ├─ DataStore           Central store: load, filter, group_by
│  ├─ aggregate()         total_spend, count, avg, max
│  ├─ search()            Full-text search
│  ├─ compare()           Benchmark institutions
│  ├─ trend()             Time-series analysis
│  ├─ sort_contracts()    Multi-column sort with None-last guarantee
│  ├─ rank_institutions() Global institution ranking
│  └─ rank_vendors()      Global vendor ranking
├─ api.py                 FastAPI REST endpoints (Phase 2)
│  ├─ lifespan()          Load DataStore at startup
│  ├─ parse_filters()     Query params → FilterState
│  ├─ encode_filter_state() FilterState → URL params
│  ├─ /api/contracts      Paginated, filterable list
│  ├─ /api/aggregations   Group-by + stats
│  ├─ /api/treemap        Hierarchical treemap data
│  ├─ /api/benchmark      Institution comparison
│  ├─ /api/trends         Time-series data
│  ├─ /api/rankings       Ranked entities
│  ├─ /api/institutions   Institution list + profiles
│  ├─ /api/vendors        Vendor list + profiles
│  └─ /api/export/csv     CSV download
├─ config.py              Environment-variable settings (Phase 2)
│  └─ Settings            host, port, data_path, LLM, scraper
└─ __init__.py

scripts/
└─ migrate_ndjson.py      NDJSON → JSON migration (Phase 0)

tests/
├─ test_parser.py         Unit tests (12 tests)
│  ├─ TestParsePrice
│  ├─ TestParseSlovakDate
│  └─ TestParseDateFromText
├─ test_integration.py    Integration tests (4 tests)
│  ├─ TestExtractListingRows
│  ├─ TestExtractContractDetails
│  └─ TestScrapeContractsSmoke
├─ test_models.py         Model & sample-data tests (24 tests, Phase 0)
│  ├─ TestContractModelDefaults
│  ├─ TestContractModelValidation
│  ├─ TestContractSerialization
│  ├─ TestContractFromScraperDict
│  ├─ TestFilterStateDefaults
│  ├─ TestAggregationResult
│  ├─ TestInstitutionModel
│  ├─ TestVendorModel
│  └─ TestSampleContractsFile
├─ test_migrate.py        Migration tests (15 tests, Phase 0)
│  ├─ TestMigrateAddsFields
│  ├─ TestMigratePreservesData
│  ├─ TestMigrateDoesNotOverwrite
│  ├─ TestMigrateOutputFormat
│  └─ TestMigrateEdgeCases
├─ test_engine.py         Engine tests (80 tests, Phase 1)
│  ├─ TestLoad
│  ├─ TestFilter
│  ├─ TestSearch
│  ├─ TestGroupBy
│  ├─ TestAggregation
│  ├─ TestInstitutionsVendors
│  ├─ TestCompare
│  ├─ TestTrends
│  ├─ TestRankings
│  ├─ TestSampleData
│  └─ TestEdgeCases
├─ test_api.py            API endpoint tests (33 tests, Phase 2)
│  ├─ TestContracts       List, filter, paginate, detail, 404
│  ├─ TestAggregations    Group by, with filter
│  ├─ TestTreemap         Structure, sub-grouping
│  ├─ TestBenchmark       Peer comparison
│  ├─ TestTrends          Time-series, filtered
│  ├─ TestRankings        Institutions, vendors
│  ├─ TestInstitutions    List, profile, ICO, not found
│  ├─ TestVendors         List, profile, ICO, not found
│  ├─ TestExport          CSV, CSV+filter, PDF 501
│  ├─ TestFilterState     Round-trip, empty encoding
│  └─ TestSampleDataSmoke Contracts, institutions, rankings, CSV
└─ __init__.py

data/
├─ sample_contracts.json  30+ seed contracts (Phase 0)
└─ pdfs/                  Downloaded PDFs (auto-created)

scrape_crz.py            CLI entry point with argparse

requirements.txt         Python dependencies

.gitignore               Git ignore rules

setup.py                 Validation script

verify_project.py        Integrity checker

init_git.py              Git initialization

setup_git.bat            Batch setup file
```

## 📊 Key Features

✓ **Pagination**: Handle multiple pages automatically
✓ **Data Extraction**: Contract listings and detail pages
✓ **PDF Handling**: Download and extract text
✓ **Price Parsing**: Convert Slovak format to float
✓ **Date Parsing**: Handle Slovak month names
✓ **Retry Logic**: Exponential backoff on failures
✓ **Polite Scraping**: Configurable delays (default 0.5s)
✓ **NDJSON Output**: One contract per line
✓ **Logging**: INFO/DEBUG/WARNING/ERROR levels
✓ **Testing**: 173 comprehensive tests
✓ **Pydantic Models**: Validated Contract, Institution, Vendor, FilterState, AggregationResult (Phase 0)
✓ **Migration Tool**: NDJSON → JSON with field backfill (Phase 0)
✓ **Sample Data**: 29 realistic seed contracts (Phase 0)
✓ **Env Config**: .env.example for LLM/server settings (Phase 0)
✓ **Query Engine**: DataStore with filtering, grouping, aggregation (Phase 1)
✓ **Full-Text Search**: Search over contract titles and summaries (Phase 1)
✓ **Benchmarking**: Compare institutions side-by-side (Phase 1)
✓ **Time Trends**: Monthly/quarterly/yearly spend analysis (Phase 1)
✓ **Rankings**: Institution and vendor rankings by multiple metrics (Phase 1)
✓ **REST API**: 14 FastAPI endpoints for contracts, analytics, and export (Phase 2)
✓ **Filter Serialization**: Encode/decode filters to/from URL query params (Phase 2)
✓ **CSV Export**: Download filtered contracts as CSV via API (Phase 2)
✓ **App Config**: Environment-variable settings via `src/config.py` (Phase 2)

## 🎯 Usage Examples

### Basic Scrape (5 pages)
```bash
python scrape_crz.py --start-page 1 --max-pages 5
```

### With Custom Settings
```bash
python scrape_crz.py \
  --start-page 1 \
  --max-pages 100 \
  --out contracts.ndjson \
  --delay 1.0 \
  --log-level INFO
```

### Debug Mode
```bash
python scrape_crz.py --start-page 1 --max-pages 1 --log-level DEBUG
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test
```bash
pytest tests/test_parser.py::TestParsePrice -v
```

### View Test Coverage
```bash
pytest --cov=src tests/
```

## 📊 Output Format

Each line is a complete JSON object with:

### Listing Fields
- `published_day`, `published_month`, `published_year`, `published_date`
- `contract_title`, `contract_number`, `contract_url`, `contract_id`
- `price_raw`, `price_numeric_eur`
- `supplier`, `buyer`

### Detail Fields (optional)
- `contract_number_detail`, `contract_id_detail`
- `ico_buyer`, `ico_supplier`
- `date_published`, `date_concluded`, `date_effective`, `date_valid_until`

### PDF Fields (optional)
- `pdf_url`, `pdf_local_path`, `pdf_text`

### GovLens Enrichment Fields (Phase 0)
- `category` — LLM-assigned category (default: `"not_decided"`)
- `pdf_text_summary` — LLM summary of PDF (default: `"not_summarized"`)
- `award_type` — Award mechanism (default: `"unknown"`)

### Always Present
- `scraped_at` (ISO datetime)

## ⚙️ Configuration

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--start-page` | int | 1 | Starting page (1-indexed) |
| `--max-pages` | int | 1 | Pages to scrape |
| `--out` | str | out.ndjson | Output file |
| `--delay` | float | 0.5 | Delay between requests (sec) |
| `--user-agent` | str | (realistic) | Custom User-Agent |
| `--pdf-dir` | str | data/pdfs | PDF directory |
| `--log-level` | str | INFO | Logging level |

### Code Constants (src/scraper.py)

```python
BASE_URL = "https://www.crz.gov.sk"
DEFAULT_TIMEOUT = 10              # seconds
DEFAULT_DELAY = 0.5               # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5               # exponential
```

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| 429 Too Many Requests | Increase `--delay` |
| No PDF text | PDF is scanned image (no OCR) |
| Script hangs | Increase timeout or reduce pages |
| Missing fields | Website structure may have changed |

**See README.md for detailed troubleshooting**

## 📈 Performance

- **1 page**: ~2-3 seconds
- **10 pages**: ~2-5 minutes  
- **100 pages**: ~20-50 minutes
- **1000 pages**: ~3-8 hours

*With `--delay 0.5` and 10% PDF downloads*

## 🛠️ Development

### Project Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Tests
```bash
pytest tests/ -v
```

### Verify Project
```bash
python verify_project.py
```

### Git Repository
```bash
python init_git.py    # First time setup
git log               # View commits
```

## 📝 Code Example

```python
from pathlib import Path
import sys
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from scraper import scrape_contracts

# Scrape 3 pages
count = scrape_contracts(
    start_page=1,
    max_pages=3,
    output_file="my_contracts.ndjson",
    delay=0.5
)

print(f"Scraped {count} contracts")

# Process results
with open("my_contracts.ndjson") as f:
    for line in f:
        contract = json.loads(line)
        print(f"{contract['contract_id']}: {contract['contract_title']}")
```

## 🎓 Learning Resources

- **BeautifulSoup4**: https://www.crummy.com/software/BeautifulSoup/
- **pdfplumber**: https://github.com/jsvine/pdfplumber
- **requests**: https://docs.python-requests.org/
- **pytest**: https://docs.pytest.org/
- **argparse**: https://docs.python.org/3/library/argparse.html

## 📞 Support

### Documentation
1. Check **[README.md](README.md)** for general help
2. Check **[QUICKSTART.md](QUICKSTART.md)** for commands
3. Check **[ARCHITECTURE.md](ARCHITECTURE.md)** for technical details

### Debugging
```bash
# Enable debug logging
python scrape_crz.py --start-page 1 --max-pages 1 --log-level DEBUG
```

### Testing
```bash
# Run tests with output
pytest tests/ -v -s
```

## ✅ Quality Checklist

- ✓ All required features implemented
- ✓ All acceptance criteria met
- ✓ 173 comprehensive tests (17 original + 39 Phase 0 + 80 Phase 1 + 33 Phase 2 + 4 integration)
- ✓ Full documentation (3 guides)
- ✓ Error handling and retries
- ✓ Polite scraping defaults
- ✓ Clean code with comments
- ✓ Real HTML examples tested
- ✓ NDJSON output format
- ✓ Git-ready structure
- ✓ Pydantic data models (Phase 0)
- ✓ Migration script (Phase 0)
- ✓ Sample data (Phase 0)

## 🎉 You're Ready!

1. **Install**: `pip install -r requirements.txt`
2. **Test**: `pytest tests/ -v`
3. **Run**: `python scrape_crz.py --start-page 1 --max-pages 1`
4. **Read**: Check [QUICKSTART.md](QUICKSTART.md) for more examples

---

**Project**: CRZ Government Contracts Scraper / GovLens
**Version**: 1.3.0 (Phase 2)
**Status**: Phase 2 Complete & Ready for Phase 3
**Last Updated**: 2026-03-03
