"""Large organisations and Move in, in the cloud (OFFICE UPDATE, master blueprint 66.5 and 66.6; section 4 step D4a), on the rules
of core/enterprise.py.

Enterprise is Max plus this set, by agreement: LynkOmni staff record the agreement; nothing here is sold per feature. An
organisation builds its own approval flows and roles (only ever doing less), keeps records under a legal hold, exports its
audit log, splits charges by department, tries changes in a test copy, and adds and removes staff from its own staff
directory through the directory connector. Move in brings charts, opening balances, customers, suppliers and open items in
after a clean check report; leaving is a full download at any time.

SANDBOX: SandboxStaffDirectory returns the changes it is given; the real connector (provider ledger staff_directory) reads the
organisation's own directory. It is for tests and the emulators only."""
import csv, io, time, uuid

from core import accounts as AC
from core import enterprise as E
from core.regions import country
from services.improvements import Table, _cur


class StaffDirectory:
    """The interface every real staff-directory connector implements."""
    def changes(self, since):
        """[{"change": add|update|suspend|remove, "user": id, "role": role?, "minute": n}] since a cursor."""
        raise NotImplementedError


class SandboxStaffDirectory(StaffDirectory):
    def __init__(self):
        self.queue = []

    def push(self, change):
        self.queue.append(change)

    def changes(self, since=0):
        out = [c for c in self.queue if c["minute"] >= since]
        self.queue = [c for c in self.queue if c["minute"] < since]
        return out


class Organisation:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.agree, s.flows, s.roles = Table(db, "ent_agreement"), Table(db, "ent_flows"), Table(db, "ent_roles")
        s.holds, s.staff, s.copies = Table(db, "ent_holds"), Table(db, "ent_staff"), Table(db, "ent_copies")
        s.directory = SandboxStaffDirectory()

    # ---- the agreement ---------------------------------------------------------------------------------------------------------
    def set_agreement(s, m, on, staff_id):
        """Recorded by LynkOmni staff when the agreement is signed (never by the customer)."""
        s.agree.put(m, {"on": bool(on), "by": staff_id, "at": s.now()})
        s.p.c.store.append(m, "server", "enterprise.agreement", {"on": bool(on)})
        return bool(on)

    def on(s, m, family="lynkacc"):
        return bool((s.agree.get(m) or {}).get("on")) and s.p.billing.tier(m, family) == "max"

    def _need(s, m, family="lynkacc"):
        if not s.on(m, family):
            raise PermissionError("the large-organisation set comes with Max and an Enterprise agreement")

    # ---- approval flows and roles ----------------------------------------------------------------------------------------------
    def set_flow(s, m, document, steps):
        if document not in E.ENT["approval_flows"]["documents"]:
            raise ValueError("unknown document")
        s._need(m, E.ENT["approval_flows"]["document_family"][document])      # that service's Max plan and the agreement (67.15)
        E.flow_steps(steps, 0)                                        # checks the number of steps
        s.flows.put(f"{m}|{document}", {"steps": steps}); return len(steps)

    def steps_for(s, m, document, amount, department=None):
        f = s.flows.get(f"{m}|{document}")
        return E.flow_steps(f["steps"], amount, department) if f else None

    def define_role(s, m, name, perms):
        area_family = {a: f for f, a in E.ENT["family_area"].items()}
        if not perms or not all(s.on(m, area_family.get(a, "lynkacc")) for a in perms):
            raise PermissionError("the large-organisation set comes with Max and an Enterprise agreement")
        problems = E.role_problems(perms)
        if problems:
            raise ValueError(problems)
        s.roles.put(f"{m}|{name}", {"perms": perms}); return name

    def role(s, m, name):
        r = s.roles.get(f"{m}|{name}")
        return r["perms"] if r else E.ENT["roles"]["base"].get(name, {})

    # ---- staff directory --------------------------------------------------------------------------------------------------------
    def sync_staff(s, m, since=0):
        """Apply the directory's changes: a removed person loses access within the register's minutes; nothing they did is deleted."""
        s._need(m)
        out = []
        for c in s.directory.changes(since):
            if c["change"] not in E.ENT["directory"]["changes"]:
                continue
            rec = s.staff.get(f"{m}|{c['user']}") or {"role": None, "state": "active"}
            if c["change"] in ("add", "update"):
                rec = {"role": c.get("role", rec["role"]), "state": "active"}
            else:
                rec = {**rec, "state": "suspended" if c["change"] == "suspend" else "removed", "access_until": E.suspended_by(c["minute"])}
            s.staff.put(f"{m}|{c['user']}", rec); out.append({"user": c["user"], **rec})
        return out

    def has_access(s, m, user, minute):
        rec = s.staff.get(f"{m}|{user}")
        if not rec:
            return False
        return rec["state"] == "active" or minute < rec.get("access_until", 0)

    # ---- holds, keeping, audit, charges, test copy -----------------------------------------------------------------------------
    def hold(s, m, record, on, reason=""):
        s._need(m)
        s.holds.put(f"{m}|{record}", {"on": bool(on), "reason": reason}); return bool(on)

    def held(s, m, record):
        return bool((s.holds.get(f"{m}|{record}") or {}).get("on"))

    def may_delete(s, m, record, age_days, policy_days, law_days):
        return E.may_delete(age_days, policy_days, law_days, s.held(m, record))

    def audit_export(s, m, fmt="csv"):
        """The whole audit log: every event's id, time, type and device; payloads are already free of personal data."""
        if fmt not in E.ENT["audit"]["formats"]:
            raise ValueError("unknown format")
        rows = [[e["id"], e["ts"], e["type"], e.get("device", "")] for e in s.p.c.store.since(m)]
        if fmt == "json":
            return [{"id": r[0], "at": r[1], "type": r[2], "device": r[3]} for r in rows]
        buf = io.StringIO(); w = csv.writer(buf); w.writerow(["id", "at", "type", "device"]); w.writerows(rows)
        return buf.getvalue()

    def split_charges(s, m, total_minor, shares):
        return E.split_charges(total_minor, shares)

    def test_copy(s, m):
        """A test copy: the same rules with every provider in its sandbox, no message sent and no money moved."""
        s._need(m)
        tid = f"{m}~test~{uuid.uuid4().hex[:6]}"
        s.p.register(tid, s.p.c.profile(m)["country"])
        s.copies.put(tid, {"of": m, "sandbox": True}); return tid

    def is_test_copy(s, m):
        return m in s.copies


