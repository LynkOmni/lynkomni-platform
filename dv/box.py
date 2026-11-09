"""LynkDVBox: the device side. Turns commands into contract events, enforcing permissions and session rules locally.
SIGNATURES ARE DEV-ONLY PLACEHOLDERS (random bytes in the right format). Real devices must sign with a hardware-backed ES256 key."""
import os, base64
from datetime import datetime, timedelta, timezone
from contract.tools.validate_contract import PERMS, REGISTER, SAMPLE_CURRENCY, event_hash, round_half_up_line, ts, uuid7, validate_event

PERM = {p["id"]: p for p in PERMS["permissions"]}
CMD = {c["name"]: c for c in REGISTER["commands"]}
ROLES = PERMS["roles"]

class LocalRejection(Exception):
    """A command refused on the device, with a reason from the command policy register."""
    def __init__(s, reason): super().__init__(reason); s.reason = reason

class ContractError(Exception):
    pass

class LynkDVBox:
    def __init__(s, merchant_id, branch_id, device_id, user_id, role, now=None, currency=SAMPLE_CURRENCY, practice=False, online=False):
        s.m, s.b, s.d, s.u, s.role = merchant_id, branch_id, device_id, user_id, role
        s.practice = practice     # practice mode (blueprint section 7): a training copy, clearly marked, that never syncs and never touches real money or records
        s.online = online         # class C commands (agent, collection, partner finance, delivery requests) need a live connection and are never queued
        s.shift, s.shift_cash, s.credits, s.tables, s.kitchen, s.clocks, s.vouchers_used, s.pickups_done = None, 0, {}, {}, {}, {}, set(), set()
        s.currency = currency   # the business's currency from its country pack (contract version 2: any currency, integer minor units)
        s.seq, s.prev, s.log = 0, "GENESIS", []
        s.clock = now or datetime.now(timezone.utc)
        s.session_started = s.clock
        s.session_max_days = {"owner": 7, "manager": 7}.get(role, REGISTER["session_policy"]["offline_session_max_days_default"])   # privileged roles re-authenticate sooner
        s.locked, s.products, s.stock, s.sales, s.receipt_no = False, {}, {}, {}, 0
        s.leased, s.public_map = {}, {}   # IDs leased by the cloud, so receipts can carry a real LO identifier before the first sync
    # time, session, permissions
    def advance(s, **kw): s.clock += timedelta(**kw)
    def reauth(s): s.session_started = s.clock               # a successful online sign-in (class C) resets the offline window
    def session_expired(s): return s.clock - s.session_started > timedelta(days=s.session_max_days)
    def _guard(s, command):
        c = CMD[command]
        if s.locked: raise LocalRejection("device_locked")
        if s.session_expired(): raise LocalRejection("session_expired")   # selling pauses, data stays safe, syncs after re-auth
        if c["class"] == "C" and not s.online: raise LocalRejection("offline_not_possible")   # online only: never queued, never shown as done offline
        if c["class"] == "B": raise LocalRejection("offline_not_possible")
        perm = c["permission"]
        if perm and (s.role not in PERM[perm]["roles"] or "mobile" not in PERM[perm]["channels"]): raise LocalRejection("permission_denied")
    def _emit(s, etype, payload):
        evt = {"event_id": uuid7(), "origin": "device", "merchant_id": s.m, "branch_id": s.b, "device_id": s.d, "actor_user_id": s.u,
               "device_seq": s.seq + 1, "type": etype, "schema_version": 3, "occurred_at_device": ts(s.clock), "prev_hash": s.prev,
               "payload": payload, "signature": base64.urlsafe_b64encode(os.urandom(64)).decode().rstrip("=")}   # DEV-ONLY signature
        problems = validate_event(evt)
        if problems: raise ContractError(f"{etype}: {problems}")
        s.seq, s.prev = evt["device_seq"], event_hash(evt); s.log.append(evt)
        return evt
    def accept_lease(s, code, public_ids): s.leased.setdefault(code, []).extend(public_ids)
    def _print_id(s, code, internal_id):
        if s.leased.get(code):
            s.public_map[internal_id] = s.leased[code].pop(0)   # used once, never reused
    def pending(s, acked_seq):
        if s.practice: return []     # a practice device never syncs: nothing it records is real
        return [e for e in s.log if e["device_seq"] > acked_seq]
    # commands (class A: local facts, never rejected by the cloud)
    def create_product(s, name, price, unit="piece", barcode=None, track_stock=True):
        s._guard("CreateProduct")
        pid, p = uuid7(), {"name": name, "unit": unit, "price": price, "track_stock": track_stock}
        if barcode: p["barcode"] = barcode
        s._emit("ProductCreated", {"product_id": pid, "currency": s.currency, **p}); s.products[pid] = {"name": name, "price": price}; s.stock[pid] = 0
        return pid
    def receive_stock(s, lines, supplier_note=None):
        s._guard("ReceiveStock")
        pl = {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": q} for pid, q in lines]}
        if supplier_note: pl["supplier_note"] = supplier_note
        s._emit("StockReceived", pl)
        for pid, q in lines: s.stock[pid] = s.stock.get(pid, 0) + q
    def adjust_stock(s, product_id, delta_milli, reason_code, note=None):
        s._guard("AdjustStock")
        pl = {"adjustment_id": uuid7(), "product_id": product_id, "delta_milli": delta_milli, "reason_code": reason_code}
        if note: pl["note"] = note
        s._emit("StockAdjusted", pl); s.stock[product_id] = s.stock.get(product_id, 0) + delta_milli
    def count_stock(s, product_id, counted_milli):
        s._guard("CountStock")
        s._emit("StockCounted", {"count_id": uuid7(), "product_id": product_id, "counted_milli": counted_milli, "device_view_milli": s.stock.get(product_id, 0)})
        s.stock[product_id] = counted_milli
    def record_sale(s, cart):
        """cart: list of (product_id, quantity_milli, discount). Emits SaleRecorded then a provisional ReceiptIssued."""
        s._guard("RecordSale")
        if not cart: raise LocalRejection("empty_cart")
        lines = []
        for n, (pid, q, disc) in enumerate(cart, 1):
            if pid not in s.products: raise LocalRejection("product_not_found_local")
            lt = round_half_up_line(q, s.products[pid]["price"], disc)
            if lt < 0: raise LocalRejection("invalid_amount")
            lines.append({"line_no": n, "product_id": pid, "product_name": s.products[pid]["name"], "quantity_milli": q,
                          "unit_price": s.products[pid]["price"], "discount": disc, "line_total": lt})
        sub = sum(l["line_total"] for l in lines); s.receipt_no += 1
        sid, rno = uuid7(), f"{s.d[:2].upper()}-{s.receipt_no}"
        s._emit("SaleRecorded", {"sale_id": sid, "receipt_number_local": rno, "lines": lines, "subtotal": sub,
                                 "discount_total": sum(l["discount"] for l in lines), "tax_total": 0, "tax_mode": "none", "total": sub, "currency": s.currency})
        rid = uuid7()
        s._emit("ReceiptIssued", {"receipt_id": rid, "sale_id": sid, "receipt_number_local": rno, "copy_number": 1, "validity": "provisional"})
        s._print_id("RCP", rid); s._print_id("ORD", sid)
        for l in lines: s.stock[l["product_id"]] = s.stock.get(l["product_id"], 0) - l["quantity_milli"]
        s.sales[sid] = {"lines": lines, "voided": False}
        return sid
    def void_sale(s, sale_id, reason_code, note=None):
        s._guard("VoidSale")
        sale = s.sales.get(sale_id)
        if sale is None: raise LocalRejection("sale_not_found_local")
        if sale["voided"]: raise LocalRejection("already_voided")
        pl = {"sale_id": sale_id, "reason_code": reason_code}
        if note: pl["note"] = note
        s._emit("SaleVoided", pl); sale["voided"] = True
        for l in sale["lines"]: s.stock[l["product_id"]] += l["quantity_milli"]
    def record_payment(s, sale_id, method, amount, provider_reference=None):
        s._guard("RecordPayment")
        status = {"cash": "cash_received", "credit": "credit_open"}.get(method, "pending_confirmation")   # a device never marks non-cash as settled
        pl = {"payment_id": uuid7(), "sale_id": sale_id, "method": method, "amount": amount, "status": status, "currency": s.currency}
        if provider_reference: pl["provider_reference"] = provider_reference
        s._emit("PaymentRecorded", pl)
        if status == "cash_received" and s.shift: s.shift_cash += amount
        return status

    # ---- build section 3: shifts and cash counts (blueprint 42 I, Run the shop). Fully offline, queued.
    def open_shift(s, float_amount):
        s._guard("OpenShift")
        if s.shift: raise LocalRejection("shift_already_open")
        s.shift, s.shift_cash = uuid7(), float_amount
        s._emit("ShiftOpened", {"shift_id": s.shift, "float_amount": float_amount, "currency": s.currency})
        return s.shift
    def expected_cash(s): return s.shift_cash
    def count_cash(s, counted, kind="spot"):
        """A cash count never blocks: a difference is a fact for the owner (CashDifferenceFlagged is the cloud's)."""
        s._guard("CountCash")
        if not s.shift: raise LocalRejection("no_open_shift")
        cid = uuid7()
        s._emit("CashCounted", {"count_id": cid, "shift_id": s.shift, "kind": kind, "counted_cash": counted, "expected_cash": s.shift_cash, "currency": s.currency})
        return cid, counted - s.shift_cash
    def close_shift(s, counted):
        s._guard("CloseShift")
        if not s.shift: raise LocalRejection("no_open_shift")
        sid, expected = s.shift, s.shift_cash
        s._emit("ShiftClosed", {"shift_id": sid, "counted_cash": counted, "expected_cash": expected, "currency": s.currency})
        s._emit("CashCounted", {"count_id": uuid7(), "shift_id": sid, "kind": "day_end", "counted_cash": counted, "expected_cash": expected, "currency": s.currency})
        s.shift, s.shift_cash = None, 0
        return counted - expected
    # ---- customer credit book (S6): a credit sale and its repayments, offline
    def record_customer_credit(s, customer_id, sale_id, amount, due_on=None):
        s._guard("RecordCustomerCredit")
        if sale_id not in s.sales: raise LocalRejection("sale_not_found_local")
        cid = uuid7(); pl = {"credit_id": cid, "customer_id": customer_id, "sale_id": sale_id, "amount": amount, "currency": s.currency}
        if due_on: pl["due_on"] = due_on
        s._emit("CustomerCreditRecorded", pl); s.credits[cid] = {"customer": customer_id, "amount": amount, "paid": 0}
        return cid
    def record_credit_payment(s, credit_id, amount, method="cash"):
        s._guard("RecordCreditPayment")
        c = s.credits.get(credit_id)
        if c is None: raise LocalRejection("credit_not_found_local")
        if amount <= 0 or c["paid"] + amount > c["amount"]: raise LocalRejection("invalid_amount")
        s._emit("CustomerCreditPaid", {"payment_id": uuid7(), "credit_id": credit_id, "amount": amount, "currency": s.currency, "method": method})
        c["paid"] += amount
        if method == "cash" and s.shift: s.shift_cash += amount
        return c["amount"] - c["paid"]
    def credit_balances(s):
        out = {}
        for c in s.credits.values(): out[c["customer"]] = out.get(c["customer"], 0) + c["amount"] - c["paid"]
        return out
    # ---- own vouchers and pickup point (S8): offline within limits, each code used once
    def redeem_voucher(s, voucher_id, amount):
        s._guard("RedeemVoucher")
        if voucher_id in s.vouchers_used: raise LocalRejection("already_redeemed")
        s._emit("VoucherRedeemed", {"redemption_id": uuid7(), "voucher_id": voucher_id, "amount": amount, "currency": s.currency}); s.vouchers_used.add(voucher_id)
    def hand_over_pickup(s, order_id, code):
        """The device holds only the hash of the pickup code; the code itself is the customer's."""
        s._guard("HandOverPickup")
        if order_id in s.pickups_done: raise LocalRejection("already_handed_over")
        import hashlib
        s._emit("PickupHandedOver", {"pickup_id": uuid7(), "order_id": order_id, "code_hash": hashlib.sha256(code.encode()).hexdigest()}); s.pickups_done.add(order_id)
    # ---- restaurant mode (N1): tables and the kitchen work offline over the shop's network or LynkMesh
    def open_table(s, label, covers=None):
        s._guard("OpenTable")
        tid = uuid7(); pl = {"table_id": tid, "table_label": label}
        if covers is not None: pl["covers"] = covers
        s._emit("TableOpened", pl); s.tables[tid] = {"label": label, "open": True, "orders": [], "sales": []}
        return tid
    def send_to_kitchen(s, table_id, lines):
        """lines: list of (product_id, quantity_milli, modifiers or None)."""
        s._guard("SendToKitchen")
        t = s.tables.get(table_id)
        if not t or not t["open"]: raise LocalRejection("table_not_open")
        oid, out = uuid7(), []
        for n, (pid, q, mods) in enumerate(lines, 1):
            if pid not in s.products: raise LocalRejection("product_not_found_local")
            l = {"line_no": n, "product_id": pid, "quantity_milli": q}
            if mods: l["modifiers"] = mods
            out.append(l)
        s._emit("OrderSentToKitchen", {"order_id": oid, "table_id": table_id, "lines": out}); t["orders"].append(oid); s.kitchen[oid] = {l["line_no"]: False for l in out}
        return oid
    def mark_kitchen_item_ready(s, order_id, line_no):
        s._guard("MarkKitchenItemReady")
        if order_id not in s.kitchen or line_no not in s.kitchen[order_id]: raise LocalRejection("order_not_found_local")
        s._emit("KitchenItemReady", {"order_id": order_id, "line_no": line_no}); s.kitchen[order_id][line_no] = True
    def kitchen_open(s): return {o: [n for n, done in lines.items() if not done] for o, lines in s.kitchen.items() if not all(lines.values())}
    def split_table_bill(s, table_id, carts):
        """Each cart becomes its own sale (one receipt each); the table remembers them all."""
        s._guard("SplitTableBill")
        t = s.tables.get(table_id)
        if not t or not t["open"]: raise LocalRejection("table_not_open")
        if len(carts) < 2: raise LocalRejection("split_needs_two")   # one bill is an ordinary sale
        ids = [s.record_sale(c) for c in carts]
        s._emit("TableBillSplit", {"table_id": table_id, "sale_ids": ids}); t["sales"].extend(ids)
        return ids
    def record_tip(s, sale_id, amount):
        """Tips belong to the business (N1): LynkOmni takes no share. Recorded apart from the sale total."""
        s._guard("RecordTip")
        if sale_id not in s.sales: raise LocalRejection("sale_not_found_local")
        if amount <= 0: raise LocalRejection("invalid_amount")
        s._emit("TipRecorded", {"tip_id": uuid7(), "sale_id": sale_id, "amount": amount, "currency": s.currency})
    def close_table(s, table_id):
        s._guard("CloseTable")
        t = s.tables.get(table_id)
        if not t or not t["open"]: raise LocalRejection("table_not_open")
        if any(not all(v.values()) for o, v in s.kitchen.items() if o in t["orders"]): raise LocalRejection("kitchen_items_open")
        s._emit("TableClosed", {"table_id": table_id}); t["open"] = False
    # ---- time clock (N2): the till records who is in; payroll itself is LynkAcc's, in the cloud
    def clock_in(s, employee_id):
        s._guard("ClockIn")
        if employee_id in s.clocks: raise LocalRejection("already_clocked_in")
        cid = uuid7(); s._emit("ClockedIn", {"clock_id": cid, "employee_id": employee_id}); s.clocks[employee_id] = cid
        return cid
    def clock_out(s, employee_id):
        s._guard("ClockOut")
        cid = s.clocks.pop(employee_id, None)
        if not cid: raise LocalRejection("not_clocked_in")
        s._emit("ClockedOut", {"clock_id": cid, "employee_id": employee_id})
    # ---- own-rider delivery steps (N8): offline with the code; the request itself is online (class C)
    def record_delivery_step(s, delivery_id, step, proof="code"):
        s._guard("RecordDeliveryStep")
        if step == "picked_up": s._emit("DeliveryPickedUp", {"delivery_id": delivery_id})
        elif step == "delivered": s._emit("DeliveryDelivered", {"delivery_id": delivery_id, "proof": proof})
        else: raise LocalRejection("invalid_step")
    def request_delivery(s, order_id, price, partner_id=None):
        s._guard("RequestDelivery")
        did = uuid7(); pl = {"delivery_id": did, "order_id": order_id, "own_rider": partner_id is None, "price": price, "currency": s.currency}
        if partner_id: pl["partner_id"] = partner_id
        s._emit("DeliveryRequested", pl)
        return did
    # ---- agent point (42 I): the device only asks; the cloud alone writes the partner's answer. Never offline, never queued.
    def request_agent_service(s, partner_id, service, amount, fee, customer_reference=None):
        s._guard("RequestAgentService")
        rid = uuid7(); pl = {"request_id": rid, "partner_id": partner_id, "service": service, "amount": amount, "fee": fee, "currency": s.currency}
        if customer_reference: pl["customer_reference"] = customer_reference
        s._emit("AgentRequestCreated", pl)
        return rid
