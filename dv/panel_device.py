"""The Emulator Panel on the device (EMULATOR UPDATE, master blueprint section 70; build section 3A). The device only asks: it answers
a connect request (online, class C), asks its manager to connect it again, signs a user in or out with the staff PIN (checked on the
device by identity/device_access.py; the PIN is never in an event), changes its own tones where the manager allows, and reports its
health. Everything else (connected, disconnected, locked, swapped) is written by the cloud alone (services/emulator_panel.py)."""
from core import emulators as R
from dv.box import LocalRejection


class PanelDevice:
    def __init__(s, box):
        s.box = box
    def answer(s, assignment_id, accept, emulator=None, caps=None):
        """Accept or Deny on the connect request. A device that cannot run the emulator at all says so before asking."""
        s.box._guard("AnswerEmulatorRequest")
        if accept and emulator and caps is not None and not R.can_run(emulator, caps)["ok"]: raise LocalRejection("device_cannot_run")
        s.box._emit("EmulatorRequestAnswered", {"assignment_id": assignment_id, "device_id": s.box.d, "answer": "accept" if accept else "deny"})
    def ask_to_connect(s, emulator):
        s.box._guard("AskToConnect"); s.box._emit("EmulatorConnectAsked", {"device_id": s.box.d, "emulator": emulator})
    def user(s, emulator, change, user_id=None):
        s.box._guard("ChangeEmulatorUser")
        p = {"device_id": s.box.d, "emulator": emulator, "change": change}
        if user_id: p["user_id"] = user_id
        s.box._emit("EmulatorUserChanged", p)
    def settings(s, tones, vibration, volume, allowed=True):
        s.box._guard("ChangeEmulatorSettings")
        if not allowed: raise LocalRejection("manager_does_not_allow")
        s.box._emit("EmulatorSettingsChanged", {"device_id": s.box.d, "tones": tones, "vibration": vibration, "volume": volume, "by": "device"})
    def health(s, online, unsent, battery_pct=None, printer=None, morning_check=None):
        s.box._guard("ReportDeviceHealth")
        p = {"device_id": s.box.d, "online": online, "unsent": unsent}
        for k, v in (("battery_pct", battery_pct), ("printer", printer), ("morning_check", morning_check)):
            if v is not None: p[k] = v
        s.box._emit("DeviceHealthReported", p)
