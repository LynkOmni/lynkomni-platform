# Blueprint checklist: Step 0 and build sections 1, 2 and 3

Every rule the master blueprint sets for these four parts, checked against the code on 9 November 2026 after the owner's
instruction: "enforce what is laid out in the blueprint for step 0, section 1, section 2 and section 3 entirely before we
continue". The blueprint section is given for each line. Status: **done** (with where), **missing** or **partial** (what is
missing). Where two blueprint lines differ, the later and more specific section wins, as section 45 states for itself, and the
choice is recorded in docs/lynkomni-decisions.md (owner, 9 November 2026: follow the blueprint, do not ask).

## Step 0: one global structure (42 A, 41 S row 0, 44 L row 0)
| # | Rule | Status |
|---|---|---|
| 0.1 | Contract version 2: any currency as integer minor units plus code, version 1 readable through an upcaster | done: contract/event-payloads.v2.json, contract/upcast.py, validator 893 checks |
| 0.2 | The 104 new event names registered with payloads and commands | done: contract v2 |
| 0.3 | Neutral sample country first and a country chooser in every emulator; a test forbids country names in emulators | done for all 13 emulators (tests/test_emulators.py) |
| 0.4 | The one-country switch becomes "A country where partners are not signed yet" | done (v0.23.1): the switch reads it in all 26 languages |
| 0.5 | A country adds only data: currency, taxes, chart of accounts, invoice numbering, payment methods, limits, holidays, legal text | **partial**: 247 packs carry currency, taxes, chart mapping, methods, limits; holidays, invoice numbering and legal text are not fields in every pack |
| 0.6 | Pending-fiscal adapter for any unconfirmed tax authority | done: core/providers.py PendingFiscalAdapter |
| 0.7 | One global chart of accounts, journal as a projection | done: core/accounts.py, contract/chart-of-accounts.v1.json |
| 0.8 | Shared username check (Instagram format, reserved words, look-alikes, never reissued) in Python and TypeScript with shared vectors | done: core/usernames.py, ts/src/usernames.ts, contract/vectors/usernames.v1.json |
| 0.9 | Portuguese as the 16th language; Dependabot drafts; stage names; LODOC-, LOREV-; catalog, address and contacts maps; support levels; revenue, expense and net-profit models; tools/blueprint_numbers.py | done |

