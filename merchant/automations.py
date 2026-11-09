"""The twenty-two automations of build section 3 (twenty, plus the two tracking automations of 9 November 2026) (blueprint 45 E row 3), each registered in catalog/automations.v1.json and run by
LynkFlow (services/flow.py). Levels: inform (tell), draft (a person confirms), auto (housekeeping the person already chose) and
auto with undo (the owner's rule, undoable). None moves money, changes a credential or acts beyond its level; LynkAssist drafts,
explains, summarises and watches, and every draft is labelled a suggestion. Outputs are signals in merchant/events.v1.json."""
import time

from merchant.cloud import SIGNALS

IDLE_LOCK_S = 120            # staff PIN lock after two idle minutes
UNDO_S = 300                 # a delivery booked by rule can be undone for five minutes, and until the partner accepts
EXPIRY_WARN_DAYS = 7
SYNC_ORDER = ("sales", "payments", "stock", "chats", "media")   # priority sync (section 7): sales and payments first, media last
CHAT_QUEUES = {"order": "orders", "price": "sales", "complaint": "owner", "payment": "owner"}


def _emit(f, subject, type_, payload, automation_id, now):
    if type_ not in SIGNALS: raise ValueError(f"{type_} is not a Business app signal")
    return f.emit(subject, type_, payload, automation_id, now)


