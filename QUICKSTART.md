# CRZ Scraper - Quick Reference

## Installation

```bash
# 1. Navigate to project
cd crz_gov_scraping

# 2. Create environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install packages
pip install -r requirements.txt

# Or use Makefile
make install
```

## Docker Quick Start

```bash
# Build and run with Docker Compose
docker compose up --build

# Or use Makefile shortcut
make docker

# Access the application
# http://localhost:8000       — API + Frontend
# http://localhost:8000/docs  — Swagger docs

# Stop
docker compose down
```

## Development Scripts

```bash
# Start backend + frontend dev servers
make dev
# Or: ./scripts/start_dev.sh      (Unix)
# Or: .\scripts\start_dev.ps1     (Windows PowerShell)

# Run all tests
make test

# Lint frontend
make lint

# Build frontend for production
make build

# Clean caches and build artifacts
make clean
```

## Basic Usage

```bash
# Scrape pages 1-3
python scrape_crz.py --start-page 1 --max-pages 3

# Scrape with custom output file
python scrape_crz.py --start-page 1 --max-pages 10 --out my_contracts.ndjson

# Scrape with longer delays (respect the server)
python scrape_crz.py --start-page 1 --max-pages 50 --delay 1.0

# Debug mode
python scrape_crz.py --start-page 1 --max-pages 1 --log-level DEBUG
```

## Output Verification

```bash
# Count contracts
wc -l out.ndjson

# View first contract (pretty-printed)
head -1 out.ndjson | python -m json.tool

# Extract contract IDs
python -c "import json; [print(json.loads(line)['contract_id']) for line in open('out.ndjson')]"

# Filter contracts over 100k EUR
python -c "import json; [print(json.loads(line)['contract_number']) for line in open('out.ndjson') if json.loads(line).get('price_numeric_eur', 0) > 100000]"
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_parser.py -v

# Run specific test
pytest tests/test_parser.py::TestParsePrice::test_parse_price_large -v

# Run Phase 0 model & migration tests
pytest tests/test_models.py tests/test_migrate.py -v

# Run Phase 1 engine tests
pytest tests/test_engine.py -v

# Run Phase 2 API tests
pytest tests/test_api.py -v

# Run Phase 8 E2E tests
pytest tests/test_e2e.py -v

# Run Phase 8 performance tests
pytest tests/test_performance.py -v

# Run frontend tests
cd frontend && npx vitest run

# Run with output
pytest tests/ -v -s

# Coverage report
pytest --cov=src tests/
```

## Migration Tool (Phase 0)

```bash
# Convert NDJSON scraper output to JSON array with GovLens fields
python scripts/migrate_ndjson.py -i out.ndjson -o data/contracts.json

# Default output is data/contracts.json
python scripts/migrate_ndjson.py -i out.ndjson
```

## Using Data Models (Phase 0)

```python
from src.models import Contract, FilterState

# Create a contract from scraper dict
contract = Contract(**json.loads(line))
print(contract.category)        # "not_decided"
print(contract.award_type)      # "unknown"

# Build a filter
fs = FilterState(
    institutions=["Mesto Bratislava"],
    value_min=10000,
    categories=["construction"],
)
print(fs.model_dump())
```

## Using the Query Engine (Phase 1)

```python
from src.engine import DataStore
from src.models import FilterState

# Load contracts into the engine
store = DataStore("data/sample_contracts.json")
print(f"Loaded {store.count} contracts")

# Filter contracts
f = FilterState(
    institutions=["Mesto Bratislava"],
    date_from="2025-01-01",
    value_min=50000,
)
results = store.filter(f)
print(f"Found {len(results)} matching contracts")

# Full-text search
matches = store.search("dodávka")
print(f"Search found {len(matches)} contracts")

# Aggregate statistics
stats = store.aggregate(results)
print(f"Total spend: {stats['total_spend']:,.2f} EUR")
print(f"Average value: {stats['avg_value']:,.2f} EUR")

# Group by category and aggregate
agg = store.aggregate_groups("category")
for r in agg:
    print(f"  {r.group_value}: {r.total_spend:,.2f} EUR ({r.contract_count} contracts)")

# Top 5 vendors by total spend
top = store.top_n_vendors(n=5)
for v in top:
    print(f"  {v.name}: {v.total_spend:,.2f} EUR")

# Compare institutions
comp = store.compare(["Mesto Bratislava", "Mesto Košice"], metric="total_spend")
for c in comp:
    print(f"  {c['institution']}: {c['value']:,.2f} EUR")

# Monthly spend trend
trend = store.trend(granularity="month")
for t in trend:
    print(f"  {t['period']}: {t['value']:,.2f} EUR")

# Institution rankings
ranked = store.rank_institutions(metric="total_spend")
for r in ranked:
    print(f"  #{r['rank']} {r['institution']}: {r['value']:,.2f} EUR")
```