## Section 1: shared shell (41 B, 41 S row 1, 44 L row 1, 43 G, 26, 30, 31)
| # | Rule | Status |
|---|---|---|
| 1.1 | One header grammar: logo place left, navigation, then search, globe, help, notifications (signed in), launcher, account | done: ts/src/shell.ts header |
| 1.2 | Logo is the default in website and dashboard headers, footer, login and onboarding; emblem only in small or crowded places and the app top bar; logo falls back to emblem only under 96 px | done (v0.23.1): logo by place and width; tests in tests/test_layout_i18n.py BrandPlaces |
| 1.3 | App top bar: emblem "with the product name as real text beside it" (30) | settled by the blueprint's order: 41 E (later, specific to the Business app) wins: emblem, screen title, chip, notifications, account (decisions 2026-11-09); done in v0.24.0 (3.2) |
| 1.4 | The same footer model everywhere: main footer on websites and web apps, the one-line short footer inside apps, copyright text fixed, year in the visitor's time zone (26) | done (v0.23.1): main footer on the browser frame, account site and owner's web view; short footer in the phone, terminal, tablet and rider apps; 26 languages |
| 1.5 | App launcher: Business, Bookings, Essentials, Exchange, Account, Help, Developers; waiting places show "Coming to your country soon." | done: shell launcher |
| 1.6 | Account menu: name and masked LynkID with copy, switch business, switch role, language and region, theme (light, dark, lite, sunlight), Security Center, help, sign out | done in the browser frame, account site and merchant phone (v0.24.0); **missing** in the terminal and counter tablet (Phase 3) |
| 1.7 | Find or do anything: products, customers, orders, reports, settings, help; runs actions; voice input; hands to LynkAssist; keyboard shortcut | done in the shell; **missing** in the device apps |
| 1.8 | Help panel (?) on every screen: articles, LynkAssist, live chat, then a case | done in the shell; **missing** in the device apps |
| 1.9 | Language and region one tap away (globe); the first-run confirmation card in apps | globe done; **missing**: first-run card and one-tap English (also 38 C, placed in section 3) |
| 1.10 | Connection chip and sync sheet in every app, five states | done in shell, phone, terminal, tablet; **partial** in kitchen screen, rider phone, scanner |
| 1.11 | Every state designed with its picture and a next step (loading, empty, offline, error, not found, no results, permission, maintenance, sync pending, coming soon) | done in the browser frame; **partial** in the device apps |
| 1.12 | Sizes: phone top bar and 4 or 5 bottom tabs; tablet navigation rail; computer left sidebar in apps; content up to 1440 px; nothing scrolls sideways | done (v0.24.0): the Business app has the phone tabs, the tablet side rail and the computer web view |
| 1.13 | Deep links: every screen has its own address | done in the shell, account site and Business app (every register screen shows its address, tested); **missing** in the other device apps (Phase 3) |
| 1.14 | Protected zones: no ads, promotions or "Powered by" on payment, refund, void, cash count, fiscal, private chat; no ads on agent, float, cash check, commission or Security Center screens (43 H) | done in rules (brand.poweredBy); not yet tested on screens |
| 1.15 | Accessibility: WCAG 2.2 AA, **44 px touch targets**, text up to 200%, reduced motion, never colour alone, screen-reader names, right to left mirrored | done (v0.23.1): the check enforces 44 px on every screen; TextAt200 test at 640 px |
| 1.16 | The low-literacy icon set for the 12 handheld tiles, word beside each icon (43 G, 44 L row 1) | **partial**: tiles use existing icons; no dedicated set |
| 1.17 | An agent point picture and float and commission icons (43 G) | **missing** |
| 1.18 | Layout test for every screen and language, speed check, wave 1 (26 languages), chat "Translated from" note, username field, charts with table view, "coming soon" state | done |

## Section 2: LynkOmni Account (41 D, 22, 44 L row 2, 43 H)
| # | Rule | Status |
|---|---|---|
| 2.1 | Sign-in pages /signin, /signup, /recover and the extra-check page | done: owner chose /sign-in and /sign-up; 41 D reworded |
| 2.2 | Overview, Profile, Security Center (passkeys and devices, sessions, events, sign-in methods, recovery settings, connected apps), Businesses (LynkOID, role, switch, create, leave), Orders and Transactions with refunds owed, Wallet, Subscriptions and billing, Memberships, Privacy and data, Notifications (channels and quiet hours), Support cases, Exchange only as a link | done: account-site pages; to be re-walked screen by screen against this list |
| 2.3 | Payslips, payments, N14 Start a business, the health pack and every data-sharing consent screen, takeover safeguards | done (v0.22.0) |
| 2.4 | Main footer on the account pages (26) | done (v0.23.1) |

