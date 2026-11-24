"""The business side of the one message engine (CONNECT UPDATE 71.7; catalog/messages.v1.json "system"; section 4 row 71.9).

Urgent broadcast with who has seen it in the app; reply by text (YES and STOP); reply by email into the record's own place;
email-in boxes (bills to a LynkAcc draft, documents to LynkFiles, CVs to LynkJobs in 8B); wording edits within safe limits with
a preview in every language; test mode (a new or edited wording goes only to the owner until approved); optional messages at a
good local time; results as totals only; the fair-use guard; linked corrections; cost previews and the country's sender name.

Everything is sent through services/messages.py Notifier; nothing here talks to a channel. The words a person writes are kept
only here and in the receiver's message, never in an event (only their sha256). Reply tokens and allowed email-in senders are
kept only as lookup digests (core/secrethash.py)."""
import hashlib, json, os, re, secrets, time, uuid
from core import regions, secrethash
from core import files as F
from core.locale import local_dt
from services import messages as M
from services import translation as TR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS = M.SYS
with open(os.path.join(ROOT, "catalog", "contacts.v1.json"), encoding="utf-8") as _f:
    PATTERNS = {p["id"]: p["address"] for p in json.load(_f)["patterns"]}
FILL_IN = re.compile(r"\{[a-z_]+\}")
NEVER_EDITED = ("security", "safety", "legal")
OWNER_ROLES = ("owner", "manager")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _day(now):
    return time.strftime("%Y-%m-%d", time.gmtime(now))


SECRET_IN_TEXT = re.compile(r"\b(pin|password|passcode|otp|code|cvv|cvc)\b\W{0,3}\d", re.I)


def check_text(text):
    """Words a person types into a message: the never-in-a-message rules, and no secret written next to its digits."""
    M.check_content({"text": text})
    if SECRET_IN_TEXT.search(text):
        raise ValueError("a PIN, password or code is never sent in a message")
    return True


def wording_kinds():
    """The customer messages a business may reword: customer audience, a transaction or opt-in basis, never security,
    safety or legal."""
    w = SYS["wording"]
    return [k["id"] for k in M.REG["kinds"] if k["audience"] in w["audiences"] and k["basis"] in w["bases"]
            and k["basis"] not in NEVER_EDITED and k["area"] not in NEVER_EDITED]


def check_wording(text):
    """The safe limits of an edited wording: length, only known placeholders, the required ones kept, nothing a message may
    never carry (secrets, card numbers, positions, links outside the app)."""
    w = SYS["wording"]
    text = (text or "").strip()
    if not text:
        return "empty"
    if len(text) > w["max_chars"]:
        return "too_long"
    used = set(FILL_IN.findall(text))
    if used - set(w["placeholders"]):
        return "unknown_placeholder"
    if set(w["required"]) - used:
        return "missing_placeholder"
    try:
        check_text(text)
    except ValueError:
        return "not_allowed"
    if re.search(r"https?://|www\.", text):
        return "not_allowed"                               # links in customer messages come only from the record, never typed
    return None


