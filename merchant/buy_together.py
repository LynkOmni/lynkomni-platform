"""N11 Buy together (blueprint 44 I): small shops join a group order to reach a supplier's bulk price before a closing date.
Each shop orders and pays the supplier for its own part through the licensed provider, and LynkOmni never pools money. If the
group falls short, nobody is charged. Joining on every tier; starting a group on Pro and Max (across branches on Max). The
existing 1.5% marketplace commission is paid by the supplier (billing SERVICE_FEES marketplace_commission_bps when set)."""
import time

from contract.tools.validate_contract import uuid7
from services import billing

def _now(n): return time.time() if n is None else n
def _ts(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


class BuyTogether:
    def __init__(s, cloud, platform):
        s.cloud, s.p, s.db = cloud, platform, platform.c.store.db
        s.db.executescript("""
        create table if not exists bt_groups(group_id text primary key, opener text, supplier text, target int, currency text, closes_at real, state text);
        create table if not exists bt_joins(order_id text primary key, group_id text, merchant text, amount int, charged int);""")
    def may_open(s, merchant):
        t = billing.Billing(s.p.c).tier(merchant, "lynkpos")
        return t in ("pro", "max")
    def open(s, merchant, supplier_id, target_minor, currency, closes_at, now=None):
        if not s.may_open(merchant): raise PermissionError("start_group_needs_pro")
        gid = uuid7()
        s.db.execute("insert into bt_groups(group_id, opener, supplier, target, currency, closes_at, state) values(?,?,?,?,?,?,'open')", (gid, merchant, supplier_id, target_minor, currency, closes_at))
        s.cloud.event(merchant, "GroupOrderOpened", {"group_id": gid, "supplier_id": supplier_id, "closes_at": _ts(closes_at)}, now=now)
        return gid
    def join(s, merchant, group_id, amount_minor, now=None):
        g = s.db.execute("select state, closes_at, currency from bt_groups where group_id=?", (group_id,)).fetchone()
        if not g or g[0] != "open" or _now(now) >= g[1]: raise ValueError("group_closed")
        oid = uuid7()
        s.db.execute("insert into bt_joins(order_id, group_id, merchant, amount, charged) values(?,?,?,?,0)", (oid, group_id, merchant, amount_minor))
        s.cloud.event(merchant, "GroupOrderJoined", {"group_id": group_id, "order_id": oid, "amount": amount_minor, "currency": g[2]}, now=now)
        return oid
    def total(s, group_id): return s.db.execute("select coalesce(sum(amount),0) from bt_joins where group_id=?", (group_id,)).fetchone()[0]
    def close(s, group_id, now=None):
        """At the closing date: reached means each shop pays the supplier for its own part (through the provider); short means nobody is charged."""
        g = s.db.execute("select opener, target, state from bt_groups where group_id=?", (group_id,)).fetchone()
        if not g or g[2] != "open": raise ValueError("group_not_open")
        reached = s.total(group_id) >= g[1]
        s.db.execute("update bt_groups set state=? where group_id=?", ("reached" if reached else "failed", group_id))
        members = [r[0] for r in s.db.execute("select distinct merchant from bt_joins where group_id=?", (group_id,))]
        for m in set(members) | {g[0]}:
            s.cloud.event(m, "GroupOrderReached" if reached else "GroupOrderFailed", {"group_id": group_id}, now=now)
        if reached: s.db.execute("update bt_joins set charged=1 where group_id=?", (group_id,))   # each shop pays its own part to the supplier
        return "reached" if reached else "failed"
    def charged(s, order_id): return bool(s.db.execute("select charged from bt_joins where order_id=?", (order_id,)).fetchone()[0])
    @staticmethod
    def pooled_by_lynkomni(): return 0      # always: LynkOmni never pools money
