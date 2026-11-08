"""The shared username check (blueprint 44 B; Step 0): one rule for every username in LynkOmni.
The rule lives in contract/usernames.v1.json; the product and brand names come from the catalog and the partner names from
the provider ledger, so nothing is typed here twice. A username is never reissued: UsernameRegistry keeps a released or
changed username reserved to its owner forever and redirects old links to the new one."""
import calendar, json, os, re, time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(*parts):
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


RULE = _load("contract", "usernames.v1.json")
PATTERN = re.compile(RULE["pattern"])
MIN, MAX = RULE["min"], RULE["max"]
_LOOK = RULE["look_alike_map"]


def _product_and_brand_words():
    words = set(RULE["reserved_words"])
    for p in _load("catalog", "products.v1.json")["products"]:
        fam = p["family"]
        words.add(fam)
        if fam.startswith("lynk"):
            words.add(fam[4:])                       # "pos", "acc", "inv", "crm", "stat", "suite", "chat" ...
    for h in _load("catalog", "addresses.v1.json")["hosts"]:
        words.add(h["host"].split(".")[0])
    return words


_GENERIC = frozenset("""ad and bank card cash country demand dispute edge evidence exchange file financing foreign fulfilment handoff
    insurance issuer licensed location lookup malware marketplace measurement merchant logos network nearby network partner payments
    payout physical companion kyc provider push delivery email rates relay scanning sms split sponsor storage suppliers tokens
    transfer transport virtual acquirer access lounge perks protection purchase travel bin cdn money mobile pay airline aggregator registration gateway
    bus coach tickets train rail operator operators hotel hotels stays homes car rental local events cinema ferry appointments
    airtime data bills electricity water gas tv streaming education vouchers esim internet credit domestic international online
    offline remittance remittances government gateway gateways lender lenders insurers banks authority tax office booking bookings
    provider providers flight flights ticket ticketing utility model models cloud hardware supplier auditor auditors and or of the
    for with via per""".split())


def _partner_words():
    """Every brand word in a provider-ledger partner name, signed or not (a name taken before the partner signs is as bad)."""
    out = set()
    for item in _load("providers", "registry.v1.json")["items"]:
        for tok in re.findall(r"[a-z0-9]+", item["name"].lower().replace("-", "")):
            if len(tok) >= 3 and tok not in _GENERIC:
                out.add(tok)
        full = re.sub(r"[^a-z0-9]", "", item["name"].lower())
        if len(full) >= 3:
            out.add(full)
    return out


RESERVED = frozenset(_product_and_brand_words() | _partner_words())


def skeleton(name):
    """What a username looks like at a glance: look-alike letters and separators folded away."""
    s = name.lower()
    for a, b in sorted(_LOOK.items(), key=lambda kv: -len(kv[0])):
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s)


_RESERVED_SKELETONS = {skeleton(w): w for w in RESERVED}


def normalize(value):
    """Not case-sensitive: the stored form is lowercase without a leading @ or spaces around it."""
    return (value or "").strip().lstrip("@").lower()


def check(value):
    """{'ok': bool, 'username': normalized, 'reason': ...}. Reasons: empty, too_short, too_long, bad_character,
    leading_or_trailing_dot, double_dot, web_address_ending, reserved_word, held_for_review (look-alike of a reserved word)."""
    u = normalize(value)
    if not u:
        return {"ok": False, "username": u, "reason": "empty"}
    if len(u) < MIN:
        return {"ok": False, "username": u, "reason": "too_short"}
    if len(u) > MAX:
        return {"ok": False, "username": u, "reason": "too_long"}
    if re.search(r"[^a-z0-9._]", u):
        return {"ok": False, "username": u, "reason": "bad_character"}
    if u.startswith(".") or u.endswith("."):
        return {"ok": False, "username": u, "reason": "leading_or_trailing_dot"}
    if ".." in u:
        return {"ok": False, "username": u, "reason": "double_dot"}
    assert PATTERN.match(u)
    for ending in RULE["reserved_endings"]:
        if u.endswith(ending):
            return {"ok": False, "username": u, "reason": "web_address_ending"}
    plain = u.replace(".", "").replace("_", "")
    if u in RESERVED or plain in RESERVED:
        return {"ok": False, "username": u, "reason": "reserved_word"}
    sk = skeleton(u)
    if sk in _RESERVED_SKELETONS and len(sk) >= 3:
        return {"ok": False, "username": u, "reason": "held_for_review", "looks_like": _RESERVED_SKELETONS[sk]}
    return {"ok": True, "username": u, "reason": None}


