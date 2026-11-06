"""Merchant logo upload check (Phase D). A merchant may upload their own logo for invoices on tiers that allow it.

Only PNG, JPEG and WebP are accepted, judged by the file's own bytes and never by its name. SVG, GIF, animated WebP, anything that
smells like markup or script, and files that are too large, too small or too stretched are refused. Nothing is fetched from the web and
nothing is executed: the logo is shown as a data: image with the merchant's name as text alternative.
Real storage, virus scanning and a content-delivery copy are added later (see providers/registry.v1.json); this module only decides whether bytes are safe to keep."""
import base64, struct

MAX_BYTES = 256 * 1024
MIN_SIDE, MAX_SIDE, MAX_RATIO = 64, 2048, 4.0
FORBIDDEN = (b"<svg", b"<script", b"<?xml", b"<html", b"<!doctype", b"javascript:", b"<iframe", b"<object", b"<embed")
MIME = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}


class LogoRejected(ValueError):
    """The upload is not an acceptable logo; the message is safe to show the merchant."""


def _png(b):
    if len(b) < 33 or b[12:16] != b"IHDR" or not b.rstrip(b"\x00").endswith(b"IEND\xaeB`\x82"):
        raise LogoRejected("This PNG file is damaged.")
    return struct.unpack(">II", b[16:24])


def _jpeg(b):
    if not b.rstrip(b"\x00").endswith(b"\xff\xd9"):
        raise LogoRejected("This JPEG file is damaged.")
    i = 2
    while i + 9 < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        marker = b[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xFF:
            i += 1
            continue
        seg = struct.unpack(">H", b[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        i += 2 + seg
    raise LogoRejected("This JPEG file is damaged.")


def _webp(b):
    if len(b) < 30 or struct.unpack("<I", b[4:8])[0] + 8 != len(b):
        raise LogoRejected("This WebP file is damaged.")
    kind = b[12:16]
    if kind == b"VP8X":
        if b[20] & 0x02:
            raise LogoRejected("Animated images are not allowed.")
        return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
    if kind == b"VP8 ":
        return struct.unpack("<H", b[26:28])[0] & 0x3FFF, struct.unpack("<H", b[28:30])[0] & 0x3FFF
    if kind == b"VP8L":
        bits = struct.unpack("<I", b[21:25])[0]
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    raise LogoRejected("This WebP file is not supported.")


def validate(data):
    """Returns {"format", "width", "height", "bytes"} for a safe logo, or raises LogoRejected."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise LogoRejected("Choose a PNG, JPEG or WebP image.")
    data = bytes(data)
    if len(data) > MAX_BYTES:
        raise LogoRejected(f"The logo must be {MAX_BYTES // 1024} KB or smaller.")
    low = data.lower()
    if any(x in low for x in FORBIDDEN):
        raise LogoRejected("This file contains markup or script. Use a plain PNG, JPEG or WebP image.")
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        fmt, (w, h) = "png", _png(data)
    elif data[:3] == b"\xff\xd8\xff":
        fmt, (w, h) = "jpeg", _jpeg(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        fmt, (w, h) = "webp", _webp(data)
    else:
        raise LogoRejected("Only PNG, JPEG and WebP images are allowed (not SVG or GIF).")
    if min(w, h) < MIN_SIDE or max(w, h) > MAX_SIDE:
        raise LogoRejected(f"The logo must be between {MIN_SIDE} and {MAX_SIDE} pixels on each side.")
    if max(w, h) / min(w, h) > MAX_RATIO:
        raise LogoRejected("The logo is too wide or too tall. Use a shape no more than four times longer than it is high.")
    return {"format": fmt, "width": w, "height": h, "bytes": len(data)}


def data_uri(data):
    """A data: URL for an <img>, after validating again (never trust a stored file)."""
    info = validate(data)
    return f"data:{MIME[info['format']]};base64," + base64.b64encode(bytes(data)).decode("ascii")
