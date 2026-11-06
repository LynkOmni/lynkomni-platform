"""LynkOmni brand assets (logo, wordmark, emblem) as the platform uses them.

The artwork is made in the lynkomni-icons repo and published as @lynkomni/icons. `python -m brand.sync` copies a
release into brand/vendor and records every file's SHA-256 in brand.lock.json. Everything here reads only that
vendored copy, never the network, so the logo works offline, and every read is checked against the lock.

Rules: code asks for an asset by id and variant (brand.asset("logo", "light")). It never builds a file path or
writes a brand colour itself. See brand/check.py for the gates that enforce this."""
import base64, hashlib, json, os
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")
LOCK = os.path.join(ROOT, "brand.lock.json")
STATE = os.path.join(HERE, "state.json")
THEMES = ("light", "dark", "contrast-light", "contrast-dark")
VARIANTS = THEMES + ("mono",)


class BrandNotSynced(RuntimeError):
    """No @lynkomni/icons release has been vendored yet. Run the brand-sync workflow or `python -m brand.sync`."""


class BrandTampered(RuntimeError):
    """A vendored file does not match brand.lock.json."""


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_synced(state_path=None):
    return bool(_load(state_path or STATE).get("synced"))


def lock(lock_path=None, state_path=None):
    if not is_synced(state_path):
        raise BrandNotSynced("brand has not been synced from @lynkomni/icons yet")
    return _load(lock_path or LOCK)


def _file(rel, vendor=None, lock_path=None, state_path=None):
    """Path of a vendored file, re-checked against the lock every time it is used."""
    lk = lock(lock_path, state_path)
    if rel not in lk["files"]:
        raise KeyError(f"{rel} is not part of the brand lock")
    path = os.path.join(vendor or VENDOR, *rel.split("/"))
    if not os.path.isfile(path) or sha256_file(path) != lk["files"][rel]:
        raise BrandTampered(f"{rel} does not match brand.lock.json")
    return path


def manifest(**kw):
    with open(_file("brand.json", **kw), encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class Asset:
    id: str
    variant: str
    rel: str            # path inside the package, e.g. "svg/lynkomni-logo-light.svg"
    path: str           # absolute path of the vendored file
    sha256: str
    min_width_px: int
    accessible_name: str
    view_box: tuple


def asset(asset_id, variant, **kw):
    m = manifest(**kw)
    if asset_id not in m["assets"]:
        raise KeyError(f"unknown brand asset {asset_id!r}")
    a = m["assets"][asset_id]
    if variant not in a["variants"]:
        raise KeyError(f"unknown variant {variant!r} for {asset_id}")
    rel = a["variants"][variant]["svg"]
    path = _file(rel, **kw)
    return Asset(asset_id, variant, rel, path, sha256_file(path), a["minWidthPx"], a["accessibleName"], tuple(a["viewBox"]))


def theme_variant(theme):
    if theme not in THEMES:
        raise KeyError(f"unknown theme {theme!r}")
    return theme


def for_theme(asset_id, theme, **kw):
    return asset(asset_id, theme_variant(theme), **kw)


def svg_text(asset_id, variant, **kw):
    with open(asset(asset_id, variant, **kw).path, encoding="utf-8") as f:
        return f.read()


def data_uri(asset_id, variant, **kw):
    """For an <img src> in an HTML email or a PDF. Needs `img-src data:` in the page's content security policy."""
    raw = svg_text(asset_id, variant, **kw).encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")


def raster(rel, **kw):
    """A generated PNG/ICO such as "email/logo-light.png". Returns its verified path."""
    if not (rel.startswith("email/") or rel.startswith("web/")):
        raise KeyError("only email/ and web/ files are rasters")
    return _file(rel, **kw)


# What an invoice shows for each LynkCheckout branding tier (billing.FEATURES invoice_branding).
INVOICE_BRANDING = {
    "lynkomni": {"show_lynkomni": True, "asset": "logo", "screen": "light", "print": "mono", "merchant_logo": False},
    "logo": {"show_lynkomni": False, "asset": None, "screen": None, "print": None, "merchant_logo": True},
    "full": {"show_lynkomni": False, "asset": None, "screen": None, "print": None, "merchant_logo": True},
}


def invoice_brand(tier):
    """Which logos an invoice carries. Only the LynkOmni tier shows the LynkOmni logo; the merchant's own logo
    (uploaded as PNG, JPEG or WebP, never SVG) is handled outside this module."""
    if tier not in INVOICE_BRANDING:
        raise ValueError(f"unknown invoice branding tier {tier!r}")
    return dict(INVOICE_BRANDING[tier])


def verify(vendor=None, lock_path=None, state_path=None):
    """Returns a list of problems; empty means every vendored file matches the lock and nothing extra is present."""
    problems = []
    if not is_synced(state_path):
        return problems
    if not os.path.isfile(lock_path or LOCK):
        return ["state says synced but brand.lock.json is missing"]
    lk = _load(lock_path or LOCK)
    vdir = vendor or VENDOR
    found = set()
    for base, _, names in os.walk(vdir):
        for n in names:
            if n == ".gitkeep":
                continue
            found.add(os.path.relpath(os.path.join(base, n), vdir).replace(os.sep, "/"))
    for rel, digest in lk["files"].items():
        p = os.path.join(vdir, *rel.split("/"))
        if rel not in found:
            problems.append(f"missing vendored file {rel}")
        elif sha256_file(p) != digest:
            problems.append(f"checksum mismatch for {rel}")
    for rel in sorted(found - set(lk["files"])):
        problems.append(f"vendored file {rel} is not in brand.lock.json")
    return problems
