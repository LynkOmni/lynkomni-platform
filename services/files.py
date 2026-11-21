"""LynkFiles' document engine in the cloud (SIX SERVICES UPDATE, master blueprint 69.7; section 4 step E3), on the rules of
core/files.py (catalog/files.v1.json). Every service stores and signs through it.

- Keeping: a file is kept under the record it belongs to (an invoice, a bill, a customer, a staff member, a project, a property, a
  school record, a deal) and opens only for those that service lets see that record. Its type is read from its bytes and programs are
  refused; storage follows the LynkFiles plan; every version is kept with its fingerprint and an earlier one can be restored.
- Holding and deleting: nothing under legal hold is changed, deleted or shared; deleting stops every share link.
- Sharing: a link has its rights, an end date (never open-ended) and, if set, a password kept only as a salted hash; downloading can
  be blocked; a link can be stopped at once.
- Signing: one or many signers, in order or together, each with their own link and no account; a signer signs the exact version they
  saw (its fingerprint); simple signatures are LynkOmni's own, identity-checked and qualified ones go through their partners and are
  written only when the partner confirms. A completed document gets a verification code anyone can check: it shows the signed
  fingerprint and how many signed, never who.
- The audit log keeps every open, download, version, share, signature, hold and deletion.

Names and contacts of signers live only in the PII vault; no event carries a file's content or name.
"""
import base64, hashlib, hmac, secrets, time

from contract.tools.validate_contract import uuid7
from core import files as F
from services.files_partners import SandboxFileScan, SandboxQualifiedSign, SandboxSignIdentity
from services.improvements import Table

AREAS = {"lynkacc": "acc", "lynkinv": "inv", "lynkcrm": "crm", "lynkhr": "hr", "lynkproject": "project", "lynkproperty": "property",
         "lynkschool": "school", "lynkfiles": "files"}
