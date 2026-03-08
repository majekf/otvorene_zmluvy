import json
from pathlib import Path

p = Path("data/josephine_tenders.json")
if not p.exists():
    raise SystemExit("data/josephine_tenders.json not found")

data = json.loads(p.read_text(encoding="utf-8"))

if isinstance(data, list):
    for tender in data:
        if not isinstance(tender, dict):
            continue

        if isinstance(tender.get("parts"), list):
            parts = tender["parts"]
        else:
            keys = sorted(
                [k for k in tender.keys() if k.startswith("part_")],
                key=lambda x: int(x.split("_")[1]),
            )
            parts = []
            for key in keys:
                value = tender.pop(key)
                if isinstance(value, dict):
                    parts.append(value)

        migrated_parts = []
        for i, part in enumerate(parts, start=1):
            if not isinstance(part, dict):
                continue
            part["part_number"] = part.get("part_number", i)
            ai = part.pop("ai_extracted", None)
            if isinstance(ai, dict):
                part.update(ai)
            migrated_parts.append(part)

        tender["parts"] = migrated_parts

p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"migrated {len(data) if isinstance(data, list) else 0} tenders")