## Using the REST API (Phase 2)

### Start the Server

```bash
# Start the API server (development mode with auto-reload)
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Open interactive API docs
# http://localhost:8000/docs
```

### Example API Calls

```bash
# List contracts (paginated)
curl "http://localhost:8000/api/contracts?page=1&page_size=10"

# Filter by institution and date range
curl "http://localhost:8000/api/contracts?institutions=Mesto%20Bratislava&date_from=2025-01-01"

# Get contract detail
curl "http://localhost:8000/api/contracts/12048046"

# Aggregation by category
curl "http://localhost:8000/api/aggregations?group_by=category"

# Treemap data (category → supplier)
curl "http://localhost:8000/api/treemap?group_by=category&sub_group_by=supplier"

# Compare institutions
curl "http://localhost:8000/api/benchmark?institutions=Mesto%20Bratislava,Mesto%20Ko%C5%A1ice&metric=total_spend"

# Monthly trends
curl "http://localhost:8000/api/trends?granularity=month&metric=total_spend"

# Institution rankings
curl "http://localhost:8000/api/rankings?entity=institutions&metric=total_spend"

# Institution profile
curl "http://localhost:8000/api/institutions/Mesto%20Bratislava"

# CSV export with filters
curl -O "http://localhost:8000/api/export/csv?categories=construction&value_min=100000"
```

### API Endpoint Reference

| Endpoint | Description |
|----------|-------------|
| `GET /api/contracts` | Paginated, filterable contract list |
| `GET /api/contracts/{id}` | Single contract detail |
| `GET /api/aggregations` | Group-by aggregations |
| `GET /api/treemap` | Hierarchical treemap data |
| `GET /api/benchmark` | Institution comparison |
| `GET /api/trends` | Time-series trends |
| `GET /api/rankings` | Entity rankings |
| `GET /api/institutions` | Institution list |
| `GET /api/institutions/{identifier}` | Institution profile |
| `GET /api/vendors` | Vendor list |
| `GET /api/vendors/{identifier}` | Vendor profile |
| `GET /api/export/csv` | CSV download |
| `GET /api/export/pdf` | PDF export (ReportLab report) |
| `POST /api/workspace/save` | Save workspace snapshot |
| `GET /api/workspace/load` | Restore workspace from token |
| `GET /api/filter-state` | Debug: filter state |

## Common Tasks

### Process Output

```python
import json
from pathlib import Path

# Read all contracts
contracts = [json.loads(line) for line in open('out.ndjson')]

# Filter by price
expensive = [c for c in contracts if c.get('price_numeric_eur', 0) > 50000]

# Get unique suppliers
suppliers = {c['supplier'] for c in contracts}

# Contracts with PDFs
with_pdfs = [c for c in contracts if c.get('pdf_text')]

# Save filtered results
with open('expensive.ndjson', 'w') as f:
    for contract in expensive:
        f.write(json.dumps(contract, ensure_ascii=False) + '\n')
```

### Python Script Usage

```python
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper import scrape_contracts

# Scrape 5 pages
count = scrape_contracts(
    start_page=1,
    max_pages=5,
    output_file="my_output.ndjson",
    delay=0.5,
    pdf_dir="pdfs"
)

print(f"Scraped {count} contracts")
```