OPENABLE = ("pdf", "png", "jpeg", "webp", "text")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _pw(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


class Files:
    def __init__(s, p, now=time.time, identity=None, qualified=None, scanner=None):
        s.p, s.now, db = p, now, p.c.store.db
        s.identity, s.qualified, s.scanner = identity or SandboxSignIdentity(), qualified or SandboxQualifiedSign(), scanner or SandboxFileScan()
        s.docs, s.blobs, s.links = Table(db, "files_docs"), Table(db, "files_blobs"), Table(db, "files_links")
        s.requests, s.tokens, s.codes, s.log = Table(db, "files_requests"), Table(db, "files_tokens"), Table(db, "files_codes"), Table(db, "files_audit")

    # ---- helpers ---------------------------------------------------------------------------------------------------------------
    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    def _audit(s, m, doc_id, what, who):
        if what not in F.FILES["audit"]:
            raise ValueError("unknown audit entry")
        s.log.put(uuid7(), {"merchant": m, "document": doc_id, "what": what, "who": who, "at": int(s.now())})

    def audit(s, m, doc_id):
        return [x for _, x in s.log.items() if x["merchant"] == m and x["document"] == doc_id]

    def _doc(s, m, doc_id):
        d = s.docs.get(doc_id)
        if not d or d["merchant"] != m or d.get("deleted"):
            raise KeyError("no such file")
        return d

    def _country(s, m):
        reg = s.p.c.store.of(m, "merchant.registered")
        return (reg[-1]["payload"].get("country") if reg else None) or "XX"

    def ent(s, m):
        return s.p.billing.entitlement(m, "lynkfiles")

    def used(s, m):
        return sum(v["size"] for _, d in s.docs.items() if d["merchant"] == m and not d.get("deleted") for v in d["versions"])

    def _check_bytes(s, m, data):
        kind = F.sniff(data)
        if kind == "blocked":
            raise ValueError("programs and scripts are never kept")
        if kind is None:
            raise ValueError("this kind of file is not kept")
        if len(data) > F.FILES["content"]["max_mb"] * 1024 * 1024:
            raise ValueError("the file is too large")
        e = s.ent(m)
        if not F.fits(s.used(m), len(data), e.get("storage_gb")):           # extra blocks of 100 GB are added with LynkFiles' own screens (4B)
            raise PermissionError("storage is full for this LynkFiles plan")
        return kind

    def _put_blob(s, data):
        h = _sha(data)
        if not s.blobs.get(h):
            s.blobs.put(h, {"b64": base64.b64encode(data).decode()})
        return h

    # ---- keeping ---------------------------------------------------------------------------------------------------------------
    def store(s, m, by, record_kind, record_id, kind, data, side="internal"):
        if record_kind not in F.FILES["record_kinds"] or kind not in F.FILES["kinds"]:
            raise ValueError("unknown record or document kind")
        ctype = s._check_bytes(m, data)
        did = uuid7()
        h = s._put_blob(data)
        scan = s.scanner.scan(did, data)["state"] if ctype not in OPENABLE else "not_needed"
        s.docs.put(did, {"id": did, "merchant": m, "record_kind": record_kind, "record_id": record_id, "kind": kind, "type": ctype,
                         "scan": scan, "versions": [{"n": 1, "sha256": h, "size": len(data), "by": by}], "hold": False, "side": side})
        s._emit(m, "DocumentFiled", {"document_id": did, "kind": kind, "record_kind": record_kind, "record_id": record_id, "sha256": h, "side": side})
        s._audit(m, did, "version_added", by)
        return did

    def add_version(s, m, doc_id, by, data):
        d = s._doc(m, doc_id)
        if d["hold"]:
            raise PermissionError("under legal hold")
        if F.sniff(data) != d["type"]:
            raise ValueError("a new version keeps the file's type")
        s._check_bytes(m, data)
        h = s._put_blob(data)
        n = len(d["versions"]) + 1
        d["versions"] = d["versions"] + [{"n": n, "sha256": h, "size": len(data), "by": by}]
        s._emit(m, "FileVersionAdded", {"document_id": doc_id, "version": n, "sha256": h})
        s._audit(m, doc_id, "version_added", by)
        return n

    def restore(s, m, doc_id, by, n):
        d = s._doc(m, doc_id)
        old = next(v for v in d["versions"] if v["n"] == n)
        return s.add_version(m, doc_id, by, base64.b64decode(s.blobs.get(old["sha256"])["b64"]))

    def may_open(s, m, doc_id, perms=None):
        """perms None is the owner; otherwise the person's permissions, and the file opens only where the owning service lets them
        view (core.enterprise roles: {area: [permissions]})."""
        d = s._doc(m, doc_id)
        if perms is None:
            return True
        area = AREAS[F.FILES["record_kinds"][d["record_kind"]]]
        return "view" in perms.get(area, []) or "admin" in perms.get(area, [])

    def open(s, m, doc_id, who, perms=None, version=None):
        if not s.may_open(m, doc_id, perms):
            raise PermissionError("this record's service does not let you see it")
        d = s._doc(m, doc_id)
        v = d["versions"][-1] if version is None else next(x for x in d["versions"] if x["n"] == version)
        s._audit(m, doc_id, "opened", who)
        return {"type": d["type"], "sha256": v["sha256"], "version": v["n"], "in_browser": d["type"] in OPENABLE or d["scan"] == "clean",
                "data": base64.b64decode(s.blobs.get(v["sha256"])["b64"])}

    def hold(s, m, doc_id, on, by):
        d = s._doc(m, doc_id)
        d["hold"] = bool(on)
        if on:
            for k, l in s.links.items():
                if l["document"] == doc_id and not l["stopped"]:
                    s._stop(m, k, "legal_hold")
        s._emit(m, "LegalHoldChanged", {"document_id": doc_id, "on": bool(on)})
        s._audit(m, doc_id, "hold_set" if on else "hold_lifted", by)

    def delete(s, m, doc_id, by, reason="owner"):
        d = s._doc(m, doc_id)
        if d["hold"]:
            raise PermissionError("nothing under legal hold is deleted")
        for k, l in s.links.items():
            if l["document"] == doc_id and not l["stopped"]:
                s._stop(m, k, "deleted")
        d["deleted"] = True
        s._emit(m, "FileDeleted", {"document_id": doc_id, "reason": reason})
        s._audit(m, doc_id, "deleted", by)

    # ---- sharing ---------------------------------------------------------------------------------------------------------------
    def share(s, m, doc_id, by, rights="view", days=None, password=None, download_blocked=False):
        d = s._doc(m, doc_id)
        days = F.FILES["sharing"]["default_days"] if days is None else days
        if d["hold"]:
            raise PermissionError("under legal hold")
        if rights not in F.FILES["sharing"]["rights"] or not F.share_days_ok(days):
            raise ValueError("unknown rights or a share longer than allowed")
        if password is not None and len(password) < F.FILES["sharing"]["password_min"]:
            raise ValueError("the password is too short")
        lid, token = uuid7(), secrets.token_urlsafe(24)
        salt = secrets.token_bytes(16)
        s.links.put(lid, {"merchant": m, "document": doc_id, "token_sha": _sha(token.encode()), "rights": rights, "until": int(s.now()) + days * 86400,
                          "password_set": password is not None, "salt": salt.hex(), "pw": _pw(password, salt) if password else None,
                          "download_blocked": download_blocked, "stopped": False})
        s._emit(m, "ShareLinkCreated", {"link_id": lid, "document_id": doc_id, "rights": rights, "days": days, "password": password is not None, "download_blocked": download_blocked})
        s._audit(m, doc_id, "shared", by)
        return lid, token

    def open_link(s, token, password=None):
        th = _sha(token.encode())
        hit = [(k, l) for k, l in s.links.items() if hmac.compare_digest(l["token_sha"], th)]
        if not hit:
            return {"ok": False, "reason": "unknown"}
        k, l = hit[0]
        pw_ok = None if password is None else (l["pw"] is not None and hmac.compare_digest(_pw(password, bytes.fromhex(l["salt"])), l["pw"]))
        ok, why = F.share_open(l, int(s.now()), pw_ok)
        if not ok:
            if why == "expired" and not l["stopped"]:
                s._stop(l["merchant"], k, "expired")
            return {"ok": False, "reason": why}
        d = s.docs.get(l["document"])
        v = d["versions"][-1]
        s._audit(l["merchant"], l["document"], "opened", "link:" + k)
        return {"ok": True, "rights": l["rights"], "download": not l["download_blocked"], "type": d["type"], "sha256": v["sha256"],
                "data": base64.b64decode(s.blobs.get(v["sha256"])["b64"])}

    def _stop(s, m, lid, reason):
        l = s.links.get(lid)
        l["stopped"] = True
        s._emit(m, "ShareLinkStopped", {"link_id": lid, "reason": reason})
        s._audit(m, l["document"], "share_stopped", reason)

    def stop_link(s, m, lid):
        l = s.links.get(lid)
        if not l or l["merchant"] != m:
            raise KeyError("no such link")
        s._stop(m, lid, "owner")

    # ---- signing ---------------------------------------------------------------------------------------------------------------
    def request_signatures(s, m, doc_id, by, signers, level="simple", order="in_order", country=None):
        """signers: their names and contacts as given; they go straight to the vault. Returns one private link token per signer."""
        d = s._doc(m, doc_id)
        if not 1 <= len(signers) <= F.FILES["signing"]["max_signers"]:
            raise ValueError("between one and {} signers".format(F.FILES["signing"]["max_signers"]))
        F.next_signers(order, ["x"], [])
        partner = F.level_partner(level)
        if partner:
            from providers import ready
            if not ready(partner, country or s._country(m))[0]:
                raise PermissionError("Coming to your country soon.")
        cap = s.ent(m).get("signature_requests")
        month = time.strftime("%Y-%m", time.gmtime(s.now()))
        sent = sum(1 for _, r in s.requests.items() if r["merchant"] == m and r["month"] == month)
        if cap is not None and sent >= cap:
            raise PermissionError("signature requests used up for this LynkFiles plan this month")
        rid = uuid7()
        refs, tokens = [], []
        for i, who in enumerate(signers, 1):
            ref = "vault:" + s.p.vault.put(f"{rid}|{i}", "signer", who)
            tok = secrets.token_urlsafe(24)
            s.tokens.put(_sha(tok.encode()), {"request": rid, "turn": i})
            refs.append(ref); tokens.append(tok)
        days = F.FILES["signing"]["link_days"]
        s.requests.put(rid, {"merchant": m, "document": doc_id, "sha256": d["versions"][-1]["sha256"], "level": level, "order": order,
                             "signers": [str(i) for i in range(1, len(signers) + 1)], "refs": refs, "signed": [], "pending": [], "declined": [],
                             "until": int(s.now()) + days * 86400, "month": month, "by": by})
        expires = time.strftime("%Y-%m-%d", time.gmtime(s.now() + days * 86400))
        s._emit(m, "SignatureRequested", {"request_id": rid, "document_id": doc_id, "level": level, "order": order, "signers": len(signers), "expires_on": expires})
        s._audit(m, doc_id, "signature_requested", by)
        return rid, tokens

    def _req_for(s, token):
        t = s.tokens.get(_sha(token.encode()))
        if not t:
            raise PermissionError("this signing link is not valid")
        return t["request"], t["turn"], s.requests.get(t["request"])

    def state(s, rid):
        r = s.requests.get(rid)
        return F.request_state(r["signers"], r["signed"], r["declined"], int(s.now()) >= r["until"])

    def sign(s, token, seen_sha256):
        """The signer signs the version they saw. Simple: written now. Identity-checked or qualified: sent to the partner and written
        only when the partner confirms (partner_answer)."""
        rid, turn, r = s._req_for(token)
        st = s.state(rid)
        if st not in ("sent", "partly_signed"):
            raise PermissionError(f"this request is {st}")
        if str(turn) not in F.next_signers(r["order"], r["signers"], r["signed"], r["declined"]):
            raise PermissionError("not your turn yet")
        if seen_sha256 != r["sha256"]:
            raise ValueError("the document changed; open it again before signing")
        if str(turn) in r["pending"]:
            return "waiting_for_partner"
        if r["level"] == "simple":
            s._signed(rid, turn)
            return s.state(rid)
        ref = r["refs"][turn - 1]
        ans = s.identity.check(rid, turn, ref, None) if r["level"] == "identity_checked" else s.qualified.sign(rid, turn, r["sha256"], ref)
        if not ans.get("ok"):
            raise ValueError(ans.get("reason", "the partner refused"))
        r["pending"] = r["pending"] + [str(turn)]
        return "waiting_for_partner"

    def partner_answer(s, rid, turn, confirmed):
        """Cloud only: the signing partner's answer for one signer."""
        r = s.requests.get(rid)
        if str(turn) not in r["pending"]:
            raise ValueError("nothing waiting for this signer")
        r["pending"] = [t for t in r["pending"] if t != str(turn)]
        if confirmed:
            s._signed(rid, turn)
        return s.state(rid)

    def _signed(s, rid, turn):
        r = s.requests.get(rid)
        m = r["merchant"]
        r["signed"] = r["signed"] + [str(turn)]
        s._emit(m, "DocumentSigned", {"request_id": rid, "turn": turn, "level": r["level"]})
        s._audit(m, r["document"], "signed", f"signer {turn}")
        if s.state(rid) == "completed":
            code = F.format_code(secrets.randbits(60))
            s.codes.put(_sha(code.encode()), {"request": rid, "sha256": r["sha256"], "signers": len(r["signers"]), "level": r["level"]})
            s._emit(m, "SignatureCompleted", {"request_id": rid, "document_id": r["document"], "signed_sha256": r["sha256"], "code_sha256": _sha(code.encode())})
            r["code"] = code
        return r

    def code_for(s, m, rid):
        r = s.requests.get(rid)
        if not r or r["merchant"] != m:
            raise KeyError("no such request")
        return r.get("code")

    def decline(s, token, reason="declined"):
        rid, turn, r = s._req_for(token)
        if s.state(rid) not in ("sent", "partly_signed"):
            raise PermissionError("this request is no longer open")
        r["declined"] = r["declined"] + [str(turn)]
        s._emit(r["merchant"], "SignatureDeclined", {"request_id": rid, "turn": turn, "reason": reason})
        s._audit(r["merchant"], r["document"], "declined", f"signer {turn}")

    @staticmethod
    def check_code_shape(code):
        return F.code_ok(code)

    def verify(s, code):
        """Anyone can check a code: the signed fingerprint, how many signed and the level; never who."""
        if not F.code_ok(code):
            return {"ok": False, "reason": "not_a_code"}
        c = s.codes.get(_sha(code.upper().encode()))
        if not c:
            return {"ok": False, "reason": "unknown"}
        return {"ok": True, "sha256": c["sha256"], "signers": c["signers"], "level": c["level"], "state": "completed"}
