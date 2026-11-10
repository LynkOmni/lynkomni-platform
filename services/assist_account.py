"""LynkAssist on the account site (MASTER UPDATE, master blueprint section 54; build section 2).

Account answers and actions, always through services/assist_register.py (the register decides, never the AI):
- open answers to anyone; personal answers to the signed-in person; verified answers (sign-in history, the data export, the
  business access list) only after a fresh identity check; never a password, code, key or full card number;
- the account actions of the register: change the language (B), end a plan at the end of its period (B), stop a location
  share (B), sign out another device (C), export my data (C), close the account (C), Lock everything (C); recovering an account
  or changing passkeys (D) are only prepared for the person's own Security Center and the recovery paths, never done here;
- class C needs the fresh identity check: a valid step-up from identity/auth.py, made in the last few minutes;
- "Everything LynkAssist did": every decision, run or not, with why, and Undo while it can be undone. History is the person's
  own and is never shown to anyone else."""
import time, uuid
from services import assist_register as AR

UNDO_S = 30


def _now(n):
    return time.time() if n is None else n


class AccountAssist:
    def __init__(self, account, billing=None):
        self.a, self.billing = account, billing
        self.history = {}
        self.handlers = {
            "change_language": self._language,
            "end_plan_at_period_end": self._end_plan,
            "stop_location_share": self._stop_share,
            "sign_out_other_device": self._sign_out_device,
            "export_my_data": self._export,
            "close_account": self._close,
            "lock_everything": self._lock,
        }

    # ---------------------------------------------------------------- answers
    def ask(self, person, topic, signed_in, stepup_token=None, now=None):
        fresh = bool(stepup_token) and self.a.auth.stepup_valid(stepup_token, now=now)
        d = AR.answer(topic, signed_in=signed_in, fresh_check=fresh, role="person")
        if not d["answer"]:
            return {"answered": False, "why": d["why"], "class": d["class"]}
        if topic == "sign_in_history":
            return {"answered": True, "class": 3, "facts": [{"device": x["device_name"], "site": x["site"], "at": x["started"]} for x in self.a.sessions(person, now)]}
        if topic == "data_export":
            return {"answered": True, "class": 3, "facts": self.a.db.execute("select opened,due,ready from acct_requests where person=? order by opened desc", (person,)).fetchall()}
        if topic == "my_plan":
            return {"answered": True, "class": 2, "facts": self.a.subscriptions(person)}
        return {"answered": True, "class": d["class"], "facts": None}

    # ---------------------------------------------------------------- actions
    def do(self, person, action_id, confirmed=False, stepup_token=None, now=None, **args):
        """Decide with the register, then run the action's handler. Every decision goes into the history."""
        fresh = bool(stepup_token) and self.a.auth.stepup_valid(stepup_token, now=now)
        d = AR.decide(action_id, "person", confirmed=confirmed, fresh_check=fresh)
        entry = {"id": uuid.uuid4().hex, "action": action_id, "class": d.get("class"), "needs": d["needs"], "why": d["why"], "at": _now(now),
                 "ran": False, "undo": None, "undone": False, "result": None}
        if d["needs"] == "hand_over":
            entry["result"] = "prepared_for_security_center"
        if d["run"]:
            if action_id == "close_account":
                args["stepup_token"] = stepup_token                  # closing checks the same fresh step-up again
            entry["result"] = self.handlers[action_id](person, now=now, **args)
            entry["ran"] = True
            entry["undo"] = d.get("undo")
        self.history.setdefault(person, []).insert(0, entry)
        self.a.emit(person, "AssistActionRecorded", {"lynkid": self.a._lynkid(person), "action": action_id, "class": d.get("class"), "needs": d["needs"], "ran": d["run"]}, now)
        return {**d, "entry": entry["id"], "result": entry["result"]}

    def undo(self, person, entry_id, now=None):
        for e in self.history.get(person, []):
            if e["id"] == entry_id:
                if not e["ran"] or not e["undo"] or e["undone"] or _now(now) - e["at"] > UNDO_S:
                    return False
                if e["action"] == "change_language":
                    self.a.db.execute("update acct_people set lang=? where person=?", (e["result"]["was"], person)); self.a.db.commit()
                elif e["action"] == "end_plan_at_period_end" and self.billing:
                    self.billing.set_plan(person, e["result"]["family"], e["result"]["was"])
                elif e["action"] == "close_account":
                    self.a.cancel_close(person)
                e["undone"] = True
                return True
        return False

    def everything_done(self, person):
        """The history page: every decision, newest first."""
        return list(self.history.get(person, []))

    # ---------------------------------------------------------------- handlers (only reached when the register allows)
    def _language(self, person, lang, now=None):
        was = self.a.db.execute("select lang from acct_people where person=?", (person,)).fetchone()[0]
        self.a.db.execute("update acct_people set lang=? where person=?", (lang, person)); self.a.db.commit()
        return {"was": was, "now": lang}

    def _end_plan(self, person, family, account=None, now=None):
        if not self.billing:
            return {"family": family, "was": None, "state": "sent"}
        was = self.billing.tier(account or person, family)
        self.billing.cancel(account or person, family)
        return {"family": family, "was": was, "state": "ends_at_period_end"}

    def _stop_share(self, person, share_id, now=None):
        self.a.safe.stop(person, share_id, now)
        return {"stopped": share_id}

    def _sign_out_device(self, person, token_tail, now=None):
        self.a.revoke_session(person, token_tail, "assist", now)
        return {"signed_out": token_tail}

    def _export(self, person, now=None):
        return self.a.open_data_request(person, now)

    def _close(self, person, stepup_token=None, now=None):
        return self.a.request_close(person, stepup_token, now)

    def _lock(self, person, now=None):
        return self.a.protect.lock_everything(person, "assist", verified=True, now=now)
