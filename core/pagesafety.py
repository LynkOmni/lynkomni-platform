"""Safe page settings for every LynkOmni page (MASTER UPDATE, master blueprint section 59; build section 1).

One policy for every page: nothing loads from anywhere else, only the page's own script runs (pinned by its SHA-256 hash, so an
injected script never runs), no plug-ins, no forms posting away, no framing by other sites. The same rules are sent as response
headers when the pages are hosted (section 14); offline single-file pages carry them as a <meta> policy, written by web/build.mjs
and tools/showcase.py. check_html() is the gate: tests/test_pagesafety.py runs it on every built page.

Styles may stay inline (screens set sizes in style attributes); scripts never may. Fonts and pictures travel inside the page as
data: addresses, so img-src and font-src allow data: and nothing else."""
import base64, hashlib, json, os, re

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "pagesafety.v1.json"), encoding="utf-8") as _f:
    _REG = json.load(_f)
DIRECTIVES = _REG["directives"]
HEADERS = _REG["headers"]          # sent with every hosted page (build section 14); frame-ancestors works only as a header

SCRIPT = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</script>", re.I)
META = re.compile(r'<meta http-equiv="Content-Security-Policy" content="(?P<csp>[^"]*)">', re.I)


def script_hash(body):
    return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode() + "'"


def policy(script_bodies):
    hashes = " ".join(script_hash(b) for b in script_bodies) or "'none'"
    return "; ".join(f"{k} {hashes if v == 'HASHES' else v}" for k, v in DIRECTIVES.items())


def meta(script_bodies):
    return f'<meta http-equiv="Content-Security-Policy" content="{policy(script_bodies)}">'


def check_html(html):
    """Problems with one built page; an empty list means it is safe to publish."""
    problems = []
    m = META.search(html)
    if not m:
        return ["no page safety policy"]
    head_end = html.lower().find("</head>")
    if m.start() > head_end or html.lower().find("<script") < m.start() and html.lower().find("<script") != -1:
        problems.append("the policy must come before any script, inside <head>")
    bodies = []
    for s in SCRIPT.finditer(html):
        if "src=" in s.group("attrs").lower():
            problems.append("a script loads from an address")
        bodies.append(s.group("body"))
    if m.group("csp") != policy(bodies):
        problems.append("the policy does not match the page's own scripts")
    if re.search(r"""<[a-z][^>]*\son[a-z]+\s*=\s*["']""", html, re.I):
        problems.append("an inline event handler (on...=) in the page")
    if re.search(r"""(?:href|src)\s*=\s*["']\s*javascript:""", html, re.I):
        problems.append("a javascript: address")
    if re.search(r"""<(?:link|img|iframe|source)[^>]+(?:href|src)\s*=\s*["']https?://""", html, re.I):
        problems.append("something loads from the web")
    return problems
