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
    def __init__(s, merchant_id, branch_id, device_id, user_id, role, now=None, currency=SAMPLE_CURRENCY):
        s.m, s.b, s.d, s.u, s.role = merchant_id, branch_id, device_id, user_id, role
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
        if c["class"] != "A": raise LocalRejection("offline_not_possible")
        perm = c["permission"]
        if perm and (s.role not in PERM[perm]["roles"] or "mobile" not in PERM[perm]["channels"]): raise LocalRejection("permission_denied")
    def _emit(s, etype, payload):
        evt = {"event_id": uuid7(), "origin": "device", "merchant_id": s.m, "branch_id": s.b, "device_id": s.d, "actor_user_id": s.u,
               "device_seq": s.seq + 1, "type": etype, "schema_version": 2, "occurred_at_device": ts(s.clock), "prev_hash": s.prev,
               "payload": payload, "signature": base64.urlsafe_b64encode(os.urandom(64)).decode().rstrip("=")}   # DEV-ONLY signature
        problems = validate_event(evt)
        if problems: raise ContractError(f"{etype}: {problems}")
        s.seq, s.prev = evt["device_seq"], event_hash(evt); s.log.append(evt)
        return evt
    def accept_lease(s, code, public_ids): s.leased.setdefault(code, []).extend(public_ids)
    def _print_id(s, code, internal_id):
        if s.leased.get(code):
            s.public_map[internal_id] = s.leased[code].pop(0)   # used once, never reused
    def pending(s, acked_seq): return [e for e in s.log if e["device_seq"] > acked_seq]
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
        return status
