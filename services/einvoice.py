"""Government e-invoices (OFFICE UPDATE, master blueprint 66.3; section 4 step D2a), behind one interface.

Where a country requires invoices in a set digital format or sent through the tax office, LynkInv hands each issued invoice to
the confirmed tax-office connector or a certified e-invoice partner and shows the five states (queued, sent, accepted,
confirmed, failed). Only the network writes accepted, confirmed or failed; LynkOmni never claims an invoice was cleared before
the network answers. Until the partner is signed in a country (provider ledger e_invoice_network) the invoice still issues and
its e-invoice waits as queued, said plainly. Supplier e-invoices received go into Bills to pay.

SANDBOX: SandboxEInvoiceNetwork accepts a complete invoice and confirms it on the next poll; it refuses an invoice with no lines,
no seller tax number where one is needed, or a total that does not add up. It is for tests and the emulators only."""
from core import invoices as I

STATES = tuple(I.INV["e_invoice"]["states"])


class EInvoiceNetwork:
    """The interface every real e-invoice connector implements (one per country or certified partner)."""
    def submit(self, invoice):
        """Hand over an issued invoice; returns {"state": "sent", "ref"} or {"state": "failed", "reason"}."""
        raise NotImplementedError

    def poll(self, ref):
        """The network's answer for a sent invoice: {"state": accepted|confirmed|failed, "reason"?}."""
        raise NotImplementedError

    def receive(self):
        """Supplier e-invoices waiting for this entity, each a bill to pay."""
        raise NotImplementedError


class SandboxEInvoiceNetwork(EInvoiceNetwork):
    def __init__(self, needs_tax_number=False):
        self.needs_tax_number, self.sent, self.inbox, self._n = needs_tax_number, {}, [], 0

    def submit(self, invoice):
        if not invoice.get("lines"):
            return {"state": "failed", "reason": "no_lines"}
        if self.needs_tax_number and not invoice.get("seller_tax_number"):
            return {"state": "failed", "reason": "seller_tax_number_missing"}
        if sum(ln.get("total", 0) for ln in invoice["lines"]) != invoice.get("total_minor"):
            return {"state": "failed", "reason": "totals_do_not_add_up"}
        self._n += 1
        ref = f"sandbox-{self._n}"
        self.sent[ref] = "accepted"
        return {"state": "sent", "ref": ref}

    def poll(self, ref):
        if ref not in self.sent:
            return {"state": "failed", "reason": "unknown_ref"}
        state = self.sent[ref]
        self.sent[ref] = "confirmed"
        return {"state": state}

    def receive(self):
        out, self.inbox = self.inbox, []
        return out


def next_state(current, answer):
    """The shown state only moves forward along the five states; failed is final until a fix is sent again as a new submission."""
    order = {"queued": 0, "sent": 1, "accepted": 2, "confirmed": 3}
    new = answer.get("state")
    if new not in STATES or current in ("confirmed", "failed"):
        return current
    if new == "failed":
        return "failed"
    return new if order[new] > order.get(current, -1) else current
