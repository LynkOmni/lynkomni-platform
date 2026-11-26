"""One helper for tests that need a finished sign-up (section 4C point 3): the legal name, then the email and the phone number,
each confirmed with its own code."""


def confirm_contacts(account, person, now, legal_name="Grace Uwase", legal_ref="pii_legal"):
    account.set_legal_name(person, legal_name, legal_ref)
    for kind in ("email", "phone"):
        account.confirm_contact(person, account.send_contact_code(person, now, kind=kind), now, kind=kind)
