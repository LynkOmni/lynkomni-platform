import copy, json, os, shutil, tempfile, unittest
import providers
from providers import check
from core import regions


class Ledger(unittest.TestCase):
    def test_repository_passes_the_gate(self):
        self.assertEqual(check.problems(), [])

    def test_every_off_by_default_service_has_a_provider_entry(self):
        self.assertEqual(check.coverage_problems(), [])
        for s in ("payments", "recovery", "paylinks", "loyalty", "marketplace", "financing", "protection", "ads", "vcard"):
            self.assertIn(s, providers.pending_services())

    def test_phase_one_services_are_never_gated(self):
        for s in ("pos", "accountant", "invoicing", "crm", "inventory", "dashboard", "intelligence", "chat"):
            self.assertEqual(providers.ready(s, "RW"), (True, []))
            self.assertTrue(regions.enabled("RW", s))

    def test_every_catalog_sub_service_is_in_the_ledger(self):
        from services import catalog
        ids = {i["id"] for i in providers.items()}
        for sid in catalog.SUBS:
            self.assertIn(f"catalog_{sid}", ids)

    def test_nothing_is_signed_yet_so_nothing_provider_dependent_is_ready(self):
        for s in providers.pending_services():
            self.assertFalse(providers.ready(s, "RW")[0], s)
        self.assertEqual([i["id"] for i in providers.items() if i["status"] != "sandbox"], [])

    def test_flag_alone_does_not_switch_a_service_on(self):
        pack = regions.COUNTRIES["RW"]
        old, mode = dict(pack["flags"]), os.environ.pop("LYNK_MODE", None)   # sandbox mode (set by other tests) turns everything on, by design
        try:
            pack["flags"]["payments"] = True
            self.assertFalse(regions.enabled("RW", "payments"))
            self.assertTrue(any("RW: payments is switched on" in p for p in check.country_problems()))
        finally:
            pack["flags"].clear(); pack["flags"].update(old)
            if mode is not None:
                os.environ["LYNK_MODE"] = mode

    def test_service_turns_on_only_when_every_provider_is_signed(self):
        reg = copy.deepcopy(providers.registry())
        old = providers._CACHE.get("r")
        try:
            for i in reg["items"]:
                if "payments" in i["used_by"]:
                    i["status"] = "contract_signed"; i["real_adapter"] = "core.providers:Simulator"
            providers._CACHE["r"] = reg
            self.assertTrue(providers.ready("payments", "RW")[0])
            self.assertTrue(providers.ready("payments", "NG")[0])   # every payments item is signed in this copy
        finally:
            providers._CACHE["r"] = old

    def test_country_status_overrides_for_one_country(self):
        reg = copy.deepcopy(providers.registry())
        old = providers._CACHE.get("r")
        try:
            m = next(i for i in reg["items"] if i["id"] == "momo_mtn")
            m["country_status"] = {"RW": "contract_signed"}
            providers._CACHE["r"] = reg
            self.assertEqual(providers.item_status(m, "RW"), "contract_signed")
            self.assertEqual(providers.item_status(m, "UG"), "sandbox")
        finally:
            providers._CACHE["r"] = old

    def test_vcard_enabled_without_issuer_is_reported(self):
        packs = {"ZZ": {"flags": {}, "vcard": {"enabled": True, "issuer": None, "bin_sponsor": None}}}
        out = " ".join(check.country_problems(packs))
        self.assertIn("vcard.enabled is true but", out)
        self.assertIn("needs issuer and bin_sponsor", out)

    def test_go_live_report_lists_providers_and_later_work(self):
        r = providers.go_live_report("vcard", "RW")
        self.assertFalse(r["may_go_live"])
        self.assertTrue(r["missing_providers"])
        self.assertTrue(any(x.startswith("security_review") for x in r["later_work"]))

    def test_off_service_shows_the_not_available_state(self):
        import visuals
        w = providers.when_off("vcard")
        self.assertEqual(w["visual"], "state-coming-soon")
        self.assertTrue(visuals.get(w["visual"]).alt)
        self.assertIn("Coming to your country soon", w["message"])


class GateCatches(unittest.TestCase):
    def test_stale_placeholder_and_missing_adapter_are_reported(self):
        reg = copy.deepcopy(providers.registry())
        reg["items"][0]["placeholders"] = [{"file": "core/providers.py", "token": "NO-SUCH-TOKEN"}]
        reg["items"][1]["interface"] = "core.providers:Nothing"
        reg["items"][2]["needed_from_provider"] = []
        reg["items"][3]["status"] = "live"
        out = " ".join(check.entry_problems(reg))
        for word in ("no longer in", "cannot be imported", "list what is needed", "needs an importable real_adapter"):
            self.assertIn(word, out)

    def test_unregistered_placeholder_is_reported(self):
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, "services"))
            with open(os.path.join(tmp, "services", "new_thing.py"), "w") as f:
                f.write("RATE = 5  # PLACEHOLDER rate\n")
            out = check.unregistered_markers(root=tmp)
            self.assertTrue(any("new_thing.py:1" in p for p in out))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


class UserActions(unittest.TestCase):
    def test_list_exists_and_is_well_formed(self):
        import copy
        from providers import check
        reg = providers.registry()
        self.assertTrue(reg["user_actions"])
        bad = copy.deepcopy(reg); bad["user_actions"].append({"id": "x", "what": "", "why": "y", "when": "z", "status": "maybe"})
        p = check.entry_problems(bad)
        self.assertTrue(any("missing what" in x for x in p) and any("open, done or dropped" in x for x in p))
        gone = copy.deepcopy(reg); del gone["user_actions"]
        self.assertTrue(any("user_actions" in x for x in check.entry_problems(gone)))
