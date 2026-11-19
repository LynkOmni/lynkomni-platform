"""The Emulator Panel's automations in build section 3A, each registered in catalog/automations.v1.json and run by LynkFlow
(services/flow.py). They tell managers and do the daily housekeeping; none moves money, connects a device or changes a credential:
connecting is always a person's choice in the panel."""


def register(flow, platform):
    pn = platform.panel

    def connect_asked(f, m, p, now):
        told = pn.connect_asked(m, p["device_id"], f"ask:{p['device_id']}:{int(now // 60)}", now)
        return {"told": len(told), "why": "a disconnected emulator asked to be connected again; its branch's managers decide in the Emulator Panel"} if told else None

    def device_alert(f, m, p, now):
        why = pn.device_alert(m, p["device_id"], p, f"health:{p['device_id']}:{int(now // 60)}", now)
        return {"alerts": why, "why": "a device needs a look (" + ", ".join(why).replace("_", " ") + ") before it stops a sale or a queue"} if why else None

    def daily(f, m, p, now):
        out = pn.daily(m, now)
        return {**out, "why": "the daily housekeeping: temporary emulators end on their last day, devices not seen for 30 days need approving again, and a downgrade's grace ends after 3 days"} if any(out.values()) else None

    for aid, fn in {"emulator-connect-asked": connect_asked, "emulator-device-alert": device_alert, "emulator-daily": daily}.items():
        flow.handle(aid, fn)
