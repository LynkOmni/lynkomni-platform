"""How LynkOmni keeps secrets it must check later (CodeQL: never a plain fast hash of sensitive data).

- lookup_digest: for long random secrets that are looked up by their digest (developer API keys). HMAC-SHA256 with the
  server's own pepper (LYNK_SECRET_PEPPER), so a copied table of digests is useless without the pepper.
- code_hash / code_matches: for short codes a person types (recovery codes, one-time codes). Salted scrypt, compared in
  constant time, so a stored value never gives the code back by trying every possibility quickly.
The development pepper is for tests and sandboxes only; production sets LYNK_SECRET_PEPPER (providers later list)."""
import hashlib, hmac, os, secrets

DEV_PEPPER = "lynkomni-development-pepper-not-for-production"
SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}


def _pepper() -> bytes:
    return os.environ.get("LYNK_SECRET_PEPPER", DEV_PEPPER).encode()


def lookup_digest(secret: str) -> str:
    return hmac.new(_pepper(), secret.encode(), hashlib.sha256).hexdigest()


def code_hash(code: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(code.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${dk.hex()}"


def code_matches(code: str, stored) -> bool:
    if not isinstance(stored, str) or stored.count("$") != 2:
        return False
    kind, salt, dk = stored.split("$")
    if kind != "scrypt":
        return False
    got = hashlib.scrypt((code or "").encode(), salt=bytes.fromhex(salt), **SCRYPT)
    return hmac.compare_digest(got.hex(), dk)
