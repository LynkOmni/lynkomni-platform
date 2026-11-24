"""The shared parts in the cloud (CONNECT UPDATE 71.3; section 4 row 71.9 step 2): one role system, one calendar, one address book,
one timeline on every record and one audit viewer, one recycle bin, one consent page, one page of plans and limits and one test copy.
Rules in catalog/shared.v1.json (core/shared.py). Each part reads the services' events or their own methods; nothing here keeps a
second copy of another service's records, and nothing here can do what a service's own rules forbid."""
import time, uuid
from core import shared as SH, build_sections as BS
from core.connections import LINKS
from services.billing import FAMILIES
from services.improvements import Table


def _built(section):
    return BS.status(section) in ("locked", "building") or str(section) == "4"


class Shared:
    def __init__(s, p, now=time.time):
        s.p, s.now = p, now
        db = p.c.store.db
        s.roles, s.bin, s.links, s.copies = Table(db, "sh_roles"), Table(db, "sh_bin"), Table(db, "sh_links"), Table(db, "sh_copies")

    # ---- one role system ----------------------------------------------------------------------------------------------------------
    def set_role(s, m, person, role, by):
        if role not in SH.SHARED["roles"]["base"]: raise ValueError("a person's role is one of the base roles")
        if by == person and role == "owner": raise PermissionError("nobody makes themselves the owner")
        s.roles.put(f"{m}|{person}", {"role": role, "by": by, "at": s.now()})
        s.p.c.store.append(m, "server", "role.set", {"person": person, "role": role, "by": by})
        return role

    def role(s, m, person):
        r = s.roles.get(f"{m}|{person}")
        return r["role"] if r else None

    def may(s, m, person, area, permission):
        role = s.role(m, person)
        return role is not None and SH.may("base", role, area, permission)

    # ---- one calendar --------------------------------------------------------------------------------------------------------------
    def calendar(s, m, start, end):
        """Everything with a date between start and end (ISO dates) from the sources built so far, oldest first."""
        out, ids = [], {x["id"] for x in SH.calendar_sources(_built)}
        day = lambda t: time.strftime("%Y-%m-%d", time.gmtime(t))
        if "invoice_due" in ids:
            for k, v in s.p.invoicing.inv.items():
                if v["merchant"] == m and v["state"] not in ("paid", "void", "credited", "written_off"):
                    out.append({"source": "invoice_due", "date": day(v["due_at"]), "ref": k})
                    if "promise_to_pay" in ids and v.get("promise"):
                        out.append({"source": "promise_to_pay", "date": v["promise"], "ref": k})
        if "bill_due" in ids:
            for k, b in s.p.books.bills.items():
                if b["merchant"] == m and b.get("due") and b.get("state") != "paid":
                    out.append({"source": "bill_due", "date": b["due"], "ref": k})
        if "lock_date" in ids and s.p.books.lock_date(m):
            out.append({"source": "lock_date", "date": s.p.books.lock_date(m), "ref": "lock_date"})
        return sorted([x for x in out if start <= x["date"] <= end], key=lambda x: (x["date"], x["source"], x["ref"]))

    # ---- one address book ----------------------------------------------------------------------------------------------------------
    def address_book(s, m):
        """The LynkCRM records every service shares: vault references only, with the services that use each."""
        used = {}
        for k, v in s.p.invoicing.inv.items():
            if v["merchant"] == m: used.setdefault(v["customer"], set()).add("lynkinv")
        for k, b in s.p.books.bills.items():
            if b["merchant"] == m and b.get("supplier"): used.setdefault(b["supplier"], set()).add("lynkacc")
        rows = []
        for rid, r in s.p.crm.recs.items():
            if r["merchant"] != m or r.get("merged_into") or r.get("binned") or r.get("purged"): continue
            if r["kind"] not in SH.SHARED["address_book"]["kinds"]: continue
            rows.append({"id": rid, "kind": r["kind"], "name_ref": r.get("name_ref"), "used_by": sorted({"lynkcrm"} | used.get(rid, set()) | ({"lynkcrm"} if r.get("activities") else set()))})
        return rows

    # ---- one timeline on every record and one audit viewer ------------------------------------------------------------------------
    def record_timeline(s, m, record_id):
        """The events that name this record, newest first: time, type and device only."""
        hits = [e for e in s.p.c.store.since(m) if record_id in _values(e["payload"])]
        return [{"at": e["ts"], "type": e["type"], "device": e.get("device", "")} for e in reversed(hits)]

    def audit(s, m, viewer, role, kind=None):
        """The whole account's events, for the owner, an auditor or the accountant only; every look is recorded."""
        if not SH.may_audit(role): raise PermissionError("the audit viewer is for the owner, an auditor or the accountant")
        rows = [{"at": e["ts"], "type": e["type"], "device": e.get("device", "")} for e in s.p.c.store.since(m) if kind is None or e["type"].startswith(kind)]
        s.p.c.store.append(m, "server", "audit.viewed", {"viewer": viewer, "role": role, "filter": kind or "all", "rows": len(rows)})
        return rows

    # ---- one recycle bin -----------------------------------------------------------------------------------------------------------
    def delete(s, m, kind, ref, by):
        if not SH.binnable(kind): raise PermissionError("this cannot be deleted; it stays in the records")
        if kind == "crm_record":
            r = s.p.crm.recs[ref]
            if r["merchant"] != m: raise KeyError(ref)
            r["binned"] = True
        elif kind == "file":
            d = s.p.files._doc(m, ref)
            if d.get("hold"): raise PermissionError("nothing under legal hold is deleted")
            if any(r["document"] == ref and r["signed"] for _, r in s.p.files.requests.items()):
                raise PermissionError("a signed document is never deleted")
            d["binned"] = True
        bid = uuid.uuid4().hex
        s.bin.put(bid, {"merchant": m, "kind": kind, "ref": ref, "by": by, "at": s.now()})
        s.p.c.store.append(m, "server", "bin.added", {"kind": kind, "ref": ref, "by": by})
        return bid

    def in_bin(s, m):
        return [{"id": k, **v} for k, v in s.bin.items() if v["merchant"] == m]

    def restore(s, m, bid, by):
        b = s.bin.get(bid)
        if not b or b["merchant"] != m: raise KeyError(bid)
        if b["kind"] == "crm_record": s.p.crm.recs[b["ref"]]["binned"] = False
        elif b["kind"] == "file": s.p.files._doc(m, b["ref"])["binned"] = False
        s.bin.pop(bid)
        s.p.c.store.append(m, "server", "bin.restored", {"kind": b["kind"], "ref": b["ref"], "by": by})
        return b["ref"]

    def empty(s, m, now=None):
        """Removed for good once the keeping time has passed; a file goes through LynkFiles' own delete."""
        now = s.now() if now is None else now; gone = []
        for bid, b in s.bin.items():
            if b["merchant"] != m or not SH.purge_due(b["at"], now): continue
            if b["kind"] == "crm_record":
                r = s.p.crm.recs[b["ref"]]; r["purged"] = True
                for f in ("name_ref", "email_ref", "phone_ref"): r[f] = None
            elif b["kind"] == "file":
                s.p.files.delete(m, b["ref"], "recycle-bin", reason="owner")
            s.bin.pop(bid); gone.append(b["ref"])
            s.p.c.store.append(m, "server", "bin.emptied", {"kind": b["kind"], "ref": b["ref"]})
        return gone

    # ---- one consent page ----------------------------------------------------------------------------------------------------------
    def set_link(s, m, link_id, on, by):
        """A link between two services that needs the business's consent is switched on or off here, once for every service."""
        l = LINKS.get(link_id)
        if not l or l["consent"] != "merchant": raise ValueError("only a link that needs the business's consent is switched here")
        s.links.put(f"{m}|{link_id}", {"on": bool(on), "by": by, "at": s.now()})
        s.p.c.store.append(m, "server", "link.consent", {"link": link_id, "on": bool(on), "by": by})
        return bool(on)

    def link_on(s, m, link_id):
        r = s.links.get(f"{m}|{link_id}")
        return bool(r and r["on"])

    def consents(s, m, owner_person=None, now=None):
        out = []
        if owner_person:
            for c in s.p.account.consents(owner_person, now):
                out.append({"source": "account", "ref": c["locns"] if "locns" in c else c.get("id"), "what": c["scope"], "with": c["grantee"], "until": c.get("expires"), "withdraw_at": "account.lynkomni.com"})
        for lid, l in LINKS.items():
            if l["consent"] == "merchant":
                out.append({"source": "links", "ref": lid, "what": l["what"], "with": l["to"], "on": s.link_on(m, lid), "withdraw_at": "here"})
        channels = {}
        for _, r in s.p.crm.recs.items():
            if r["merchant"] != m or r.get("purged"): continue
            last = {}
            for c in r.get("consents") or []: last[c["channel"]] = not c["withdrawn"]
            for ch, ok in last.items():
                if ok: channels[ch] = channels.get(ch, 0) + 1
        for ch, n in sorted(channels.items()):
            out.append({"source": "contact_channels", "ref": ch, "what": ch, "count": n, "withdraw_at": "each contact"})
        return out

    # ---- one page of plans and limits ----------------------------------------------------------------------------------------------
    def plans_and_limits(s, m):
        used = {("lynkinv", "invoices_per_month"): s.p.invoicing.used(m, time.strftime("%Y-%m", time.gmtime(s.now()))),
                ("lynkcrm", "customers"): sum(1 for _, v in s.p.crm.recs.items() if v["merchant"] == m and not v.get("merged_into") and not v.get("purged"))}
        out = []
        for fam in FAMILIES:
            if fam not in s.p.billing.effective(m): continue
            tier = s.p.billing.tier(m, fam)
            if tier == "free" and not any(used.get((fam, k)) for f, k in used if f == fam): continue      # Free and unused: not listed
            ent = s.p.billing.entitlement(m, fam)
            limits = [{"key": k, "limit": v, "used": used.get((fam, k))} for k, v in sorted(ent.items()) if isinstance(v, int) and not isinstance(v, bool)]
            out.append({"family": fam, "tier": tier, "limits": limits})
        return out

    # ---- one test copy -------------------------------------------------------------------------------------------------------------
    def test_copy(s, m):
        """A test copy for any account: sample data, every provider in its sandbox, no message sent and no money moved."""
        tid = f"{m}~try~{uuid.uuid4().hex[:6]}"
        s.p.register(tid, s.p.c.profile(m)["country"])
        s.copies.put(tid, {"of": m})
        s.p.c.store.append(m, "server", "test_copy.opened", {"copy": tid})
        return tid

    def is_test_copy(s, m):
        return m in s.copies or s.p.enterprise.is_test_copy(m)


def _values(x):
    if isinstance(x, dict):
        for v in x.values(): yield from _values(v)
    elif isinstance(x, list):
        for v in x: yield from _values(v)
    else:
        yield x
