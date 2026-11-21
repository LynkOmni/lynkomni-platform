"""Which Lynk names still confuse people (owner, 21 November 2026; catalog/names.v1.json "asks").

A device counts how often each name's note, "What is ...?" answer or comparison is opened (ts/src/names.ts nameAsked) and sends
only the totals by name: never a person, device, account, place or time finer than the day. LynkOmni staff see the totals of 5 or
more, so a name that keeps needing an explanation can be renamed or given a clearer plain word."""
from core import names


class NameAsks:
    def __init__(self):
        self.days = {}

    def receive(self, day, counts):
        """Add a device's totals for one day (YYYY-MM-DD). Unknown names and anything that is not a whole positive count are dropped."""
        if not (isinstance(day, str) and len(day) == 10):
            raise ValueError("day must be YYYY-MM-DD")
        box = self.days.setdefault(day, {})
        for nid, n in counts.items():
            if nid in names.BY_ID and isinstance(n, int) and not isinstance(n, bool) and n > 0:
                box[nid] = box.get(nid, 0) + n
        return len(box)

    def report(self, since=None):
        """Totals by name over the days from since (inclusive), shown only from 5 up, most asked first."""
        tot = {}
        for day, box in self.days.items():
            if since is None or day >= since:
                for nid, n in box.items():
                    tot[nid] = tot.get(nid, 0) + n
        shown = names.asks_report(tot)
        return [{"name": names.BY_ID[k]["name"], "asks": v} for k, v in sorted(shown.items(), key=lambda kv: (-kv[1], kv[0]))]
