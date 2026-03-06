# 🚀 START HERE - CRZ Scraper Setup Guide

Welcome! This guide will get you running the CRZ scraper in 5 minutes.

## 📍 You Are Here

```
c:\Users\arath\git_projects\crz_gov_scraping\
```

A complete, production-ready Python web scraper for Slovak government contracts.

## ⚡ Quick Start (5 minutes)

### 1️⃣ Open Terminal

```bash
# Open Windows Command Prompt or PowerShell
# Navigate to project directory
cd c:\Users\arath\git_projects\crz_gov_scraping
```

### 2️⃣ Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

**Packages installed:**
- requests (HTTP client)
- beautifulsoup4 (HTML parsing)
- lxml (HTML parser)
- pdfplumber (PDF text extraction)
- pytest (testing)

### 4️⃣ Run Tests (optional but recommended)

```bash
# Run all tests to verify everything works
pytest tests/ -v
```

Expected output: **16 passed** ✓

### 5️⃣ Try the Scraper!

```bash
# Scrape just 1 page to test
python scrape_crz.py --start-page 1 --max-pages 1

# This creates: out.ndjson
```

### 6️⃣ View Results

```bash
# See how many contracts were scraped
wc -l out.ndjson

# View the first contract (formatted)
head -1 out.ndjson | python -m json.tool
```

## 📚 Documentation Map

| Document | Purpose | Read When |
|----------|---------|-----------|
| **INDEX.md** | Navigation guide | First time |
| **DELIVERY_SUMMARY.md** | What was built | Want overview |
| **README.md** | Full user guide | Need detailed help |
| **QUICKSTART.md** | Command reference | Need specific commands |
| **ARCHITECTURE.md** | Technical details | Contributing code |
| **PROJECT_COMPLETION.md** | Acceptance criteria | Want verification |

## 🎯 Common Tasks

### Scrape 3 Pages

```bash
python scrape_crz.py --start-page 1 --max-pages 3 --out my_contracts.ndjson
```

### Scrape with Longer Delays (Be Nice to Server)

```bash
python scrape_crz.py --start-page 1 --max-pages 50 --delay 1.0
```

### Continue from Page 11 (Resume Scraping)

```bash
python scrape_crz.py --start-page 11 --max-pages 10 --out part2.ndjson
```

### Enable Debug Logging

```bash
python scrape_crz.py --start-page 1 --max-pages 1 --log-level DEBUG
```

## 📊 What Gets Scraped

Each contract gets these fields:

```json
{
  "contract_id": "12048046",
  "contract_title": "rámcová dohoda",
  "contract_number": "2026/22/E/CI",
  "contract_url": "https://www.crz.gov.sk/zmluva/12048046/",
  "published_date": "2026-03-01",
  "price_numeric_eur": 28978.27,
  "supplier": "Company Name",
  "buyer": "Organization Name",
  "ico_buyer": "17336163",
  "ico_supplier": "36394556",
  "pdf_url": "https://www.crz.gov.sk/data/att/6568046.pdf",
  "pdf_text": "Contract text extracted from PDF...",
  "scraped_at": "2026-03-01T10:30:45.123456Z"
}
```

## ⚙️ Configuration

### Change Request Delay (seconds)

```bash
# Faster (not recommended): --delay 0.1
# Normal (default): --delay 0.5
# Polite (recommended): --delay 1.0
# Very polite: --delay 2.0
```

### Change Output File

```bash
# Default
python scrape_crz.py --out out.ndjson

# Custom
python scrape_crz.py --out my_contracts.ndjson
```

### Change PDF Directory

```bash
python scrape_crz.py --pdf-dir my_pdfs
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Only Unit Tests

```bash
pytest tests/test_parser.py -v
```

### Run Only Integration Tests

```bash
pytest tests/test_integration.py -v
```

## 🔍 Verify Installation

```bash
# Run project verification script
python verify_project.py
```

Expected: **✓ PROJECT COMPLETE AND VERIFIED**

## ❓ Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'requests'"

**Solution**: Make sure virtual environment is activated

```bash
# Activate venv
venv\Scripts\activate