## Configuration Reference

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `--start-page` | int | 1 | First page to scrape (1-indexed) |
| `--max-pages` | int | 1 | How many pages to scrape |
| `--out` | str | out.ndjson | Output file path |
| `--delay` | float | 0.5 | Seconds between requests |
| `--user-agent` | str | realistic | Custom User-Agent header |
| `--pdf-dir` | str | data/pdfs | Where to save PDFs |
| `--log-level` | str | INFO | DEBUG/INFO/WARNING/ERROR |

## Output Fields

### Required in all records
- `contract_id`: Extracted from URL
- `contract_url`: Link to detail page
- `scraped_at`: ISO datetime

### From listing page
- `published_date`: ISO format date
- `contract_title`: Contract name
- `contract_number`: Number from listing
- `price_numeric_eur`: Parsed price as float
- `supplier`: Supplier company name
- `buyer`: Buyer organization name

### From detail page (optional)
- `contract_id_detail`: ID from detail page
- `contract_number_detail`: Number from detail page
- `ico_buyer`: Tax ID of buyer
- `ico_supplier`: Tax ID of supplier
- `date_published`, `date_concluded`, `date_effective`, `date_valid_until`

### From PDF (optional)
- `pdf_url`: Direct link to PDF
- `pdf_local_path`: Where PDF was saved
- `pdf_text`: Extracted text (first 50k chars)

### GovLens Enrichment (Phase 0)
- `category`: LLM-assigned category (default: `"not_decided"`)
- `pdf_text_summary`: LLM summary (default: `"not_summarized"`)
- `award_type`: Award type (default: `"unknown"`)

## File Structure After Run

```
crz_gov_scraping/
├── out.ndjson           # Output file with contracts
├── data/
│   ├── sample_contracts.json  # Seed data (Phase 0)
│   ├── contracts.json        # Migrated JSON (after migration)
│   └── pdfs/            # Downloaded PDF files
│       ├── 6568046.pdf
│       ├── 6568047.pdf
│       └── ...
└── [other files unchanged]
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "429 Too Many Requests" | Increase `--delay` to 1.0-2.0 |
| No PDF text extracted | PDF is scanned image (install OCR) |
| Script hangs | Increase timeout or reduce `--max-pages` |
| Wrong date format | Check Slovak month names in MONTH_MAP |
| Missing fields | Website HTML structure changed |

## Tips

1. **Start small**: Test with `--max-pages 1` first
2. **Be polite**: Use `--delay 1.0` or higher for production runs
3. **Monitor logs**: Use `--log-level INFO` to track progress
4. **Save results**: Choose meaningful `--out` names
5. **Check output**: Verify first few contracts manually

## Links

- **CRZ Website**: https://www.crz.gov.sk/
- **Documentation**: See README.md and ARCHITECTURE.md
- **Tests**: Run `pytest tests/ -v`
- **Issues**: Check GitHub issues or create new one

## Performance Estimates

- Single page: ~2-3 seconds
- 10 pages: ~2-5 minutes
- 100 pages: ~20-50 minutes
- 1000 pages: ~200-500 minutes (3-8 hours)

With PDF downloads (10% of contracts):
- Add 2-10 seconds per PDF (depends on size)

With `--delay 1.0`:
- Roughly doubles total time

## Examples

```bash
# Scrape just page 1, save to test.ndjson
python scrape_crz.py --start-page 1 --max-pages 1 --out test.ndjson

# Scrape pages 1-10 with longer delay
python scrape_crz.py --start-page 1 --max-pages 10 --delay 1.0

# Scrape pages 11-20 (continue from where you left off)
python scrape_crz.py --start-page 11 --max-pages 10 --out part2.ndjson

# Debug first page
python scrape_crz.py --start-page 1 --max-pages 1 --log-level DEBUG

# Production run: pages 1-100 with conservative settings
python scrape_crz.py --start-page 1 --max-pages 100 --delay 1.5 --out all_contracts.ndjson
```

## Getting Help

1. Check README.md for detailed documentation
2. Review ARCHITECTURE.md for technical details
3. Look at test examples in `tests/` directory
4. Enable DEBUG logging to see what's happening
5. Check GitHub issues or create a new one
