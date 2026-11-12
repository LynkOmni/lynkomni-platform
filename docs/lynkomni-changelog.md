# LynkOmni change log

What changed in each version, in plain words, newest first. Version numbers: `0.MINOR.PATCH` until the first pilot (a new feature raises MINOR, a fix raises PATCH). Each version has a Git tag `v<number>`.

## v0.42.0 (2026-11-11)
NEW UPDATE 4, section 1 (shared shell and design):
- LynkAttend, LynkQueue and LynkSurvey are in the app launcher with their plain words, and in the footer under "People & service"; their product marks (an arrow going in through a door, a ticket, a clipboard with a tick) come from @lynkomni/icons 1.7.0.
- The device names for the whole of LynkOmni are on the screens: Change view says LynkMobile, LynkTab or LynkPC; the Business app calls its devices LynkMobile and LynkTab; the customer display is the LynkPOS customer screen; emulator titles and the showcase name the device each one runs on.
- Shared parts for the three services, by touch and by keys: the ticket card (the big ticket number, the section, your place as a plain number and the estimate, or "It's your turn" with the counter), the IDCN entry (dots, never the digits) with the checker notice and the list without your own name, the quick rating with a word under every face, the 0 to 10 score and "Rate us" with its QR.
- 33 new and changed screen words in all 38 languages.

## v0.41.0 (2026-11-11)
NEW UPDATE 4, Step 0 (LynkAttend, LynkQueue and LynkSurvey: one global structure):
- Three new services, each its own plan outside LynkSuite: LynkAttend (attendance) $0 / $49.50 / $95 / $179, LynkQueue (queue and tickets) $0 / $55 / $115 / $249 and LynkSurvey (surveys) $0 / $59 / $155 / $249 a month, with people, places or creators included and a price for each extra; 20% off when two or three are held together. Pro and Max were topped up a little for the links across LynkOmni; Free and Plus stay as agreed. Prices are pinned by the price lock.
- Their places everywhere: product pages, the Business app (/attendance, /queue, /survey with their lists and the Storefront side), the account site (My details, My tickets, My answers, the Panel), public pages (the queue page, ticket tracker, survey and verified-results pages, certificates) and every menu, the footer ("People & service") and search.
- New public identifiers LOSRV- (survey), LORSP- (survey answer), LOVIS- (visitor) and LOATT- (attendance record); contract version 6 with 47 new events and 14 commands that work offline; nothing secret (a PIN, IDCN, ID number, face or finger pattern, phone number, position or anonymous identity) is ever in an event.
- The rules, the same in Python and TypeScript: the IDCN from an ID number, PINs that are never easy, never given twice and never reused, the door order Face, Finger, IDCN with every backup marked; ticket numbers like LAB-A2K9P2 from the Lynk Alphabet (1.07 billion per section at each place, never used twice, rude words skipped), a fair order staff cannot change; one person one answer, results never shown for fewer than 5 people, sample size and margins.
- The device names for the whole of LynkOmni: LynkMobile, LynkTab, LynkPC, LynkPOS, LynkKiosk, LynkDScreen and LynkCDisplay (hardware without a screen keeps its plain name and runs through LynkDriver, which gains fingerprint readers, pagers, feedback buttons, speakers and number boards).
- Registers: 17 messages, 32 automations (every link across LynkOmni, only when switched on), LynkAssist actions and answers, 7 security controls, 3 open APIs, the queue ticket tracker, a new build section 3B (the three in full on every emulator, before section 4); every country pack carries the attendance and survey settings (unconfirmed until the lawyer checks); text, WhatsApp, USSD, voice-call and reward partners are sandboxes until signed; the revenue model shows the three as their own assumed stream; three new product pictures.

