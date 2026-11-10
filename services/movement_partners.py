"""Partners of LynkMotion and LynkGuard (NEW UPDATE 1, owner approved 2026-11-10, master blueprint section 49 M).

The core of LynkTrace, LynkGPS and LynkSentry needs no partner: the phone is the tracker, maps are LynkOmni's own, and the
service "movement" works in every country. Only these parts need a licensed partner per country, each behind its interface with a
working sandbox, and each stays "Coming to your country soon." until its partner is signed (providers/registry.v1.json):

- vehicle_data: connected-car data from a carmaker or its licensed data partner, only with the owner's consent;
- monitoring: a 24/7 monitoring centre that watches LynkGuard Max alerts, only with the owner's consent;
- transport_data: licensed ship-position and flight-status data;
- satellite: satellite messaging for SOS and trackers where there is no network;
- iot_sim: data plans for trackers, seals and sensors bought on demand.

Rules every adapter keeps: no adapter ever returns or stores a customer's position; a partner answer is a fact only when the
partner confirms it; nothing here moves money; and LynkSentry never contacts police by itself (the owner sends the report pack).
"""


class VehicleDataProvider:
    """Connected-car data (ignition, motion, odometer, alerts) for a vehicle whose owner consented."""
    def link(self, vehicle_ref, owner_consent_id):
        raise NotImplementedError

    def unlink(self, link_id):
        raise NotImplementedError


class SandboxVehicleData(VehicleDataProvider):
    """SANDBOX: no carmaker is connected yet; a link is refused without consent and answered "sandbox" otherwise."""
    def link(self, vehicle_ref, owner_consent_id):
        if not owner_consent_id:
            return {"ok": False, "reason": "consent_missing"}
        return {"ok": True, "link_id": f"sandbox-{vehicle_ref}", "status": "sandbox"}

    def unlink(self, link_id):
        return {"ok": True, "link_id": link_id, "status": "sandbox"}


class MonitoringCentre:
    """A licensed 24/7 monitoring centre that receives LynkGuard alerts the owner chose to share."""
    def hand_over(self, incident_id, alert_kind, owner_consent_id):
        raise NotImplementedError


class SandboxMonitoring(MonitoringCentre):
    """SANDBOX: accepts the hand-over and answers that a person will call the owner; never contacts police."""
    def hand_over(self, incident_id, alert_kind, owner_consent_id):
        if not owner_consent_id:
            return {"ok": False, "reason": "consent_missing"}
        return {"ok": True, "incident_id": incident_id, "next": "partner_calls_owner", "status": "sandbox"}


class TransportData:
    """Licensed ship-position and flight-status data for a journey leg (never a person's position)."""
    def leg_status(self, mode, carrier_ref):
        raise NotImplementedError


class SandboxTransportData(TransportData):
    """SANDBOX: a fixed, clearly labelled sample status for road, rail, sea or air."""
    MODES = ("road", "rail", "sea", "air")

    def leg_status(self, mode, carrier_ref):
        if mode not in self.MODES:
            raise ValueError(f"unknown mode {mode}")
        return {"mode": mode, "carrier_ref": carrier_ref, "step": "on_the_way", "status": "sandbox"}


class SatelliteMessaging:
    """Short satellite messages (SOS, a tracker's last report) where no network exists."""
    def send(self, device_id, kind, size_bytes):
        raise NotImplementedError


class SandboxSatellite(SatelliteMessaging):
    """SANDBOX: refuses anything over the short-message size and anything that is not SOS or a report."""
    MAX_BYTES = 160

    def send(self, device_id, kind, size_bytes):
        if kind not in ("sos", "last_report", "alert"):
            return {"ok": False, "reason": "kind_not_allowed"}
        if size_bytes > self.MAX_BYTES:
            return {"ok": False, "reason": "too_long"}
        return {"ok": True, "device_id": device_id, "status": "sandbox"}


class IotSim:
    """Data plans for trackers, seals and sensors bought on demand."""
    def activate(self, device_id, plan):
        raise NotImplementedError


class SandboxIotSim(IotSim):
    """SANDBOX: activates a labelled sample plan; real plans and prices come from the partner."""
    def activate(self, device_id, plan):
        return {"ok": True, "device_id": device_id, "plan": plan, "status": "sandbox"}
