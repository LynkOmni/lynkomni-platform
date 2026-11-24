"""The code-scanning findings stay fixed (owner, 2026-11-24, 23 CodeQL findings on main): workflow tokens only read,
secrets a person or program must prove are kept keyed or salted, never as a plain fast hash, and addresses are compared
by whole host name."""
import pathlib, re, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import secrethash


class WorkflowTokens(unittest.TestCase):
    def test_every_workflow_says_what_its_token_may_do(self):
        for f in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            s = f.read_text()
            self.assertRegex(s, r"(?m)^permissions:", f"{f.name}: add a top-level permissions line (least privilege)")
            if f.name in ("ci.yml", "cd.yml"):                       # building and checking only ever read the code
                self.assertEqual(re.findall(r"(?m)^\s*permissions:.*?(?=\s*#|$)", s), ["permissions: {contents: read}"], f.name)

class SecretHashing(unittest.TestCase):
    def test_secrets_are_hashed_with_a_pepper_and_codes_with_salted_scrypt(self):
        import hashlib
        key = "lk_example"
        self.assertNotEqual(secrethash.lookup_digest(key), hashlib.sha256(key.encode()).hexdigest())
        self.assertEqual(secrethash.lookup_digest(key), secrethash.lookup_digest(key))
        a, b = secrethash.code_hash("123456"), secrethash.code_hash("123456")
        self.assertNotEqual(a, b)                                    # salted: the same code never gives the same stored value
        self.assertTrue(secrethash.code_matches("123456", a) and not secrethash.code_matches("123457", a))
        self.assertFalse(secrethash.code_matches("123456", "nonsense"))

    def test_no_plain_fast_hash_of_a_secret_in_identity_or_developer_keys(self):
        for f in ("identity/auth.py", "identity/account.py", "services/devplatform.py"):
            self.assertNotIn("hashlib.sha256", (ROOT / f).read_text(), f)


class Addresses(unittest.TestCase):
    def test_address_tests_compare_whole_host_names(self):
        for f in ("tests/test_catalog.py", "ts/test/footer.test.ts"):
            s = (ROOT / f).read_text()
            self.assertIsNone(re.search(r'includes\("https://[a-z.]+lynkomni\.com"\)', s), f)
            self.assertIsNone(re.search(r'startswith\("[a-z]+\.lynkomni\.com', s), f)


if __name__ == "__main__":
    unittest.main()
