# LynkOmni decision diary

Every decision the owner made, newest first. Lines are never deleted: a changed decision gets a new line that says what it replaces. Decisions from before this diary started are in the master blueprint, sections 1 to 29 (final blueprint v5, October 2026); they are summarised at the bottom.

| Date | Decision | Applied in |
|---|---|---|
| 2026-11-06 | Use the five working standards: one rule book, a finish checklist, test before adding, version numbers with a change log, and this decision diary. | docs/lynkomni-standards.md; master blueprint section 36 |
| 2026-11-06 | The six-step build order stays a suggestion for now ("Not yet"). | Master blueprint section 38 A |
| 2026-11-06 | Resolve every open item in the master blueprint one at a time; add each to the blueprint once confirmed solved. | Master blueprint section 38 |
| 2026-11-06 | Put together the MASTER BLUEPRINT: everything finalized and agreed, plus four lists (suggested; should not be applied; should be applied but not yet; anything else left out). | Master blueprint, sections 30 to 38 |
| 2026-11-06 | Cash withdrawal and cash deposit: leave for now. | Master blueprint section 38 A |
| 2026-11-06 | Full font system for every LynkOmni language, including Arabic and the other right-to-left languages, working online and offline; Montserrat and Inter keep their roles. | design/fonts; master blueprint section 31 |
| 2026-11-06 | Set up the brand fonts (Montserrat, Inter) before going back to building. | design/fonts |
| 2026-11-06 | Interface emulator list and order agreed; start with the LynkPOS handheld terminal. | Master blueprint section 35 |
| 2026-11-06 | Every service with a screen gets a real-device interface emulator (for example LynkPOS as a physical POS terminal), to make the UI and UX appealing and unique. | CLAUDE.md; master blueprint section 35 |
| 2026-11-06 | Default way of working: build everything possible now, use placeholders for provider work, record only what truly must wait, and always say what needs the owner. | providers/registry.v1.json; master blueprint section 34 |
| 2026-11-06 | Design the LynkVCard cards by tier level following the supplied specification (EDGE, HUB, CORE, OMNI). | visuals/cards.py; master blueprint section 33 |
| 2026-11-06 | Claude creates every icon, picture, chart and figure whenever development needs it; the owner supplies only the logos; no image is ever left missing. | visuals/; master blueprint section 32 |
| 2026-11-06 | Prices raised slightly ("a little more but still cheaper overall") and locked at version 1. | services/billing.py; tests/test_price_lock.py; master blueprint section 14 |
| 2026-11-06 | "Powered by LynkOmni" required on LynkCheckout Free, removable from Plus up. | services/billing.py; master blueprint section 30 |
| 2026-11-06 | Logo placement approved: logo by default, emblem for small or crowded places, wordmark where the name must be read; receipts use the wordmark. | brand/surfaces.v1.json; master blueprint section 30 |
| 2026-11-06 | Workflow warnings are bugs and are fixed in the same task. | CLAUDE.md; master blueprint section 36 |
| Before 2026-11-06 | Repository naming: lowercase, hyphens, starting with "lynkomni"; repositories under the LynkOmni organisation. | Master blueprint sections 30 and 36 |
| October 2026 | Final blueprint v5 locked (sections 1 to 29): two channels, ten CORE services, four geo engines, Rwanda first, LynkOmni never holds funds, approved improvements (section 28), invoicing in LynkCheckout (section 29), and the rest of sections 1 to 29. | Master blueprint sections 1 to 29 |
