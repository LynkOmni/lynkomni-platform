"""Partners of LynkVote (VOTE UPDATE, owner approved 2026-11-18, master blueprint 68.13).

LynkVote itself needs no partner: "voting" works in every country (the security core, the public list, the count and the proofs
are LynkOmni's own). Only these parts need an outside partner per country, each behind its interface with a working sandbox, and
each stays "Coming to your country soon." until its partner is signed (providers/registry.v1.json):

- vote_identity: national identity connectors for votes whose assurance level asks for a checked identity (blueprint 68.6). The
  partner answers whether the person matches; LynkOmni keeps only the answer and a vault reference, never the ID number;
- vote_seal: a recognised trust-service partner that seals and time-stamps the certified result so it holds as a legal record;
- vote_post: a printing and postal partner for postal ballots, code sheets and posted notices;
- vote_mirror: independent witness organisations that each keep a copy (a mirror) of a vote's public list, so nobody, LynkOmni
  included, can change the list unseen (blueprint 68.7). The mirror is checked against LynkOmni's own list; a difference is
  flagged as mirror_mismatch for the organiser and observers. "Mirrored by independent witnesses" is claimed only when signed.

Rules every adapter keeps: a voter's contact or identity is only ever a vault reference; the partner never sees a choice (a ballot is
locked on the voter's device before anything leaves it); a partner's answer is a fact only when the partner confirms it, so the
sandbox answers "pending" first and never claims a check, seal or delivery happened.
"""
import re

_SHA = re.compile(r"^[0-9a-f]{64}$")


def _vault(ref):
    return isinstance(ref, str) and ref.startswith("vault:")


class VoteIdentity:
    """Checks that a person on the roll is who they say, at the assurance level the vote's rules ask for."""
    LEVELS = ("document", "national_id")

    def check(self, check_id, person_ref, level, country):
        raise NotImplementedError


class SandboxVoteIdentity(VoteIdentity):
    """SANDBOX: accepts a vault reference and answers "pending"; the identity partner's confirmation is written by the cloud alone."""
    def check(self, check_id, person_ref, level, country):
        if level not in self.LEVELS:
            raise ValueError(f"unknown identity level {level}")
        if not _vault(person_ref):
            return {"ok": False, "reason": "person_must_be_a_vault_reference"}
        return {"ok": True, "check_id": check_id, "state": "pending", "country": country, "status": "sandbox"}


class VoteSeal:
    """Seals and time-stamps a certified result (by its fingerprint) through a recognised trust-service partner."""
    def seal(self, vote_id, certificate_sha256):
        raise NotImplementedError


class SandboxVoteSeal(VoteSeal):
    """SANDBOX: takes only a fingerprint, never the result itself, and answers "pending"; VoteResultCertified says sealed only
    when the real partner confirms."""
    def seal(self, vote_id, certificate_sha256):
        if not _SHA.match(certificate_sha256 or ""):
            raise ValueError("a seal is asked for a sha256 fingerprint")
        return {"ok": True, "vote_id": vote_id, "state": "pending", "sealed": False, "status": "sandbox"}


class VotePost:
    """Prints and posts postal ballots, code sheets and notices to a voter's address held in the PII vault."""
    KINDS = ("postal_ballot", "code_sheet", "notice")

    def send(self, item_id, kind, address_ref, language):
        raise NotImplementedError


class SandboxVotePost(VotePost):
    """SANDBOX: accepts a registered kind to a vault reference and answers "pending"; nothing is printed or posted."""
    def send(self, item_id, kind, address_ref, language):
        if kind not in self.KINDS:
            raise ValueError(f"unknown post kind {kind}")
        if not _vault(address_ref):
            return {"ok": False, "reason": "address_must_be_a_vault_reference"}
        return {"ok": True, "item_id": item_id, "kind": kind, "language": language, "state": "pending", "status": "sandbox"}


class VoteMirror:
    """An independent witness's copy of a vote's public list: it takes every published head (the last tracking code of the chain) and
    the codes, and answers what it holds. It never takes a voter, a code sheet or a choice: the public list holds none."""
    def publish(self, vote_id, head, codes):
        raise NotImplementedError

    def held(self, vote_id):
        raise NotImplementedError


class SandboxVoteMirror(VoteMirror):
    """SANDBOX: keeps the copy in memory and answers "sandbox"; nothing reaches a real witness until one is signed."""
    def __init__(self, name="sandbox-witness"):
        self.name, self.copies = name, {}

    def publish(self, vote_id, head, codes):
        if head is not None and not _SHA.match(head):
            raise ValueError("a head is a sha256 tracking code")
        if any(not _SHA.match(c or "") for c in codes):
            raise ValueError("the public list holds tracking codes only")
        self.copies[vote_id] = {"head": head, "codes": sorted(codes)}
        return {"ok": True, "vote_id": vote_id, "witness": self.name, "status": "sandbox"}

    def held(self, vote_id):
        return self.copies.get(vote_id)

