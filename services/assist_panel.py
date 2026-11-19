"""LynkAssist in the Emulator Panel (EMULATOR UPDATE 70 and CONNECT UPDATE 71.9, build section 3A): explaining a device, and
connecting, disconnecting, marking lost and the staff coach's practice mode, each prepared by LynkAssist and done only after the
manager's Confirm, through the same decisions, history and Undo as every Business app action (services/assist_business.py).
Every action is in catalog/assist.v1.json; nothing here runs outside it.

What LynkAssist never does here: give an emulator to a device nobody accepted, wipe a device (the owner alone, after a fresh check,
identity/device_access.py), view a screen (only with the user's consent) or pass the plan's limit (it suggests the $2 extra slot
for the owner to choose)."""
from services.assist_business import BusinessAssist

PANEL_ACTIONS = ("panel_explain_device", "panel_connect_device", "panel_disconnect_device", "panel_mark_lost", "panel_practice_mode")
WORDS = {"printer": "the printer is out of paper or low", "battery": "the battery is low", "unsent": "many records are still to be sent",
         "morning_check": "the morning check failed", "offline": "it has not been online for a while", "reapproval": "it needs approving again",
         "lost": "it is marked as lost"}


class PanelAssist(BusinessAssist):
    def __init__(self, platform, merchant, owner, acting_as, **kw):
        super().__init__(merchant, owner, **kw)
        self.p, self.m, self.by, self.e = platform, merchant, acting_as, platform.panel

    def explain(self, device):
        """Why this device shows what it shows, in plain words (the live view's "Why?")."""
        d, h = self.e._dev(device), self.e._health_of(device)
        why = self.e.needs_alert({"printer": h["printer"], "battery_pct": h["battery"], "unsent": h["unsent"], "morning_check": h["morning"]})
        if not h["online"]: why.append("offline")
        if d["reapprove"]: why.append("reapproval")
        if d["lost"]: why.append("lost")
        return {"device": d["name"], "reasons": why, "words": [WORDS[w] for w in why], "suggestion": True}

    def _run(self, action_id, args):
        e, m, by = self.e, self.m, self.by
        if action_id == "panel_explain_device":
            return self.explain(args["device"]), None
        if action_id == "panel_connect_device":
            r = e.connect(m, [args["device"]], args["emulator"], by)[0]
            undo = (lambda: e.disconnect(m, [args["device"]], by, emulator=args["emulator"])) if r["state"] == "confirmed" else None
            return r, undo
        if action_id == "panel_disconnect_device":
            r = e.disconnect(m, [args["device"]], by, emulator=args.get("emulator"))[0]
            return r, (lambda: e.connect(m, [args["device"]], r["emulator"], by))
        if action_id == "panel_mark_lost":
            e.mark_lost(m, args["device"], by)
            return {"device": args["device"], "locked": True}, (lambda: e.mark_lost(m, args["device"], by, found=True))
        if action_id == "panel_practice_mode":
            r = e.connect(m, [args["device"]], args["emulator"], by, practice=True)[0]
            return {**r, "practice": True, "counts": False}, (lambda: e.disconnect(m, [args["device"]], by, emulator=args["emulator"]))
        return super()._run(action_id, args)
