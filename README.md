# LynkOmni platform (v0.8)

Ten CORE services, two sub-core service categories (25 sub-services, advertising), the Adaptive Locale System, a mode manager
and an internal Control Center, all over one offline-first event log. Pure Python standard library: nothing to install.

    python3 -m unittest discover -s tests -t .     # run all 104 tests (plus 11 in ts: cd ts && npm test)
    python3 server.py                               # API on http://localhost:8080
    LYNK_MODE=sandbox python3 server.py             # turn every service on (simulated providers)

## Map
| Area | Where |
|---|---|
| 1 Universal Payment App, 4 Failure Recovery | services/suite.py `Payments` |
| 2 POS, 3 Accountant, 6 Inventory, 7 Loyalty, 8 Dashboard, 9 Growth Engine | services/suite.py |
| 5 Pay-by-Link and QR | services/suite.py `PayLinks` |
| 10 Chat (threads, inbox, quote to paid order, safety) | services/extras.py `Chat` |
| Credit and collections, Shop QR, Verified Receipts, Staff and cash controls, Assistant | services/extras.py |
| Data rights (consent log, revoke, export) | services/suite.py `DataRights` |
| Sub-core: Booking & Ticketing (10) and Utility, Payments & Connectivity (14, including Currency and Crypto Exchange) | services/catalog.py |
| Language, formats, local time, receipts text, mode manager | core/locale.py |
| Countries, currencies, time zones, feature flags, geo | core/regions.py, core/money.py |
| Company Control Center (revenue, costs, profit, acquisition, alerts) | services/control.py |
| Providers and fiscal adapters (simulators) | core/providers.py, services/catalog.py |
| Advertising structure (campaigns, review, serving, offline bundles, billing, merchant share) | services/ads.py |
| Subscription families, LynkSuite, billing rules, entitlements (15 families) | services/billing.py |
| Developer platform: LynkHub apps, keys, consent scopes, metering, LynkAPI quotas and audit | services/devplatform.py |
| Step-up verification for Exchange and credit | services/identity.py |
| Everything wired together | services/platform.py |

## Add a country / integrate a provider
Add one entry to `COUNTRIES` (`core/regions.py`) and a currency (`core/money.py`). Turn a service on with
`flags={"payments": True, "svc_airtime": True}`. Real providers: subclass `Provider` (payments) or replace
`SandboxProvider` (catalog); real tax systems: implement `FiscalAdapter`. Nothing else changes.

## What is simulated or unfinished
- All payment and catalog providers are simulators. No money moves and nothing is booked or delivered.
- FX rates, commission rates and prices are placeholders. Geo lookup uses crude boxes; the merchant's choice wins.
- No authentication yet. Do not expose the API publicly. The Control Center is library-only for that reason.
- Verified Receipts use a server-side HMAC. Offline verification by customers needs public-key signatures (add the `cryptography` package).
- Translations are drafts needing native-speaker review. Kinyarwanda is pending and falls back to English.
- Rwanda fiscal receipts stay `pending_fiscal`: not valid tax invoices until the RRA workflow is confirmed.
- No app screens yet. Devices keep the same event log locally and call `/v1/sync`.
- Anything that moves money or lends needs a qualified security review and licensed partners before real use.

## Contract v1 (authority for the merchant core)
`contract/` holds the frozen-draft contract between the phone (LynkDVBox) and the cloud (LynkCCBox): event envelope, 21 event types,
permissions, command policy register, state machines, and a validator (`python3 contract/tools/validate_contract.py`, 382 checks).
- `dv/box.py` is the device side: commands become contract events with hash chain, local permission and session rules.
- `cc/box.py` is the cloud intake: idempotent, gap and tamper handling, quarantine, revocation, negative-stock flags, SQLite.
- `tests/test_contract.py` runs the validator and checks the cloud against the contract's own reference model.
Signatures are DEV-ONLY placeholders until real hardware-backed ES256 keys exist. The v0.1-v0.4 domain modules (suite.py, extras.py, ...)
still use their own events; bridging them to the contract (money in RWF, quantities in thousandths, UUIDv7 ids) is the next step.
Offline selling pauses after 14 days without sign-in (the contract default, configurable per device).

## v0.6 additions (blueprint sections 14, 20 and the developer infrastructure)
- Billing follows the blueprint rules: one subscription per product, highest tier wins, LynkSuite replaces its seven products, a product above the
  LynkSuite tier pays only the difference, add-on families (LynkMPay, LynkRecover, LynkCheckout, LynkAssist) are never inside LynkSuite, one invoice per
  period, and each paid subscription is counted once. Prices are standard USD placeholders scaled by the country price index.
