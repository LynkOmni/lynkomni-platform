"""Print the counts, prices and versions the master blueprint quotes, read from the code (review S1, 2026-11-07).
The blueprint copies these numbers instead of typing its own, so the two never disagree."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from services import billing
from finance import revenue_model as rm

def numbers():
    reg = json.loads((ROOT / "providers" / "registry.v1.json").read_text())
    ids = json.loads((ROOT / "contract" / "identifier-registry.v1.json").read_text())
    needs = json.loads((ROOT / "visuals" / "needs.v1.json").read_text())["needs"]
    langs = json.loads((ROOT / "design" / "fonts" / "scripts.v1.json").read_text())
    version = next(l for l in (ROOT / "docs" / "lynkomni-changelog.md").read_text().splitlines() if l.startswith("## "))
    return {
        "version": version[3:].split()[0],
        "billing_families": len(billing.FAMILIES),
        "prices_usd": {f: v[3] for f, v in billing.FAMILIES.items()},
        "identifier_types": len(ids["types"]),
        "provider_items": len(reg["items"]), "later_items": len(reg["later"]), "user_actions": len(reg["user_actions"]),
        "pictures": len(needs),
        "automations": len(json.loads((ROOT / "catalog" / "automations.v1.json").read_text())["automations"]),
        "languages": len(langs.get("languages", langs)),
        "ecosystem_revenue": rm.ecosystem_totals(),
        "stage_names": rm.STAGE_NAMES,                  # the stages are sizes (proving ground, regional scale, global scale), never countries
        "contract_version": 2, "event_types": len(json.loads((ROOT / "contract" / "event-payloads.v2.json").read_text())["events"]),
        "currencies": len(json.loads((ROOT / "contract" / "currencies.v1.json").read_text())["decimals"]),
        "country_packs": len([f for f in (ROOT / "contract" / "country-packs").iterdir() if f.suffix == ".json" and f.stem != "XX"]),
    }

if __name__ == "__main__":
    print(json.dumps(numbers(), indent=1, default=str))
