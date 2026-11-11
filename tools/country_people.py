#!/usr/bin/env python3
"""LynkAttend and LynkSurvey settings in every country pack (NEW UPDATE 4, owner locked 2026-11-11, master blueprint 63.6).
Rule 0.5: a country adds only data.

  people.attendance.face_allowed / finger_allowed   whether Face and Finger may be used for attendance (with the person's agreement);
                                                    null means not yet confirmed: they stay selectable with agreement, and IDCN
                                                    is always there; false removes them from the sets the manager can pick
  people.attendance.id_documents                    which official ID documents may be recorded (null: not yet confirmed; a work
                                                    ID issued by the organisation can always be used)
  people.attendance.hours_records_years             how long the law keeps hours records (null: not yet confirmed)
  people.survey.consent_age                         below this age a parent or guardian agrees first (null: 18 until confirmed)
  people.survey.answers_in_country                  whether survey answers must stay in the country (null: not yet confirmed)

Nothing is invented: every value starts unknown and unconfirmed (ledger item people_services_legal).
  python3 tools/country_people.py          writes the field into every pack (keeps confirmed values)
  python3 tools/country_people.py --check  fails when a pack lacks it (tests/test_people_rules.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")
DEFAULT = {"attendance": {"face_allowed": None, "finger_allowed": None, "id_documents": None, "hours_records_years": None, "confirmed": False},
           "survey": {"consent_age": None, "answers_in_country": None, "confirmed": False},
           "note": "Set per country after the lawyer review (ledger item people_services_legal); unknown until then."}


def main(argv):
    names = sorted(n for n in os.listdir(PACKS) if n.endswith(".json"))
    if "--check" in argv:
        bad = [n for n in names if "people" not in json.load(open(os.path.join(PACKS, n), encoding="utf-8"))]
        if bad:
            print(f"{len(bad)} packs lack people settings (run python3 tools/country_people.py)"); return 1
        print("every pack has its people settings"); return 0
    for n in names:
        path = os.path.join(PACKS, n)
        with open(path, encoding="utf-8") as f: p = json.load(f)
        if "people" not in p:
            p["people"] = json.loads(json.dumps(DEFAULT))
        with open(path, "w", encoding="utf-8") as f: f.write(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote people settings into {len(names)} packs"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