class MoveIn:
    """Move in and leave (66.6): every file gets a check report first; nothing goes live while it shows an error."""
    def __init__(s, p):
        s.p, s.refs = p, Table(p.c.store.db, "movein_refs")

    def _decimals(s, m):
        from core.money import CURRENCIES
        return CURRENCIES[_cur(s.p, m)]

    def _known(s, m):
        r = s.refs.get(m) or {"customers": [], "suppliers": []}
        return {k: list(r.get(k, [])) for k in ("customers", "suppliers", "products", "members")}

    def _accounts(s, m):
        local = AC.local_chart(country(s.p.c.profile(m)["country"]))
        return sorted(set(AC.ACCOUNTS) | {v["code"] for v in local.values()})

    def check(s, m, kind, header, rows, date_format="iso"):
        return E.check(kind, header, rows, s._decimals(m), date_format, s._known(m), s._accounts(m))

    def apply(s, m, kind, header, rows, by, date_format="iso", entity_kind="business"):
        """Brings a checked file in. Customers and suppliers go to LynkCRM (names and contacts to the vault); opening balances
        wait for a second person as a sensitive journal; open invoices and bills are kept as open items without posting again
        (the opening balances already carry them)."""
        rep = s.check(m, kind, header, rows, date_format)
        if not rep["ok"]:
            return {"applied": 0, "report": rep}
        idx = {c: i for i, c in enumerate(header)}
        get = lambda r, c: (r[idx[c]] if c in idx and idx[c] < len(r) else "")
        dec, done = s._decimals(m), 0
        refs = s.refs.get(m) or {"customers": [], "suppliers": []}
        if kind in ("customers", "suppliers"):
            for r in rows:
                s.p.crm.create(m, by, "customer" if kind == "customers" else "supplier", name=get(r, "name") or None,
                               email=get(r, "email") or None, phone=get(r, "phone") or None, source="import")
                refs = {**refs, kind: refs[kind] + [str(get(r, "ref")).strip()]}; done += 1
            s.refs.put(m, refs)
            return {"applied": done, "report": rep}
        if kind == "opening_balances":
            lines = [[str(get(r, "account")).strip(), E.parse_amount(get(r, "debit"), dec) or 0, E.parse_amount(get(r, "credit"), dec) or 0] for r in rows]
            return {"applied": len(lines), "pending": s.p.books.prepare_journal(m, "opening_balance", lines, by), "report": rep}
        if kind in ("open_invoices", "open_bills"):
            items = [{"ref": str(get(r, "number" if kind == "open_invoices" else "ref")).strip(), "who": str(get(r, "customer_ref" if kind == "open_invoices" else "supplier_ref")).strip(),
                      "amount": E.parse_amount(get(r, "amount"), dec), "due": E.parse_date(get(r, "due_on"), date_format)} for r in rows]
            Table(s.p.c.store.db, "movein_open").put(f"{m}|{kind}", {"items": items})
            return {"applied": len(items), "report": rep}
        # every service's files (SERVICES UPDATE 67.15)
        if kind in ("products", "stock_levels"):
            # products and stock are created on a device (ProductCreated and StockAdjusted come only from devices): the cloud keeps a
            # catalog pack and each device writes the events when it takes the pack (catalog_pack)
            t = Table(s.p.c.store.db, "movein_catalog"); pack = t.get(m) or {"products": [], "stock": []}
            if kind == "products":
                items = [{"ref": str(get(r, "ref")).strip(), "name": str(get(r, "name")).strip(), "price": E.parse_amount(get(r, "price"), dec),
                          "unit": str(get(r, "unit")).strip() or "each", "barcode": str(get(r, "barcode")).strip() or None, "tax_code": str(get(r, "tax_code")).strip() or None} for r in rows]
                refs = {**refs, "products": sorted(set(refs.get("products", [])) | {i["ref"] for i in items})}
                pack = {**pack, "products": pack["products"] + items}
            else:
                items = [{"product_ref": str(get(r, "product_ref")).strip(), "place": str(get(r, "place")).strip() or None, "quantity": int(str(get(r, "quantity")).strip())} for r in rows]
                pack = {**pack, "stock": pack["stock"] + items}
            t.put(m, pack); s.refs.put(m, refs)
            return {"applied": len(items), "report": rep, "on_devices": True}
        if kind == "members":
            from core import crm as C
            entity, kinds = entity_kind, C.kinds_for(entity_kind)
            rkind = next((k for k in ("member", "customer", "client", "donor", "student", "contact") if k in kinds), None)
            if rkind is None:
                raise ValueError("this kind of workspace keeps no members")
            ids = dict(refs.get("member_ids", {}))
            for r in rows:
                ids[str(get(r, "ref")).strip()] = s.p.crm.create(m, by, rkind, entity_kind=entity, name=get(r, "name") or None,
                                                                 email=get(r, "email") or None, phone=get(r, "phone") or None, source="import")
            refs = {**refs, "members": sorted(set(refs.get("members", [])) | set(ids)), "member_ids": ids}
            s.refs.put(m, refs)
            return {"applied": len(rows), "report": rep}
        if kind == "points":
            for r in rows:
                ref = str(get(r, "member_ref")).strip()          # points follow the member's LynkCRM record, not the old system's number
                s.p.c.store.append(m, "server", "loyalty.earned", {"customer": refs.get("member_ids", {}).get(ref, ref), "points": int(str(get(r, "points")).strip()), "source": "move_in"})
            return {"applied": len(rows), "report": rep}
        if kind == "payees":
            for r in rows:
                s.p.exchange_office.add_payee(m, by, str(get(r, "name")).strip(), str(get(r, "bank_details")).strip(), entity_kind=entity_kind)
            return {"applied": len(rows), "report": rep}
        if kind == "bookings":
            items = [{"ref": str(get(r, "ref")).strip(), "customer_ref": str(get(r, "customer_ref")).strip() or None, "service": str(get(r, "service")).strip() or None,
                      "starts_on": E.parse_date(get(r, "starts_on"), date_format), "total": E.parse_amount(get(r, "total"), dec) if str(get(r, "total")).strip() else None} for r in rows]
            Table(s.p.c.store.db, "movein_bookings").put(m, {"items": items})       # kept as moved-in bookings for LynkBooking's business side (section 8)
            return {"applied": len(items), "report": rep}
        return {"applied": 0, "report": rep}

    def catalog_pack(s, m):
        """What a device takes after a products or stock Move in: it writes ProductCreated and StockAdjusted for each line."""
        return Table(s.p.c.store.db, "movein_catalog").get(m) or {"products": [], "stock": []}

    def leave(s, m):
        """A full download at any time, in the same standard files."""
        out = {"journal.csv": [["event", "type", "account", "debit", "credit"]] + [[e["event_id"], e["type"], a, d, c] for e in s.p.accountant.journal(m) for a, d, c in e["lines"]]}
        out["customers.csv"] = [["id", "kind", "tags"]] + [[k, v["kind"], " ".join(v["tags"])] for k, v in s.p.crm.recs.items() if v["merchant"] == m]
        out["invoices.csv"] = [["id", "number", "total", "paid", "state"]] + [[k, v["number"], v["total_minor"], v["paid_minor"], v["state"]] for k, v in s.p.invoicing.inv.items() if v["merchant"] == m]
        out["audit.csv"] = s.p.enterprise.audit_export(m) if s.p.enterprise.on(m) else ""
        return out
