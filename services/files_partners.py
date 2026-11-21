"""Partners of LynkFiles (SIX SERVICES UPDATE, owner approved 2026-11-18, master blueprint 69.7 and 69.13).

LynkFiles itself needs no partner: "files" works in every country (keeping, versions, sharing and simple signatures are LynkOmni's
own). Only these parts need an outside partner per country, each behind its interface with a working sandbox, and each stays
"Coming to your country soon." until its partner is signed (providers/registry.v1.json):

- sign_identity: the licensed identity partner that checks a signer before an identity-checked signature;
- sign_qualified: a recognised trust-service partner for qualified signatures where a country requires them;
- file_scan: the scanning partner that checks office files and archives before they open in a browser.

Rules every adapter keeps: a signer is only ever a vault reference; a partner sees a document only by its fingerprint, never its
content, except the scanner, which reads the bytes and keeps nothing; a partner's answer is a fact only when the partner confirms
it, so each sandbox answers "pending" and never claims a check, signature or clean scan.
"""
import re

_SHA = re.compile(r"^[0-9a-f]{64}$")


class SignIdentity:
    def check(self, request_id, turn, signer_ref, country):
        raise NotImplementedError


class SandboxSignIdentity(SignIdentity):
    """SANDBOX: accepts a vault reference and answers "pending"; the partner's confirmation is written by the cloud alone."""
    def check(self, request_id, turn, signer_ref, country):
        if not (isinstance(signer_ref, str) and signer_ref.startswith("vault:")):
            return {"ok": False, "reason": "signer_must_be_a_vault_reference"}
        return {"ok": True, "request_id": request_id, "turn": turn, "state": "pending", "status": "sandbox"}


class QualifiedSign:
    def sign(self, request_id, turn, document_sha256, signer_ref):
        raise NotImplementedError


class SandboxQualifiedSign(QualifiedSign):
    """SANDBOX: takes only the document's fingerprint and answers "pending"; a qualified signature is never claimed."""
    def sign(self, request_id, turn, document_sha256, signer_ref):
        if not _SHA.match(document_sha256 or ""):
            raise ValueError("a qualified signature is asked for a sha256 fingerprint")
        if not (isinstance(signer_ref, str) and signer_ref.startswith("vault:")):
            return {"ok": False, "reason": "signer_must_be_a_vault_reference"}
        return {"ok": True, "request_id": request_id, "turn": turn, "state": "pending", "qualified": False, "status": "sandbox"}


class FileScan:
    def scan(self, document_id, data):
        raise NotImplementedError


class SandboxFileScan(FileScan):
    """SANDBOX: never says a file is clean; office files and archives stay "not_scanned" and are not opened in a browser."""
    def scan(self, document_id, data):
        return {"ok": True, "document_id": document_id, "state": "not_scanned", "status": "sandbox"}
