# LynkOmni change log

What changed in each version, in plain words, newest first. Version numbers: `0.MINOR.PATCH` until the first pilot (a new feature raises MINOR, a fix raises PATCH). Each version has a Git tag `v<number>`.

## v0.26.0 (2026-11-09)
Section 3, Phase 5: language wave 2 (blueprint 43 G). LynkOmni now speaks 38 languages: Bangla, Tamil, Thai, Amharic, Hausa, Yoruba, Zulu, Filipino, Polish, Dutch, Ukrainian and Malay join the 26 of wave 1.
- Every screen text of every emulator (the shell, the shared POS words, the footer, the account site, the Business app and every device) is translated by Claude into the 12 languages and checked by tools/translation/claude_packs.py (names, placeholders and numbers unchanged, no repetition, written in the language's own script).
- Four new scripts with self-hosted fonts from the official Google Fonts repository (same pinned commit, SIL Open Font License): Noto Sans Bengali, Noto Sans Tamil, Noto Sans Thai and Noto Sans Ethiopic. Bengali, Tamil and Thai get the taller line height and are never letter-spaced or uppercased. Ukrainian uses the Cyrillic files and the Latin-script languages use Montserrat and Inter.
- Yoruba's dot-below vowels sit in the Vietnamese block, so a language can now name extra script files ("also" in design/fonts/scripts.v1.json) and offline apps store them too (fontFilesFor).
- The translation script check knows Bengali, Tamil, Thai and Ethiopic.
- Country packs: Bangladesh, Sri Lanka, Thailand, Ethiopia, Malaysia, Brunei, Poland, Ukraine, the Netherlands, Belgium, Suriname, the Dutch Caribbean and the Cocos Islands now open in their own language; every country name is available in the 12 new languages. No language waves are left in design/fonts/language_waves.v1.json; the other official languages stay "planned".
- File size budgets raised for five demo files (they carry every text in all 38 languages; a real app downloads one language at a time) and the pricing ladder chart (the longer font stack).

## v0.25.0 (2026-11-09)
Section 3, Phase 3 and 4: the 41 B shell parts in every device app, picture mode on every device, and the agent point pictures.
- Every navigated device (terminal, counter tablet, kitchen screen, rider phone, stock scanner, owner's web view) now has "Find or do anything" (search that runs actions, with voice and LynkAssist), help (?) for the screen in view with a way to a person, the account menu, the connection chip with its sync sheet, the language and region card on first use with one-tap English, designed empty states, and an address for every screen from the address map. "/" or Ctrl+K opens search on a computer; Escape closes.
- The Business app keeps its five-part top bar (41 E): help (?) sits beside the screen title, "Find or do anything" is a search field on Home and the Business hub, and Help in the account screen opens the help panel.
- The button phone has no touch screen, so its numbered menu is its "find or do": Help, Language and region, Sync and Account are menu numbers, and the language card is a numbered list on first use.
- Picture mode (bigger pictures with the word beside them) on every device: a switch in the account menu and in search; the button phone shows a picture beside each menu line.
- New icons in lynkomni-icons: float and commission (released and vendored by brand-sync). New illustration: the agent point (a counter with the agent's cash and a phone with the partner's tick), on the agent home; hidden in lite mode.
- Tests: tests/test_device_shell.py (shell parts on every device, addresses from the address map, the button phone menu, protected zones with nothing promoted on payment, cash count, private chat, agent, float and commission screens); the layout test now walks the first-run card and every shell panel in every language.
- Leftovers fixed: the counter tablet's customer screen showed "Powered by LynkOmni" during payment (never allowed); the Business app's language card "Change" button used the word for cash change in 25 languages; the owner's web view used two addresses not in the address map (/business/staff, /business/money/commissions, now /business/team and /business/agent-earnings); the terminal's connection icon did nothing (it now opens the sync sheet, also in the menu).
- Every country pack now carries the rule 0.5 fields it lacked: public holidays for 2026 and 2027 (from the open-source holidays package, MIT, through tools/country_holidays.py; 247 countries covered, all unconfirmed until a person checks), invoice numbering (the services/invoicing.py rules, unconfirmed) and legal text (empty until the country's lawyer sets it; nothing legal is printed before). The later list has country_legal_text.
- File size budgets raised for the terminal, counter tablet and Business app demo files, which carry the shell words in all 26 languages (a real app downloads one language).

## v0.24.1 (2026-11-09)
LynkVCard faces carry the full LynkOmni logo instead of the emblem alone (owner decision). Brand place vcard-face now chooses the logo in one colour; the four card fronts and backs, the tier ladder and the card emulator are regenerated from it; card alt texts say "the LynkOmni logo"; a test checks every face and back uses the logo and never the emblem alone. Blueprint sections 30 and 33 and CLAUDE.md updated.

## v0.24.0 (2026-11-09)
The whole Business app as blueprint 41 E lays it out (Phase 2 of enforcing sections 1 to 3). catalog/business-app.v1.json lists its 46 screens with what each must hold and its address; the merchant phone emulator shows every one and tests/test_business_app.py checks each screen, item and address.
- Getting in runs in the blueprint's order: sign in, choose the business, register this device, the language and region card with one-tap English, the setup checklist (name and type, currency, first products by scan, photo, voice, template or import, invite staff, print the shop QR, every step skippable), then the first sale.
- The phone top bar holds the emblem, screen title, connection chip, notifications and the account menu (masked LynkID, switch business and role, language and region, theme, Security Center, help, sign out). Tabs follow the business type (shop, without a till, agent point, restaurant); a tablet shows them in a side rail and a computer that is not registered gets the web view "View only on this computer".
- Sell: search, scan, voice, categories; basket with quantity, discount, note and customer; every payment way (cash, mobile money, card, tap to pay on the phone, bank transfer, QR, pay link, credit, split) with the proof warning and visitor prices; receipts by print, QR, chat or SMS link (by plan) with the verify QR; today's sales with reprint, void and return or refund (contract reason codes); shifts with float, counts, handover and differences flagged; practice mode with practice cash.
- Stock: filters, product page, add product five ways, received, full or partial count, removals with reasons, moves between branches, suppliers, reorder drafts and purchase orders, supplier marketplace with buy together, labels, import and export.
- Chats: filters, pinned LynkOmni Support, a thread with attached cards, send product, quote, pay link or receipt, saved replies, photo, voice note, assign, and the "Translated from" note.
- The Business hub: every section and setting in the blueprint's order; regulated items wait for their partner with Notify me; online shop with the shop username check and shop QR; team with time clock; devices with revoke; plans with LynkPOS prices from billing; automations with history, "Why did this happen?" and an off switch; Academy lessons; data-sharing consents off until turned on.
- Agent point: outlets on Pro and Max, cash checks at day start, day end and handover, a practice partner that confirms, fails or stays silent (no cash before the partner confirms), one receipt with its LORCP- id, the partner reference and the state, and agent activity in the health score only with consent.
- The terminal prints the verify QR and receipt id under every receipt and shows the shop QR (38 C). The owner's web view says "View only on this computer".
- Picture mode on the phone (bigger pictures with the word beside them).
- About 470 new screen texts, translated into all 25 other languages and checked by the translation tool.
- Leftovers fixed: sample public ids in the emulators had made-up check digits (now valid, and a test checks every id written); chat ids were not in the public id format; agent partner ids were not uuids as the contract requires; events the contract does not have (a daily-close event, a waitlist event, staff clock events with the wrong names) are no longer written.
- The merchant phone file budget is raised to 760 KB with its reason (web/budgets.v1.json); first-screen and tap budgets are unchanged and pass.

## v0.23.1 (2026-11-09)
Enforcing the blueprint for Step 0 and sections 1 and 2 (owner, 9 November 2026: "enforce what is laid out in the blueprint ... entirely"). The full list of rules and their status is docs/lynkomni-blueprint-checklist.md.
- Brand marks follow their places (section 30): screens ask the brand module for their place (ts/src/brand.ts markFor and brandMark). The logo now shows in web headers at every size (it falls back to the emblem only under 96 px), on every sign-in screen, in the owner's sidebar and on the customer welcome screen (a 24th place, customer-welcome, taking the blueprint's default, the logo); the emblem stays in app bars; the wordmark stays on printed receipts. Tests: no fixed marks, every place named is live, each screen shows its mark, markFor picks by room.
- The footer (section 26) now shows: the main footer on the web apps (browser frame, account site, owner's web view) with every 26 A column, payment methods from the chosen country's pack as LynkOmni icons with the provider's name as text, social channels as text links, an unticked double-opt-in newsletter and the fixed copyright line; the one-line short footer inside the apps (merchant phone, terminal, counter tablet, rider phone). Its 61 words are translated into all 26 languages (web/footer). The tagline is the section 5 positioning line only ("Works with or without internet."). App Store and Google Play are protected names.
- 44 px touch targets (41 B), enforced by the accessibility check on every screen (it checked 24 px before) and fixed everywhere it failed.
- Text up to 200% (41 B): a new test opens every emulator at 640 px (a 1280 px window at 200% zoom) in English and long text.
- The Step 0 country switch reads "A country where partners are not signed yet" (42 A), in every language.
- Language wave 2 is the blueprint's twelve (43 G); the order I had generated is replaced, and the section numbers I had invented for later waves are removed (the blueprint defines waves 1 and 2 only).
- Bundled code drops whole-line comments (smaller files). The account site's file budget is 520 KB: it carries the shell, account and footer words in 26 languages (a real app downloads one).
- tools/translation/update_keys.py updates changed translations without retyping the rest; it compares with the last committed English.

## v0.23.0 (2026-11-09)
Build section 3, the Business app and the whole of LynkPOS (blueprint 41 S row 3, 42 I and J row 3, 44 L row 3, 45 E row 3), built and locked.
- Device commands for the whole till (dv/box.py): shifts with opening float, cash counts and differences flagged for the owner (never blocking), the customer credit book with reminders, vouchers, parcel and order pickup by code, restaurant tables, kitchen tickets, splitting a bill, tips, closing a table, the staff time clock, delivery steps with proof, and practice mode (a clearly marked copy that never syncs). Agent, collection and partner requests are online only and never queued.
- The cloud side (merchant/): agent point mode with licensed partners, limits per tier, float read from the partner, low-float warning and forecast, statement matching, collections and referrals (cash only after the partner confirms; LynkOmni never holds the float or pays commission); deliveries with partner quotes or the shop's own riders; restaurant limits; buy together; registered devices and the web rule (selling, cash, shifts and agent services only on an enrolled device); the business profile (tabs by business type, setup in under two minutes, receipts by tier, second currency, sell by voice, day close, data sharing with suppliers by consent). 20 section-3 automations run on LynkFlow.
- The same rules in TypeScript (ts/src/business.ts, agent.ts, restaurant.ts), proved against contract/vectors/pos.v1.json. 75 TypeScript tests.
- Nine new real-device emulators on one shared device runtime (ts/src/emulator.ts): counter tablet with customer screen, kitchen screen, customer display, rider phone, stock scanner, button phone (short-code menu), LynkVCard as a real card (freeze shows only after the issuer confirms; details only after step-up, never offline), LynkMesh relay between two devices, and the owner's web view on a laptop. The handheld terminal gained its 12-tile home, agent services, codes, credit and a low-literacy setting; the merchant phone gained agent point mode.
- Every screen word of the POS devices (390 texts) and every new emulator translated into all 25 other languages and checked automatically.
- Leftovers fixed in this section (owner rules 2026-11-08 and 2026-11-09): a country pack for every ISO country (247) instead of 9, with names in every interface language, 154 currencies and a plan of language waves; the emulators' data now travels compressed (English stays plain), so every file is back under the 480 KB default and the three raised budgets were removed; the speed test now times the moment the app is ready, not only page load; the accessibility check judges tap size in the real device's pixels; a new layout test walks every screen of the nine new devices in every language, long text and right to left at desktop and phone size, plus the dark theme, and the faults it found were fixed (wrapping, a clashing class name, contrast of small notes, a 24 px chip).
- The new devices' brand buttons named a design token that does not exist (`--text-on-brand`), so the dark theme showed dark text on violet (3.7:1); they now use `--on-brand`, and a new test refuses any CSS variable that is not a real token. CI now installs Babel 2.18.0 so it can re-check the generated country files.
- Each language wave now names its build section (wave 2, ten languages, in section 4; one a section after it), and a test refuses to lock a section while its wave is missing; every planned language has its English name (Samoan and 19 others were shown as bare codes).

## v0.22.1 (2026-11-08)
- Showcase: `python3 tools/showcase.py` builds one offline page of everything completed (emulator pages, the 15 build steps, numbers from tools/blueprint_numbers.py, products with prices and pictures, LynkVCard faces, charts and diagrams, other pictures, store and web images) from web/showcase/showcase.v1.json and the code. Published for the owner after every section (owner rule 2026-11-08).

## v0.22.0 (2026-11-08)
Build section 2, LynkOmni Account and sign-in (blueprint 41 S row 2, 42 J row 2 and 44 L row 2), built and locked.
- The account rules in Python (identity/account.py, on the identity platform and the layered recovery of section 10): sign-up as four steps (username in the Instagram format, a verified phone or email, a passkey, the recovery code shown once); passkeys (never the last one removed, a fresh step-up to remove); sessions bound to one site, with an alert on every channel and no link in it when a sign-in comes from a new device or place; the Security Center (passkeys and devices, sessions, recent events, recovery settings, connected apps and sharing, memberships); data-sharing consents with a scope, a purpose and an end (health pack, accountant, lender, developer app, support, supplier sell-through; capped days per scope); the takeover safeguards of 43 H (a 24-hour wait before payout details change unless a second enrolled device approves; exports need a step-up and never run from a device still restricted after recovery); download-my-records with a 30-day due date; closing with a 30-day grace period and a LynkID and username that are never reused; businesses, leaving (never the last owner) and the accountant's client switcher, which shows a client only with the owner's consent; subscriptions read from billing; N14 Start a business (four steps, "Coming to your country soon." where no gateway is signed, nothing approved before the authority answers) behind a new `registration` service and its sandbox gateway in the provider ledger; N4 standing payments (the customer's own capped instruction, held by the licensed provider, told every time, revocable). 17 Python tests.
- The account event register identity/events.v1.json: every account event the cloud writes, with references only; a test keeps every automation trigger up to the built sections on a registered event.
- LynkFlow runs (services/flow.py): only registered automations run, once per trigger, loop-guarded, with "Why did this happen?", history and an off switch per subject. The seven section-2 automations run on it (identity/automations.py): sign-in alert, recovery guide, consent expiry, data-request timer, start-business tracker, quiet-business watch (draft) and renewal reminders.
- The same rules in TypeScript (ts/src/account.ts), proved against the shared vectors contract/vectors/account.v1.json (tools/account_vectors.py). 4 new TypeScript tests (71 in all).
- The account-site emulator (web/emulators/account-site): account.lynkomni.com in a browser window at computer, tablet and phone size, built on the shared shell: sign-in with a passkey, the four sign-up steps, the three recovery paths with their waits and the restricted day, the Security Center, businesses with the client switcher, orders, transactions, wallet, plans, memberships, privacy and data, notifications, support, payslips, standing payments and Start a business; in all 26 languages (25 packs written and checked), walked by the layout and accessibility test at every size.
- The shared shell's words moved to web/shell/strings.en.json with their 26 packs, merged into every emulator built on the shell, so the shell is translated once.
- Catalog: the account site's addresses (/, /sign-in, /sign-up, /recover, /profile, /security, /businesses, /wallet, /billing, /memberships, /privacy, /support, /start/{LODOC}); the `accountant` role (reads only, with consent).
- Leftovers adjusted in this section (owner rule of 8 November): the data-request timer is a daily schedule; two shell events of section 1 (CountryPackSelected, ConnectionWeak) are now registered; an invented identifier (LOSEC-) in the browser-frame notice is LONTF- and a test keeps emulator ids to the registry; the recovery and payout waits are hours, as the blueprint says, not days; placeholder-only strings pass the script check. The account-site file budget is 900 KB with its reason (26 languages of the shell and the site in one offline file).

## v0.21.1 (2026-11-08)
- Dependency updates taken in (owner rule of 8 November: merge them without asking once the checks are green and nothing else is pending): the GitHub Actions moved to their current major versions (checkout 7, setup-node 6, setup-python 6, setup-java 6, cache 6, upload-artifact 5) and the pinned Python and Node packages to their latest releases (Dependabot pull requests #29 to #36; #30 was superseded by the same change on #39).
- The Kotlin job caches its Gradle downloads and retries up to five times when GitHub's release store times out, so a 504 no longer fails a run.
- Traditional Chinese: the engine's language tag is `zh_Hant` (MADLAD-400 writes the script with an underscore); the test that had pushed it to a hyphen now accepts the underscore, and the translation workflow passes again.

## v0.21.0 (2026-11-08)
Build section 1, the shared shell (blueprint 41 S row 1 and 44 L row 1), built and locked.
- The shell component library (ts/src/shell.ts, web/shell/shell.css): translator, viewport, header, navigation (tabs on a phone, rail on a tablet, sidebar on a computer), app launcher, account menu, language and region sheet, "find or do anything" search and command bar, help panel, notifications with quiet hours, every screen state with its picture and next step, connection chip and sync sheet, data-saver plan, deep links from the address map, protected zones, undo toasts, continue-on-any-device handoff, two-language chat banner and notes, the username field and accessible charts. 19 TypeScript tests.
- The browser-frame emulator (web/emulators/browser-frame): the shell in a browser window at computer, tablet and phone size, every state, every overlay, dark, lite and sunlight modes, the country chooser and all languages.
- Speed and accessibility in the build: size budgets per emulator (web/budgets.v1.json, tests/test_speed_budget.py) and LynkOmni's own accessibility checker (tools/a11y/check.js) run on every screen in English and the right-to-left test, light and dark; a new `on-brand-hover` token and contrast fixes that came out of it.
- Icons: @lynkomni/icons 1.4.0 vendored (eleven shell icons and the twelve low-literacy tiles); emulators embed only the icons they use.
- Language wave 1: German, Italian, Turkish, Indonesian, Vietnamese, Russian, Chinese (simplified and traditional), Japanese and Korean, making 26 languages. Chinese, Japanese and Korean fonts are split into blocks within a per-slice budget; every emulator is translated into all 26 and the layout test walks every screen in each of them at every size.
- Leftovers adjusted in this section (owner rule of 8 November): the Chinese traditional machine-translation code, visuals regenerated after the token change, the chat demo always showing two different languages, and the layout test measuring after the browser's next frame.

## v0.20.0 (2026-11-08)
Step 0, one global structure (blueprint 42 A and 44 L row 0), built and locked.
- Contract version 2: every amount is an integer in its currency's minor unit and carries its ISO 4217 currency; one currency list (contract/currencies.v1.json, 37 currencies) that the contract and the code both read; version 1 is never edited and stays readable through the upcaster (contract/upcasters.v1.json, contract/upcast.py); the 104 event names of blueprint sections 42 I, 44 E, 44 G, 44 I (N1 to N14), 44 J and 45 A are registered with their payloads, and 22 new device commands issue the new device events (agent, financing and delivery requests are class C: never queued offline). Generated by contract/tools/build_v2.py; the validator runs 893 checks.
- Emulators open on a neutral sample country and carry a country chooser listing every country pack; what works in a country is read from the provider ledger; a test fails if a country name or currency code is ever written into an emulator's source.
- Rule texts, revenue stages and test titles speak of the country pack: one pending-fiscal adapter for any tax authority not yet confirmed in writing; stage names proving ground, regional scale, global scale; tools/blueprint_numbers.py also prints the contract version, event types, currencies and country packs.
- One global chart of accounts (contract/chart-of-accounts.v1.json, 20 accounts) and the double-entry journal as a projection of the event log at every tier (core/accounts.py, LynkAcc journal and trial balance); a country pack may map the global codes to its own labels.
- The shared username check (contract/usernames.v1.json, core/usernames.py, ts/src/usernames.ts, 42 shared vectors): Instagram format 3 to 30, reserved words from the rule, the product catalog, the address hosts and the provider ledger, web-address endings refused, look-alikes held for review, one owner forever, never reissued, old names redirect, transfer only by a recorded staff decision with a 90-day redirect.
- Portuguese is the 16th language (fonts, both emulators, layout test). The dependency-updates automation runs through .github/dependabot.yml as drafts.

## v0.19.2 (2026-11-08)
- The owner's 14 to-dos locked as the REMINDER in the provider ledger (none mandatory before building).
- General rule (owner, 8 November 2026): anything left out is adjusted automatically during the build, in the section it belongs to, and recorded; written into CLAUDE.md, the decisions diary and blueprint section 40.
- Final deep scan, part two. The address map now holds every product's place in the Business app (/business/money, /pay-links, /recovery, /cards, /plans, /loyalty, /growth), the shared LynkStat dashboards (/analytics/shared) and the account site's /invoices, /orders and /transactions, with a new test: a product's place must be a registered address, so the catalog and the address map can never drift apart.
- Blueprint brought in line with the later decisions in sections 9, 13, 16, 17, 20, 21, 23, 24, 25, 28, 29, 30, 38, 41, 42 and 45: the global rule replaces the one-type pilot and one-country segments, legal pages at /legal, support levels from billing, 40 identifier types, price lock version 3, LynkInv in place of the old invoicing table, six new risk rows, the stack table as it runs in CI today, and the automation table read from the register.

## v0.19.1 (2026-11-08)
- Nine more automations for speed and trust: undo for anything within 30 seconds, a speed budget per screen, continue on any device, a quiet-business watch for support, renewal reminders, one-tap reorder, an automatic accessibility check in the build, automatic data saver, and a visible reply-time promise in support. 105 automations in all.

## v0.19.0 (2026-11-08)
- Automation across LynkOmni: one list of 96 automations, from the daily close and stock reorders to invoice reminders, support triage and partner failover, each with a clear level (tell, prepare for a person, do with undo, or do) and checked by safety tests.
- LynkAssist is placed in every section to answer, guide, prepare drafts, explain, summarise, watch and support, and it never moves money or acts without the right confirmation. Custom automations come with LynkAssist plans (0, 3, 20, unlimited).
- The expense model includes LynkAssist's running cost across the ecosystem.

## v0.18.0 (2026-11-08)
- LynkStat, the new analytics service, takes over LynkDash: $0, $12, $29 and $79. LynkOps now bundles four services (accounting, invoicing, CRM and analytics) at $0, $20, $49 and $129. LynkSuite keeps its price, so it is now about 37% cheaper than buying its services.
- Two new record numbers: LODOC- for business documents and LOREV- for verified reviews.
- The limits and fees of 14 new services are set (restaurant mode, payroll, tax filing, standing payments, e-signature, get paid early, device lease, delivery, warranty, reviews, buy together, supplier sell-through, Academy, start a business). Each is built in its own build section.
- New expense model: LynkOmni's expenses and net profit per day, month and year, beside the revenue. Every figure is an assumption.
- The address map knows every new path and the partners.lynkomni.com door; usernames follow the Instagram format.
- Fixed: two daily limits (developer API calls and ads) now count days in UTC, like the event times, so they no longer break around midnight.

## v0.17.0 (2026-11-07)
- The whole LynkOmni system was reviewed end to end and every conflict fixed, so all parts work as one. There is now one product list, one address map and one email map, and automatic checks stop them from ever disagreeing with the footer, billing or the code.
- Support follows the plan: every product's Plus gives priority help, Pro higher priority and Max a dedicated manager, including LynkPOS and LynkSuite.
- The footer lists LynkOps, LynkCheckout and LynkRecover. The "not available" picture is now "coming soon", matching the rule that users never read "not available".
- The revenue model counts every income stream across the ecosystem (agent services, setup fees, hardware, partner referrals) minus discounts and partner costs, per day, month and year. The new rates are assumptions.

## v0.16.3 (2026-11-07)
- Fourteen safeguards added to the email plan, among them a second emergency admin account, phishing-proof sign-in for both admins, and no sign-in links in security emails. The owner's steps after paying for Google Workspace are on the action list.

## v0.16.2 (2026-11-07)
- The full list of LynkOmni and CruxOmni email addresses is agreed and written down, with the steps to set them up. Sign-in codes and security alerts come from a no-reply address; every other email can be answered.

## v0.16.1 (2026-11-07)
- The LynkPOS services are agreed and written down: 31 services in 6 groups, agent point mode, how each one reaches the books, customers, stock and reports, and how LynkOmni stays out of holding money. They are built in build section 3.
- New working rule: the real-device emulators are updated whenever the product changes, and every agreed emulator has its place in the build order.

## v0.16.0 (2026-11-07)
- New prices, locked as version 2. LynkPOS is now $0, $12, $29 and $79 a month, with every agent, collection and partner service at every level, unlimited sales, and an Agent point mode planned for vendors who run LynkPOS full-time.
- Three standalone services: LynkAcc for accounting (it takes over LynkLedger), LynkInv for invoicing (moved out of LynkCheckout, which keeps pay links and QR) and LynkCRM for customers. Each can be bought alone; LynkOps puts all three together for less ($0, $12, $29, $79).
- Invoicing is friendlier on Free: five invoices a month, credit notes and a pay link on every invoice at every level.
- LynkSuite now holds nine services for $0, $29, $75 and $195, and also replaces LynkOps. A business is never billed twice: bundles replace their services, LynkPOS Pro and Max include LynkRewards, and a service above its bundle's level costs only the difference.
- The revenue model was re-run with the new prices (the adoption mix, including the new services, is an assumption, not a forecast).
- New pictures for LynkAcc, LynkInv, LynkCRM and LynkOps, and the LynkSuite picture now shows nine services. The website footer lists LynkAcc, LynkInv and LynkCRM.
- LynkInv and LynkCRM work in every country from day one, like LynkPOS and LynkAcc, because they need no partner.

## v0.15.0 (2026-11-07)
- The LynkOmni merchant app, as a phone you can click: sign in with a phone number and a code, the phone registers itself with its own security key, then the five tabs Home, Sell, Stock, Chats and Business.
- Home changes with the person: the owner sees today's sales and profit, a big New sale button, stock that needs attention, unread customer chats, one insight for the day and what is waiting to send; staff see selling and stock first, and profit only if the owner allows it.
- Selling works with or without internet. Stock may go below zero (a sale is never blocked) and the owner is told to count it. Stock received, counted or removed with a reason. Customer chats show their real state (queued or sent). Business shows the day's closing summary, every LynkOmni service with "Coming to your country soon." and Notify me where its partner is not signed, and who may see profit.
- The connection chip and sync sheet: a weak connection counts as offline and sends when it can; "stay offline to save data"; nothing is ever shown as paid before the provider confirms.
- All screens in all 15 languages (translated by Claude, checked automatically), and the layout test now opens every phone screen in every language at desktop and phone size.
- The owner's actions list now includes the company email (domains bought), company registration, the GitHub Team plan (last) and the Google Cloud account.

## v0.14.0 (2026-11-07)
- The LynkPOS terminal emulator now works in all 15 languages (English, French, Spanish, Swahili, Kinyarwanda, Arabic, Persian, Urdu, Pashto, Kurdish, Sindhi, Uyghur, Hebrew, Yiddish, Hindi), with right-to-left layout where needed, all inside the offline file. Every screen text is translated by Claude and passes automatic checks: names, amounts and placeholders unchanged, no repeated or added words, the right script for each language, nothing left in English.
- The translation engine for text people type is installed: Google's MADLAD-400 model (Apache 2.0 licence, so commercial use is allowed), replacing Meta's NLLB-200, whose licence forbids commercial use. It is installed on GitHub's machines (workflow "translation"), which check the licence and pin the exact model version. It refuses any translation that drifts in meaning, repeats itself or adds words, and then shows the original text instead.
- The automatic layout check now opens every screen in every language at desktop and phone size, with the brand's Noto fonts for Arabic, Hebrew and Hindi.
- Still to come: running the engine on LynkOmni's own server for text people type; until that server exists such text shows in the original, marked queued.

## v0.13.1 (2026-11-06)
- Translation works offline: screen text is translated ahead of time into language packs that ship inside the apps, so every language works with no internet and no engine on the phone. Text people type is translated on LynkOmni's server when online, saved on the device, and shown in the original (marked queued) when offline.
- The Meta NLLB-200 engine is connected behind the translation slot (compact int8 version, loaded only from LynkOmni's own server, never downloaded while the app runs). Every language has its NLLB code. The model itself is installed once package installs are allowed.

## v0.13.0 (2026-11-06)
- Machine translation for every language, the way large platforms do it: one engine slot (Meta's open NLLB-200 model, the engine behind Facebook's translations, to be installed when package installs are allowed). Brand, product and provider names, amounts and numbers are protected; a damaged translation is refused and English is kept.
- Translations can never break a screen: the terminal emulator has a long-text test and a right-to-left test, and a new automatic check opens every screen in four languages at desktop and phone size and fails if any text spills over or the device changes size.
- Native-speaker review dropped from the owner's actions list.

## v0.12.4 (2026-11-06)
- LinkedIn link corrected: LynkOmni is a showcase page under the CruxOmni Group company page.

## v0.12.3 (2026-11-06)
- The footer now links to the official LynkOmni accounts on LinkedIn, X, Facebook, Instagram, YouTube, TikTok and WhatsApp Business. The LynkOmni name is claimed on all ten platforms.

## v0.12.2 (2026-11-06)
- Recorded that the remaining owner decisions follow the global rule: every business type, standard devices, every supported language, competitors stay competitors, merchants own their data.

## v0.12.1 (2026-11-06)
- Recorded the nine approved experience improvements in the decision diary (they are built during building).

## v0.12.0 (2026-11-06)
- Global availability rule: every service is shown in every country. Services that need no licensed partner (POS, books, stock, dashboard, insights, chat) work everywhere, even in countries without their own settings file. Regulated services say "Coming to your country soon." with a Notify me option until their partner is signed, then switch on by themselves.
- Notify me list: needs the person's consent, keeps only a reference to their contact details, and tells each person once when the service arrives.

## v0.11.1 (2026-11-06)
- Recorded the owner's decisions on the footer social channels, the build order and the POS additions; added "claim the LynkOmni name on every social platform" to the owner's actions list.

## v0.11.0 (2026-11-06)
- Payment methods follow the country. Rwanda shows Visa, Mastercard, MTN MoMo, Airtel Money, bank transfer and QR payment; every other country shows its own list from its country file. Visa and Mastercard appear everywhere; crypto appears only where a country allows it and a licensed partner exists (none today).
- Six new LynkOmni payment icons (card, mobile money, bank, instant bank payment, phone wallet, digital asset) in icon package 1.3.0. Each method shows our icon with the provider's name as text; drawn copies of other companies' logos were removed from the footer preview. Official provider artwork is added only when a provider is signed and supplies it.
- The terminal emulator's payment screen uses the new icons. The brand-sync workflow now rebuilds the emulators by itself.
- Fixed a rare false alarm: the personal-data check no longer mistakes a random record ID for a phone number.

## v0.10.1 (2026-11-06)
- Working standards: a rule book (docs/lynkomni-standards.md), a finish checklist used on every change, changes tested on a copy before they enter the main version, version numbers with this change log, and a decision diary (docs/lynkomni-decisions.md).

## v0.10.0 (2026-11-06)
- LynkPOS handheld terminal emulator: a clickable card machine with printer, keypad, tap lights, card slot and scan key, running the real sale rules on practice providers.
- Brand fonts Montserrat and Inter, self-hosted and offline.
- Full font system for 15 languages, including Arabic, Persian, Urdu, Hebrew and the other right-to-left languages, and Hindi.
- Swift tests run on Linux on every change; a weekly Mac run.

## v0.9.9 (2026-11-06)
- Provider ledger: every provider service has a practice version and stays off until signed; the later list; the owner's actions list.
- LynkVCard card backs, physical OMNI card and CORE near-limit state; merchant logo safety check; install manifest for the web app.

## v0.9.8 (2026-11-06)
- Automatic pictures system: product illustrations, screen states, onboarding, charts, diagrams, share and store images, app and web icons.
- LynkVCard tier faces (EDGE, HUB, CORE, OMNI) and the tier ladder.

## v0.9.7 (2026-11-06)
- 43 one-colour icons from the lynkomni-icons package (product marks, status icons, everyday icons).

## v0.9.6 (2026-11-06)
- Invoices, receipts and emails drawn with the brand module (logo rules by tier, wordmark on receipts).

## v0.9.5 (2026-11-06)
- Logo placement rules for every place; "Powered by LynkOmni" rule; prices raised and locked at version 1.

Version tags are created automatically by the version-tag workflow when a new entry reaches main (from v0.10.1 on; v0.9.5 was tagged by hand, v0.10.0 has no tag).

Earlier versions (up to v0.9.4) are described in README.md and the master blueprint, sections 1 to 29.
