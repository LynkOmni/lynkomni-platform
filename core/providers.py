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

class RraEbmAdapter(FiscalAdapter):
    """Rwanda EBM. NOT certified. RRA says certified private systems must be always online,
    so offline sales must stay marked 'pending_fiscal' until RRA confirms the allowed workflow."""
    def issue(self, sale):
        return {"status": "pending_fiscal", "fiscal": False, "note": "Not a valid tax invoice until submitted"}

FISCAL = {"RRA_EBM": RraEbmAdapter}
def fiscal_for(code):
    return FISCAL.get(code, FiscalAdapter)()