## Section 3: Business app and the whole of LynkPOS (41 E, 42 C, 42 I, 42 J, 44 L row 3, 38 C, 7, 5)
| # | Rule | Status |
|---|---|---|
| 3.1 | Getting in: sign in, choose business, register device, language and region card, setup checklist under two minutes (name and type, currency confirmed, first products by scan, photo, voice, template or import, invite staff, print the shop QR, all skippable), first sale | done (v0.24.0): the phone runs all six in order with one-tap English; tests/test_business_app.py |
| 3.2 | Phone top bar: emblem, screen title, connection chip, notifications, account | done (v0.24.0), tested |
| 3.3 | Tabs by business type: shop; without a till (Home, Invoices, Customers, Chats, Business); agent point; restaurant (Home, Tables, Kitchen, Chats, Business) | done (v0.24.0): all four on the phone, tested |
| 3.4 | Tablet: the same tabs in a side rail; enrolled counter: left sidebar with the full tree; unenrolled computer: web view with "View only on this computer" | done (v0.24.0): phone, tablet rail and computer web view; the note on the owner's web view and the phone's computer size |
| 3.5 | Home by role (owner, manager, cashier) (5) | done (v0.15.0) |
| 3.6 | Sell: grid, categories, search, scan, voice; basket with quantity, discount and note; attach a customer; payment: cash, mobile money, card (tap to pay on the phone or terminal), bank transfer, QR, pay link, pay later on credit, split payment; receipt: print, QR, chat or SMS link | done (v0.24.0) on the phone; chat and SMS links follow the plan (Plus) |
| 3.7 | Inside Sell: Today's sales (reprint, void with a reason, return or refund), Shift, Services for customers, practice mode | done (v0.24.0) on the phone (contract reason codes) |
| 3.8 | Stock: filters (low, below zero, category, branch); product page (price, cost, barcode, variants, units, photos, stock per branch, history); add product; received; count; remove with reason; move between branches; suppliers; reorder drafts and purchase orders; supplier marketplace; labels and barcodes; import and export | done (v0.24.0) |
| 3.9 | Chats: inbox filters (unread, assigned to me, orders, all); thread with attached order, quote or payment card; send product, quote, pay link, receipt; saved replies, photos, voice notes; assign to staff; pinned LynkOmni Support | done (v0.24.0), with the "Translated from" note |
| 3.10 | Business hub sections: Reports, Daily close, Money (with Recovery, evidence packs, payout splits), Invoicing and Pay links, Customers, Loyalty, Books, Growth, Assistant, Cards, Online shop, Agent earnings, Team, Branches and devices, Plans and billing, Settings (full list), every waiting service with "Coming to your country soon." and Notify me | done (v0.24.0): every section and setting with its register items; regulated items wait for their partner; the full pages of Reports, Invoicing, Customers and Books come in section 4 (41 S) |
| 3.11 | Agent point mode: home (float per partner live, cash, today's services and commission, low-float warning), services grid, the service flow (number, amount, fee and commission, limit, identity check, send, confirmed, then cash or receipt), float top-ups through the partner, cash check at day start, day end and shift handover, commissions matched, outlets on Pro and Max, day close; a practice partner that confirms, fails or stays silent | done (v0.24.0), tested: no cash before the partner confirms |
| 3.12 | S1 to S12: partner routing; low-float warning; customer display; low-literacy mode on every device; practice float; credit book with reminders; second currency; vouchers and pickup; outlet view; one receipt with LORCP-, the partner reference and the state; agent activity in the health score with consent; commission check | done on the phone and terminal (v0.24.0); picture mode on the remaining devices and its own icon set come with Phase 3 and 4 |
| 3.13 | Handheld with 12 tiles; counter tablet with customer display, printer, scanner, drawer, card tap area | done |
| 3.14 | The nine improvements (7, 38 C): tap to pay on the phone, sell by voice, instant online shop, visitor prices, business passport, paperless receipts, practice mode, fake payment protection, daily closing summary | done (v0.24.0) |
| 3.15 | Terminal shop services (38 C): airtime, data, bills, tickets; shifts with float and discrepancy; credit sales; verified receipt QR; shop QR | done (v0.24.0): every printed receipt carries the verify QR and its LORCP- id; the menu shows the shop QR |
| 3.16 | 44 L row 3: web rule and /business/devices, tabs by type, N1 restaurant with kitchen screen, time clock, tips, N8 delivery, N11 buy together, shop usernames, LynkStat Home cards and daily close, float forecast, /business/settings/data-sharing, /business/academy | done (v0.24.0): shop usernames with the shared Instagram-format check; Academy lessons |
| 3.17 | Emulators (42 J): merchant phone with agent point mode and every service, handheld, counter tablet with display, button phone, scanner, card, mesh relay, owner's web view, kitchen screen, rider phone, standalone customer display, automation panel | done (v0.24.0) |
| 3.18 | Customer display welcome screen brand mark | done (v0.23.1): place customer-welcome, logo |
| 3.19 | Control Center screens (38 C row 1 sends merchant-app items to section 3; 41 S row 12 lists the Control Center in section 12) | settled by the blueprint's order: section 12 (41 S) |
| 3.20 | Language wave 2 (43 G): Bengali, Tamil, Thai, Amharic, Hausa, Yoruba, Zulu, Filipino, Polish, Dutch, Ukrainian, Malay | list restored (v0.23.1); built now under the owner's rule "build everything that can be built now" (Phase 5) |
