#!/usr/bin/env python3
"""Release gate: every font file named in fonts.css exists, and the Latin first load stays within the budget."""
import json, os, re, sys
import pathlib
H = os.path.dirname(os.path.abspath(__file__)); css = pathlib.Path(os.path.join(H, "fonts.css")).read_text()
files = sorted(set(re.findall(r"/fonts/([\w-]+\.woff2)", css))); budget = json.loads(pathlib.Path(os.path.join(H, "tokens.v1.json")).read_text())["fonts"]["first_load_budget_kb"] * 1024
missing = [f for f in files if not os.path.exists(os.path.join(H, "fonts", f))]
first = sum(os.path.getsize(os.path.join(H, "fonts", f)) for f in files if "latin.woff2" in f and f not in missing)
if missing: print("MISSING:", ", ".join(missing)); sys.exit(1)
if first > budget: print(f"Latin first load {first} bytes is over the {budget} byte budget"); sys.exit(1)
print("fonts ok")
