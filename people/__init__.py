"""LynkAttend, LynkQueue and LynkSurvey in full (NEW UPDATE 4, master blueprint section 63; build section 3B).

The rules live in core/attendance.py, core/queue_tickets.py and core/surveys.py. This package is the working service around them:
the cloud side (registration, PINs, records, flags, requests, reports), the device side (the door, reception, counters, answering,
all offline) and their automations on LynkFlow. Every fact is a contract version 6 event; a PIN, an IDCN, an ID number, a face or
finger pattern, a phone number or a position is never in one."""
