"""Partners of LynkAttend, LynkQueue and LynkSurvey (NEW UPDATE 4, owner locked 2026-11-11, master blueprint section 63).

The three services need no partner: "attendance", "queue" and "survey" work in every country. Only these parts need a licensed partner
per country, each behind its interface with a working sandbox, and each stays "Coming to your country soon." until its partner is
signed (providers/registry.v1.json):

- people_messages: text messages, WhatsApp and USSD for PINs and agreement codes (LynkAttend), queue joining and "Please come now"
  (LynkQueue) and survey invitations and answering (LynkSurvey). LynkChat, email and in-app messages never need a partner;
- survey_voice: voice calls that read a survey aloud and take answers by keys or speech;
- survey_rewards: airtime, credit and voucher rewards and LynkSurvey Panel payments through a licensed payment partner.

Rules every adapter keeps: a PIN or IDCN is sent only to the person's own contact and never logged; a partner answer is a fact only when
the partner confirms it; LynkOmni never holds a reward or panel payment.
"""


class PeopleMessages:
    """Text, WhatsApp and USSD sending for the three services."""
    CHANNELS = ("text", "whatsapp", "ussd")

    def send(self, channel, contact_ref, template_id, language):
        raise NotImplementedError


class SandboxPeopleMessages(PeopleMessages):
    """SANDBOX: accepts a registered template to a vault reference and answers "sandbox"; nothing reaches a real phone."""
    def send(self, channel, contact_ref, template_id, language):
        if channel not in self.CHANNELS:
            raise ValueError(f"unknown channel {channel}")
        if not contact_ref.startswith("vault:"):
            return {"ok": False, "reason": "contact_must_be_a_vault_reference"}
        return {"ok": True, "channel": channel, "template_id": template_id, "language": language, "status": "sandbox"}


class SurveyVoice:
    """Voice calls that read a survey aloud in the person's language."""
    def call(self, contact_ref, survey_id, language):
        raise NotImplementedError


class SandboxSurveyVoice(SurveyVoice):
    """SANDBOX: a labelled sample call that answers with the keys pressed in the emulator."""
    def call(self, contact_ref, survey_id, language):
        if not contact_ref.startswith("vault:"):
            return {"ok": False, "reason": "contact_must_be_a_vault_reference"}
        return {"ok": True, "survey_id": survey_id, "language": language, "status": "sandbox"}


class SurveyRewards:
    """Rewards and LynkSurvey Panel payments, paid by a licensed payment partner from the organisation's own money."""
    KINDS = ("airtime", "credit", "voucher", "panel_payment")

    def pay(self, reward_id, kind, amount_minor, currency, recipient_ref):
        raise NotImplementedError


class SandboxSurveyRewards(SurveyRewards):
    """SANDBOX: integers only; answers "pending" first, as a real partner would, and never claims the reward was paid."""
    def pay(self, reward_id, kind, amount_minor, currency, recipient_ref):
        if kind not in self.KINDS:
            raise ValueError(f"unknown reward kind {kind}")
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
            raise ValueError("a reward is a whole number of minor units")
        return {"ok": True, "reward_id": reward_id, "state": "pending", "currency": currency, "status": "sandbox"}