- Ads show on POS, Dashboard and Inventory surfaces only while that product is on its Free tier. LynkSuite Free still shows ads.
- Alternative Accommodation is the 25th sub-service. Insurance, credit and exchange need per-country terms. Exchange and credit need step-up verification.
- Not built: real step-up (second factor), site sessions and the account.lynkomni.com sign-in, consumer recovery, add-ons billing (extra branches, AI packs),
  payment orchestration behind LynkCCBox (the old Payments class is still separate), and bridging v0.1-v0.4 modules to contract v1.

## v0.7 additions (Identity, Universal Identifier Standard, Chat and Support ecosystem, language stack)
- `contract/identifier-registry.v1.json` and `core/ids.py`: the LO identifier standard (35 types, random, Luhn check digit, never reused, offline ID leases).
- `identity/`: LynkID and LynkOID, memberships and roles, PIN and limited feature-phone sessions, recovery, verification cases with partner attestations, support-access grants, pseudonymous customer references.
- `services/support.py`: LynkSupport cases, support conversations, routing, transfers (accept, reject, timeout, fallback), FAQ, status, feedback, safety, vulnerability disclosure.
- `core/capability.py` and `services/privacy.py`: capability tokens (tickets, links), PII vault, encryption-claims guard. `core/naming.py`: one source of truth for names and URLs.
- Chat is customer-business conversations and live support only. There is no personal or group messaging.
- LynkOmni AI and LynkOmni Assistant are one entity (LynkAssist, lynkomni.com/ai). Developer docs are LynkDoc at doc.lynkomni.com. Support is lynkomni.com/support.
- See STACK.md for the TypeScript, SQL, Rust, Kotlin, Swift and Python allocation, and what has and has not been compiled here.