# Install again
pip install -r requirements.txt
```

### Issue: "429 Too Many Requests" Error

**Solution**: Increase the delay

```bash
python scrape_crz.py --start-page 1 --max-pages 10 --delay 1.0
```

### Issue: Script Hangs or Times Out

**Solution**: Reduce number of pages

```bash
python scrape_crz.py --start-page 1 --max-pages 5 --delay 1.0
```

### Issue: No PDF Text Extracted

**Reason**: PDF is a scanned image (no text)
**Solution**: Add OCR library (advanced - see README.md)

### Issue: Tests Fail

**Solution**: Verify installation

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## 📈 Performance Tips

- **For testing**: Use `--max-pages 1` (3 seconds)
- **For small batch**: Use `--max-pages 10` (1-2 minutes)
- **For medium batch**: Use `--max-pages 100` (20-50 minutes)
- **For large batch**: Use `--max-pages 1000` (3-8 hours)

Adjust `--delay` for your needs:
- Faster: 0.5 seconds (default)
- Slower: 1.0-2.0 seconds (more polite)

## 🎓 Learning Path

1. **Quick Start** (you are here)
   - Get it running
   - Try a simple scrape
   
2. **QUICKSTART.md**
   - Learn all commands
   - See examples
   - Configuration options

3. **README.md**
   - Full documentation
   - Output format
   - Troubleshooting
   
4. **ARCHITECTURE.md**
   - How it works
   - Code structure
   - Future enhancements

## 📋 File Structure

```
📁 crz_gov_scraping
├── 📄 START_HERE.md              ← You are here
├── 📄 INDEX.md                   ← Navigation guide
├── 📄 README.md                  ← User guide
├── 📄 QUICKSTART.md              ← Command reference
├── 📄 ARCHITECTURE.md            ← Technical details
├── 📄 DELIVERY_SUMMARY.md        ← What was delivered
├── 📄 PROJECT_COMPLETION.md      ← Acceptance criteria
│
├── 📁 src/
│   ├── scraper.py               ← Core implementation
│   └── __init__.py
│
├── 📁 tests/
│   ├── test_parser.py           ← Unit tests
│   ├── test_integration.py      ← Integration tests
│   └── __init__.py
│
├── 📁 data/
│   └── pdfs/                    ← Downloaded PDFs (auto-created)
│
├── 📄 scrape_crz.py             ← Run this!
├── 📄 requirements.txt          ← Dependencies
├── 📄 verify_project.py         ← Verify installation
├── .gitignore                   ← Git ignore rules
└── (other support files)
```

## ✅ Checklist

- [ ] Opened terminal
- [ ] Navigated to project directory
- [ ] Created virtual environment (`python -m venv venv`)
- [ ] Activated it (`venv\Scripts\activate`)
- [ ] Installed dependencies (`pip install -r requirements.txt`)
- [ ] Ran tests (`pytest tests/ -v`)
- [ ] Tried scraper (`python scrape_crz.py --start-page 1 --max-pages 1`)
- [ ] Viewed results (`head -1 out.ndjson | python -m json.tool`)

## 🎉 You're Ready!

You now have a working CRZ scraper!

### Next: Pick a Task

**Option A: Run Full Scrape**
```bash
python scrape_crz.py --start-page 1 --max-pages 100 --out contracts.ndjson
```

**Option B: Process Existing Results**
```bash
# View first 5 contracts
python -c "import json; [print(json.loads(line)['contract_id'], json.loads(line)['contract_title']) for line in open('out.ndjson')]" | head -5
```

**Option C: Contribute**
- Read ARCHITECTURE.md
- Modify src/scraper.py
- Add tests
- Submit PR

**Option D: Learn More**
- Read README.md for detailed guide
- Read QUICKSTART.md for commands
- Check ARCHITECTURE.md for design

## 💬 Questions?

1. **Usage**: See README.md
2. **Commands**: See QUICKSTART.md
3. **Technical**: See ARCHITECTURE.md
4. **Issues**: Check troubleshooting sections

## 📞 Help

If something doesn't work:

1. Check troubleshooting section above
2. Read README.md
3. Run `pytest tests/ -v` to verify setup
4. Run `python verify_project.py` to check installation
5. Enable DEBUG: `python scrape_crz.py --log-level DEBUG`

---

**Ready to scrape?** Run this:

```bash
python scrape_crz.py --start-page 1 --max-pages 3
```

Then view results:

```bash
head -1 out.ndjson | python -m json.tool
```

Good luck! 🚀
