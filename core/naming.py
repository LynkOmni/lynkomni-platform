"""One source of truth for service names, short names and URLs. Corrections applied: LynkDoc (not LynkDocs) at doc.lynkomni.com;
support lives at lynkomni.com/support; LynkOmni AI and LynkOmni Assistant are one entity with the short name LynkAssist at lynkomni.com/ai."""
SERVICES = {
 "chat": ("LynkOmni Chat", "LynkChat", "lynkomni.com/chat"), "support": ("LynkOmni Support", "LynkSupport", "lynkomni.com/support"),
 "faq": ("LynkOmni FAQ", "LynkFAQ", "lynkomni.com/faq"), "ai": ("LynkOmni AI", "LynkAssist", "lynkomni.com/ai"),
 "status": ("LynkOmni Status", "LynkStatus", "status.lynkomni.com"), "feedback": ("LynkOmni Feedback", "LynkFeedback", "lynkomni.com/feedback"),
 "safety": ("LynkOmni Safety", "LynkSafety", "lynkomni.com/safety"),
 "booking": ("LynkOmni Booking", "LynkBooking", "booking.lynkomni.com"), "essential": ("LynkOmni Essential", "LynkEssential", "essential.lynkomni.com"),
 "exchange": ("LynkOmni Exchange", "LynkExchange", "exchange.lynkomni.com"), "vcard": ("LynkOmni Virtual Card", "LynkVCard", "lynkomni.com/vcard"),
 "vcrbox": ("LynkOmni Virtual Card Risk Box", "LynkVCRBox", None), "sdk": ("LynkOmni SDK", "LynkSDK", "sdk.lynkomni.com"),
 "hub": ("LynkHub", "LynkHub", "hub.lynkomni.com"), "doc": ("LynkDoc", "LynkDoc", "doc.lynkomni.com"), "api": ("LynkAPI", "LynkAPI", "api.lynkomni.com"),
 "flow": ("LynkFlow", "LynkFlow", None)}                       # LynkFlow is internal: no public domain
ALIASES = {"LynkOmni Assistant": "LynkAssist", "LynkOmni AI": "LynkAssist"}   # the merchant add-on and the platform-wide AI are the same entity
BANNED = ("bookings.lynkomni.com", "essentials.lynkomni.com", "LynkBookings", "LynkEssentials", "lynkbookings", "lynkessentials", "LynkAI", "LynkDocs", "support.lynkomni.com", "docs.lynkomni.com", "flow.lynkomni.com", "LynkHub Plus", "LynkOmni AI Assistant", "portal.lynkomni.com")