def suggestions(value, taken=lambda u: False, limit=3):
    """Free usernames close to a wanted one: the app shows these when the wanted one is taken or refused."""
    base = re.sub(r"[^a-z0-9._]", "", normalize(value).replace(" ", ".")).strip("._") or "shop"
    base = re.sub(r"\.\.+", ".", base)[:MAX - 4]
    out = []
    for cand in (base, f"{base}.shop", f"{base}_1", f"{base}.store", f"{base}.2", f"the.{base}", f"{base}.official"[:MAX]):
        c = check(cand)
        if c["ok"] and not taken(c["username"]) and c["username"] not in out:
            out.append(c["username"])
        if len(out) >= limit:
            break
    return out


class UsernameRegistry:
    """Who owns which username, forever. In production the cloud alone writes this (a username is taken in the cloud);
    this reference keeps the rules: free before taken, one owner, never reissued, old names redirect to the new one."""
    REDIRECT_DAYS_AFTER_DISPUTE = 90

    def __init__(self):
        self.owners = {}      # username -> {"owner": public id, "kind": shop|business|person|app|partner|agent_point, "since": ts}
        self.redirects = {}   # old username -> {"to": new username, "owner": id, "until": ts or None}

    def status(self, value):
        u = normalize(value)
        c = check(u)
        if not c["ok"]:
            return c["reason"]
        if u in self.owners:
            return "taken"
        if u in self.redirects:
            return "reserved"      # released by its owner; only that owner may take it again
        return "available"

    def take(self, value, owner, kind, now=None):
        u = normalize(value)
        c = check(u)
        if not c["ok"]:
            raise ValueError(c["reason"])
        if u in self.owners:
            raise ValueError("taken")
        if u in self.redirects and self.redirects[u]["owner"] != owner:
            raise ValueError("never_reissued")      # it belonged to someone else once; it is theirs forever
        self.redirects.pop(u, None)
        self.owners[u] = {"owner": owner, "kind": kind, "since": now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        return u

    def change(self, owner, old, new, now=None):
        """The owner picks a new username. The old one redirects to the new one for ever and can never go to anyone else."""
        old, new = normalize(old), normalize(new)
        if self.owners.get(old, {}).get("owner") != owner:
            raise ValueError("not_owner")
        kind = self.owners[old]["kind"]
        self.take(new, owner, kind, now)
        del self.owners[old]
        self.redirects[old] = {"to": new, "owner": owner, "until": None}
        for o, r in self.redirects.items():          # older names follow the chain to the newest
            if r["to"] == old:
                r["to"] = new
        return new

    def release(self, owner, value):
        u = normalize(value)
        if self.owners.get(u, {}).get("owner") != owner:
            raise ValueError("not_owner")
        del self.owners[u]
        self.redirects[u] = {"to": None, "owner": owner, "until": None}

    def transfer_by_dispute(self, value, new_owner, kind, staff_id, reason, now):
        """A trademark claim decided by staff (through safety@): the reason is recorded and the old owner keeps a redirect
        for 90 days. This is the only way a username ever moves between owners."""
        u = normalize(value)
        old = self.owners.get(u)
        if not old:
            raise ValueError("unknown")
        until = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(calendar.timegm(time.strptime(now, "%Y-%m-%dT%H:%M:%SZ")) + 86400 * self.REDIRECT_DAYS_AFTER_DISPUTE))
        record = {"username": u, "from": old["owner"], "to": new_owner, "staff": staff_id, "reason": reason, "at": now, "old_owner_redirect_until": until}
        self.owners[u] = {"owner": new_owner, "kind": kind, "since": now}
        return record

    def resolve(self, value):
        """Where a link or QR with this username lands: the owner, or the newest username it redirects to, or None."""
        u = normalize(value)
        seen = set()
        while u in self.redirects and u not in seen:
            seen.add(u)
            u = self.redirects[u]["to"]
            if u is None:
                return None
        return {"username": u, **self.owners[u]} if u in self.owners else None
