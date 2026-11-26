"""The age ID check partner (neutral age gate, owner 2026-11-26; catalog/ways-in.v1.json sign_up.age.under_age).

Someone who came out under age at sign-up cannot try again by retyping a date. If it was a mistake, only a licensed identity
partner, reached through LynkOmni, can clear it: the person shows an ID document to the partner, and the partner answers only
"adult" or "not adult" for the country's age. The partner never sends LynkOmni the document, the birth date or the age, and
LynkOmni keeps none of them. The person pays the partner's fee, shown before they start (providers/registry.v1.json
age_id_check, who_pays user). The check stays "Coming to your country soon." until the partner is signed there.

Rules every adapter keeps: the request carries only its own id and the country; the partner's answer is a fact only when the
partner confirms it, so the sandbox answers "pending" and never claims a result (identity/account.py partner_age_answer is
written by the cloud alone).
"""


class AgeIdCheck:
    def start(self, request_id, country):
        raise NotImplementedError


class SandboxAgeIdCheck(AgeIdCheck):
    """SANDBOX: accepts the request and answers "pending"; the partner's adult yes or no is written by the cloud alone."""
    def start(self, request_id, country):
        if not (isinstance(request_id, str) and request_id):
            return {"ok": False, "reason": "request_id_needed"}
        return {"ok": True, "request_id": request_id, "state": "pending", "status": "sandbox"}
