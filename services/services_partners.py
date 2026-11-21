"""Partners of SERVICES UPDATE (master blueprint 67.18; sandbox adapters and ledger entries built in section 4, row 67.17). Every part
listed here needs a partner per country, sits behind its interface with a working sandbox, and stays "Coming to your country soon."
until its partner is signed (providers/registry.v1.json). Delivery firms already have theirs (merchant.delivery:DeliveryPartner) and
phone wallet programmes come through the card issuer (services.vcard, vcard_wallet_tokens).

Rules every adapter keeps: a customer is only ever a vault reference; nothing is sent to a channel the person did not choose; a
partner's answer is a fact only when the partner confirms it, so every sandbox answers "pending" and never claims a delivery, a
listing, a loan, a payment or a stocked item; LynkOmni never holds money (the lender, the biller and the collector do); WhatsApp is
never a channel (owner decision 2026-11-19).
"""


def _person(ref):
    return isinstance(ref, str) and ref.startswith("vault:")


def _pending(**kw):
    return {"ok": True, "state": "pending", "status": "sandbox", **kw}


def _refused(reason):
    return {"ok": False, "reason": reason}


def _minor(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise ValueError(f"{what} is a whole number of minor units")


class ChatChannel:
    """Chat app and social page connectors for LynkChat (67.7): messages from a business's own pages land in its inbox."""
    NEVER = ("whatsapp",)

    def send(self, message_id, channel, customer_ref, text_sha256):
        raise NotImplementedError


class SandboxChatChannel(ChatChannel):
    """SANDBOX: refuses WhatsApp and anything but a vault reference; takes the message's fingerprint only; answers "pending"."""
    def send(self, message_id, channel, customer_ref, text_sha256):
        if channel.lower() in self.NEVER:
            return _refused("channel_not_used")
        if not _person(customer_ref):
            return _refused("customer_must_be_a_vault_reference")
        if not (isinstance(text_sha256, str) and len(text_sha256) == 64):
            raise ValueError("a connector is given the message's sha256, never its words in an event")
        return _pending(message_id=message_id, delivered=False)


class CallPartner:
    """Voice calls in LynkChat (67.7), through a licensed call partner."""
    def call(self, call_id, customer_ref, recording):
        raise NotImplementedError


class SandboxCallPartner(CallPartner):
    """SANDBOX: never records unless the country's rule allows it and the person was told (the caller passes recording=False until then)."""
    def call(self, call_id, customer_ref, recording):
        if not _person(customer_ref):
            return _refused("customer_must_be_a_vault_reference")
        return _pending(call_id=call_id, connected=False, recording=bool(recording))


class PayInPartsLender:
    """Pay in parts through a licensed lender (67.8): the lender alone decides and pays the shop; LynkOmni never lends or holds money."""
    def apply(self, application_id, amount_minor, currency, customer_ref, consent_id):
        raise NotImplementedError


class SandboxPayInParts(PayInPartsLender):
    """SANDBOX: consent first; integers only; answers "pending" and never approves."""
    def apply(self, application_id, amount_minor, currency, customer_ref, consent_id):
        _minor(amount_minor, "an amount")
        if not consent_id:
            return _refused("consent_required")
        if not _person(customer_ref):
            return _refused("customer_must_be_a_vault_reference")
        return _pending(application_id=application_id, approved=False)


class ListingConnector:
    """Map and search listing connectors for LynkGrow (67.6): a business's hours, address and offers kept right on outside listings."""
    def sync(self, listing_id, sites):
        raise NotImplementedError


class SandboxListingConnector(ListingConnector):
    """SANDBOX: answers "pending" for each site; nothing is shown live on another site."""
    def sync(self, listing_id, sites):
        return _pending(listing_id=listing_id, sites={s: "pending" for s in sites})


class OutsideWarehouse:
    """Outside warehouses for LynkStock (67.3): stock held by a third party, reported by it."""
    def stock_report(self, warehouse_id):
        raise NotImplementedError


class SandboxOutsideWarehouse(OutsideWarehouse):
    """SANDBOX: reports nothing in stock until a real warehouse is connected; never claims goods it does not hold."""
    def stock_report(self, warehouse_id):
        return _pending(warehouse_id=warehouse_id, lines=[])


class ShopPluginListing:
    """Online-shop plugin listings for LynkDev (67.12): LynkOmni's plugins on other shop platforms' app stores."""
    def submit(self, plugin_id, store):
        raise NotImplementedError


class SandboxShopPluginListing(ShopPluginListing):
    """SANDBOX: answers "pending"; nothing is listed on another platform."""
    def submit(self, plugin_id, store):
        return _pending(plugin_id=plugin_id, store=store, listed=False)


class TransportBiller:
    """Transport cards, tolls and parking for LynkEssential (67.13), paid to the biller through the licensed payment provider."""
    KINDS = ("transport_card", "toll", "parking")

    def pay(self, payment_id, kind, account_ref, amount_minor, currency):
        raise NotImplementedError


class SandboxTransportBiller(TransportBiller):
    """SANDBOX: answers "pending"; never claims a top-up, a toll or parking paid."""
    def pay(self, payment_id, kind, account_ref, amount_minor, currency):
        if kind not in self.KINDS:
            raise ValueError("unknown kind")
        _minor(amount_minor, "an amount")
        if not _person(account_ref):
            return _refused("account_must_be_a_vault_reference")
        return _pending(payment_id=payment_id, paid=False)


class GovernmentFeeCollector:
    """Government fees for LynkEssential (67.13), through the authority's own collector or gateway."""
    def pay(self, payment_id, fee_code, amount_minor, currency, payer_ref):
        raise NotImplementedError


class SandboxGovernmentFee(GovernmentFeeCollector):
    """SANDBOX: answers "pending"; no receipt is claimed until the authority confirms."""
    def pay(self, payment_id, fee_code, amount_minor, currency, payer_ref):
        _minor(amount_minor, "a fee")
        if not _person(payer_ref):
            return _refused("payer_must_be_a_vault_reference")
        return _pending(payment_id=payment_id, receipt=None)
