"""Partner interfaces the Storefront needs (BIZZ & DEVICE, owner approved 2026-11-09), each with a working SANDBOX adapter
until a licensed partner is signed per country (providers/registry.v1.json: merchant_of_record, live_video, content_store,
tap_to_pay). LynkOmni never holds money: the merchant of record collects tax, the payment provider moves the money, and these
adapters only describe or simulate what the partner does. Nothing here is shown to real users while a partner is a sandbox."""
import hashlib
from dataclasses import dataclass, field


class MerchantOfRecord:
    """A licensed partner per country that sells digital goods to consumers on the seller's behalf and collects and pays the
    tax on digital sales (VAT, GST, sales tax) where the law makes the marketplace responsible."""
    def quote(self, country, sale_minor, currency, digital=True):
        raise NotImplementedError


class SandboxMerchantOfRecord(MerchantOfRecord):
    """SANDBOX: never invents a tax rate. It returns the sale with tax 'unconfirmed' (zero added) so screens can show the
    shape of a receipt; real rates come only from the signed partner."""
    def quote(self, country, sale_minor, currency, digital=True):
        if isinstance(sale_minor, bool) or not isinstance(sale_minor, int) or sale_minor < 0:
            raise ValueError("a sale is a whole number of minor units")
        return {"country": country, "currency": currency, "net_minor": sale_minor, "tax_minor": 0, "total_minor": sale_minor,
                "tax_status": "unconfirmed", "partner": "sandbox"}


class LiveVideo:
    """Live classes and sessions (LynkAcademy and other Storefronts): rooms with a seat cap from the seller's Storefront plan."""
    def open_room(self, seller, seats):
        raise NotImplementedError


@dataclass
class SandboxLiveVideo(LiveVideo):
    """SANDBOX: rooms in memory. Questions go to the presenter only; learners never chat with each other (no group chat)."""
    rooms: dict = field(default_factory=dict)

    def open_room(self, seller, seats):
        if not isinstance(seats, int) or seats <= 0:
            raise ValueError("this Storefront plan has no live sessions")
        rid = f"room-{len(self.rooms) + 1}"
        self.rooms[rid] = {"seller": seller, "seats": seats, "joined": set(), "questions": []}
        return rid

    def join(self, room, person):
        r = self.rooms[room]
        if person not in r["joined"] and len(r["joined"]) >= r["seats"]:
            return {"ok": False, "reason": "room_full"}
        r["joined"].add(person)
        return {"ok": True}

    def ask(self, room, person, text):
        """A question reaches the presenter only (chat rule: no learner-to-learner chat)."""
        r = self.rooms[room]
        if person not in r["joined"]:
            raise PermissionError("join the session first")
        r["questions"].append({"from": person, "text": text, "to": r["seller"]})
        return {"to": r["seller"]}


class ContentStore:
    """Files a seller offers (documents, video, audio, e-books, images): allowed types only, scanned, size-capped per plan."""
    def put(self, seller, name, data, limit_bytes):
        raise NotImplementedError


ALLOWED = {
    b"%PDF-": "application/pdf", b"PK\x03\x04": "application/zip-container",          # PDF; EPUB and office files are zip containers
    b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg", b"RIFF": "riff",   # images; WebP and WAV are RIFF
    b"ID3": "audio/mpeg", b"OggS": "audio/ogg", b"fLaC": "audio/flac",
}
REFUSED = (b"MZ", b"\x7fELF", b"#!", b"<script", b"<?php", b"<svg", b"<html", b"<!DOCTYPE")   # programs and markup are never stored


@dataclass
class SandboxContentStore(ContentStore):
    """SANDBOX: keeps files in memory and checks them by their bytes, never by their name. A real store adds malware
    scanning and delivery through the signed partner."""
    files: dict = field(default_factory=dict)

    @staticmethod
    def kind(data):
        head = data[:16]
        if any(head.lstrip().lower().startswith(r.lower()) for r in REFUSED):
            return None
        for magic, k in ALLOWED.items():
            if head.startswith(magic):
                return k
        if len(data) > 12 and data[4:8] == b"ftyp":
            return "video/mp4"
        return None

    def put(self, seller, name, data, limit_bytes):
        k = self.kind(data)
        if k is None:
            return {"ok": False, "reason": "type_not_allowed"}
        if len(data) > limit_bytes:
            return {"ok": False, "reason": "over_plan_storage"}
        digest = hashlib.sha256(data).hexdigest()
        self.files[digest] = {"seller": seller, "name": name, "kind": k, "size": len(data)}
        return {"ok": True, "id": digest[:16], "kind": k}


class TapToPay:
    """Contactless card acceptance on an ordinary phone, through a licensed provider's certified software (no card reader)."""
    def start(self, amount_minor, currency):
        raise NotImplementedError


class SandboxTapToPay(TapToPay):
    """SANDBOX: a tap is only ever 'sent'; it is confirmed solely by the provider (never by the app), as every payment is."""
    def start(self, amount_minor, currency):
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
            raise ValueError("an amount is a positive whole number of minor units")
        return {"state": "sent", "amount_minor": amount_minor, "currency": currency, "confirmed_by": "provider", "partner": "sandbox"}