def register(flow, biz, agent, deliveries, restaurant, devices, platform):
    c = platform.c

    # ---- setup and stock (drafts)
    def setup_autofill(f, m, p, now):
        _emit(f, m, "DraftCreated", {"kind": "business_profile", "ref": p["lynkoid"], "lines": ["name", "type", "currency_from_pack", "receipt_header", "first_products"]}, "setup-autofill", now)
        return {"draft": "business_profile", "why": "a business was created; LynkAssist drafts its profile from the country pack and the name, for the owner to confirm"}

    def product_from_photo(f, m, p, now):
        _emit(f, m, "DraftCreated", {"kind": "product", "ref": p.get("photo_ref", "photo"), "lines": ["name", "price", "category"]}, "product-from-photo", now)
        return {"draft": "product", "why": "a photo was taken; LynkAssist drafts name, price and category, and nothing is saved until confirmed"}

    def low_stock_reorder(f, m, p, now):
        _emit(f, m, "DraftCreated", {"kind": "reorder", "ref": p["product_id"], "lines": [f"quantity_milli:{max(p['reorder_at_milli'] * 2 - p['level_milli'], 1000)}"]}, "low-stock-reorder", now)
        return {"draft": "reorder", "product_id": p["product_id"], "why": "stock reached its reorder level; a purchase is drafted for the owner to confirm"}

    def reorder_one_tap(f, m, p, now):
        last = next((e for e in reversed(c.store.of(m, "StockReceived")) if any(l["product_id"] == p["product_id"] for l in e["payload"]["lines"])), None)
        if not last: return None
        _emit(f, m, "DraftCreated", {"kind": "reorder_last_supplier", "ref": p["product_id"], "lines": [f"supplier_note:{last['payload'].get('supplier_note', '')}"]}, "reorder-one-tap", now)
        return {"draft": "reorder_last_supplier", "why": "the same product was received before; one tap reorders from the last supplier after the owner confirms"}

    def expiry_alert(f, m, p, now):
        near = [e for e in c.store.of(m, "ExpiryNear") if _days_until(e["payload"]["expires_on"], now) <= EXPIRY_WARN_DAYS]
        if not near: return None
        for e in near: _emit(f, m, "DraftCreated", {"kind": "expiry_action", "ref": e["payload"]["product_id"], "lines": ["discount", "move_to_front", "write_off"]}, "expiry-alert", now)
        return {"drafts": len(near), "why": "a batch expires within a week; a discount or write-off is drafted for the owner"}

    def negative_stock_flag(f, m, p, now):
        _emit(f, m, "AlertSent", {"kind": "negative_stock", "ref": p["product_id"], "detail": {"projected_milli": p["projected_milli"]}}, "negative-stock-flag", now)
        return {"alert": "negative_stock", "why": "a sale took stock below zero while offline; the sale was never blocked and the owner is told to count"}

    # ---- the day (inform)
    def day_close_prepare(f, m, p, now):
        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        s = biz.day_close(m, day)
        _emit(f, m, "AlertSent", {"kind": "day_close", "ref": day, "detail": s}, "day-close-prepare", now)
        return {"summary": "day_close", "sales": s["sales"], "why": "closing time: sales, cash expected in the drawer, items running low and anything unusual, in one message"}

    def cash_difference_flag(f, m, p, now):
        diff = p["counted_cash"] - p["expected_cash"]
        if diff == 0: return None
        _emit(f, m, "AlertSent", {"kind": "cash_difference", "ref": p["count_id"], "detail": {"difference": diff, "kind": p["kind"]}}, "cash-difference-flag", now)
        return {"alert": "cash_difference", "difference": diff, "why": "a cash count differs from what the till expected; LynkAssist explains which sales, voids and credit payments make up the expected amount"}

    def shift_reminder(f, m, p, now):
        due = [e for e in c.store.of(m, "ShiftDue") if 0 <= _epoch(e["payload"]["starts_at"]) - now <= 3600]
        if not due: return None
        for e in due: _emit(f, m, "AlertSent", {"kind": "shift_soon", "ref": e["payload"]["employee_id"], "detail": {"starts_at": e["payload"]["starts_at"]}}, "shift-reminder", now)
        return {"reminders": len(due), "why": "a shift starts within the hour"}

    # ---- receipts, kitchen, delivery (auto / auto with undo)
    def receipt_delivery(f, m, p, now):
        channels = biz.receipt_channels(m)
        chosen = p.get("receipt_channel") or ("message" if "message" in channels else "qr")
        if chosen not in channels: chosen = channels[0]
        _emit(f, m, "ReceiptDelivered", {"sale_id": p["sale_id"], "channel": chosen}, "receipt-delivery", now)
        return {"channel": chosen, "why": "the receipt goes out the way the customer chose, within the channels of this plan; printing stays available"}

    def kitchen_routing(f, m, p, now):
        station = restaurant.kitchen_output(m)
        _emit(f, m, "KitchenTicketRouted", {"order_id": p["order_id"], "station": station}, "kitchen-routing", now)
        return {"station": station, "why": "a table order went to the kitchen screen, or to the printer on the Free plan"}

    def delivery_auto_request(f, m, p, now):
        qs = deliveries.quotes(m, {"order_id": p["order_id"]})
        if not qs: return None
        q = qs[0]
        _emit(f, m, "DeliveryAutoRequested", {"order_id": p["order_id"], "partner_id": q["partner_id"], "price": q["price"], "undo_until": now + UNDO_S}, "delivery-auto-request", now)
        return {"partner_id": q["partner_id"], "price": q["price"], "undo_s": UNDO_S, "why": "the owner's rule books the cheapest partner for a paid order; undoable for five minutes and until the partner accepts"}

    # ---- tracking (catalog/tracking.v1.json): customer step messages and the owner's late alerts
    def order_updates(f, m, p, now):
        tr = platform.tracking
        sub = tr.t.subs.get((p["kind"], p["record"]))
        if not p.get("customer") or not sub: return None                 # only customer steps, only to a customer who chose a way to hear
        held = None
        if p["step"] not in tr_act_now():
            held = tr.quiet_until(now, _tz(biz, m))
        _emit(f, m, "TrackingUpdateSent", {"kind": p["kind"], "record": p["record"], "step": p["step"], "channel": sub["channel"], "lang": sub["lang"], "held_until": held}, "order-updates", now)
        return {"step": p["step"], "channel": sub["channel"], "held_until": held,
                "why": "the customer chose to hear each step; the message is in their language and waits for quiet hours unless they must act now"}

    def tracking_late_watch(f, m, p, now):
        tr = platform.tracking
        told = {e["payload"]["ref"] for e in c.store.of(m, "AlertSent") if e["payload"].get("kind") == "tracking_late"}
        late = [v for v in tr.t.late(now, owner=m) if v["record"] not in told]
        if not late: return None
        for v in late:
            _emit(f, m, "AlertSent", {"kind": "tracking_late", "ref": v["record"], "detail": {"tracking_kind": v["kind"], "step": v["step"], "eta": v["eta"]}}, "tracking-late-watch", now)
        return {"late": len(late), "why": "a tracked delivery or order passed its promised time; the owner is told once, with the latest estimate"}

    # ---- agent point (inform / auto)
    def low_float_warning(f, m, p, now):
        if not agent.low_float(m, p["partner_id"], p["balance"]): return None
        _emit(f, m, "AlertSent", {"kind": "low_float", "ref": p["partner_id"], "detail": {"balance": p["balance"]}}, "low-float-warning", now)
        return {"alert": "low_float", "why": "the float at this partner is under a fifth of a usual day; top up through the partner's own process"}

    def commission_match(f, m, p, now):
        r = agent.match_statement(m, p["partner_id"], p["period"], rows=p.get("rows"), now=now)
        _emit(f, m, "CommissionChecked", {"partner_id": p["partner_id"], "period": p["period"], "matched": r["matched"], "mismatches": r["mismatches"]}, "commission-match", now)
        return {"matched": r["matched"], "mismatches": len(r["mismatches"]), "why": "the partner's statement arrived and was matched line by line; each difference is flagged for the owner"}

    # ---- devices (auto / inform)
    def sync_retry(f, m, p, now):
        pending = p.get("pending", {})
        order = [k for k in SYNC_ORDER if pending.get(k)]
        if not order: return None
        _emit(f, m, "SyncRetried", {"device_id": p["device_id"], "sent": sum(pending.get(k, 0) for k in order), "order": order}, "sync-retry", now)
        return {"sent": order, "why": "the link came back; queued items were sent, sales and payments first, media last"}

    def device_health(f, m, p, now):
        issues = devices.health(m, current_version=p.get("current_version", "current"), now=now)
        if not issues: return None
        for d in issues:
            _emit(f, m, "AlertSent", {"kind": "device_health", "ref": d["device_id"], "detail": {"issues": d["issues"]}}, "device-health", now)
        return {"devices": len(issues), "why": "a registered device has an old app, a low battery, little storage or has not been seen for days; LynkAssist shows what to do"}

    def staff_pin_lock(f, m, p, now):
        if p.get("idle_s", 0) < IDLE_LOCK_S: return None
        _emit(f, m, "DeviceLocked", {"device_id": p["device_id"], "after_s": IDLE_LOCK_S}, "staff-pin-lock", now)
        return {"locked": p["device_id"], "why": "no touch for two minutes; the staff PIN lock engaged so the till is never left open"}

    # ---- chat (draft / auto / inform)
    def chat_suggested_replies(f, m, p, now):
        _emit(f, m, "DraftCreated", {"kind": "chat_reply", "ref": p["thread_id"], "lines": ["thanks_and_answer", "price_and_stock", "ask_for_details"]}, "chat-suggested-replies", now)
        return {"draft": "chat_reply", "why": "a customer wrote; LynkAssist suggests replies in the customer's language for a person to pick and send"}

    def chat_routing(f, m, p, now):
        to = CHAT_QUEUES.get(p.get("topic", "order"), "orders")
        _emit(f, m, "ChatRouted", {"thread_id": p["thread_id"], "to": to}, "chat-routing", now)
        return {"to": to, "why": "the message went to the staff member or queue that handles this kind of question"}

    def chat_summary(f, m, p, now):
        n = len([e for e in c.store.of(m, "MessageReceived") if e["payload"].get("thread_id") == p["thread_id"]])
        _emit(f, m, "AlertSent", {"kind": "chat_summary", "ref": p["thread_id"], "detail": {"messages": n}}, "chat-summary", now)
        return {"messages": n, "why": "the person asked for a summary of this conversation; figures stay visible and the summary is labelled"}

    # ---- LynkDriver (BIZZ & DEVICE, 2026-11-09): one driver pack, strongly enforced updates, a sale never blocked
    DRIVER_DAYS = {"security": 0, "required": 3, "normal": 7}

    def driver_update_reminder(f, m, p, now):
        level = p.get("level")
        if level not in DRIVER_DAYS: return None
        told = {(e["payload"]["ref"]) for e in c.store.of(m, "AlertSent") if e["payload"].get("kind") == "driver_update"}
        if p["version"] in told: return None
        due = now + DRIVER_DAYS[level] * 86400
        _emit(f, m, "AlertSent", {"kind": "driver_update", "ref": p["version"], "detail": {"level": level, "due_at": due, "devices": p.get("devices", [])}}, "driver-update-reminder", now)
        return {"level": level, "due_at": due, "why": "a LynkDriver update is out; security updates install now, required ones within 3 days and normal ones within 7. Only the affected device pauses at the deadline, and a sale is never blocked (it ends with a digital receipt)"}

    for aid, fn in {"setup-autofill": setup_autofill, "product-from-photo": product_from_photo, "day-close-prepare": day_close_prepare, "cash-difference-flag": cash_difference_flag,
                    "shift-reminder": shift_reminder, "low-stock-reorder": low_stock_reorder, "expiry-alert": expiry_alert, "negative-stock-flag": negative_stock_flag,
                    "receipt-delivery": receipt_delivery, "kitchen-routing": kitchen_routing, "delivery-auto-request": delivery_auto_request, "low-float-warning": low_float_warning,
                    "commission-match": commission_match, "sync-retry": sync_retry, "device-health": device_health, "staff-pin-lock": staff_pin_lock,
                    "chat-suggested-replies": chat_suggested_replies, "chat-routing": chat_routing, "chat-summary": chat_summary, "reorder-one-tap": reorder_one_tap,
                    "order-updates": order_updates, "tracking-late-watch": tracking_late_watch, "driver-update-reminder": driver_update_reminder}.items():
        flow.handle(aid, fn)


def tr_act_now():
    from services.tracking import ACT_NOW_STEPS
    return ACT_NOW_STEPS


def _tz(biz, m):
    """The business's own time zone (its country pack), for quiet hours."""
    from core import regions
    r = biz.db.execute("select country from biz where lynkoid=?", (m,)).fetchone()
    return regions.country(r[0] if r else None).get("tz") or "UTC"


def _epoch(ts):
    import calendar
    return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))


def _days_until(date, now):
    import calendar
    return (calendar.timegm(time.strptime(date, "%Y-%m-%d")) - now) / 86400
