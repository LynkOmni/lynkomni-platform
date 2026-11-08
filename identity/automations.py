"""The seven automations of build section 2 (blueprint 45 E row 2), each registered in catalog/automations.v1.json and run by
LynkFlow (services/flow.py). Levels: six inform (tell), one draft (a person confirms). None moves money, changes a credential
or completes a recovery; LynkAssist only guides and watches, and every guide is labelled a suggestion."""
from identity.account import DAY

RECOVERY_STEPS = {"device": ["approve_on_other_device", "sign_in_on_new_device"],
                  "code": ["enter_recovery_code", "enter_sms_code", "wait_24_hours", "any_device_can_cancel", "new_device_restricted_24h"],
                  "assisted": ["id_document", "business_proof", "live_check", "wait_72_hours", "two_staff_approve", "new_device_restricted_24h"]}
START_STEPS = ["profile", "registration", "tax_number", "bank_account", "wait_for_the_authority"]
QUIET_DAYS, RENEWAL_DAYS, CONSENT_WARN_DAYS, DATA_WARN_DAYS = 14, 7, 7, 3


def register(flow, account, platform):
    acct, c = account, platform.c

    def sign_in_alert(f, person, payload, now):
        if not (payload.get("new_device") or payload.get("new_place")): return None
        f.emit(person, "SecurityAlertSent", {"lynkid": payload["lynkid"], "kind": "new_sign_in", "channels": ["push", "email", "sms"]}, "sign-in-alert", now)
        return {"alert": "new_sign_in", "links": False, "why": "a sign-in from a new device or place; the message carries no link and points to the Security Center"}

    def recovery_guide(f, person, payload, now):
        steps = RECOVERY_STEPS.get(payload.get("path"), [])
        f.emit(person, "GuideOffered", {"lynkid": payload["lynkid"], "topic": f"recovery_{payload.get('path')}", "steps": steps}, "recovery-guide", now)
        return {"topic": "recovery", "steps": len(steps), "labelled": "suggestion", "why": "a recovery started; LynkAssist shows the steps and the waiting time, and never completes recovery itself"}

    def consent_expiry(f, person, payload, now):
        ending, ended = acct.consents_ending(CONSENT_WARN_DAYS, now)
        did = 0
        for e in ending:
            if e["person"] != person: continue
            f.emit(person, "ConsentExpiring", {"lynkid": acct._lynkid(person), "locns": e["locns"], "expires_at": e["expires"]}, "consent-expiry", now); acct.mark_warned(e["locns"]); did += 1
        for e in ended:
            if e["person"] != person: continue
            f.emit(person, "ConsentExpired", {"lynkid": acct._lynkid(person), "locns": e["locns"]}, "consent-expiry", now); acct.withdraw_consent(person, e["locns"], "expiry", now); did += 1
        return {"consents": did, "why": "a data-sharing consent ends soon or has ended; nothing is shared past its end"} if did else None

    def data_request_timer(f, person, payload, now):
        due = [r for r in acct.data_requests_due(DATA_WARN_DAYS, now) if r["person"] == person]
        for r in due: f.emit(person, "DataRequestReminder", {"lynkid": payload.get("lynkid") or acct._lynkid(person), "request_id": r["request_id"], "due_at": r["due_at"]}, "data-request-timer", now)
        return {"reminders": len(due), "why": "a download-my-records request is due within three days"} if due else None

    def start_business_tracker(f, person, payload, now):
        f.emit(person, "GuideOffered", {"lynkid": payload["lynkid"], "topic": "start_business", "steps": START_STEPS}, "start-business-tracker", now)
        return {"topic": "start_business", "why": "an application was submitted; LynkAssist shows where it stands and what the authority still needs"}

    def churn_watch(f, org, payload, now):
        sales = c.store.of(org, "SaleRecorded")
        last = max([e["ts"] for e in sales], default=None)
        import calendar, time
        quiet = QUIET_DAYS if last is None else int((now - calendar.timegm(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ"))) // DAY)
        if quiet < QUIET_DAYS or not sales: return None
        f.emit(org, "CheckInDrafted", {"lynkoid": platform.ids.public_for("OID", org) or org, "days_quiet": quiet}, "churn-watch", now)
        return {"draft": "support_check_in", "days_quiet": quiet, "why": f"no sale for {quiet} days; a support check-in is drafted for a person to confirm"}

    def renewal_reminder(f, person, payload, now):
        out = 0
        for sub in acct.subscriptions(person):
            for fam, v in sub["plans"].items():
                renews = _renews_at(c, sub["lynkoid"], fam, now)
                if renews is not None and 0 <= renews - now <= RENEWAL_DAYS * DAY:
                    f.emit(person, "RenewalReminderSent", {"lynkid": acct._lynkid(person), "family": fam, "tier": v["tier"], "renews_at": renews}, "renewal-reminder", now); out += 1
        return {"reminders": out, "why": "a paid plan renews within seven days"} if out else None

    for aid, fn in (("sign-in-alert", sign_in_alert), ("recovery-guide", recovery_guide), ("consent-expiry", consent_expiry), ("data-request-timer", data_request_timer),
                    ("start-business-tracker", start_business_tracker), ("churn-watch", churn_watch), ("renewal-reminder", renewal_reminder)):
        flow.handle(aid, fn)


def _renews_at(c, lynkoid, family, now):
    """The next renewal: 30 days after the plan was last set (billing writes the real date with the provider's confirmation)."""
    import calendar, time
    for org in [r[0] for r in c.store.db.execute("select internal from orgs where lynkoid=?", (lynkoid,))]:
        ev = [e for e in c.store.of(org, "subscription.set") if e["payload"]["family"] == family]
        if ev:
            t = calendar.timegm(time.strptime(ev[-1]["ts"], "%Y-%m-%dT%H:%M:%SZ")); period = 30 * DAY
            return t + period * (int((now - t) // period) + 1)
    return None
