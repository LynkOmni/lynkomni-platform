"""N1 Restaurant and food mode (blueprint 44 I): tables and floor plan, open tabs, courses and modifiers, a kitchen screen on the
counter tablet (or its own wall display), order and pay at the table by QR, split bills and tips. The facts are the device
events in dv/box.py (TableOpened, OrderSentToKitchen, KitchenItemReady, TableBillSplit, TipRecorded, TableClosed: all offline).
This is the cloud projection and the tier limits (billing FEATURES: tables, kitchen_screens, split_bills, tips,
table_qr_ordering, central_menu). Tips belong to the business; LynkOmni takes no share."""
from services import billing

TABS = ("home", "tables", "kitchen", "chats", "business")
KITCHEN_WITHOUT_SCREEN = "printed_tickets"      # Free: the kitchen gets printed tickets


class Restaurant:
    def __init__(s, cloud, platform): s.cloud, s.p = cloud, platform
    def limits(s, merchant):
        e = billing.Billing(s.p.c).entitlement(merchant, "lynkpos")
        return {"tables": e.get("tables"), "kitchen_screens": e.get("kitchen_screens", 0), "split_bills": bool(e.get("split_bills")), "tips": bool(e.get("tips")),
                "table_qr_ordering": bool(e.get("table_qr_ordering")), "central_menu": bool(e.get("central_menu"))}
    def may_open_table(s, merchant, open_now):
        lim = s.limits(merchant)["tables"]
        return lim is None or open_now < lim
    def may_add_kitchen_screen(s, merchant, screens_now):
        lim = s.limits(merchant)["kitchen_screens"]
        return lim is None or screens_now < lim
    def kitchen_output(s, merchant):
        return KITCHEN_WITHOUT_SCREEN if s.limits(merchant)["kitchen_screens"] == 0 else "screen"
    @staticmethod
    def tip_share_for_lynkomni(amount): return 0        # always zero: tips belong to the business
    def table_qr_path(s, username, table_label): return f"shop.lynkomni.com/{username}/tables/{table_label}"
    # ---- projection from the events that reached the cloud
    def tables(s, merchant):
        out = {}
        for e in s.cloud.of(merchant, "TableOpened", "OrderSentToKitchen", "KitchenItemReady", "TableBillSplit", "TipRecorded", "TableClosed"):
            p, t = e["payload"], e["type"]
            if t == "TableOpened": out[p["table_id"]] = {"label": p["table_label"], "covers": p.get("covers"), "open": True, "orders": {}, "sales": [], "tips": 0}
            elif t == "OrderSentToKitchen" and p["table_id"] in out: out[p["table_id"]]["orders"][p["order_id"]] = {l["line_no"]: False for l in p["lines"]}
            elif t == "KitchenItemReady":
                for tb in out.values():
                    if p["order_id"] in tb["orders"]: tb["orders"][p["order_id"]][p["line_no"]] = True
            elif t == "TableBillSplit" and p["table_id"] in out: out[p["table_id"]]["sales"].extend(p["sale_ids"])
            elif t == "TableClosed" and p["table_id"] in out: out[p["table_id"]]["open"] = False
        return out
    def kitchen_queue(s, merchant):
        """Open kitchen lines in the order they were sent (the kitchen screen reads this, or prints it on Free)."""
        q = []
        for tid, tb in s.tables(merchant).items():
            for oid, lines in tb["orders"].items():
                for n, done in lines.items():
                    if not done: q.append({"table": tb["label"], "order_id": oid, "line_no": n})
        return q
    def tips_total(s, merchant): return sum(e["payload"]["amount"] for e in s.cloud.of(merchant, "TipRecorded"))
