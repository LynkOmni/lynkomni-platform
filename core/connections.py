"""Every link between two LynkOmni services and the ten journeys that cross services (master blueprint 71.2 and 71.3), read
from catalog/connections.v1.json. Services stay loosely coupled: a link reads events or a published API, never another
service's storage. tests/test_connections.py checks both ends of every link."""
import json, os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "catalog", "connections.v1.json"), encoding="utf-8") as _f:
    _REG = json.load(_f)
LINKS = {l["id"]: l for l in _REG["links"]}
JOURNEYS = {j["id"]: j for j in _REG["journeys"]}
PLATFORM = tuple(_REG["platform"])


def links_for(service):
    """Every link that starts or ends at a service, in register order."""
    return [l for l in _REG["links"] if service in (l["from"], l["to"])]


def journey(jid):
    """The links of a journey, in order."""
    return [LINKS[i] for i in JOURNEYS[jid]["links"]]


def edges():
    """The map: (from, to) pairs, each once."""
    return sorted({(l["from"], l["to"]) for l in _REG["links"]})
