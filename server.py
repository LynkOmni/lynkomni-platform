"""Minimal JSON API (stdlib only). NO AUTHENTICATION YET: add auth before any real use."""
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from core.regions import country, resolve_country
from services.platform import Platform, ServiceOff

P = Platform(os.environ.get("LYNK_DB", "lynkomni.db"))

class H(BaseHTTPRequestHandler):
    def _send(s, code, obj):
        b = json.dumps(obj).encode()
        s.send_response(code); s.send_header("Content-Type", "application/json"); s.send_header("Content-Length", str(len(b))); s.end_headers(); s.wfile.write(b)
    def do_GET(s):
        u = urlparse(s.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/v1/dashboard":
            s._send(200, P.dashboard.view(q["merchant"], q.get("currency")))
        elif u.path == "/v1/config":
            code = resolve_country(float(q["lat"]) if "lat" in q else None, float(q["lon"]) if "lon" in q else None, q.get("country"))
            s._send(200, {"country": code, **{k: v for k, v in country(code).items() if k != "bbox"}})
        else:
            s._send(404, {"error": "not found"})
    def do_POST(s):
        try:
            body = json.loads(s.rfile.read(int(s.headers.get("Content-Length", 0))) or b"{}")
            if s.path == "/v1/register":
                s._send(200, P.register(body["merchant"], body.get("country"), body.get("lat"), body.get("lon")))
            elif s.path == "/v1/sync":
                s._send(200, P.sync(body["merchant"], body["device"], body.get("events", []), body.get("cursor", 0)))
            else:
                s._send(404, {"error": "not found"})
        except ServiceOff as e:
            s._send(403, {"error": str(e)})
        except (KeyError, ValueError) as e:
            s._send(400, {"error": f"bad request: {e}"})

if __name__ == "__main__":
    print("LynkOmni API on http://localhost:8080"); HTTPServer(("", 8080), H).serve_forever()