## v0.8 additions (LynkVCard, consumer Max tiers, footer, naming fixes)
- `services/vcard.py` and `contract/vcard.v1.json`: LynkOmni Virtual Card (LynkVCard) and its risk module LynkVCRBox. Issuer-hosted card display (no card number stored), idempotency keys on every request, freeze may queue offline (24h, nonce), 2% FX buffer released at settlement, chargeback tiers 0.3%/0.9%, issuance velocity limit, supplier scores need 3 or more merchants, signed webhooks. A sandbox issuer is included; real issuers plug in per country. Cards are off in every country until activated.
- `contract/country-packs/*.json`: shared JSON country packs (currency, time zone, languages, providers, card networks, wallets, card block). A pack alone never enables cards.
- `services/billing.py`: 16 families. LynkBooking and LynkEssential now have a Max tier; LynkVCard is an add-on family, never inside LynkSuite.
- `core/naming.py`: SDK = LynkOmni SDK / LynkSDK / sdk.lynkomni.com; booking.lynkomni.com; essential.lynkomni.com.
- `services/newsletter.py` and `ts/src/footer.ts`: ecosystem footer model (fixed copyright text, year in the viewer's time zone, payment marks from the country pack, double opt-in newsletter). `ts/scripts/preview.mjs` renders a preview. Brand marks are placeholders and translations are drafts.
- Not run in the build environment: Rust, Kotlin, Swift, PostgreSQL, Docker. `core/ids.py` now serialises access to its shared connection with a lock.

## v0.9: design system and approved improvements
- design/tokens.v1.json is the single source for colours (light, dark, high contrast) and fonts (Montserrat, Inter). `python3 design/generate.py` writes CSS, Tailwind preset, TypeScript, Kotlin and Swift. Contrast pairs are tested.
- Font files are NOT in the repo (no internet here). Put the WOFF2 files listed in design/fonts/README.md in place; `python3 design/check_fonts.py` is the release gate (Latin first load under 100 KB).
- services/improvements.py: MeshRelay, OfflineRisk, ProofPack, AuditExport, Split, Seats, Meter, Edge, GuestCheckout, BusinessSettings. All providers and CDN are sandbox interfaces.
- Identifier registry now has 38 types (added LOPRF-, LOAUD-, LOSPLT-).
- Not tested here: Rust (dependencies cannot be downloaded without network), Kotlin and Swift builds; only the shared vectors were extended for the new ID types. Prices, names, domains and trademarks are unchecked placeholders.

## v0.9.3: invoicing
- services/invoicing.py: invoices inside LynkCheckout with tier limits (3, 20, 200, unlimited a month), leased offline number blocks, pay link after cloud acceptance, provider-confirmed payment only, credit notes, partial payments, consent-based reminders, recurring invoices. Legal invoice content, numbering and retention rules per country are NOT checked and need a local adviser.

## v0.9.4: logos and icons
- The artwork lives in its own repo, `lynkomni-icons`, and is published as `@lynkomni/icons`. This repo never edits it: the brand-sync workflow vendors a release into `brand/vendor` with a SHA-256 `brand.lock.json`, and every read is re-checked. Works offline; nothing is fetched at run time.
- `brand/` (Python) and `ts/src/brand.ts` choose which asset and variant to show per theme; invoice logo rules by tier (`lynkomni`, `logo`, `full`) are in one table.
- New `logo-ink` design token (logo only). `python3 brand/check.py` guards the token mirror, surfaces and hard-coded logo colours or file names.
- Until the first sync, the footer preview shows a text placeholder. Brand wording, names and trademarks are still unchecked; accessibility claim stays WCAG 2.2 AA only.

### v0.9.5: which logo goes where
- `brand/surfaces.v1.json` now lists 21 places and, for each, which of logo, emblem and wordmark to show, with automatic fall-back to the emblem when space is narrow. `brand.for_surface(place, theme, width)` returns the right file; the CI `brand` job rejects bad rules and any code that places the emblem and wordmark together.
- Receipts use the wordmark in one colour. "Powered by LynkOmni" (wordmark) shows on pay links and checkout: required on Free, removable on paid tiers (`powered_by` in LynkCheckout FEATURES; which tier removes it is an unconfirmed pricing decision).
- Needs `@lynkomni/icons` 1.1.0 (adds wordmark email images). Run the brand-sync workflow and merge its pull request.

### Prices updated (2026-11-06)
- Standard USD prices raised about 25 to 40% on paid tiers after the first price check (still placeholders, not market-tested). LynkSuite is now $0/$17/$49/$125 (about 30% below its seven products). LynkBooking, LynkEssential and LynkDev unchanged. Free tiers unchanged.
- Prices are now LOCKED (v1) and pinned by `tests/test_price_lock.py`. `finance/revenue_model.py` reproduces the blueprint's subscription revenue from its stated user numbers and re-runs it at the new prices: Stage 3 is now $33.1 million a month ($397 million a year), Stage 1 $9,639, Stage 2 $900,522. The section 28 lines ($24,825 a month) are per-use fees and did not change.

## Documents with logos (v0.9.6)

`services/documents.py` renders the invoice page, the receipt and a plain email shell. Logos come only from `brand.for_surface`: the LynkOmni logo shows on an invoice only on the Free LynkCheckout tier; receipts use the one-colour wordmark and never a badge; email uses the PNG logo on top and the wordmark in the footer. The "Powered by LynkOmni" badge is removable from LynkCheckout Plus upward (decided 2026-11-06). Invoices are never called tax invoices and say Paid only after the provider confirms. Merchant logo upload (PNG, JPEG, WebP only) is still to come, so a merchant's name shows as text. Fixed: the footer preview's Privacy link no longer floats at the edge.

## Icons (v0.9.7)

Brand release 1.2.0 adds 43 one-colour icons (16 product marks, 5 status icons, 22 core UI icons), vendored under brand/vendor/icons and locked by SHA-256. `brand.icon(id)` and `brand.status_icon(state)` look them up; only the five user-facing states have status icons. They are drafts for designer review. A new gate checks that all five status icons are present and locked.

## v0.9.8: visuals made automatically
- `visuals/needs.v1.json` lists every picture the product needs (36 so far: 16 product illustrations, 9 state screens, 4 onboarding steps, 2 charts, 1 diagram, share card, store graphic, app icons, web icons). `python3 visuals/generate.py` draws them all from the design tokens, in light, dark and the two high-contrast themes, into `visuals/generated`.
- Code asks for a picture by id (`visuals.get("product-pos", "dark")`, TypeScript `visual(...)`). An unknown id is an error with instructions, never a placeholder. Lite mode hides decorative pictures; sunlight mode uses the contrast set.
- Charts and the sync diagram read their numbers and wording from the code (billing, revenue model, state tokens). The revenue chart says it is an assumption, not a forecast.
- `python3 visuals/check.py` (CI job `visuals`) fails on a missing, orphaned, off-token, wordy, oversized or stale picture, a placeholder or "TODO image", a stock-image service, a web image, or a call for an id that does not exist.
- All of it is a draft until a human designer reviews it. Photographs and screenshots of real screens are not made here.
