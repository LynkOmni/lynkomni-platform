import os, struct, unittest, zlib
os.environ["LYNK_MODE"] = "sandbox"
from services import merchant_logo as M
from services import documents as D
from services.platform import Platform

LINES = [{"description": "Rice", "qty_milli": 1000, "unit_minor": 1000}]


def png(w=128, h=128, extra=b""):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00" * 8) + extra) + chunk(b"IEND", b"")


def jpeg(w=128, h=128):
    return b"\xff\xd8" + b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", h, w) + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00" + b"\xff\xd9"


def webp(w=128, h=128, animated=False):
    body = b"VP8X" + struct.pack("<I", 10) + bytes([0x02 if animated else 0, 0, 0, 0]) + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WEBP" + body


class Validate(unittest.TestCase):
    def test_accepts_png_jpeg_webp_by_content(self):
        for data, fmt in ((png(), "png"), (jpeg(), "jpeg"), (webp(), "webp")):
            info = M.validate(data)
            self.assertEqual((info["format"], info["width"], info["height"]), (fmt, 128, 128))

    def test_name_never_matters_only_bytes(self):
        self.assertEqual(M.validate(png())["format"], "png")
        with self.assertRaises(M.LogoRejected):
            M.validate(b"<svg xmlns='http://www.w3.org/2000/svg'/>")

    def test_refuses_svg_gif_html_and_script_hidden_in_an_image(self):
        for bad in (b"<svg/>", b"GIF89a" + b"\x00" * 40, b"<html></html>", png(extra=b"<script>alert(1)</script>"), png(extra=b"<svg onload=x>"), jpeg() + b"javascript:"):
            with self.assertRaises(M.LogoRejected):
                M.validate(bad)

    def test_size_and_shape_limits(self):
        for bad in (png(32, 32), png(4000, 4000), png(1000, 100), b"", None, png(extra=b"\x00" * (M.MAX_BYTES + 1))):
            with self.assertRaises(M.LogoRejected):
                M.validate(bad)

    def test_animated_and_damaged_files_are_refused(self):
        with self.assertRaises(M.LogoRejected):
            M.validate(webp(animated=True))
        with self.assertRaises(M.LogoRejected):
            M.validate(png()[:-6])
        with self.assertRaises(M.LogoRejected):
            M.validate(jpeg()[:-2])

    def test_data_uri_is_an_image_data_url(self):
        self.assertTrue(M.data_uri(png()).startswith("data:image/png;base64,"))


class OnInvoices(unittest.TestCase):
    def setUp(self):
        self.p = Platform(); self.p.register("m1", "RW")

    def test_free_tier_never_shows_the_merchant_logo(self):
        iid = self.p.invoicing.issue("m1", "c", LINES)["id"]
        h = D.invoice_html(self.p, "m1", iid, merchant_name="Shop", merchant_logo=png())
        self.assertNotIn("data:image/png", h)

    def test_paid_tier_shows_the_logo_with_the_merchant_name_as_alt_and_escapes_it(self):
        self.p.billing.set_plan("m1", "lynkcheckout", "plus")
        iid = self.p.invoicing.issue("m1", "c", LINES)["id"]
        h = D.invoice_html(self.p, "m1", iid, merchant_name='Shop "<b>"', merchant_logo=png())
        self.assertIn("data:image/png;base64,", h)
        self.assertIn('alt="Shop &quot;&lt;b&gt;&quot;"', h)

    def test_a_bad_stored_logo_is_refused_at_render_time(self):
        self.p.billing.set_plan("m1", "lynkcheckout", "plus")
        iid = self.p.invoicing.issue("m1", "c", LINES)["id"]
        with self.assertRaises(M.LogoRejected):
            D.invoice_html(self.p, "m1", iid, merchant_logo=b"<svg/>")


if __name__ == "__main__":
    unittest.main()