## v0.40.0 (2026-11-10)
MASTER UPDATE, section 3 (Business app and every LynkPOS device):
- Each person signs in to a device with their own PIN, also offline: a wait after wrong tries and a hard lock that never wipes; the owner or a manager resets a staff PIN on the spot (never the owner's own PIN, which only online recovery resets).
- A duress PIN opens a quiet limited till while the alert leaves by the first path that appears (text, a nearby device, then the internet); nothing calls the police by itself.
- Offline limits by role: above a cashier's limit a void, refund or larger discount needs a manager's PIN on the same device, or Ask the owner, who answers in one tap.
- The owner locks a device from afar (owner or manager after a check) and only the owner wipes one, after a fresh check and after being told how many records were never sent; an altered app holds its uploads for the owner and selling still works; the owner keeps an encrypted offline backup.
- LynkAssist on devices and in the Business app: selling, shift, cash, stock and device fixes; offline, device fixes run at once, cloud fixes are confirmed, sealed and shown as queued until the cloud does them (they expire after 7 days), and partner or person work is prepared to send later; the owner switches areas off, asks to approve fixes first, or gives standing permission for chosen fixes; one history with Undo.
- Notifications: role routing with "Done by", the owner's thresholds (cash difference, low stock, a cashier's offline discount), banners on the terminal, tablet, kitchen screen and scanner, each device's own offline bell merged without doubles, the owner's daily or weekly summary (opt-in), and receipts or documents by text or email only when the customer asks.
- Basic phones: a LynkOmni account by menu numbers (sign up with the age step, username, PIN and terms; sign in with a hard lock; messages and help), and notifications read by text.
- Breadcrumbs in the Business app and on devices; the card type word (PREPAID, DEBIT or CREDIT) on the card screens; the card emulator shows all twelve sample cards and Get a card waits for the licensed partner's answer.
- Leftovers fixed: the LynkAssist register had no shift and cash actions (reprint receipt, recount cash, hand over the shift) and no offline rule per action; the card form words were moved to the shared device words; two pages had clashing names inside one bundled file (a Business app freeze), so the bundler now refuses duplicate names; hardware attestation is listed as later work with a sandbox check now; the Ask box in the help panel spilled out of narrow device screens (the scanner), so it now shrinks to fit.
- Size budgets raised for the device emulators, the Business app and the pages that share the device shell (these parts in 38 languages; a real app downloads one language at a time).

