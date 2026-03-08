# load contracts_subcontractors.json and count their records
import json
from pathlib import Path

with open(Path(__file__).parent / "contracts.json", encoding="utf-8") as f:
    data = json.load(f)
    print(f"Loaded {len(data)} records from contracts_subcontractors.json")