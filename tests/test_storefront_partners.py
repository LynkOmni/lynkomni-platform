"""Storefront partner sandboxes (BIZZ & DEVICE, 2026-11-09): working placeholders behind interfaces, never inventing a tax
rate, never confirming a payment themselves, never storing programs or markup, questions only to the presenter."""
import unittest
from services.storefront_partners import SandboxContentStore, SandboxLiveVideo, SandboxMerchantOfRecord, SandboxTapToPay


class Partners(unittest.TestCase):
    def test_merchant_of_record_never_invents_tax(self):
        q = SandboxMerchantOfRecord().quote("XX", 1500, "XXX")
        self.assertEqual((q["tax_minor"], q["total_minor"], q["tax_status"]), (0, 1500, "unconfirmed"))
        with self.assertRaises(ValueError): SandboxMerchantOfRecord().quote("XX", 1.5, "XXX")

    def test_live_rooms_cap_seats_and_questions_go_to_the_presenter_only(self):
        v = SandboxLiveVideo(); r = v.open_room("grace", 2)
        self.assertTrue(v.join(r, "a")["ok"]); self.assertTrue(v.join(r, "b")["ok"])
        self.assertEqual(v.join(r, "c")["reason"], "room_full")
        self.assertEqual(v.ask(r, "a", "When is the next class?")["to"], "grace")
        with self.assertRaises(PermissionError): v.ask(r, "c", "hi")
        with self.assertRaises(ValueError): v.open_room("free-seller", 0)        # Free plans have no live sessions

    def test_content_by_bytes_never_programs_or_markup(self):
        s = SandboxContentStore()
        self.assertTrue(s.put("g", "notes.pdf", b"%PDF-1.7 ...", 10_000)["ok"])
        self.assertTrue(s.put("g", "clip.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8, 10_000)["ok"])
        for bad in (b"MZ\x90\x00", b"\x7fELF", b"<svg onload=x>", b"<script>alert(1)</script>", b"plain text"):
            self.assertEqual(s.put("g", "x.pdf", bad, 10_000)["reason"], "type_not_allowed")
        self.assertEqual(s.put("g", "big.pdf", b"%PDF-" + b"x" * 100, 50)["reason"], "over_plan_storage")

    def test_tap_to_pay_is_only_sent_until_the_provider_confirms(self):
        t = SandboxTapToPay().start(2500, "XXX")
        self.assertEqual((t["state"], t["confirmed_by"]), ("sent", "provider"))
        for bad in (0, -5, 2.5, True):
            with self.assertRaises(ValueError): SandboxTapToPay().start(bad, "XXX")


if __name__ == "__main__": unittest.main()
