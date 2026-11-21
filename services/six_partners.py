"""Partners of the six services (SIX SERVICES UPDATE, owner approved 2026-11-18, master blueprint 69.13; sandbox adapters and ledger
entries built in section 4, row 69.14). LynkHR, LynkProject, LynkSchool, LynkProperty, LynkFiles and LynkJobs work without a partner;
only these parts need one per country, each behind its interface with a working sandbox, and each stays "Coming to your country soon."
until its partner is signed (providers/registry.v1.json). The trust-service partner for qualified signatures is in
services/files_partners.py; the video partner and the connected meters and door access (through LynkDriver) are listed already.

Rules every adapter keeps: a person is only ever a vault reference; a check runs only with the person's own recorded consent; a
partner's answer is a fact only when the partner confirms it, so every sandbox answers "pending" and never claims a result, a
listing, a payment or a cover; LynkOmni never holds wages, pensions, rent, deposits or premiums; a named person decides, never
LynkOmni or LynkAssist (69.12).
"""


def _person(ref):
    return isinstance(ref, str) and ref.startswith("vault:")


def _pending(**kw):
    return {"ok": True, "state": "pending", "status": "sandbox", **kw}


def _refused(reason):
    return {"ok": False, "reason": reason}


class BackgroundCheck:
    """Background and reference checks for LynkHR and LynkJobs (69.3, 69.8)."""
    KINDS = ("identity", "right_to_work", "references", "qualifications", "criminal_record_where_lawful")

    def check(self, check_id, person_ref, kinds, consent_id):
        raise NotImplementedError


class SandboxBackgroundCheck(BackgroundCheck):
    """SANDBOX: needs the person's consent and a vault reference; answers "pending"; never returns a finding."""
    def check(self, check_id, person_ref, kinds, consent_id):
        if not consent_id:
            return _refused("consent_required")
        if not _person(person_ref):
            return _refused("person_must_be_a_vault_reference")
        if any(k not in self.KINDS for k in kinds):
            raise ValueError("unknown check")
        return _pending(check_id=check_id)


class TenantScreening:
    """Tenant screening for LynkProperty (69.6)."""
    def screen(self, screening_id, applicant_ref, consent_id):
        raise NotImplementedError


class SandboxTenantScreening(TenantScreening):
    """SANDBOX: consent first; answers "pending"; the owner decides, never the screening."""
    def screen(self, screening_id, applicant_ref, consent_id):
        if not consent_id:
            return _refused("consent_required")
        if not _person(applicant_ref):
            return _refused("person_must_be_a_vault_reference")
        return _pending(screening_id=screening_id)


class ExamBoard:
    """Qualification and exam-board connectors for LynkSchool and LynkAcademy (69.5, 80.10)."""
    def register(self, entry_id, learner_ref, exam_code):
        raise NotImplementedError


class SandboxExamBoard(ExamBoard):
    """SANDBOX: answers "pending"; a result is only as official as the board behind the connector."""
    def register(self, entry_id, learner_ref, exam_code):
        if not _person(learner_ref):
            return _refused("person_must_be_a_vault_reference")
        return _pending(entry_id=entry_id, exam_code=exam_code)


class Notary:
    """A licensed notary service for LynkFiles, only where the law allows remote notarisation (69.7)."""
    def notarise(self, request_id, document_sha256, signer_refs):
        raise NotImplementedError


class SandboxNotary(Notary):
    """SANDBOX: takes only the document's fingerprint and answers "pending"; never claims a notarised document."""
    def notarise(self, request_id, document_sha256, signer_refs):
        if not (isinstance(document_sha256, str) and len(document_sha256) == 64):
            raise ValueError("a notary is asked for a sha256 fingerprint")
        if not signer_refs or not all(_person(r) for r in signer_refs):
            return _refused("signers_must_be_vault_references")
        return _pending(request_id=request_id, notarised=False)


class Pension:
    """Pension and benefit providers for LynkHR (69.3)."""
    def enrol(self, enrolment_id, staff_ref, scheme):
        raise NotImplementedError


class SandboxPension(Pension):
    """SANDBOX: answers "pending"; contributions are paid by the employer through the licensed provider, never held by LynkOmni."""
    def enrol(self, enrolment_id, staff_ref, scheme):
        if not _person(staff_ref):
            return _refused("person_must_be_a_vault_reference")
        return _pending(enrolment_id=enrolment_id, scheme=scheme)


class DepositProtection:
    """Deposit-protection schemes for LynkProperty (69.6)."""
    def protect(self, deposit_id, amount_minor, currency, tenant_ref):
        raise NotImplementedError


class SandboxDepositProtection(DepositProtection):
    """SANDBOX: integers only; answers "pending"; the deposit sits with the scheme, never with LynkOmni."""
    def protect(self, deposit_id, amount_minor, currency, tenant_ref):
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
            raise ValueError("a deposit is a whole number of minor units")
        if not _person(tenant_ref):
            return _refused("person_must_be_a_vault_reference")
        return _pending(deposit_id=deposit_id, protected=False)


class RentInsurance:
    """A licensed rent insurer for LynkProperty (69.6)."""
    def quote(self, quote_id, unit_id, monthly_rent_minor, currency):
        raise NotImplementedError


class SandboxRentInsurance(RentInsurance):
    """SANDBOX: answers "pending"; no cover is claimed and no premium is taken."""
    def quote(self, quote_id, unit_id, monthly_rent_minor, currency):
        if isinstance(monthly_rent_minor, bool) or not isinstance(monthly_rent_minor, int) or monthly_rent_minor <= 0:
            raise ValueError("rent is a whole number of minor units")
        return _pending(quote_id=quote_id, covered=False)


class PropertyListings:
    """Property-site connectors for LynkProperty adverts (69.6)."""
    def publish(self, listing_id, sites):
        raise NotImplementedError


class SandboxPropertyListings(PropertyListings):
    """SANDBOX: answers "pending" for each site; nothing is shown live on another site."""
    def publish(self, listing_id, sites):
        return _pending(listing_id=listing_id, sites={s: "pending" for s in sites})


class JobListings:
    """Other job sites and search engines' job listings for LynkJobs (69.8)."""
    def publish(self, job_id, sites):
        raise NotImplementedError


class SandboxJobListings(JobListings):
    """SANDBOX: answers "pending" for each site; job seekers never pay to search, apply or be hired."""
    def publish(self, job_id, sites):
        return _pending(job_id=job_id, sites={s: "pending" for s in sites})


class EmployerOfRecord:
    """Employer-of-record partners for hiring abroad through LynkHR and LynkJobs (69.3, 69.8)."""
    def onboard(self, request_id, worker_ref, country):
        raise NotImplementedError


class SandboxEmployerOfRecord(EmployerOfRecord):
    """SANDBOX: answers "pending"; wages are paid by the partner, never held by LynkOmni."""
    def onboard(self, request_id, worker_ref, country):
        if not _person(worker_ref):
            return _refused("person_must_be_a_vault_reference")
        return _pending(request_id=request_id, country=country)


class EmploymentServices:
    """Public employment services for LynkJobs (69.8)."""
    def share_job(self, job_id, country):
        raise NotImplementedError


class SandboxEmploymentServices(EmploymentServices):
    """SANDBOX: answers "pending"; nothing reaches a public service."""
    def share_job(self, job_id, country):
        return _pending(job_id=job_id, country=country)
