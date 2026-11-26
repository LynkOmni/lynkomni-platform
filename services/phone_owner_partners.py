"""The mobile network partner for the phone owner check (section 4C point 4, master blueprint section 87).

Only where deep identity is needed (catalog/ways-in.v1.json phone_owner activities), with the person's consent, the legal name
(or a business's registered name) and the number go to the mobile network through the worldwide standard (GSMA Open Gateway:
KYC Match and SIM Swap). Both go only as vault references the adapter resolves inside the partner call; the network answers
match, partial or no_match and the date of the last SIM change. The network's own name for the person is never shown or kept.

Stays off for real users until a mobile partner is signed in that country (providers/registry.v1.json phone_owner_networks);
until then the licensed identity partner's ID document check is used (identity/phone_owner.py). The sandbox never claims a
match: it answers "pending", and the answer is written by the cloud alone (PhoneOwner.network_answer).
"""


def _ref(x):
    return isinstance(x, str) and x.startswith("vault:")


class NetworkOwnerMatch:
    def kyc_match(self, request_id, number_ref, name_ref, country):
        raise NotImplementedError

    def sim_swap(self, request_id, number_ref, country):
        raise NotImplementedError


class SandboxNetworkOwnerMatch(NetworkOwnerMatch):
    """SANDBOX: takes vault references only and answers "pending"; never says match, partial or no_match by itself."""
    def kyc_match(self, request_id, number_ref, name_ref, country):
        if not (_ref(number_ref) and _ref(name_ref)):
            return {"ok": False, "reason": "name_and_number_must_be_vault_references"}
        return {"ok": True, "request_id": request_id, "state": "pending", "status": "sandbox"}

    def sim_swap(self, request_id, number_ref, country):
        if not _ref(number_ref):
            return {"ok": False, "reason": "number_must_be_a_vault_reference"}
        return {"ok": True, "request_id": request_id, "state": "pending", "status": "sandbox"}