## v0.39.0 (2026-11-10)
MASTER UPDATE, section 2 (account, security and notifications):
- The larger Security Center: a security check-up with Fix this, two ways in, Lock everything (signs out everywhere, sends a freeze for the cards and pauses app keys; location shares keep running; unlocking needs a fresh check), "This was not me", advanced protection (passkeys only, longer waits), a cool-off after a new device, a slow contact change the old contact can cancel, who at LynkOmni looked at the account, and a successor ("Coming to your country soon." until the law and a partner are in place).
- Sign-up by phone or email side by side, two ways in at the last step, start now and confirm later with the device's records joined after a check, and the agreed terms recorded at sign-up and shown on the Privacy page.
- Notification settings: what comes where (security and safety always on), mute per business, pause all optional, do not disturb, one summary a day, what the lock screen shows, a deputy for up to 90 days (security and account stay with the person), a test and a channel check, and personal reminders.
- New security and account messages (contact change, cool-off, everything locked, not me, successor, personal reminders), read on one device is read on every device, and the new Messages page.
- LynkAssist on the account site: answers by class, account actions through the register only (class C after a fresh check; recovery and passkeys only prepared), and "Everything LynkAssist did" with Undo.
- Breadcrumbs, the bell and LynkAssist's Ask box on the account site; a person's cards listed by group (LynkPrima, LynkDyna, LynkCrest, last four only, the lender's interest and fees beside LynkCrest).
- Leftovers fixed: card records had no group; security notice kinds were missing for the new protections; LynkAssist's decisions had no event of their own (AssistActionRecorded); the bell's small action button was under the 44 px touch size; the "Why did this happen?" link on LynkAssist's receipt was too faint in dark mode.
- The account site's size budget is raised to 1200 KB (these parts in 38 languages; a real app downloads one language at a time).

## v0.38.0 (2026-11-10)
MASTER UPDATE, section 1 (shared shell and design):
- Safe page settings on every page: only the page's own script runs, pinned by its hash; nothing loads from anywhere else. Sessions now belong to the device that signed in.
- Shared sign-in parts: a PIN pad with pictures and a tone for each key (digits never shown, keys never move), and number matching for face-to-face permission.
- The notification bell on every screen: New and Earlier, filters, folded repeats, actions with "Done by" and Undo, "Why am I seeing this?", an empty state, banners, and sound and vibration by priority (urgent breaks through and repeats until seen). Private lock screens.
- The message parts: the email, the text message (with its length in parts) and the Messages list.
- LynkAssist in the help button: Ask (answers offline from the saved help in every language), Fix this, the Confirm or Deny card and the receipt with Undo and "Why did this happen?".
- Breadcrumbs from the address map on every screen, and the head for public pages (title, description, one address per language, search engine trail).
- The twelve sample LynkVCard cards (three groups on the four faces) in the fixed layout, fronts and backs, with layout and contrast tests.
- Leftovers fixed: the footer newsletter form no longer uses an inline handler; event-log icons in the shell emulator have their size; a device page carries only the shared words it can show.
- The shell emulator's size budget is raised to 740 KB (all these parts in 38 languages; a real app downloads one language at a time).

## v0.37.0 (2026-11-10)
MASTER UPDATE, Step 0 (groundwork for sections 54 to 62):
- Security register (catalog/security.v1.json) with its seven principles, a secret scan in CI and a tamper-evident chain on the event log.
- Offline sign-in rules: device keys, a clock that cannot be turned back, PIN lock with a hard lock (never a wipe), "start now, confirm later" accounts, face-to-face permission, and an attack bank of 12 cases.
- One register for every message and notification (catalog/messages.v1.json) and its engine: the bell, four priorities, folding, quiet hours, daily cap, repeats and escalation, in the reader's language.
- LynkAssist registers (catalog/assist.v1.json): action classes A to D, five answer classes, a question bank and a signed offline knowledge pack in all 38 languages.
- Search register and breadcrumbs from the address map.
- LynkVCard card groups: LynkPrima (prepaid), LynkDyna (debit) and LynkCrest (credit) with Free, Plus, Pro and Max; sample details that can never work as a real card; online-only requests answered by the licensed partner; sandbox account partner and lender in the provider ledger.
- Contract version 5 (card request events; upcaster 4 to 5 changes nothing).

## v0.36.2 (2026-11-10)
Cash everywhere it applies (owner rule).
- **Pickup-point mode:** when money is due, the pickup point now chooses **Cash received** or **Electronic payment**.
  - Cash: counted, recorded and handed over at once, also offline; it joins the till's expected cash.
  - Electronic: handed over only after the provider confirms, as before. If it fails, cash can still be taken.
- **One list for cash:** catalog/cash.v1.json names every place money is taken in person, whose cash it is, and the build section that builds it. Built places must show the cash choice on their screens (tests/test_cash.py); the planned ones are built in sections 4, 7, 7B and 8.
- **Where cash does not apply** is listed with the reason: remote payments, LynkOmni plans, cards, agent point services, exchange.
- New words in all 38 languages.

## v0.36.1 (2026-11-10)
- **Fix, buttons-only devices** (owner report): on the "Buttons, no touch" versions of the POS terminal, stock scanner and kitchen screen, pressing the pad keys on the device body with a finger or a mouse did nothing useful. Every press jumped back to the first control, and OK never reached the control you chose. The pad key was taking the focus away from the screen. Now the pad never takes the focus, and the screen remembers its place, also after it redraws.
- **New test:** it presses the pad with real mouse clicks and finger taps. The old test used only a keyboard, which is why it missed this.

## v0.36.0 (2026-11-10)
NEW UPDATE 1, section 3 (devices).
- **LynkDriver:** six new kinds of device in catalog/drivers.v1.json: vehicle tracker, car plug-in (OBD), tag, electronic seal, condition sensor and satellite tracker. Each falls back to a virtual device (the phone as tracker, or a photo seal), so nothing is ever blocked.
- **Rider phone:**
  - battery warnings at 20% and 10%, and a last message at 3% (DeviceLastReport);
  - an on-shift switch: off shift, nothing about where the rider is is shared;
  - every hand-over is one sealed record, and its hash is shown;
  - SOS on the watch with a confirm step (ProtectionAlertRaised).
- **Business app, pickup-point mode** at app.lynkomni.com/business/pickup-point:
  - parcels waiting;
  - hand-over with the parcel's own code (works offline) or the person's Collect Pass (checked by the cloud, so it needs the network);
  - pay on collection only after the provider confirms;
  - each hand-over is a sealed ShipmentHandedOver.
- **Planned business types:** delivery and fleet are recorded for build section 7B.
- All new words are in all 38 languages. The merchant phone and rider phone size budgets were raised, with a reason.

## v0.35.0 (2026-11-10)
NEW UPDATE 1, section 2 (LynkOmni Account).
- **Arrive Safe** on account.lynkomni.com/trips (identity/arrive_safe.py):
  - share a trip with people you choose, for a set time, under a location-share consent of at most 30 days;
  - a share ends by itself or with one tap, and is always shown to the person sharing;
  - a trip plan with a check-in deadline and trusted contacts, watched by the cloud, so contacts are told even if the phone dies.
- **Collect Pass** on account.lynkomni.com/collect: one code that changes every minute and collects every parcel waiting at any pickup point, once per parcel. The QR picture of the code comes with the pay pages in section 7.
- **My plans:** LynkMotion and LynkGuard appear on the billing page.
- **Account site:** Trips and sharing and Collect Pass are in the account menu and search, in all 38 languages. The file budget was raised to 920 KB for these words.
- **Contract:** every event matches contract version 4, and no position is ever stored.

## v0.34.0 (2026-11-10)
NEW UPDATE 1, section 1 (shell and design).
- **New LynkVCard faces,** one colour, finish and metal per tier:
  - EDGE: Aurora Teal, aurora waves, a point of light, silver chip;
  - HUB: Royal Sapphire, guilloche, a silver hub, silver chip;
  - CORE: Imperial Amethyst, a holographic band, a glowing core in its spend gauge, gold chip;
  - OMNI: Black Gold, gold pinstripes, foil edge, a gold globe and orbit.

  No number dots and no contactless symbol. Calm backs with a stripe, a plain panel for the issuer and the motif as a watermark. "LynkOmni Reserve Network" removed. 18 new colour tokens.
- **Plan marks:** product marks for LynkMotion (a route to a pin) and LynkGuard (a padlock in a ring), released in @lynkomni/icons 1.6.0 and vendored by the brand-sync workflow.
- **Launcher:** LynkMotion and LynkGuard are in the launcher of every emulator with their plain words; they open /tracking and /protection.

## v0.33.0 (2026-11-10)
NEW UPDATE 1, Step 0 (one global structure).
- **Billing:** LynkMotion ($0, $9, $29, $79) and LynkGuard ($0, $15, $49, $149) are new families outside LynkSuite. Each covers LynkTrace, LynkGPS and LynkSentry, with:
  - their limits and the LynkMotion extras;
  - LynkGuard's extra vehicles and the 20% pair discount;
  - the API prices.

  All are locked by the price test.
- **Catalog and addresses:**
  - product pages /motion, /guard, /tracking, /gps and /protection;
  - Business app paths under /tracking, /gps and /protection, each with its Storefront twin;
  - public pages /track/{LOSHP} and /track/{LOSHP}/custody;
  - placements for both products and the three services;
  - a "Move & protect" footer column in all 38 languages.
- **Identifiers:** LOAST- (asset), LOTRP- (trip or journey) and LOSNT- (LynkSentry incident), now 44 types in every code language.
- **Contract version 4:** 23 milestone events and 12 class A commands. No event carries a position. The upcaster from version 3 changes nothing.
- **Tracking:** new planned kinds (journey leg, vehicle trip, rental, security incident) with their words in 38 languages, and 16 automations registered for build section 7B.
- **Partners:** the "movement" service is on everywhere. Its partner parts (connected cars, monitoring centres, ship and flight data, satellite messaging, tracker data plans) have working sandboxes and stay off until signed. Five "later" items added.
- **APIs:** the API catalog lists one API for every family and the platform services (catalog/apis.v1.json).
- **Other:**
  - product illustrations for LynkMotion and LynkGuard;
  - the new service names are reserved as usernames;
  - a separate assumed revenue stream for movement and APIs;
  - build section 7B in the build order.

## v0.32.0 (2026-11-10)
Every service in every place (owner rule, 10 November 2026).
- Every product is now in the website header, the launcher, search, help, its product page, the sitemap and the footer. It is also on the pricing page when it has a paid tier, and in the app navigation when it has an app place.
- New footer entries, with plain words translated into all 38 languages:
  - LynkBooking (Travel & ticketing) and LynkEssential (Bills & connectivity) replace their plain links in Solutions;
  - LynkDev (Developer platform) leads the Developers column, with its own product page, lynkomni.com/developers.

  The Products column stays within its three sub-columns of six.
- 16 platform services and tier features are now in the placements register with their places:
  - LynkHub, LynkDoc, LynkAPI and LynkSDK;
  - LynkStatus, LynkFAQ, LynkFeedback, LynkSafety and LynkSupport;
  - LynkFlow and LynkMesh, and the Partner Hub;
  - LynkProof, LynkSplit, LynkAudit and LynkEdge.
- New tests make this the rule for every new service. A new billing family fails until it is placed everywhere, and the footer must show exactly what the register places there.
- Master blueprint: sections 49 (LynkMotion and LynkGuard) and 50 (open APIs for every service) added, and section 51 (every service in every place). LynkMotion and LynkGuard get their places when their groundwork is built.

## v0.31.0 (2026-11-10)
BIZZ & DEVICE, section 3 (the Business app, LynkPOS and every device).
- The Business app has its Storefront side, with its own pages:
  - Storefront home (/external/business);
  - Offers and a new offer;
  - stock for online orders;
  - buyer chats;
  - payouts.

  You switch from the Business hub, the account screen or search. A first paid offer waits for the partner's identity check. Storefront plans sit beside the LynkPOS plans.
- Stock held at online checkout (core/reservations.py, ts/src/reservations.ts):
  - a Storefront checkout holds free stock for 15 minutes;
  - the provider's confirmation sells it; a failure or the time frees it;
  - a counter sale is never blocked, and a clash becomes a flag for the owner.
- LynkDriver, one driver pack for every kind of hardware (catalog/drivers.v1.json, core/drivers.py, ts/src/drivers.ts, shared vectors):
  - install it online from Devices › Driver (/business/devices/driver) or offline from lynkomni.com/download/driver;
  - the app asks to install it as soon as hardware needs it;
  - updates are strongly enforced: security now, required in 3 days, normal in 7;
  - past the deadline the hardware pauses and a screen version stands in, so selling goes on.
- Every device in its touch and buttons-only versions:
  - the POS terminal, the stock scanner, the kitchen screen and the customer display each have a buttons-only version (the screen takes no taps; a navigation pad, the bump bar or a remote moves a thick focus ring);
  - the rider app runs on a phone, a watch and a car screen (voice only while moving);
  - the button phone comes as a button phone, a simple phone or a basic phone.
- Basic phones with no apps use LynkPOS by USSD, text message or a voice menu, through one engine (core/channels.py, ts/src/channels.ts, shared vectors). A sale needs the PIN, and the commands are numbers so they work in every language. The gateway is a sandbox placeholder until one is signed (provider ledger ussd_gateway).
- New checks:
  - Business app Storefront and Driver screens at their addresses;
  - section-3 placements;
  - buttons-only versions reached by arrows alone;
  - drivers, reservations and channels in Python and TypeScript.
- 97 new words in all 38 languages. Size budgets raised with their reason (web/budgets.v1.json).

## v0.30.0 (2026-11-09)
BIZZ & DEVICE, section 2 (the account).
- My Storefront on the account site (account.lynkomni.com/storefront, in the account menu, search and help). It shows:
  - your public page at shop.lynkomni.com/(username);
  - your Storefront plan and its share, read from billing;
  - the identity check before your first paid offer.
- The identity check is done by the licensed payment partner (a sandbox until one is signed; "Coming to your country soon" for real users). It shows "sent" until the partner answers, and only the cloud records the partner's confirmation (LOVER- case). Free offers never need it, and the new draft automation guides a seller through it before a first paid offer.
- Support follows the side: Storefront questions (selling, offers, buyers, payouts) go to seller support and are labelled so. Workspace questions go to the usual desks; safety and security keep their own desks on both sides. Priority is the highest across all plans, the Storefront plan included.
- Sign-up asks the person to confirm they are 18 or older, or of age where they live (the country pack can set a higher age). A birth date is never asked for or stored.
- The account site chooses its own view for the device (touch or not), with Change view and Why this view? in the account menu, keyboard and remote arrows, and touch gestures with button equivalents.
- Fixed on the way: on a phone, the page title moves to its own line under the header instead of being cut to "A..". The account-site size budget is now 860 KB (reason in web/budgets.v1.json).

## v0.29.0 (2026-11-09)
BIZZ & DEVICE, section 1 (the shared shell and the device rule).
- One device register (catalog/devices.v1.json: 7 device classes, 21 ways to use a device, 14 interfaces, 24 devices with their touch and non-touch versions, the key meanings) and one decision function in Python and TypeScript with 4,320 shared test cases. The order is always: your own Change view, the registered device, what the device reports about itself (never the browser's name), then the safe default that works with every input.
- The shell shows which side you are in (your workspace word or Storefront) in the header, and one tap switches sides from the launcher, the account menu or search. The account menu has Change view and Why this view?; a new view never starts in the middle of a payment, count or signature.
- Type and spacing per kind of screen (watch, phone, tablet, computer, TV, e-reader) come from the design tokens. Touch gestures (edge swipe, swipe down, long-press) always have a button or key that does the same; arrows, Home and End move through groups for keyboards, TV remotes and switch access.
- New checks: every view fits every width from 240 to 3840 px in English, long text and right-to-left (nothing spills over, nothing overlaps, no stretched picture, no sideways scrolling); everything is reached by keyboard with a visible focus ring; real phones and computers get the right view; key words and colours exist; each section-1 item is in the places the register lists.
- The showcase works out which device you opened it on (with the same decision function) and puts the emulators made for it first.
- Fixed on the way: the footer and home cards now shrink to a single column on a watch-sized screen; device emulators carry the shell's username helpers in the shell's own scope (no name clashes) and only the shell words they can show. Size budget: default 540 KB, browser frame 580 KB (reasons in web/budgets.v1.json).

## v0.28.0 (2026-11-09)
BIZZ & DEVICE, Step 0 (the global structure for the owner's locked plan; sections 1, 2 and 3 follow in their own changes).
- Every service has two sides with one name: the workspace (using a service for your own affairs: today's paths and prices) and the Storefront (offering to others and earning). The side is read from the address alone, in Python and TypeScript with shared test cases: Storefront paths in the Business app are /external plus the workspace path, and every app path is classified as mirrored, Storefront only, shared (stock, devices, notifications) or workspace only (the in-person till and partner work). Public Storefront pages, Explore and buying an offer have their addresses; external, explore and storefront are reserved usernames.
- New public ID LOLST- for Storefront offers (41 identifier types).
- Contract version 3: every event may say which side it belongs to; version 2 events read as the workspace side, never rewritten.
- One legal ledger per entity, every entry labelled by side; statutory reports and the draft tax return count both sides.
- Storefront plans in billing, locked like every price: Free $0 (8% share per Storefront sale), Plus $12 (5%), Pro $29 (3%), Max $79 (1.5%, at most $50 a sale), Enterprise by contract; one plan per account for every service, outside LynkSuite; the share only on Storefront sales, taken by the licensed provider. Support priority is the highest across all plans. The revenue model shows the Storefront as its own stream, an assumption kept outside the agreed totals.
- Every service is open to every entity (person, company, organisation), with the partner's identity check for each kind and a minimum account age of 18 or the local age of majority. Every country pack gains unconfirmed Storefront settings (seller income reporting, data location, age of majority).
- Placements register: every product and new item lists the places it must appear in (header, app navigation, launcher, account menu, footer, search, help, settings, product and pricing pages, sitemap, showcase).
- Provider ledger: merchant of record and tax on digital sales, live sessions, Storefront file storage and tap to pay on a phone, each with a working sandbox; later items for the Storefront lawyer review, the LynkDriver signing key and real-device checks; the hardware supplier step moves to "on demand".
- Automations: driver-update-reminder (built now), plus the Storefront payout notice, the first paid listing guide and the listing review notice in their sections (110 automations).

## v0.27.0 (2026-11-09)
Before section 4 (owner request): one tracking system for every service that moves through steps, office services for everyone (a person, a company or an organisation), and the footer, favicon and responsiveness fixes.
- Tracking: one register (catalog/tracking.v1.json) and one engine (services/tracking.py, with the TypeScript port ts/src/tracking.ts and shared vectors) follow 18 kinds of record from the event log: delivery, order, payment, agent request, group order, device lease, business registration, account recovery, data download, payout account change, staff pay, repair, invoice, quote, standing payment, collection, get paid early and tax return. Six more are planned with their build sections (support case 6, refund 7, shipment 7, booking 8, airtime/data/bill 9, exchange order 10). A step is reached only by an event the cloud recorded; the state chip uses only queued, sent, accepted, confirmed and failed; customers see only their steps (no ids, addresses, phone numbers or positions); live progress is a share of the trip in steps of 5%, never a position, and is cleared when the trip ends.
- Tracking is wired into the platform: every recorded event feeds it (core/events.py observers), it raises TrackingStepReached, and two automations use it: order-updates (tells the customer each step by SMS or chat in their language, quiet hours 21:00 to 07:00 in the shop's time zone unless the step needs them) and tracking-late-watch (tells the owner once when a promised time is missed). Automations: 106.
- New screens: the customer's tracking page (new emulator track-page, shop.lynkomni.com/track/(order)), the Business app's Deliveries list and delivery timeline, "On the way" on Home and "Deliver this order" on a receipt, the rider phone's tracker with "Share trip progress" (rider's choice, this trip only), and the account site's Orders page with the person's own order trackers. Every tracker is drawn by one look (ts/src/trackview.ts) so a step reads the same everywhere. The tracker words live in their own pack (web/tracking) that travels only with the tracker.
- Office services for everyone: accounting (LynkAcc), invoicing (LynkInv), contacts (LynkCRM), analytics (LynkStat), the LynkOps tier, stock (LynkStock), business chat (LynkChat), LynkAssist, pay links (LynkCheckout) and LynkSuite work for a person (household money or freelance work), a company of any size, or an organisation (non-profit, school, faith group, association or club, cooperative, public body). catalog/workspaces.v1.json and core/workspaces.py set the words, tabs, income and expense categories (each posts to one global chart account) and organisation funds (restricted or unrestricted). Prices, limits, events and rules are the same for everyone. The Business app setup asks "Who is LynkOmni for?" first; the account site has "Run your affairs" to start a personal, company or organisation workspace.
- Footer: the full LynkOmni logo (light and dark versions) sits above "Works with or without internet"; long lists wrap into columns of six so there is no empty space, and future items follow the same rule; every product's short name carries a plain word, for example "LynkAcc (Accounting)"; Solutions gains Individuals & Freelancers, Companies and Organisations & Non-profits; container queries keep it right at every width.
- Favicon: the emblem for light browsers and the emblem for dark browsers (brand place favicon), in every emulator and the showcase. Leftover fixed: the emulated browser tab used the one-colour (all white) mark; it now shows the emblem that matches the page's theme.
- Leftovers fixed: the rider phone's title broke into pieces on a narrow screen; the build now refuses renamed imports (they silently broke the merchant phone and account site files); trackers never read a summary as live progress (no "NaN%").
- File size budgets raised (the favicon in every file, and the tracker engine and words where trackers show), each with its reason in web/budgets.v1.json.

## v0.26.1 (2026-11-09)
Dependency update: TypeScript 5.9.3 to 7.0.2 and the Node.js type definitions (Dependabot, merged once every check was green). The brand-sync pull request for icons 1.5.0 was closed because that artwork was already in v0.25.0.

## v0.26.0 (2026-11-09)
Section 3, Phase 5: language wave 2 (blueprint 43 G). LynkOmni now speaks 38 languages: Bangla, Tamil, Thai, Amharic, Hausa, Yoruba, Zulu, Filipino, Polish, Dutch, Ukrainian and Malay join the 26 of wave 1.
- Every screen text of every emulator (the shell, the shared POS words, the footer, the account site, the Business app and every device) is translated by Claude into the 12 languages and checked by tools/translation/claude_packs.py (names, placeholders and numbers unchanged, no repetition, written in the language's own script).
- Four new scripts with self-hosted fonts from the official Google Fonts repository (same pinned commit, SIL Open Font License): Noto Sans Bengali, Noto Sans Tamil, Noto Sans Thai and Noto Sans Ethiopic. Bengali, Tamil and Thai get the taller line height and are never letter-spaced or uppercased. Ukrainian uses the Cyrillic files and the Latin-script languages use Montserrat and Inter.
- Yoruba's dot-below vowels sit in the Vietnamese block, so a language can now name extra script files ("also" in design/fonts/scripts.v1.json) and offline apps store them too (fontFilesFor).
- The translation script check knows Bengali, Tamil, Thai and Ethiopic.
- Country packs: Bangladesh, Sri Lanka, Thailand, Ethiopia, Malaysia, Brunei, Poland, Ukraine, the Netherlands, Belgium, Suriname, the Dutch Caribbean and the Cocos Islands now open in their own language; every country name is available in the 12 new languages. No language waves are left in design/fonts/language_waves.v1.json; the other official languages stay "planned".
- Leftover fixed: the Business app's customer list showed "{name}" in the "owes" line in every language (the name was not passed in); it now reads, for example, "Eric owes $45.00".
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
- 2026-11-10: MASTER UPDATE section 2 (v0.39.0) built by the blueprint: the larger Security Center and account protections, sign-up by phone or email with two ways in, notification settings, the security and account messages, the Messages page, LynkAssist on the account site with its history, breadcrumbs and cards by group.
- 2026-11-10: Leftovers fixed in section 2: card records now carry their group (older cards are prepaid); the security notice kinds for the new protections and personal reminders joined the message register; LynkAssist's decisions are recorded as AssistActionRecorded; the bell's small action button now has the full touch size.
