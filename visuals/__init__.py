"""LynkOmni visuals: illustrations, charts, diagrams, share and store images, app and web icons.

Everything is drawn by visuals/generate.py from visuals/needs.v1.json and the design tokens, and lives in
visuals/generated. Product code asks for a visual by id and theme and never builds a file path:

    visuals.get("product-pos", "dark")        -> Visual (path, alt text, kind, sha256)
    visuals.decorative("state-offline", "light", mode="lite")   -> None in lite mode (no decorative images)
    visuals.svg_text("chart-pricing-ladder", "light")

An unknown id raises KeyError that tells you how to add it. There is never a placeholder: if a screen needs a
picture that does not exist yet, add it to needs.v1.json and run `python3 visuals/generate.py`.
All assets are drafts until a human designer has reviewed them (see needs.v1.json `status`)."""
import base64, hashlib, json, os
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATED = os.path.join(HERE, "generated")
THEMES = ("light", "dark", "contrast-light", "contrast-dark")
_CACHE = {}


class VisualsTampered(RuntimeError):
    """A generated file does not match visuals/generated/index.json. Regenerate with python3 visuals/generate.py."""


@dataclass(frozen=True)
class Visual:
    id: str
    kind: str          # illustration, chart, diagram, share, store or icon-set
    theme: str
    file: str          # path inside visuals/generated
    path: str          # absolute path
    alt: str           # the text alternative; always show it to assistive technology
    sha256: str
    decorative: bool   # true for illustrations: hidden in lite mode, and aria-hidden when the screen already says it in words


def index():
    if "index" not in _CACHE:
        with open(os.path.join(GENERATED, "index.json"), encoding="utf-8") as f:
            _CACHE["index"] = json.load(f)
    return _CACHE["index"]


def ids():
    return sorted(index()["needs"])


def _theme_for(need, theme, mode):
    if mode == "sunlight" and theme in ("light", "dark"):
        theme = "contrast-" + theme       # sunlight mode uses the high-contrast set
    have = {f["theme"] for f in need["files"]}
    if theme in have:
        return theme
    if have == {"light"}:
        return "light"                    # fixed-appearance images (link previews, store graphics)
    raise KeyError(f"no {theme} version of this visual; available: {sorted(have)}")


def get(visual_id, theme="light", mode=None, file_ext="svg"):
    idx = index()["needs"]
    if visual_id not in idx:
        raise KeyError(f"no visual {visual_id!r}: add it to visuals/needs.v1.json and run python3 visuals/generate.py (never use a placeholder)")
    need = idx[visual_id]
    th = _theme_for(need, theme, mode)
    options = [f for f in need["files"] if f["theme"] == th and f["file"].endswith("." + file_ext)]
    if not options:
        raise KeyError(f"{visual_id} has no .{file_ext} file for {th}")
    f = options[0]
    full = os.path.join(GENERATED, f["file"])
    v = Visual(visual_id, need["kind"], th, f["file"], full, need["alt"], f["sha256"], need["kind"] == "illustration")
    _verify(v)
    return v


def decorative(visual_id, theme="light", mode=None):
    """Like get(), but returns None in lite mode, which shows no decorative images (design tokens `modes.lite`)."""
    v = get(visual_id, theme, mode)
    return None if (mode == "lite" and v.decorative) else v


def alt(visual_id):
    return get(visual_id).alt


def _verify(v):
    key = ("ok", v.file)
    if key in _CACHE:
        return
    with open(v.path, "rb") as fh:
        got = hashlib.sha256(fh.read()).hexdigest()
    if got != v.sha256:
        raise VisualsTampered(f"{v.file} does not match index.json; run python3 visuals/generate.py")
    _CACHE[key] = True


def svg_text(visual_id, theme="light", mode=None):
    with open(get(visual_id, theme, mode).path, encoding="utf-8") as f:
        return f.read()


def data_uri(visual_id, theme="light", mode=None, file_ext="svg"):
    """For an <img src> in an email or PDF. Needs `img-src data:` in the page's content security policy."""
    v = get(visual_id, theme, mode, file_ext)
    with open(v.path, "rb") as f:
        raw = f.read()
    mime = {"svg": "image/svg+xml", "png": "image/png"}[file_ext]
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
