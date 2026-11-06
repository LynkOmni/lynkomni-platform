import os, re, unittest
os.environ["LYNK_MODE"] = "sandbox"
from services.platform import Platform
from services import documents as D

LINES = [{"description": "Rice <b>5kg</b>", "qty_milli": 2000, "unit_minor": 1000}, {"description": "Oil", "qty_milli": 1500, "unit_minor": 333}]
IMG = re.compile(r'<img [^>]*alt="([^"]*)"')


class T(unittest.TestCase):
    def setUp(self):
        self.p = Platform(); self.p.register("m1", "RW"); self.iv = self.p.invoicing

    def _inv(self, tier=None):
        if tier: self.p.billing.set_plan("m1", "lynkcheckout", tier)
        return self.iv.issue("m1", "Cust <script>x</script>", LINES)["id"]

    def test_free_invoice_shows_lynkomni_logo_badge_and_is_never_a_tax_invoice(self):
        h = D.invoice_html(self.p, "m1", self._inv())
        alts = IMG.findall(h)
        self.assertEqual(len(alts), 2)                                  # logo in the header, wordmark in the badge
        self.assertIn("Powered by", h); self.assertIn("not a tax invoice", h)
        self.assertNotIn("Tax invoice", h.replace("not a tax invoice", ""))
        self.assertIn("Status: Not yet paid", h)

    def test_text_is_escaped(self):
        h = D.invoice_html(self.p, "m1", self._inv())
        self.assertNotIn("<script>", h); self.assertNotIn("<b>5kg", h); self.assertIn("&lt;script&gt;", h)

    def test_paid_tier_has_no_lynkomni_logo_and_the_badge_can_be_removed(self):
        iid = self._inv("plus")
        self.assertEqual(len(IMG.findall(D.invoice_html(self.p, "m1", iid))), 1)               # only the badge, default shown
        self.assertEqual(IMG.findall(D.invoice_html(self.p, "m1", iid, merchant_removed_badge=True)), [])
        self.p.register("m2", "RW"); free = self.iv.issue("m2", "c", LINES)["id"]
        self.assertEqual(len(IMG.findall(D.invoice_html(self.p, "m2", free, merchant_removed_badge=True))), 2)   # Free cannot remove it

    def test_money_and_quantities_have_no_floats(self):
        iid = self._inv(); h = D.invoice_html(self.p, "m1", iid)
        self.assertIn("RWF 2,500", h); self.assertIn("1.5", h)
        self.assertEqual(D._qty(2000), "2"); self.assertEqual(D._qty(1500), "1.5"); self.assertEqual(D._qty(125), "0.125")

    def test_paid_is_only_claimed_after_provider_confirms(self):
        iid = self._inv("pro"); r = self.iv.inv[iid]
        with self.assertRaises(PermissionError): self.iv.record_payment("m1", iid, "mobile_money", r["total_minor"])
        self.assertIn("Not yet paid", D.invoice_html(self.p, "m1", iid))
        self.iv.record_payment("m1", iid, "mobile_money", r["total_minor"], provider_confirmed=True, payment_ref="t1")
        self.assertIn("Status: Paid", D.invoice_html(self.p, "m1", iid))

    def test_receipt_has_wordmark_header_and_never_a_badge(self):
        iid = self._inv(); self.iv.record_payment("m1", iid, "cash", self.iv.inv[iid]["total_minor"])
        h = D.receipt_html(self.p, "m1", iid, 0)
        self.assertNotIn("Powered by", h); self.assertEqual(len(IMG.findall(h)), 1)
        self.assertIn("not a tax receipt", h)
        with self.assertRaises(KeyError): D.receipt_html(self.p, "m1", iid, 1)

    def test_other_merchants_cannot_read_an_invoice(self):
        iid = self._inv(); self.p.register("m3", "RW")
        with self.assertRaises(PermissionError): D.invoice_html(self.p, "m3", iid)
        with self.assertRaises(PermissionError): D.receipt_html(self.p, "m3", iid, 0)

    def test_email_uses_png_logo_on_top_and_wordmark_below_never_together(self):
        h = D.email_html("Your invoice", ["Hello", "Thanks <3"], "dark")
        self.assertEqual(len(IMG.findall(h)), 2); self.assertEqual(h.count("data:image/png"), 2)
        self.assertLess(h.index("<header>"), h.index("<footer>")); self.assertIn("Thanks &lt;3", h)
        with self.assertRaises(ValueError): D.email_html("x", [], "contrast-light")

    def test_documents_write_no_colours(self):
        for h in (D.invoice_html(self.p, "m1", self._inv()), D.email_html("s", ["p"])):
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", re.sub(r"data:[^\"]+", "", h)))
            self.assertNotIn("color", h.lower()); self.assertNotIn("style=", h)


if __name__ == "__main__":
    unittest.main()