class MessageDesk:
    def __init__(s, platform, notifier=None, engine=None):
        s.p = platform
        s.n = notifier or getattr(platform, "notifier", None) or M.Notifier()
        s.engine = engine or TR.SandboxTranslator()
        s.on_yes = {}                       # message kind -> callback(person, business, record) for a YES reply
        s.land = None                       # callback(where, record, business, text) for an email reply; default keeps a thread
        s.on_shift = None                   # callback(business) -> people checked in now (LynkAttend)
        s.broadcasts, s.wordings, s.tokens, s.threads = {}, {}, {}, {}
        s.senders, s.held, s.drafts, s.daily, s.stops, s.warned = {}, {}, {}, {}, {}, {}
        s.scheduled = []

    def _emit(s, m, type_, payload):
        store = getattr(getattr(s.p, "c", None), "store", None)
        if store is not None:
            store.append(m, "server", type_, payload)

    def _people_now(s, m, holders):
        return s.on_shift(m) if s.on_shift else None

    # ---- urgent broadcast
    def broadcast(s, m, by, by_role, audience, people, text, now, lang="en", contacts=None, cost_seen=False, country=None):
        b = SYS["broadcast"]
        if by_role not in b["senders"]:
            raise PermissionError("only the owner or a manager sends an urgent broadcast")
        if audience not in b["audiences"]:
            raise ValueError("unknown audience")
        text = (text or "").strip()
        if not text or len(text) > b["max_chars"]:
            raise ValueError("a broadcast has 1 to %d characters" % b["max_chars"])
        check_text(text)
        people = list(dict.fromkeys(people))
        if not people:
            raise ValueError("nobody to send to")
        day = (m, _day(now))
        if s.daily.get(("bc",) + day, 0) >= b["per_day"]:
            return {"state": "refused", "reason": "per_day"}
        contacts = contacts or {}
        if not cost_seen:                                   # cost-aware: texts and calls are shown before they are spent
            first = [s.n.first_outside(b["kind"], p, contacts.get(p, ("bell", "push", "email", "text")), now) for p in people]
            preview = s.n.cost_preview(first, country)
            if preview:
                return {"state": "confirm_cost", "preview": preview}
        s.daily[("bc",) + day] = s.daily.get(("bc",) + day, 0) + 1
        bid = uuid.uuid4().hex
        eid = f"broadcast:{bid}"
        nids = {}
        for p in people:
            r = s.n.notify(b["kind"], p, eid, now, business=m, record=bid, lang=lang,
                           contacts=contacts.get(p, ("bell", "push", "email", "text")))
            if r.get("nid"):
                nids[p] = r["nid"]
        s.broadcasts[bid] = {"merchant": m, "by": by, "audience": audience, "people": people, "nids": nids, "text": text, "at": now}
        s._emit(m, "UrgentBroadcastSent", {"broadcast_id": bid, "audience": audience, "count": len(people), "text_sha256": _sha(text), "by": by})
        return {"state": "sent", "broadcast_id": bid, "count": len(people)}

    def seen(s, m, bid):
        """Who has seen it, from the app's own read state only (never email or text opens)."""
        b = s.broadcasts.get(bid)
        if not b or b["merchant"] != m:
            raise KeyError("no such broadcast")
        yes = [p for p, nid in b["nids"].items() if s.n.lines[nid]["seen"] or s.n.lines[nid]["read"]]
        return {"seen": yes, "not_seen": [p for p in b["people"] if p not in yes], "count": len(b["people"])}

    # ---- reply by text
    def reply_text(s, person, business, body, now):
        word = re.sub(r"[^A-Za-z0-9]", "", (body or "")).upper()
        rt = SYS["reply_text"]
        if word in rt["stop"]:
            s.n.stop(person, business)
            s.stops[business] = s.stops.get(business, 0) + 1
            s._emit(business, "MessageStopped", {"business": business})
            s._fair_use(business, now)
            return {"state": "stopped"}
        if word in rt["yes"]:
            open_ = [l for l in s.n.lines.values() if l["person"] == person and l["business"] == business and not l["done_by"]
                     and set(M.KINDS[l["kind"]]["actions"]) & set(rt["yes_actions"]) and M.KINDS[l["kind"]]["audience"] in rt["yes_audiences"]]
            if not open_:
                return {"state": "nothing_to_confirm"}
            l = max(open_, key=lambda x: x["at"])
            cb = s.on_yes.get(l["kind"])
            result = cb(person, business, l["record"]) if cb else None
            s.n.act(l["nid"], person, channel="text", now=now)
            s._emit(business, "MessageReplied", {"channel": "text", "lands_in": l["kind"], "record": l["record"], "text_sha256": _sha(word)})
            return {"state": "confirmed", "kind": l["kind"], "record": l["record"], "result": result}
        return {"state": "help", "words": {"yes": rt["yes"][0], "stop": rt["stop"][0]}}

    # ---- reply by email
    def reply_address(s, m, record, now):
        """The Reply-To of an email about a record: a random token kept only as a lookup digest."""
        tok = secrets.token_urlsafe(18)
        s.tokens[secrethash.lookup_digest(tok)] = {"merchant": m, "record": record, "until": now + SYS["reply_email"]["token_days"] * 86400}
        return PATTERNS["reply"].replace("{token}", tok)

    def reply_email(s, token, text, now):
        t = s.tokens.get(secrethash.lookup_digest(token or ""))
        if not t or now > t["until"]:
            return {"state": "refused", "reason": "unknown_or_old_address"}
        prefix = (t["record"] or "").split("-")[0]
        where = SYS["reply_email"]["lands_in"].get(prefix, SYS["reply_email"]["else"])
        if s.land:
            s.land(where, t["record"], t["merchant"], text)
        else:
            s.threads.setdefault((t["merchant"], t["record"]), []).append({"from": "email", "at": now, "text": text})
        s._emit(t["merchant"], "MessageReplied", {"channel": "email", "lands_in": where, "record": t["record"], "text_sha256": _sha(text or "")})
        return {"state": "landed", "lands_in": where, "record": t["record"]}

    def thread(s, m, record):
        return list(s.threads.get((m, record), ()))

    # ---- email-in
    def email_in_address(s, username, box):
        if box not in SYS["email_in"]["boxes"]:
            raise ValueError("unknown box")
        return PATTERNS[f"email_in_{box}"].replace("{username}", username)

    def allow_sender(s, m, email):
        s.senders.setdefault(m, set()).add(secrethash.lookup_digest(email.strip().lower()))

    def email_in(s, m, box, sender_email, attachments, now, by="email_in"):
        cfg = SYS["email_in"]["boxes"].get(box)
        if not cfg:
            raise ValueError("unknown box")
        attachments = list(attachments or [])
        if len(attachments) > SYS["email_in"]["max_attachments"]:
            return {"state": "refused", "reason": "too_many_attachments"}
        from core import build_sections
        if build_sections.status(cfg["build_section"]) not in ("locked", "building"):   # CVs wait for LynkJobs (8B)
            s._emit(m, "EmailInReceived", {"box": box, "state": "planned", "attachments": len(attachments), "draft": None})
            return {"state": "planned", "build_section": cfg["build_section"]}
        if secrethash.lookup_digest((sender_email or "").strip().lower()) not in s.senders.get(m, ()):
            hid = uuid.uuid4().hex
            s.held.setdefault(m, {})[hid] = {"box": box, "attachments": attachments, "at": now}
            s._tell_owner(m, "email_in_arrived", hid, now, {"state": "held"})
            s._emit(m, "EmailInReceived", {"box": box, "state": "held", "attachments": len(attachments), "draft": None})
            return {"state": "held", "held_id": hid}
        return s._file(m, box, cfg, attachments, now, by)

    def release(s, m, hid, by, allow=False, sender_email=None):
        """The owner lets a held email through (and may allow its sender from now on)."""
        h = s.held.get(m, {}).pop(hid)
        if allow and sender_email:
            s.allow_sender(m, sender_email)
        return s._file(m, h["box"], SYS["email_in"]["boxes"][h["box"]], h["attachments"], h["at"], by)

    def _file(s, m, box, cfg, attachments, now, by):
        kept, refused = [], []
        draft = uuid.uuid4().hex if box == "bills" else None
        for data in attachments:
            kind = F.sniff(data)
            if kind in (None, "blocked"):
                refused.append("blocked" if kind == "blocked" else "unknown_type")
                continue
            try:
                kept.append(s.p.files.store(m, by, cfg["record_kind"], draft or "inbox", cfg["kind"], data))
            except (ValueError, PermissionError) as e:
                refused.append(str(e))
        if not kept:
            return {"state": "refused", "reasons": refused}
        if draft:
            s.drafts.setdefault(m, {})[draft] = {"documents": kept, "at": now, "state": "draft"}
        s._tell_owner(m, "email_in_arrived", draft or kept[0], now, {"state": "draft" if draft else "filed"})
        s._emit(m, "EmailInReceived", {"box": box, "state": "draft" if draft else "filed", "attachments": len(kept), "draft": draft})
        return {"state": "draft" if draft else "filed", "draft": draft, "documents": kept, "refused": refused}

    def complete_draft(s, m, draft, by, total_minor, **kw):
        """A person completes a draft bill: it becomes a real bill in LynkAcc (and still needs someone else to approve it)."""
        d = s.drafts[m][draft]
        if d["state"] != "draft":
            raise ValueError("this draft is already a bill")
        bill = s.p.books.record_bill(m, by, total_minor, source="email", bill_id=draft, **kw)
        d["state"] = "bill"
        return bill

    def _tell_owner(s, m, kid, record, now, facts):
        owner = getattr(s.p, "owner_of", lambda m: m)(m)
        s.n.notify(kid, owner, f"{kid}:{record}", now, business=m, record=record, role="owner", facts=facts)

    # ---- wording edits and test mode
    def edit_wording(s, m, by, by_role, kind, text, now, languages=None):
        if by_role not in OWNER_ROLES:
            raise PermissionError("only the owner or a manager edits message wording")
        if kind not in wording_kinds():
            raise ValueError("this message's words cannot be changed")
        why = check_wording(text)
        if why:
            return {"state": "refused", "reason": why}
        langs = languages or list(TR.languages())
        preview, kept = {"en": text.strip()}, []
        for lang in langs:
            if lang == "en":
                continue
            out, err, _ = TR.run(s.engine, [text.strip()], "en", lang)[0]
            if err or check_wording(out):
                kept.append(lang)                          # that language keeps the standard words
            else:
                preview[lang] = out
        s.wordings[(m, kind)] = {"text": text.strip(), "preview": preview, "standard_kept": kept, "state": "testing", "by": by, "at": now}
        s._emit(m, "MessageWordingTested", {"kind": kind, "lang": "en", "text_sha256": _sha(text.strip()), "by": by})
        s._tell_owner(m, "message_wording_test", kind, now, {"kind": kind})
        return {"state": "testing", "preview": preview, "standard_kept": kept}

    def approve_wording(s, m, kind, by, by_role):
        if by_role != "owner":
            raise PermissionError("only the owner approves a wording")
        w = s.wordings[(m, kind)]
        w["state"] = "live"
        s._emit(m, "MessageWordingApproved", {"kind": kind, "by": by})
        return {"state": "live"}

    def reset_wording(s, m, kind, by_role):
        if by_role not in OWNER_ROLES:
            raise PermissionError("only the owner or a manager edits message wording")
        s.wordings.pop((m, kind), None)
        return {"state": "standard"}

    def words_for(s, m, kind, lang):
        w = s.wordings.get((m, kind))
        if not w or w["state"] != "live":
            return None                                    # the standard words
        return w["preview"].get(lang)

    # ---- sending a customer message (test mode, good time, fair use)
    def send_customer(s, m, kid, customer, event_id, now, lang="en", country=None, consent=False, record=None, facts=None,
                      contacts=("bell", "push", "email", "text")):
        k = M.Notifier.kind(kid)
        w = s.wordings.get((m, kid))
        if w and w["state"] == "testing":                  # test mode: only the owner gets it until they approve
            owner = getattr(s.p, "owner_of", lambda m: m)(m)
            return {"test": True, **s.n.notify(kid, owner, f"test:{event_id}", now, business=m, record=record, lang=lang,
                                               facts=facts, consent=True, role="owner")}
        if k["basis"] == "opt_in":
            slowed = s._fair_use(m, now)
            if slowed and s.daily.get(("opt_hour", m, int(now // 3600)), 0) >= SYS["fair_use"]["slowed_per_hour"]:
                return {"state": "slowed"}
            at = s.good_time(now, country)
            if at > now:
                s.scheduled.append({"at": at, "args": (m, kid, customer, event_id), "lang": lang, "country": country,
                                    "consent": consent, "record": record, "facts": facts, "contacts": contacts})
                return {"state": "scheduled", "at": at}
            s.daily[("opt", m, _day(now))] = s.daily.get(("opt", m, _day(now)), 0) + 1
            s.daily[("opt_hour", m, int(now // 3600))] = s.daily.get(("opt_hour", m, int(now // 3600)), 0) + 1
        return s.n.notify(kid, customer, event_id, now, business=m, record=record, lang=lang, country=country,
                          consent=consent, facts=facts, contacts=contacts)

    def due(s, now):
        """Send the optional messages whose good time has come."""
        out, keep = [], []
        for job in s.scheduled:
            if job["at"] <= now:
                m, kid, customer, eid = job["args"]
                out.append(s.send_customer(m, kid, customer, eid, now, job["lang"], job["country"], job["consent"],
                                           job["record"], job["facts"], job["contacts"]))
            else:
                keep.append(job)
        s.scheduled = keep
        return out

    @staticmethod
    def good_time(now, country):
        """Now, if it is between 09:00 and 18:00 in the receiver's country; otherwise the next 10:00 there."""
        if not country:
            return now
        g = SYS["good_time"]
        h = local_dt(time.strftime(M.FMT, time.gmtime(now)), country).hour
        if g["window"][0] <= h < g["window"][1]:
            return now
        t = int(now // 3600 + 1) * 3600
        for _ in range(48):
            if local_dt(time.strftime(M.FMT, time.gmtime(t)), country).hour == g["send_at"]:
                return t
            t += 3600
        return now

    def _fair_use(s, m, now):
        f = SYS["fair_use"]
        sent = s.daily.get(("opt", m, _day(now)), 0)
        total = sum(1 for l in s.n.lines.values() if l["business"] == m and M.KINDS[l["kind"]]["basis"] == "opt_in")
        stops = s.stops.get(m, 0)
        rate = (stops * 10000 // total) if total else 0
        reason = "too_many" if sent >= f["daily_optional"] else ("stops" if total >= f["min_sample"] and rate >= f["stop_rate_bp"] else None)
        if reason and s.warned.get(m) != _day(now):
            s.warned[m] = _day(now)
            s._tell_owner(m, "fair_use_warning", _day(now), now, {"reason": reason})
            s._emit(m, "FairUseWarned", {"reason": reason, "sent_today": sent, "stop_rate_bp": rate})
        return reason

    # ---- results, corrections, cost and sender name
    def results(s, m):
        """Totals by kind (sent, delivered, failed, acted on); below min_shown a total is not shown; nothing per person."""
        out = {}
        for l in s.n.lines.values():
            if l["business"] != m or str(l["person"]).startswith("inbox:"):
                continue
            t = out.setdefault(l["kind"], {"sent": 0, "delivered": 0, "failed": 0, "acted": 0})
            t["sent"] += 1
            st = l.get("state")
            t["delivered"] += st == "confirmed"
            t["failed"] += st == "failed"
            t["acted"] += bool(l["done_by"])
        lo = SYS["results"]["min_shown"]
        return {k: {n: (v if v >= lo else None) for n, v in t.items()} for k, t in out.items()}

    def correct(s, m, by, nid, text, now):
        c = SYS["corrections"]
        l = s.n.lines.get(nid)
        if not l or l["business"] != m:
            raise PermissionError("only the business that sent a message corrects it")
        if l.get("corrected_by"):
            return {"state": "refused", "reason": "already_corrected"}
        text = (text or "").strip()
        if not text or len(text) > SYS["wording"]["max_chars"]:
            raise ValueError("a correction has 1 to %d characters" % SYS["wording"]["max_chars"])
        check_text(text)
        r = s.n.notify(c["kind"], l["person"], f"correct:{nid}", now, business=m, record=l["record"], lang=l.get("lang", "en"),
                       contacts=tuple(ch for ch in l["channels"] if ch != "call") or ("bell",))
        if r.get("nid"):
            s.n.lines[r["nid"]]["corrects"] = nid
            l["corrected_by"] = r["nid"]
        s._emit(m, "MessageCorrected", {"nid": nid, "correction_nid": r.get("nid"), "record": l["record"], "text_sha256": _sha(text), "by": by})
        return {"state": "sent", "nid": r.get("nid")}

    @staticmethod
    def sender_name(business_name, country):
        """A text shows the business's own name only where the country pack confirms it may register one."""
        pack = regions.country(country) if country else {}
        return business_name if (pack.get("messages") or {}).get("own_sender_name") is True else "LynkOmni"
