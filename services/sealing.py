"""Sealed batches for LynkMesh: only the intended recipient (LynkCCBox) can read them. A relay carries bytes it cannot open.
X25519 key agreement + HKDF-SHA256 + ChaCha20-Poly1305 from the `cryptography` library. Do not write your own crypto.
Production note: the recipient key must be pinned per device at enrolment and rotated; get a security review before release."""
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

INFO = b"lynkomni-mesh-v1"
_RAW = dict(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)

def generate_keypair():
    k = X25519PrivateKey.generate()
    return k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()), k.public_key().public_bytes(**_RAW)
def _key(shared, eph_pub, rcpt_pub): return HKDF(hashes.SHA256(), 32, salt=eph_pub + rcpt_pub, info=INFO).derive(shared)
def seal(plaintext: bytes, recipient_pub: bytes) -> bytes:
    eph = X25519PrivateKey.generate(); eph_pub = eph.public_key().public_bytes(**_RAW)
    key = _key(eph.exchange(X25519PublicKey.from_public_bytes(recipient_pub)), eph_pub, recipient_pub); nonce = os.urandom(12)
    return eph_pub + nonce + ChaCha20Poly1305(key).encrypt(nonce, plaintext, eph_pub + recipient_pub)
def unseal(blob: bytes, recipient_priv: bytes) -> bytes:
    priv = X25519PrivateKey.from_private_bytes(recipient_priv); rcpt_pub = priv.public_key().public_bytes(**_RAW)
    eph_pub, nonce, ct = blob[:32], blob[32:44], blob[44:]
    key = _key(priv.exchange(X25519PublicKey.from_public_bytes(eph_pub)), eph_pub, rcpt_pub)
    return ChaCha20Poly1305(key).decrypt(nonce, ct, eph_pub + rcpt_pub)
