"""Payment methods are shown per country with LynkOmni icons and the provider's name as text; another company's logo is never drawn."""
import json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


class PaymentDisplay(unittest.TestCase):
    def test_no_drawn_copies_of_other_companies_logos(self):
        src = read("ts", "scripts", "preview.mjs") + read("ts", "src", "payments.ts") + read("ts", "src", "footer.ts")
        for colour in ("1a1f71", "eb001b", "f79e1b", "ffcc00", "e40000", "2ea44f", "e8742c"):   # the drawn marks used these brand colours
            self.assertNotIn(colour, src.lower())
        self.assertNotRegex(src, r"<text[^>]*>\s*(VISA|MoMo|M-PESA|airtel|UPI)\b")

    def test_every_pack_method_is_known(self):
        known = set(re.findall(r'\["([a-z_]+)", "[^"]+", "(?:card|mobile_money|bank|instant|wallet|qr|crypto)"\]', read("ts", "src", "payments.ts")))
        for f in os.listdir(os.path.join(ROOT, "contract", "country-packs")):
            pack = json.loads(read("contract", "country-packs", f))
            for m in pack.get("card_networks", []) + pack.get("wallets", []) + [p for p in pack.get("providers", []) if p != "card"]:
                self.assertIn(m, known, f"{f}: payment method {m} has no entry in ts/src/payments.ts")

    def test_official_artwork_is_a_tracked_later_item(self):
        later = {x["id"] for x in json.loads(read("providers", "registry.v1.json"))["later"]}
        self.assertIn("official_payment_marks", later)


if __name__ == "__main__":
    unittest.main()
