"""Payment and fiscal adapters. Everything here is a SANDBOX SIMULATOR until a real partner is wired in.
To integrate a real provider: subclass Provider, implement charge(), register it in build_providers()."""

METHODS = {"momo_mtn": ("mobile_money",), "airtel_money": ("mobile_money",), "mpesa": ("mobile_money",),
           "upi": ("upi", "qr"), "bank_transfer": ("bank",), "card": ("card",), "qr": ("qr",)}

class Provider:
    name, methods = "", ()
    def charge(self, amount_minor, currency, method, key):
        raise NotImplementedError

class Simulator(Provider):
    def __init__(self, name, methods, fail_first=0, fee_bps=100):
        self.name, self.methods, self.fail_first, self.fee_bps, self.calls, self.done = name, methods, fail_first, fee_bps, 0, {}
    def charge(self, amount_minor, currency, method, key):
        if key in self.done:  # idempotent: same key never charges twice
            return self.done[key]
        self.calls += 1
        if self.calls <= self.fail_first:
            return {"ok": False, "error": "timeout"}
        self.done[key] = {"ok": True, "ref": f"{self.name}-{key}", "fee_minor": amount_minor * self.fee_bps // 10000}
        return self.done[key]

def build_providers(names, **sim):
    return [Simulator(n, METHODS[n], **sim) for n in names]

class FiscalAdapter:
    """Issues legally valid tax receipts. One implementation per tax authority."""
    def issue(self, sale):
        return {"status": "not_applicable", "fiscal": False}

class PendingFiscalAdapter(FiscalAdapter):
    """Any tax authority whose offline workflow is not yet confirmed in writing (the country pack names the authority in its
    `fiscal` field; the provider ledger holds the item). NOT certified: an offline sale stays 'pending_fiscal' until the
    authority confirms the allowed workflow, and nothing is ever called a valid tax receipt before that."""
    def issue(self, sale):
        return {"status": "pending_fiscal", "fiscal": False, "note": "Not a valid tax invoice until submitted"}

RraEbmAdapter = PendingFiscalAdapter   # the name used by one country pack today; every unconfirmed authority gets the same adapter

def fiscal_for(code):
    """A pack with no fiscal code gets the plain adapter (not applicable); any named authority is pending until confirmed."""
    return PendingFiscalAdapter() if code else FiscalAdapter()
