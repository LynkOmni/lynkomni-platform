# LynkOmni change log

What changed in each version, in plain words, newest first. Version numbers: `0.MINOR.PATCH` until the first pilot (a new feature raises MINOR, a fix raises PATCH). Each version has a Git tag `v<number>`.

## v0.91.0 (2026-11-21)
Section 4 review, sixth part (row 76.8, turning every screen already built):
- Every emulator of a device a person can turn now offers both directions: the rider phone, the tracking, queue and survey pages on a phone, the touch version of the stock scanner and the account site on a phone can be turned sideways, and the counter tablet can stand upright. The layout comes from the device register as on the Business app; nothing on the screen is redrawn, lost or repeated.
- The fit guard tries every one of them both ways, and a new check fails if a turnable emulator stops offering both.
- Build-table row 76.8 is done, and row 70.16's section 4 share too: no office service built in section 4 uses emulators, so none needs a panel entry; LynkFiles' panel entry and its signing tablet come with LynkFiles' screens in 4B.

## v0.90.0 (2026-11-21)
Section 4 review, fifth part (row 68.14, LynkVote's mirrors):
- The public list of locked ballots is copied to every independent witness's mirror as ballots arrive, and the cloud checks each copy against its own list. A difference is flagged once for the organiser and observers (mirror_mismatch); nothing is ever removed. The witnesses are sandboxes until the owner chooses and signs real ones, and the public page says "witnessed" only after that.
- Build-table row 68.14 is done. Row 78.16 (LynkAcademy's groundwork) is marked done too: its last part, the large-organisation set, came with v0.85.0.

## v0.89.0 (2026-11-21)
- Every Lynk name has its own product mark: @lynkomni/icons 1.10.0 adds 22 marks (accounting, invoicing, customers, office bundle, analytics, currency exchange, voting, staff management, projects, school management, courses and training, property management, documents and signing, jobs and hiring, questions and answers, help and support, service status, product feedback, safety and reporting, automations, hardware drivers, account ID), vendored by brand-sync (#141). The names register now names each one; services, features and card groups inside a product use that product's mark.
- LynkInv and LynkCRM joined the Business tab and launchers with their own marks; LynkAcc, LynkStat and the office notifications moved off the borrowed marks. The provider ledger's later items ops_product_icons and product_marks_all are done and removed; build table 84.6's section 4 row is done, so it no longer holds section 4's lock.
- Opening the launcher stays within its tap budget: a place that already shows its plain word under its name is marked as explained, so the names part skips it (the two new launcher places had pushed the browser's first tap to 127 ms against 120).

## v0.87.0 (2026-11-21)
Section 4 review, fourth part (row 67.17, the partners of 67.18 and the registers of section 67):
- Every partner the improved services need has its interface, a working sandbox and a ledger entry, and stays "Coming to your country soon." until it is signed: chat app and social page connectors and a call partner for LynkChat, a licensed lender for pay in parts, map and search listing connectors for LynkGrow, outside warehouses for LynkStock, online-shop plugin listings for LynkDev, and transport card, toll, parking and government fee collectors for LynkEssential. Delivery firms and phone wallets already had theirs.
- No sandbox claims a delivery, a listing, a loan, a payment or stocked goods; people are only vault references; WhatsApp is refused as a channel.
- Every improvement of section 67 is now in the registers: 92 features placed in help, search and the sitemap with the section that builds each, 37 automations (at their levels: money moves only on a person's confirmation or the customer's own standing instruction, marketing only with consent) and 17 message kinds, each in the section that builds it. Prices are unchanged.
- Build-table row 67.17 is done.

## v0.86.0 (2026-11-21)
Section 4 review, third part (row 67.17, the office side of money in LynkAcc):
- Gift cards and store credit are a debt of the shop in the books: a gift card sold or topped up is owed to its holder, store credit given for a return, as cashback or as goodwill is owed to the customer, and spending either is a sale. A card spent below nothing (offline sales are never blocked) is flagged for the owner once.
- Deposits for pre-orders, special orders, rentals and layaways are received in advance until they are used, kept under terms shown before paying, or returned (in cash at the till, or electronically only when the provider confirms).
- The matching centre: every provider payment is matched to its sale, invoice or booking by its reference; a single candidate with the same amount within three days is a suggestion; two candidates are never guessed; everything else is listed as unmatched. From LynkAcc Plus suggestions for sales and bookings are matched automatically and can be undone; an invoice payment always waits for a person.
- What each payment cost: the provider's fee and LynkOmni's part, per payment and per month, from the provider's settlement report only; a fee the cloud already posted is never posted again.
- When the money arrives: a payout calendar from each provider (expected, arrived, late after two days), with its own tracker.
- Contract version 16 adds these events; selling a gift card, giving store credit, taking a deposit and settling one work offline and are never rejected; the provider's facts are written by the cloud alone.

## v0.85.0 (2026-11-21)
Section 4 review, second part (row 67.17, Move in and the large-organisation set for every service):
- Move in for every service: besides customers, suppliers, opening balances and open invoices and bills, a business can now bring in its products, stock levels, members, loyalty points, bookings and payees. Every column is checked by its type (an amount in the currency's own minor units, a whole number, a date) and every reference must be known (stock for a product moved in, points for a member moved in). Nothing moves in while the check shows an error. Products and stock wait in a pack that each device takes, because products and stock are only ever created on a device; members go to LynkCRM with names and contacts in the vault; points follow the member's LynkCRM record; payees go to LynkExchange with bank details in the vault; bookings are kept for LynkBooking's business side.
- The large-organisation set for every service: approval flows now cover each service's own documents (refunds, discounts over a limit, price changes, stock adjustments, purchase orders, payouts, exchange orders, vote rule changes, job offers, leases, leave and more), and own roles cover every service's area. Each needs that service's Max plus an Enterprise agreement.

## v0.84.0 (2026-11-21)
Section 4 review, first part (the groundwork rows):
- LynkSchool's limits and registers for section 80 (row 80.15): catalog/school.v1.json read by core/school.py (every kind and level of school in five groups, the school year, offline working, the children's rules, what LynkAssist may and never does, the partners and where each part is built) and the 80.13 tier features in billing: every kind of school, the school year, offline working and every safety rule on every tier; Plus adds the learner, guardian and safety tools in full, meals, transport, school property, sponsors and grants; Pro adds vocational, university and centre tools and staff and quality; Max adds ministries and groups.
- The six services' partners (row 69.14): every partner of 69.13 has its interface, a working sandbox and a ledger entry, and stays "Coming to your country soon." until signed (services/six_partners.py: background and reference checks, tenant screening, exam boards, a licensed notary, pensions and benefits, deposit protection, a rent insurer, property sites, job sites, employer of record, public employment services). Connected meters and door access are LynkDriver kinds. Messages and automations of LynkHR, LynkProject, LynkSchool, LynkProperty and LynkJobs are registered in the sections that build them. The notary moved from the later list to a sandbox and ledger entry, as 69.13 asks.
- Leftover fixed: two automations did the same job (signature reminders); the one from v0.49.0 is kept, now in section 4 where the engine is.
- Build-table rows marked done in this review: 64.11 (v0.80.0), 65.9 (v0.82.0), 74.9 and 75.9 (v0.74.0), 69.14 and 80.15 (v0.84.0).

## v0.83.0 (2026-11-21)
Section 4, leftover step (things section 4 had planned or claimed but not yet done):
- The three trackers planned for section 4 now work: a supplier's bill in LynkAcc (received, approved, partly paid, paid), a staff expense claim (submitted, approved, repaid) and one message from the message register (waiting to send, sent, delivered in the app, not completed on a channel). The bill and claim trackers show through the LynkAcc API; message delivery is a personal account tracker and never in an API. "Waiting to send" and "Sent" are in 38 languages.
- Services that keep their own state report it in their events, and the tracking register's new list from_service_events says which event moves which tracker. This also fixes the invoice tracker, which LynkInv never fed before: it now moves from issued to paid, credited or voided. LynkAcc's bill and claim events carry their state, and submitting a bill or a claim is recorded.
- The message engine reports each message's state (notification.state, never the message's words).
- Ad earnings: once a month the merchant's ad share is recorded as AdEarningsRecorded (each month and currency once) and posted to LynkAcc as other income, held in the payments clearing account until the payout (automation ads-earnings-to-books).

## v0.82.1 (2026-11-21)
- Guard: section 4 cannot be locked until every Lynk name that still borrows or lacks a product mark has its own one released in lynkomni-icons and vendored. Build table 84.6's section 4 row stays open until then (it was marked done in v0.81.0 while the marks were only in the provider ledger's later list).

## v0.82.0 (2026-11-21)
Section 4, step E4b (EXCHANGE UPDATE: LynkExchange in the office services):
- New rules core/exchange.py and ts/src/exchange.ts with shared test answers (python3 tools/exchange_vectors.py): LynkOmni's part (the lower of the plan's part and the level reached by the last 30 days), one full price from a rate kept as a fraction of whole numbers (never a decimal) and rounded down so nobody is promised more than arrives, the distance from the mid-market rate, and the book value of foreign money spent at its average cost.
- Contract version 15 (contract/tools/build_v15.py; upcaster 14 to 15 only raises the version): ExchangeOrderPlaced, ExchangeOrderPaid, ExchangeOrderFailed, ExchangeRefunded and ExchangeProofIssued beside ExchangeSettled. All cloud only (nothing about an exchange is queued offline); money facts carry the partner's reference; no payee's name, bank account or contact is ever in an event.
- LynkExchange in the office services (services/exchange_office.py): prices with a countdown and "Coming to your country soon." where no licensed partner is signed (service exchange, ledger exchange_currency_partner); Practice mode everywhere with the practice partner, never moving money or touching the books; a second person approves orders above the owner's amount; repeated partner answers change nothing. LynkAcc: money sent to the partner in the clearing account, foreign money held at its cost, a rate gain or loss only when it comes back, spending for money sent with no bill, refunds put back. LynkInv: an invoice paid from abroad. LynkAcc bills: a bill paid to a supplier abroad. LynkCRM: payees as records of the new kind payee, bank details only in the vault. LynkStat: the Exchange report. LynkFiles: a proof of exchange with a code anyone can check (LynkFiles now issues certificates without signers).
- The exchange tracker (order placed, paid, completed, not completed, refunded) in 38 languages and in the exchange API; links to LynkAcc, LynkInv (moved to section 4, as 65.9 says), LynkCRM, LynkStat and LynkFiles; three messages, three automations, placements and five security controls; crypto referral as a later item ($0 until the lawyer approves).

## v0.81.0 (2026-11-21)
Plain words, the 15 improvements (owner, 21 November 2026):
- Each name shows its product's own mark beside it, in search and in labels (catalog/names.v1.json icon). Names still waiting for their own mark in lynkomni-icons show their product's mark or none, never a wrong one (provider ledger later item product_marks_all).
- The first time someone opens a service in the Business app, one card shows what it is, what it does and where to start; Got it closes it for good on that device.
- Old names still lead to the new ones: searching "LynkDash" finds "LynkDash is now LynkStat.", and a person whose account is older than a change sees a one-time notice.
- How to say each name ("Link P O S"): in each name's note, for voice menus on basic phones (core/channels.py aloud) and for LynkAssist.
- Brackets step back once a name is known: after 10 openings of a service its brackets stop showing for that person (the underline and the note stay); a switch in the names setting keeps them.
- "Which one do I need?": 13 groups of names that sound alike, side by side, from a name's note, search and LynkAssist.
- Outside the app: emails, texts and push notifications explain the first Lynk name in each message; each line of LynkOmni's own bill carries its name and plain word; a printed receipt that shows a Lynk name ends with one line explaining it (fiscal documents keep the authority's layout).
- Names A to Z: in the app from search and help, every name with its plain word and what it does; the public page lynkomni.com/names joined the address map and the search register for build section 5.
- Search engines: the search register now carries, for every product page, its name, plain-word key and old names, and the rule that titles, descriptions, sharing cards and app store text lead with "{name}: {plain}" in every language; section 5's keyword register reads every name, plain word, description, spoken form and old name.
- A check on every plain word in all 38 languages (no short forms in capitals except QR, AI, ID and their local forms, no Lynk name, no technical words).
- Which names confuse people: devices count how often each note, answer or comparison is opened as totals by name only; LynkOmni staff see totals of 5 or more (services/name_asks.py; the staff screen comes in section 12).
- The rule for every name widened in the universal register and CLAUDE.md: a new name comes with its plain word, description, spoken form, mark, similar group and now-called line in the same change. Developer pages (section 11) and staff tools (section 12) carry it in their own sections (build table 84.6).
- New words in all 38 languages; page size budgets rise by the words (reasons in web/budgets.v1.json).

## v0.80.0 (2026-11-21)
Section 4, step E4a (BOOKING UPDATE: LynkBooking's money and figures in the office services):
- New rules core/booking.py and ts/src/booking.ts with shared test answers (python3 tools/booking_vectors.py): LynkOmni's commission from the locked rule (nothing on a business's own link, QR code, front desk or returning customers; appointments only on a new customer's first visit, capped; events a share plus a fixed amount per paid ticket and nothing on free events; tables per seated guest; partner supply still without a rate), the busy-time forecast (always an estimate), the empty-hours report and the no-show rate.
- Contract version 14 (contract/tools/build_v14.py; upcaster 13 to 14 only raises the version): BookingConfirmed, BookingPaid, BookingCheckedIn, BookingCancelled, BookingNoShow, BookingRefunded and BookingCommissionRecorded. Checking in and cancelling at the front desk may come from a device, offline; payments and refunds only from the provider's confirmation; no customer's name or contact, ticket code or address in any event.
- LynkBooking in the office services (services/booking_office.py), reading booking events only: LynkAcc holds money paid before a visit as received in advance until the customer comes, then earns it; kept fees are earned; refunds come out of what is held first; commission is a provider fee. LynkInv: deposit invoices (the pay link shows "Coming to your country soon." where payments are not yet switched on), passes and a company's bookings for a period on one invoice, each booking once; LynkInv now takes prices that already hold the tax. LynkCRM: a confirmed booking goes on the customer's timeline. LynkStat: the busy-time forecast, the empty-hours report and the no-show rate.
- Every country pack carries its booking settings (sent first, as v0.79.1), unknown until confirmed (tools/country_booking.py; ledger later booking_country_rules): the fixed commission amounts in the country's currency, the tourist tax, the travel-seller licence, the most a deposit may be and the shortest legal cancelling notice. Until a currency's fixed amounts are confirmed, commissions that use them are not recorded there.
- The business address app.lynkomni.com/booking and its Storefront twin; service booking (direct listings, on everywhere); links to LynkAcc, LynkInv, LynkCRM and LynkStat with their events (the CRM link moved from section 8 to 4, as 64.11 says); three automations, placements and three security controls.

## v0.79.1 (2026-11-21)
Section 4, step E4a, part 1 (BOOKING UPDATE): every country pack carries LynkBooking's settings, all unknown until the lawyer and accountant confirm them (tools/country_booking.py; ledger later booking_country_rules): the fixed commission amounts in the country's currency, the tourist tax, the travel-seller licence, the most a deposit may be and the shortest legal cancelling notice. The pack generator keeps the new section. Sent on its own because the 248 packs together with the rest of the step went past the 300 files the code-scanning check reads.
- Fix: the plain words for Lynk names (v0.79.0) made opening the launcher slower than its tap budget on a slow phone (138 to 178 ms against 120). The names part now reads every style it needs first and changes the page after, and builds its name pattern once instead of for every piece of text; marking is unchanged (the first mention on a screen still shows its plain word). The budget is not raised.

## v0.79.0 (2026-11-21)
Plain words for every Lynk name, everywhere (owner, 21 November 2026):
- One register, catalog/names.v1.json, holds every Lynk name a person can see (33 products, 16 services, 4 features, 3 card groups and 6 devices) with its plain word and a one-line description of what it does, in all 38 languages (web/names, web/nameinfo). It also lists the company name, the internal names and the retired names, which never show.
- Every screen of every emulator marks every Lynk name it shows: the first mention on a screen in running text shows its plain word in brackets ("LynkStat (Analytics)"); every other mention has a quiet dotted line and explains itself on hover, focus or a long press, with what it does on the pages that carry the descriptions; screen readers hear it too. Receipts, printed paper, the copyright line, what people type and code are left alone.
- Launchers in the browser, the account site and the owner's computer view show each product with its plain word; search finds a product by its plain word or what it does ("accounting" finds LynkAcc and LynkOps), on every device.
- LynkAssist answers "What is LynkStat?" for every name, in every language, offline too (the knowledge pack).
- Basic phones show the plain word first: the menu title is now "Point of sale (LynkPOS)".
- Plain words first: a person can choose it in their account (Language and region) and the owner can switch it on for the business's devices; launchers, labels and notes then show "Analytics (LynkStat)".
- Clearer plain words where two were too close: LynkTrace is now "Order & delivery tracking" (was "Tracking") and LynkSentry "Theft & incident alerts" (was "Protection").
- The footer reads its plain words from the register; tests/test_names.py checks the register (every family has a name, one plain word per name in every language, at most 40 characters, every Lynk word on a screen registered) and the fit guard's walk fails any screen that shows a name without its plain word. Page size budgets rise by the words (reasons in web/budgets.v1.json).

## v0.78.0 (2026-11-21)
Section 4, step E3 (SIX SERVICES UPDATE: LynkFiles' document engine, which every service stores and signs through):
- New register catalog/files.v1.json, read by core/files.py and ts/src/files.ts with shared test answers (python3 tools/files_vectors.py): a file's type from its bytes (programs and scripts refused), who signs next, the state of a signature request, when a share link may open, the verification code (three groups of the Lynk Alphabet) and whether a file fits the plan's storage.
- Contract version 13 (contract/tools/build_v13.py; upcaster 12 to 13 only raises the version): SignatureRequested, DocumentSigned, SignatureDeclined, SignatureCompleted, ShareLinkCreated, ShareLinkStopped, FileVersionAdded (may be made offline on a device), LegalHoldChanged and FileDeleted. No file content or name, signer's name or contact, link address, password or verification code is ever in an event.
- The engine in the cloud (services/files.py): files kept under the record they belong to and opened only where that record's service allows; every version kept and restorable; storage and signature requests follow the LynkFiles plan; legal hold blocks changes, sharing and deleting and stops share links; share links always end, keep a password only as a salted hash and stop at once; signers sign in order or together on their own link, each signing the exact version they saw; identity-checked and qualified signatures wait for their partners; a code anyone can check shows the signed fingerprint and how many signed, never who; an audit log of every open, version, share, signature, hold and deletion.
- The signature tracker (sent for signing, signed, completed, declined) in 38 languages and in the documents API; four messages and four automations; the HR, CRM and property links now name the signing events; services files (on everywhere) and its partner parts sign_identity, sign_qualified and file_scan with sandboxes (services/files_partners.py); the notary as a later item; placements and six security controls.
- Leftover fixed: a person's own pages for LynkFiles, LynkHR, LynkSchool and LynkProperty (account.lynkomni.com/documents, /work, /school and /home, blueprint 69) joined the address map, so those names are now reserved as usernames.

## v0.77.0 (2026-11-21)
Section 4, step E2 (VOTE UPDATE: LynkVote's groundwork around the security core):
- Contract version 12 (contract/tools/build_v12.py; upcaster 11 to 12 only raises the version): 18 voting events, from VoteCreated to VoteResultCertified, with reminder rounds, flags, reissued codes, the governance home's DecisionRecorded and MinutesSigned. A choice, a voter beside a ballot, a key part, a code, a contact or a time of casting is never in an event; a ballot is only its tracking code. Casting and challenging may come from a polling-place device in sealed batches (the cloud checks every proof and may refuse); everything else is cloud only. Events name a vote by its internal id, like VoteRollImported, and its public LOVOT- id comes from the id registry.
- LynkVote in the cloud (services/vote.py): set-up, the trustees' key ceremony (only public parts and proofs kept), the roll with its check report and the plan's voter limit (extra blocks of 1,000 on paid plans), a code for every voter kept only as its fingerprint, contacts in the PII vault, ballots checked and put on the public list, voting again where the rules allow (the link is deleted at closing), a reissued code cancelling the old one, closing, a threshold of trustees opening the count with proofs, every counting method on real ballots (totals or shuffled ballots), weighted votes sized by each voter's weight, and certifying (sealed only when the partner confirms). Public elections wait for certification.
- The governance home: templates per kind of organisation (a starting point, never legal advice), committees, the register of decisions with who must act, and minutes signed by every required role. Federations: branches link with their own consent; the result combines only published branch results by one of three rules, and a branch below 5 ballots is never shown alone. Move in: a "voters" file kind in the shared check report (a reference only once, weights whole numbers), the same in TypeScript, and past votes kept as moved-in history.
- The vote tracker (set up, roll ready, voting open, voting closed, counted, results published; voters see only the last four) in 38 languages, shown through the voting API; seven messages and six automations; the roll links from LynkAcc and LynkAttend; services voting (on everywhere) and its partner parts vote_identity, vote_seal and vote_post with sandboxes (services/vote_partners.py); later items for the mirror witnesses, certification and the audit firm; placements and five security controls.
- Leftover fixed: account.lynkomni.com/votes (a person's votes, blueprint 68) joined the address map.

## v0.76.0 (2026-11-21)
Section 4, step E1 (VOTE UPDATE: LynkVote's security core and counting methods):
- New register catalog/vote.v1.json, read by core/vote_crypto.py, core/vote_count.py and their TypeScript ports with shared test answers (python3 tools/vote_vectors.py). It covers every kind of vote, way to vote and counting method, the assurance levels, the published tie draw and the words LynkVote never uses.
- The security core, in the published RFC 7919 group (a test proves it is a safe prime group):
  - a choice is locked on the voter's device and every locked choice carries a proof that it is allowed, so a ballot cannot vote twice or vote negative;
  - the key is split between trustees, each proving their part; any threshold of them opens a total, one trustee alone or LynkOmni opens nothing, and a false opening is caught;
  - totals are added while still locked, so no single ballot is ever opened in such a count;
  - ballots read one by one are shuffled first, with a proof that catches a changed ballot;
  - every voter gets a tracking code that chains the public list, which is sorted so the order is hidden;
  - a voter may challenge the device to prove it locked the choice honestly.
- The device's own SHA-256 and HMAC run in the browser and offline, checked against Node's.
- Every counting method of 68.5, in whole numbers and exact fractions, with published examples. The Tennessee capital example gives Memphis by most votes, Knoxville by instant run-off and Nashville by the head-to-head methods; the standard D'Hondt, Sainte-Laguë, Hare and Droop seat examples also match.
- Yes, no or abstain with simple, absolute, two-thirds and custom majorities and a quorum; abstentions never count as yes.
- Honest claims: a test fails if any screen or message says unhackable, 100% secure or fraud-proof.
- Encryption that stays secret against future computers is not claimed yet. It and the outside cryptographers' review are in the provider ledger's later list.
- Three features placed; four security controls.

## v0.75.0 (2026-11-20)
Section 4, step D5 (the office services in the browser, in 38 languages):
- New shared part ts/src/officeview.ts draws LynkAcc (app.lynkomni.com/accounting), LynkInv (/invoicing), LynkCRM (/crm) and LynkStat (/analytics) in the owner's computer view, computed with the real rules (books, invoices, crm and stats) and the shared page parts (list toolbar, record header with the same tabs, save bar):
  - LynkAcc: the statements (profit and loss, balance sheet, balanced or not), bills to pay with approval (the person who entered a bill never approves it; a payment counts only when the provider confirms), bank matching as labelled suggestions, and closing the month with its checklist and a lock date a second person approves;
  - LynkInv: money owed with how late it is, the invoice list with filters, an invoice record (a sent invoice never changes; a credit note never exceeds what is still owed and needs a reason) and a new invoice with live totals and approval over the approval amount;
  - LynkCRM: customers (contact details private), duplicates that keep the oldest with Undo, and the pipeline with its likely value labelled an estimate;
  - LynkStat: the overview with freshness and a goal, your own measures (figures added by buttons in the reader's language; nothing shown on division by zero), what if (labelled an estimate), groups over time and a public report with small groups hidden.
- Words in web/office (prefix of_) in all 38 languages; sample data is labelled Sample; every list has its empty state with a next step; every field has its hint and a visible label.
- The page builder now also catches a second name declared on one top-level line (const A = 1, B = 2), which had let two modules clash.
- The owner view's off switch and the office state tags now meet 4.5:1 contrast.
- The owner view's size budget is raised to 1300 KB (web/budgets.v1.json, reason recorded): it now carries the four office services with their rules and their words in all 38 languages.

## v0.74.0 (2026-11-20)
Section 4, step D4c (CHAT UPDATE 74.5 and ASSIST UPDATE 75.6: the office services in a conversation, and LynkAssist's office skills):
- The office cards work in the cloud (services/office_chat.py):
  - LynkInv's invoice, quote and credit-note cards, LynkAcc's statement and reminder cards and LynkStat's report card, each read from its own service;
  - Pay opens LynkCheckout's pay link and is never offered offline or on an invoice with nothing left to pay; Accept opens LynkInv;
  - from a conversation: make a quote or an invoice (an invoice waiting for approval sends no card), note a payment promise, add a new customer (name and contacts to the vault), a note or a follow-up;
  - every conversation goes on the customer's LynkCRM timeline and on the record it is about;
  - the chat figures (first reply, time to solve, reopened, solved by LynkAssist alone) come from real conversations; "usually replies within" needs at least 20 replies; the chats behind a figure open only for the owner and managers.
- LynkAssist's office skills (services/assist_office.py), ten new actions in catalog/assist.v1.json:
  - LynkAcc: suggests a category and a bank match (labelled suggestions, never posted), explains a statement line by line and shows the month-end checklist (it never closes the period);
  - LynkInv: drafts an invoice or quote from a conversation or a photo (nothing issued until the person issues it), and drafts a polite plan for a late payer (it never sends a reminder the business did not approve);
  - LynkCRM: a customer summary from what the role may see, and who to contact next and why (a message only where the customer agreed, otherwise a call or a visit);
  - LynkStat: "Why did this change?" from the figures and the owner's notes, with an estimate always labelled;
  - issuing a credit note runs after Confirm; tax filing and payroll are only prepared and handed to a person.
- Three features placed in search, help and the sitemap; two security controls.

## v0.73.0 (2026-11-20)
Section 4, step D4b (SERVICES UPDATE 67.5: the LynkStat additions):
- New register catalog/stats.v1.json, read by core/stats.py and ts/src/stats.ts with shared test answers (python3 tools/stats_vectors.py). It covers:
  - groups over time: customers grouped by the month they first bought, and how many came back each later month;
  - "what if": change a price, a cost or staff hours and see the likely result, always labelled an estimate;
  - your own measures from existing figures with + - * / and brackets, never code; dividing by zero or a result too large for every device shows nothing, never a made-up number;
  - seeing only your part (a branch manager sees only that branch, and nothing without a branch), freshness with missing sources, scheduled export dates, goals with progress and "on track", and public reports with every group below 5 hidden.
- LynkStat in the cloud (services/stats.py): figures read from the books, LynkInv and LynkCRM; groups over time from issued invoices; own measures, roles' scope, freshness, scheduled exports (figures only, never customers' personal data), goals, notes on a chart and public reports.
- Tiers (no price changes): freshness and notes on every tier; groups over time, goals and public reports from Plus; what if, own measures and branch scope from Pro; scheduled exports on Max.
- Nine features placed in search, help and the sitemap; two security controls.

## v0.72.0 (2026-11-20)
Section 4, step D4a (OFFICE UPDATE: the large-organisation set and Move in):
- New register catalog/enterprise.v1.json, read by core/enterprise.py and ts/src/enterprise.ts with shared test answers (python3 tools/enterprise_vectors.py). It covers:
  - approval flows an organisation builds itself: steps by amount and department, stand-ins only while the approver is away, never the preparer, one step per person;
  - its own roles, never more than the owner's, with preparing and approving kept apart;
  - charges split by department exactly; legal hold and keeping times never shorter than the law's; where data is kept;
  - the Move in check report: amounts read exactly as whole minor units ("1,234.50", "1234,5"), dates that exist, required fields, the same reference twice, open items for people not moved in, and opening balances that balance.
- Large organisations in the cloud (services/enterprise.py): Enterprise is Max plus this set, by an agreement LynkOmni staff record. It adds own flows and roles; the staff directory (a removed person loses access within 15 minutes; provider ledger item staff_directory, sandbox until signed); legal holds; audit log export; charge splits; and a test copy where every provider is a sandbox.
- Move in and leave (services/enterprise.py MoveIn):
  - customers and suppliers go to LynkCRM, with names and contacts in the vault;
  - opening balances wait for a second person;
  - open invoices and bills are kept as open items without posting twice;
  - nothing goes in while the check report shows an error;
  - leaving is a full download at any time.
- Ten features placed in search, help and the sitemap; four security controls.
- Fixed while building: the audit log export now carries every event. The event store's of() returned nothing when no event type was named, so it now refuses such a read and since() gives every event. Four older privacy checks in the attendance, survey and queue tests had read that empty list; they now read every event and still pass.

## v0.71.0 (2026-11-20)
Section 4, step D3 (OFFICE UPDATE: LynkCRM):
- New register catalog/crm.v1.json, read by core/crm.py and ts/src/crm.ts with shared test answers (python3 tools/crm_vectors.py). It covers:
  - record kinds for every kind of entity and relations (a guardian only in a school);
  - own fields with their checks and limits, required fields, and saved segments worked out again each time;
  - pipelines on the contract's five stages, with won and lost reasons and the forecast;
  - lead scores, always labelled as LynkAssist's suggestion;
  - who sees which records, and fields hidden by role;
  - cases with promised answer times, and the one full picture (each source only when its link is on);
  - duplicates found by email, phone or name set aside of case and accents, and merged into the oldest record (undo for 30 days);
  - consent per channel (marketing needs "asked"), a person's data requests, and sensitive records only where the law allows.
- LynkCRM in the cloud (services/crm.py): records with public id LOCST-. Names, emails and phone numbers live only in the PII vault; the record keeps fingerprints to find duplicates, and no event carries them. The service also handles fields, segments, deals, cases, hand-overs, merges with undo, consent, data requests, the timeline and field visits.
- LynkCRM's tiers follow blueprint 66.7. Consent records, data requests, offline working, import, duplicate merging and the change history are on every tier.
- Eight LynkCRM features placed in search, help and the sitemap; two security controls.

## v0.70.0 (2026-11-20)
Section 4, step D2b (OFFICE UPDATE: contract version 11 and the cloud services):
- Contract version 11 (contract/tools/build_v11.py) adds the facts of bills, expense claims, assets, loss of value, journals and the lock date, and of documents, reminders, promises to pay, disputes, write-offs, credit balances, instalment plans, subscription changes and e-invoice answers, and LynkCRM's facts: a record created, records merged, a customer handed over, a case opened and moved on, consent per channel, a data request and a field visit.
  - A device may record a bill, submit an expense claim, record a promise to pay, mark a dispute, create a customer record, open a case, change consent and check in a visit, offline.
  - Everything that needs the rules, a second person or a provider is written by the cloud alone.
  - A journal must balance and name real accounts.
  - No name, contact detail, bank account, card or tax number, address, photo or position is ever in an event.
- LynkAcc in the cloud (services/accounting.py):
  - bills entered, approved step by step by people other than the one who entered them, matched with the order and the goods received, and paid only when the provider confirms; payment runs;
  - expense claims approved by someone else and repaid;
  - assets with their loss of value (once per period), and selling or writing one off;
  - journals with two people for sensitive kinds, the lock date (two people), and the year-end close with its checklist;
  - revaluation, bank matching and the statements.
- LynkInv in the cloud (services/invoicing.py):
  - documents with their own identifiers, and approval before sending;
  - stepped reminders with promises and disputes, write-offs by two people, paying several invoices at once with a credit balance, instalment plans, subscriptions and billing by use;
  - government e-invoices waiting as queued until the country's partner is signed.
- Leftover fixed: issued invoices, invoice payments, credit notes and voids never reached the books. They now post as checked journals: an invoice is owed, earned and taxed; an electronic payment sits in the payments clearing account until the payout, as card and mobile-money sales already did. The quote-to-cash and sale-to-books journeys run end to end in tests, with the books balanced at every step.
- Three security controls: paid only when confirmed, write-offs by two people, approval before sending.
- Leftover fixed: on some demo pages (the kitchen screen, the stock scanner) a link the screen handles itself, such as a breadcrumb, also made the browser leave the page. A small shared part now keeps such links in the page on every demo (they keep their real address for hosted pages and screen readers), and a new fit-guard check clicks every such link on every page. This was the cause of the layout check that failed from time to time on CI.

## v0.69.0 (2026-11-20)
Section 4, step D2a (OFFICE UPDATE: LynkInv's rules):
- New register catalog/invoices.v1.json, read by core/invoices.py and ts/src/invoices.ts with shared test answers (python3 tools/invoices_vectors.py), on top of LynkAcc's rules. It covers:
  - the documents and what each may be made from: quote, pro-forma, sales order, delivery note, invoice, receipt, credit note, debit note, statement of account, and a buyer-issued invoice only where the country allows it. Each keeps an identifier that already exists;
  - the invoice states, payment terms and due dates;
  - totals with several taxes per line and per invoice, discounts per line and per invoice, and prices with tax included;
  - a credit-limit warning (never a block) and approval before sending;
  - stepped reminders (before the due date, then friendly, firm and final), paused by a promise-to-pay date or a dispute;
  - late fees only where the country's law allows them, never above its rate;
  - ageing, and paying several invoices at once (oldest first), with any overpayment kept as a credit balance;
  - instalment plans, subscription changes for the days left, billing by use (per unit, graduated or volume), project stages and retainers;
  - another currency at a recorded rate, cash rounding, keeping times, and at most two languages on one invoice.
- Every country pack now has office settings: late fees, e-invoices, keeping times, mileage and daily allowance, allowed costing and loss-of-value methods, buyer-issued invoices and the reverse charge, and for LynkCRM the days to answer a data request, the data region, keeping times and which sensitive records are allowed (tools/country_office.py). All start unknown and unconfirmed, and the safe default applies until a local lawyer and accountant confirm them.
- Government e-invoices sit behind one interface (services/einvoice.py) with a working sandbox; provider ledger item e_invoice_network stays a sandbox until a partner is signed per country. Only the network writes accepted, confirmed or failed.
- LynkInv's tiers follow blueprint 66.7. E-invoices, tax held back and keeping invoices are on every tier, Free included.
- Seven LynkInv features placed in search, help and the sitemap.
- Leftover fixed: invoice totals and the dashboard's tax estimate used decimal arithmetic. They now read the country's rate exactly as basis points (a new exact rate reader, also in TypeScript) and work in whole minor units.

## v0.68.0 (2026-11-20)
Section 4, step D1 (OFFICE UPDATE: LynkAcc's rules):
- Chart of accounts version 2 (contract/chart-of-accounts.v2.json): every version 1 account and posting unchanged, plus the accounts LynkAcc needs: mobile money, cheques waiting to clear, paid in advance, earned not yet billed, tax to reclaim, tax held back, equipment and the loss of value so far, money owed between group entities, loans and leases, staff claims to repay, profit kept from earlier years, funds for a set purpose, member shares, grants, exchange gains and losses, late fees, interest, bad debts. Each account has a group for the statements. New postings for bills, expense claims, assets, loss of value, loans, write-offs, late fees, grants and a checked journal (it must balance and name real accounts, or nothing posts).
- New register catalog/books.v1.json, read by core/books.py and ts/src/books.ts with shared test answers (python3 tools/books_vectors.py): bills to pay with their steps, approval by amount (the person who entered a bill never approves it) and three-way matching with the order and the goods received; early-payment discounts; expense claims with mileage and daily allowances; company-card spending matched to receipts; loss of value (straight line or reducing balance) ending exactly at the value left; selling or writing off an asset; loans with equal monthly payments that clear exactly; repeating entries (a month-end stays at the month's end) and reversing entries; the lock date; two people for sensitive entries; the year-end close; bank matching; several taxes on one line (added or included, tax held back, the reverse charge); profit and loss, balance sheet, cash flow and changes in equity; period-end revaluation; stock value by FIFO or average cost; group books; budgets against actual; restricted funds; a public body's budget lines; the tools for each kind of entity.
- Every amount is an integer and every split adds up exactly to its whole.
- LynkAcc's tiers follow blueprint 66.7. What the law requires (tax held back, keeping records), offline working, import and the change history are on every tier, Free included.
- Twelve LynkAcc features placed in search, help and the sitemap; four new security controls.

## v0.67.0 (2026-11-20)
Section 4, step C3b (ASSIST UPDATE: LynkAssist's trust part on screen):
- New shared part ts/src/assistview.ts (with web/shell/assist.css), drawn from the trust register: LynkAssist's answer with how sure it is (an icon and its word, never colour alone), the working behind a figure (the records and the sum, added up twice, or why it is not shown), the "not an adviser" and "unconfirmed rule" lines; the before-and-after preview (what changes, what it costs, who will be told, a sample of 5 when many change); a warning line with Fix or It is fine; "Ask about this"; and the owner's controls.
- The Business app uses it: Ask about this on today's sales on Home (a button, or press and hold for half a second); in the Assistant, correcting a price shows the preview and warns when the new price is below cost; rounding every price is a big change, so it goes to a second approver who is never the person asking (the owner or another manager answers it in the requests list); practice mode changes nothing real.
- The owner's controls on the Assistant screen: Pause LynkAssist actions (answers carry on), what LynkAssist may do for each role, the second-approver amount, how many tips a day, and the memory card (what it remembers, Remember that…, Forget, memory off). Memory never keeps a card number or a code. Staff see the controls greyed.
- The 79 LynkAssist words in all 38 languages (web/assist, prefix at_), travelling only with pages that use the part.
- Every hinted field on these screens keeps an accessible name.
- The Business app demo's size budget is 3,240 KB (the LynkAssist words in 38 languages).

## v0.66.0 (2026-11-20)
Section 4, step C3a (ASSIST UPDATE: LynkAssist's trust layer):
- New register catalog/assist-trust.v1.json, read by core/assist_trust.py and ts/src/assisttrust.ts with shared test answers (python3 tools/assist_trust_vectors.py), on top of the LynkAssist register that already decides what may run.
- How sure: "certain" only when every figure comes from the records, worked out exactly and checked twice; "likely" for an estimate or missing records; "I am not sure" when sources disagree or a country rule is unconfirmed; "I do not know" when there is no source. Figures are integer minor units of one currency, added up twice; otherwise not shown. Tax, law, money, investment and health answers carry the "not an adviser" line.
- Cannot be tricked: only the person's own request can start an action; text in a document, email, chat message, product name, review or web page is content and is never obeyed.
- Memory under control: preferences and "remember that…", kept apart by business, person and household; never a card number, PIN or code; sensitive things only when asked; memory follows the role; an off switch; kept in its own store, never in the event log.
- Doing things safely: a before-and-after preview for every confirmed action; many changes show a sample of 5; the owner's limits only lower the register's; a big change (over 50 items or the amount) needs a second approver who is never the person asking; per-role permission; "Pause LynkAssist actions" (answers carry on); plans that pause and carry on; practice mode changes nothing real.
- Warnings at the right moment (price below cost, a copy of an invoice, a date in the past, a cash mismatch, a failing payment, low stock): told once, never inside a payment or count, within the person's daily pace.
- "Ask about this" targets; quality gates: no release when a scorecard gets worse by more than 1 point, a language only when it passes its bar, a new skill starts as suggestions only.
- The Business app's LynkAssist service uses the trust layer: new signals AssistPaused, AssistRoleSet, AssistLimitSet and AssistPlanChanged in merchant/events.v1.json.
- Three security controls: content never obeyed, no secrets in memory, the second approver.
- The Business app chat test now finds the Stop button again when it clicks (the answer redraws as it is written; a slower test machine caught it).

## v0.65.0 (2026-11-20)
Section 4, step C2 (CHAT UPDATE: the shared chat part):
- New shared part ts/src/chatview.ts (with web/shell/chat.css), drawn from the chat register: messages with the five states (a person's "seen" choice followed, a failed message with Try again), "edited", a quoted reply and message details; live signs always with words (still words when motion is off), announced once to a screen reader; your own connection ("Waiting for internet", "Back online"); the unread line; LynkAssist always named, its answer appearing as it is written with its stage and Stop; upload progress with pause, carry on and cancel; buttons and small forms (a tap sends the choice as the person's own message); cards drawn by their own service; mute for an hour, a day or always; "Why did I get this chat?" and "Who is helping me?"; "Chat about this"; the composer with a visible label and an example as its hint.
- Before a message is queued, a card number or a code is masked and the writer is warned ("LynkOmni and its staff never ask for these"); MessagePosted carries only the text's sha256 (worked out on the device, the same as the cloud's).
- Chat sounds and vibration play from the design tokens and follow the device's switches, silent mode, quiet hours and each conversation's mute; never inside a payment or cash count; many messages at once make one sound.
- The Business app's chats run on the shared part: messages move queued, sent, accepted and seen (the cloud writes the last two); the sample customer's typing sign; LynkOmni Support with LynkAssist first, buttons, a small form, the answer as it is written with Stop, and Talk to a person routed by the routing register; queued messages send by themselves when the connection is back.
- The 88 chat words in all 38 languages (web/chat, prefix ch_), travelling only with pages that use the chat part.
- The showcase's part gallery shows the chat part.
- The Business app demo's size budget is 3,080 KB (the chat words in 38 languages).

## v0.64.0 (2026-11-20)
Section 4, step C1 (CHAT UPDATE: the conversation engine and its registers):
- New register catalog/chat.v1.json: the three kinds of conversation (customer and business, Storefront, support; never personal, group or staff-to-staff chat), the five message states and who writes each, the 15-minute edit window, live signs (always with words, never stored, both sides online, still words when motion is off, "Ama is replying" for the team only), presence, the chat sounds and vibrations, masking, routing (LynkAssist first, the fast lane, same helper, language, least busy with a limit of 5, the owner's team rules), the offline rules and the cards each service may put in a chat.
- The rules in Python (core/chat.py) and TypeScript (ts/src/chat.ts), checked against each other by shared test answers (python3 tools/chat_vectors.py).
- Masking: a card number (13 to 19 digits that pass the card check) is always hidden except its last four; a 4 to 8 digit code is hidden when the message also has a code word (PIN, password, code and their translations), on the device before the message is queued and again in the cloud. An amount like "I paid 5000" is not touched.
- Contract version 10 (contract/tools/build_v10.py): eight conversation events. A device may open a conversation, post a message, fix its own text message, close and report one, all offline; the cloud alone writes that a message reached the other side, was seen or failed, and who a chat was routed or handed to. A message's text is never in an event (the event carries only its sha256); nor are live signs, card numbers, PINs, codes, positions, votes or names. ConversationCardSent can name every card of the chat register. Upcaster 9 to 10 only raises the version.
- The chat cards each have their link in catalog/connections.v1.json (13 new links; Track joins the platform services); the LynkAcc, LynkInv, LynkCRM and LynkStat cards are drawn in step D with those services.
- An original set of soft chat tones and vibrations in design/tokens.v1.json (sent, received, LynkAssist, a helper joining, recording, failure, your turn, the counter chime); each vibration differs, and typing never sounds. They play from step C2.
- Two security controls: chat masking and message text kept out of the event log.

## v0.63.0 (2026-11-20)
Section 4, step B2c (INTERFACE UPDATE: page templates, the part gallery and the speed targets; step B is complete with this):
- The counter tablet's tabs come from the navigation register through the app shell: a side rail (a tablet on its side), hidden during a cash count.
- New shared page parts ts/src/pagekit.ts (with web/shell/pagekit.css): the record header (name, state, one main button and the same tabs on every record: Details, Activity, Files, Related; at most seven, the rest under More), the list toolbar (search with a visible label and an example as its hint, filter chips) and the save bar that stays in view. Screens take them up as their services are built (LynkAcc, LynkInv, LynkCRM and LynkStat in step D).
- The showcase has a part gallery: every app-shell and page-template part, drawn by the real code from the registers (web/build.mjs writes web/showcase/gallery.generated.html; its check fails when the gallery is out of date).
- New speed target: nothing jumps while a page loads (layout shift at most 0.1 from opening to two seconds after the first screen, on the four-times-slower CPU; web/budgets.v1.json layout_shift_max, tests/test_speed_budget.py).
- Leftover fixed by that check: on a narrow screen, 14 demo pages drew the device at full size and then shrank it, so the page jumped (scores up to 0.36). The device drawing is now scaled before the first paint, and each demo page stays invisible until its first screen is drawn, so it appears all at once; every page is now at or under 0.066 here. Like the time budgets, the best of up to three fresh loads counts (a busy test machine once scored the shell page 0.131).
- The account site moves onto the app shell in section 7 with the personal account frame and the person's bottom bar (blueprint 73.9 places that frame in section 7).
- The counter tablet demo's size budget is 1,130 KB (menu words in 38 languages).

## v0.62.0 (2026-11-20)
Section 4, step B2b (INTERFACE UPDATE and TURN UPDATE: the two-level side bar on a computer and turning the phone):
- The owner's view on a laptop now has the two-level side bar from the app shell: a slim first column (Home, Inbox, All services; at the bottom Emulators, Automations, Settings and Help, which can never be hidden) and the page menu in the fixed order (Overview, the lists, Automations, Settings), with the logo above it. "All services" opens the launcher with "My services" first and then the eight groups; a service whose computer screens come in a later section opens at its own address with its name. Track joins this view with the "Track" home in section 7.
- The Business app in a browser uses the side rail instead of phone tabs, as the device register says for a computer.
- The Business app can now be turned: a new choice "Phone turned sideways" shows the same phone on its side, with a side rail instead of the bottom tabs and a one-line header. The tablet's shape is now recorded as it is drawn (on its side).
- New check tests/test_turning.py (CI layout job): turning in the middle of a sale keeps the screen, the basket and the event log exactly as they were and repeats nothing; typed text is kept; a payment keeps its step and its calm header either way round. The fit guard checks the sideways phone like every other size.
- Narrow columns of the app shell (the first column and the page menu) let a long word break inside them, so no language pushes a word past the edge (found by the layout check in Kurdish, Uyghur, Hebrew and Tamil).
- The launcher gets every product's short name and app address from the catalog and billing (web/emulators/build_data.py launcher), for every page that uses the app shell.

## v0.61.0 (2026-11-20)
Section 4, step B2a (INTERFACE UPDATE: the app shell's menus, first on the Business app):
- The menu words of the navigation register (the eight groups, the side bar, the person's bottom bar, quick create, search groups, the account menu, record tabs and the turning messages) are now in all 38 languages (web/navigation; 28 reused from words already translated, 42 new). They use their own prefix nv_ and travel only with pages that use the app shell.
- New shared part ts/src/appshell.ts (with web/shell/appshell.css): the bottom bar and side rail, the two-level side bar's first column and service menu, quick create (+) and the launcher in the eight groups with "My services" first, all drawn from the navigation register and the layout of the screen's shape, never from a screen's own list.
- The Business app now uses it: its tabs come from the register (four on a small phone, a side rail on a tablet, none during a payment or cash count); a + button in the header opens quick create by role (new sale, product, invoice, customer); payment and cash-count screens show the calm focus header with only Back and the connection chip; the screen's shape is written on the screen root, so a turn never redraws it. On a phone the screen title now has its own line under the header buttons, so it is never cut.
- Leftover fixed: the breadcrumb on the Business app's Home screen at tablet size showed a raw word name ("tab_") because the trail held the same place twice; Home now shows no trail.
- The Business app in a browser keeps its bottom tabs until the two-level side bar replaces them in the next part (B2b), together with the owner's web view, the counter tablet, the account site and the sideways checks.

## v0.60.0 (2026-11-20)
Sounds and vibration can be switched on and off everywhere (owner request):
- **One account setting:** a new Sounds and vibration card in the account's Notifications page has tap and key sounds, vibration, volume (low, medium, high) and notification sounds, in all 38 languages.
- **Remembered and followed:** the choice is remembered and followed on every device and page the person signs in on: the device settings on every LynkOmni device, the button phone, and the sign-in pad and notifications in the shell.
- **The button phone** now has a volume choice too.
- **Shared devices:** they still follow their manager, who can let each person's own choice apply. Silent mode, do not disturb and quiet hours still switch sounds off.
- **Always sound:** security and safety alerts always make a sound, and a sound is never the only signal.
- **The rule:** this is now a rule for all services. Every sound source is listed with its switch (catalog/sounds.v1.json), including the ones still to come (chat sounds in section 4, counter sounds in 13, spoken announcements and watch taps in 14, safety alarms in 7B). A page that makes a sound without being listed, or without following the person's choice, fails the checks.

## v0.59.1 (2026-11-20)
The LynkOmni emblem takes its final shape (owner decision, brand release @lynkomni/icons 1.9.0):
- The black bottom bar is thicker, now 186, the same as the violet arc. The arc is an even 186 all the way round.
- Around the lower dot, the arc and the bottom bar are mirror images of each other across the bar. The lower dot sits level with the bottom of the bar and the right side of the arc.
- The top is flat and level: the black frame and the violet arc meet the top gap at exactly the same height, and the line runs straight into the arc's curve.
- Unchanged: every gap (72), every gap around the centre dot (180), the bar at 45°, the colours and the LynkOmni name.
- Updated everywhere through the brand release:
  - the emblem and full logo in every colour version;
  - the small-size browser tab icon, the email images, and the app and install icons;
  - every emulator page;
  - the LynkVCard faces, and the share and store images.
- The geometry check now also locks the stroke thickness, the level edges and the flat top.

## v0.59.0 (2026-11-20)
The final LynkOmni emblem is in place everywhere (owner decision, brand release @lynkomni/icons 1.8.1):
- The three gaps in the emblem are all the same width (72), and every gap around the centre dot is the same (180), including the corner between top and right.
- The bar runs at exactly 45 degrees, both dots are true circles, and the outline flows as one figure through the top gap.
- The full logo carries the same emblem; the LynkOmni name is unchanged.
- The browser tab icon uses the small-size version, whose gaps stay open at 16 to 24 pixels.
- Updated through the brand release everywhere the logo appears:
  - the emblem and full logo in light, dark, high-contrast and one-colour;
  - the email images, the favicon, and the app and install icons;
  - every emulator page;
  - the LynkVCard faces and backs, and the share and store images.
- The brand library now has a geometry check that fails if the emblem ever drifts from these numbers.

## v0.58.3 (2026-11-20)
Ready for the final LynkOmni emblem (owner decision, brand release @lynkomni/icons 1.8.0):
- The final emblem is locked in the project rules: three gaps of 72, every gap around the centre dot 180, the bar at exactly 45°, one figure through the top gap. It must never be redrawn without the owner's written approval.
- The browser tab icon now uses the small-size version of the emblem when the brand release has one, so its gaps stay open at 16 to 24 pixels. No other place uses it.
- The automatic brand update could not rebuild the pictures that carry the logo (the picture renderer was missing). It now sets up the same fonts and browser as the layout checks first.

## v0.58.2 (2026-11-20)
The LynkOmni emblem is refined (owner request, brand release @lynkomni/icons 1.7.1):
- All three gaps in the emblem now match the top gap exactly; the two gaps around the lower dot are true circular curves.
- The violet arc is a perfect circular band, and the black frame flows into it as one smooth outline across the top gap. Nothing else changes: the dots, the connecting line, the colours, the size and the LynkOmni name.
- Updated everywhere through the brand release: the emblem and full logo in light, dark, high-contrast and one-colour, the email images, the favicon and app icons, every emulator page, the LynkVCard faces, and the share and store images.
- The brand-sync workflow now also rebuilds the pictures that carry the logo, so a future brand release reaches them by itself.

## v0.58.1 (2026-11-20)
PLACEHOLDER UPDATE, nothing left out (blueprint 83.7):
- Number hints now use the reader's own digits (for example Arabic-Indic or Bengali), like every number on screen.
- Thirteen more rules recorded in catalog/placeholders.v1.json and built with section 4 and every later section: load-more rows and "That's everything", new items shown at once as queued, upload previews with real progress, picture stand-ins instead of broken images, maps and media framed while loading, recent searches in an empty search, character counters, a reason on every disabled field, drafts kept as people type, upgrade previews instead of hidden features, initials for logos waiting their check, spoken interfaces never silent, skeletons in every colour mode.

## v0.58.0 (2026-11-19)
PLACEHOLDER UPDATE, the groundwork (owner request; master blueprint section 83):
- One shared part for waiting screens: cached content shows first; otherwise a grey skeleton shaped like the content to come (11 shapes: lists, cards, records, forms, tables, charts, chats, trackers, tiles, media, text). It never flashes (nothing before 300 ms, at least 300 ms once shown), says "taking longer" with Retry after 8 seconds, stays still with reduced motion or lite mode, and is read once as "Loading" by screen readers.
- Field hints: an example of what to type, never the instruction; the label always stays. Amounts, counts, emails and usernames use the same hint in every language; other hints come from each page's words. PINs, passwords, card details, codes and ID numbers never show example values.
- New checks: a new typing field without a hint fails at once; a hinted field must keep its label; no filler text (Latin filler, TODO, TBD, [Bank]) on any screen. 34 existing fields still need a hint and 2 a label; they are due in section 4, which cannot lock until they are done.
- Rules for all services now include skeletons, field hints and empty states, so every new screen gets them. Build table 83.6 added.

## v0.57.0 (2026-11-19)
Section 4, step B1 (INTERFACE UPDATE and TURN UPDATE groundwork: the registers, the rules and the checks):
- New navigation register (catalog/navigation.v1.json, read by core/navigation.py and ts/src/navigation.ts with shared vectors): the eight groups (Sell; Get paid; Run the office; People; Move and protect; Learn and work; Ask and decide; Build) with every one of the 33 products in exactly one; the app header and the focus header (only Back or Cancel and the connection chip in a payment, cash count, void, signature or ballot); the two-level side bar with Settings and Help that can never be hidden; the phone bottom bars (a person: Home, Track, Scan, Chats, Me; business types keep their five; four on a small phone; none on focus screens); quick create by role; the same menu order in every service; at most seven tabs in a page.
- New page-template register (catalog/templates.v1.json): every one of the 91 Business app screens has its template (Home, List, Record, Form, Steps, Report, Board and calendar, Inbox, Settings or Focus), and every emulator names its frame (app, device or page).
- Checks: every screen has a way in (no orphans) and everything used often is at most three taps from Home on a phone.
- Turning (TURN UPDATE): the device register now holds the layout for every shape (phone upright and sideways, small phones, tablets, folds half open, short and very wide screens, TVs, watches and buttons-only phones) through one decision function in Python and TypeScript, with shared vectors at real sizes from 240 by 320 to 3840 by 2160. Only fixed devices (kiosks, counter screens, displays, terminals) can be held to one direction; a person's own phone never is. The new ts/src/turn.ts applies a turn without redrawing the screen, so nothing typed, chosen or paid is lost or repeated, and a screen reader hears the change once.
- Leftover fixed: the installed web app was locked upright ("orientation": "portrait"); it now turns freely ("any"), and a check makes sure nothing in the code locks the direction again.
- The rules for all services (catalog/universal.v1.json) gained the navigation rule: every service, existing or new, must sit in one of the eight groups, and every screen needs its template and a way in.
- The English words of the new menus are in web/navigation/strings.en.json; they are translated when the shared parts that show them are built (step B2).

## v0.56.0 (2026-11-19)
Rules for all services now apply to everything by themselves (owner rule):
- A new register, catalog/universal.v1.json, lists every rule the blueprint lays down for all services: tracking, APIs, places, pictures, automations, LynkAssist, messages, emulators, connections, build tables, ads, cash and both sides, plus the rules already checked on every screen (five states, 38 languages, layout and turning, design, safe pages, global availability, security, money, prices, identifiers, speed, open to all).
- For every service the check answers by itself: met, not applicable with a written reason, or due in the service's home build section. A new service is checked by every rule the moment it exists; a build section cannot lock while anything is due there.
- What is due today, by section: LynkAssist skills, messages and trackers for most services in their own sections (for example LynkSchool and LynkProperty in 9B, LynkAcademy and LynkVote in 7, LynkFiles, LynkHR and LynkProject in 4B), cash at the counter for LynkSchool, LynkProperty and LynkAcademy, and the LynkAcademy and LynkProject emulators.

## v0.55.0 (2026-11-19)
Section 4, step A2 (shared groundwork: contract version 9 and new tracker kinds):
- Contract version 9 (contract/tools/build_v9.py): version 8 plus nine events that the section 4 links need: InvoiceIssued and CreditNoteIssued (an issued invoice never changes), PeriodClosed, DealStageChanged, ConversationCardSent, AdEarningsRecorded (validated impressions only), DocumentFiled, VoteRollImported (only the count, never a voter's name) and ExchangeSettled (by the licensed partner). Only moving a deal and filing a document can come from a device, and both work offline; the cloud alone writes the rest. Upcaster 8 to 9 only raises the version; nothing stored is rewritten. The validator now checks version 9 (1,508 checks pass).
- The connections register's section 4 links now name these events instead of planned ones.
- 21 new tracker kinds registered with their build sections, each on an identifier that already exists: bill to pay, expense claim, message delivery, signature request, approval, document request, verification, plan change, vote, dispute, held payment, pre-order, return, card request, journey, advert review, deposit return, report card, app review, purchase order and stock transfer. Their names are in all 38 languages.
- The account site, Business app and rider app demo files carry those names in 38 languages, so their size budgets rose a little (1,440 KB, 2,920 KB and 1,100 KB).

## v0.54.1 (2026-11-19)
The approved company profile words replace the old ones everywhere (owner, 19 November 2026):
- The main footer line under the logo is now the tag phrase "Run it all. Anywhere. Nonstop." (was "Works with or without internet."), in all 38 languages.
- The Business app's sign-in screen now says the plain line "One app to run your business, money and daily life, with or without internet." under the welcome, in all 38 languages.
- The README opens with the tag phrase and the approved definition; the brand note for the footer logo names the tag phrase.
- Master blueprint section 81 (in its new tab "Sections 81 onward", since the first tab is full) records the company profile and every page where each part appears.

## v0.54.0 (2026-11-19)
Section 4, step A1 (shared groundwork: connections and identifiers):
- New register catalog/connections.v1.json (blueprint 71.3): 49 links between services, each with its two ends, what passes, the contract events that carry it (or the events its build section will add), whose consent it needs and its build section. Every product family and the support desk, the Storefront and ads have at least one link. Read through core/connections.py.
- The ten journeys that cross services (blueprint 71.2): sale to books, quote to cash, hire to work, document to record, meeting to action, problem to fix, booking to visit, enrol to class, lease to rent and low stock to supplier, each made of registered links and finished in its build section.
- New check tests/test_connections.py: both ends of every link are real services, every event named is in the contract or waits for its section, a journey never finishes before its links, and everything is connected.
- Two new identifiers agreed in VOTE UPDATE: LOVOT- (a vote) and LOBLT- (a ballot receipt), now 50 types, read by Python, TypeScript, Rust, Kotlin and Swift.

## v0.53.0 (2026-11-19)
Section 4, part 1d (the ACADEMY UPDATE and SCHOOL UPDATE groundwork):
- New billing family LynkAcademy, outside LynkSuite, one price per organisation: $0, $19, $49, $129 a month, with 10, 50, 250 and 1,000 learners who opened a lesson that month, $5 per extra 100 on paid tiers, 3 own courses on Free (unlimited from Plus), and the tier features of blueprint 78.12. Learners never pay to join.
- LynkSchool Pro is now $55 (was $49) and Max $139 (was $129), agreed by the owner; Free and Plus are unchanged. Its tiers carry the new features of 78.18.
- Each LynkSchool tier includes the same LynkAcademy tier for the school's own learners and staff, never billed twice (78.17).
- LynkAcademy is a product in the catalog, its placements, the footer's "Work & records" column ("Courses & training" in 38 languages), the API register (built in section 11) and has its own picture.
- The revenue model: LynkAcademy joins the new families' stream (an assumption, outside the agreed totals), and LynkSchool's figures follow its new prices: about $2,476, $141,499 and $4,323,589 a month at the three stages.
- The build tables register now has the ACADEMY UPDATE (78.16) and SCHOOL UPDATE (80.15) tables, which their headings ("Build table") had kept out of the first count.

## v0.52.3 (2026-11-19)
Faster start-up on every screen, and a steadier speed check (owner: "Do it"):
- Every emulator now turns its packed data into bytes with a plain loop, about ten times faster than before. LynkPOS opens in about 1.1 to 1.3 s on the four-times-slower test phone (was 1.5 to 2.2 s, over its 1.5 s limit on the test machine), the Business app in about 1.4 s (was about 2 s), the others faster too.
- The speed check (every screen opens and answers a tap in time on a four-times-slower phone) now loads each screen up to three times and counts the fastest, because a shared test machine is sometimes busy for a moment. The time limits are unchanged; a real slowdown still fails all three loads, and a failure now shows every load's time.

## v0.52.2 (2026-11-19)
No crowded areas, even spacing (owner: "not only crowded buttons but also crowded areas and uneven spacing"):
- New rules in tests/test_fit_guard.py, on every emulator, every size, state and pop-up: two visible boxes (cards, fields, panels, chips, filled buttons) never sit closer than 3.5 px, side by side or stacked; a run of three or more repeated items (rows, cards, buttons, chips) has even gaps, apart from a deliberate section break of 24 px or more. Proven on a sample page with both faults; the pointer is moved away first, so a hovered item never counts.
- Found and fixed: notification rows touched each other (now 4 px apart); LynkAssist's action buttons in help were stacked with no space (now 8 px).
- Screens still fit every width from 240 to 3840 px with nothing spilling or scrolling sideways (tests/test_layout_i18n.py DeviceFit, unchanged).
- A check warning (an unclosed file and a text escape in the fit guard) is fixed.

## v0.52.1 (2026-11-19)
No space that is not needed (owner report, a phone screenshot of the newsletter's topics: "Avoid unnecessary empty space around menus, topics"):
- Newsletter topics (the footer on every page): the four choices now sit in two even columns that line up, with no extra space between the rows. Each tick box keeps its full tap size.
- "We accept" list in the footer: these are words only, with nothing to tap, so the rows no longer take a tap-sized height (about 16 px less each).
- App launcher (every product tile, on every device): tiles and rows sit closer together, about 12 px less a row, and every tile can still be tapped easily.
- Account menu: the LynkOmni ID now sits under the person's name instead of running into it ("GraceLOID-4…").
- New check in the fit guard (every emulator, every size, light and dark, every pop-up): tick choices that wrap must line up in columns with no extra space between rows; menu and list rows may not leave more than 12 px of empty space beyond what they hold; the account menu's name and ID never share a line. It fails on the old pages and passes now.
- All emulators rebuilt.

## v0.52.0 (2026-11-19)
ADS UPDATE, the groundwork (owner request; master blueprint section 79):
- One ads register, catalog/ads.v1.json, now lists every place an ad may appear. It is an allow-list: a screen not listed there never shows an ad. It also holds the protected screens (payments, cards, exchange, agent services, sign-in, security, signatures, LynkAssist answers, notifications, messages, children's and household places and more), the categories, caps, the "really seen" rule, the controls and the revenue streams with their build sections.
- The ads service follows the register. An impression counts only when at least half the ad was on screen for a second; a device can count at most 6 an hour; clicks and redemptions count only after a counted impression.
- Merchants decide: receipts, the customer display, in-store screens and offers show ads only after the merchant switches them on, and the merchant earns the share there. Merchants can block an advertiser or a competitor and see their ad earnings.
- People decide: every ad has Why am I seeing this? (never anything about the person) and Report this ad; reports from three shops pause a campaign for a person's review.
- Useful beats loud: an ad that matches the screen's subject ranks twice as high. Advertisers see totals only, and nothing below 5.
- New categories: get-rich-quick, unlicensed finance, counterfeits, surveillance tools and hate are always refused; alcohol, dating, diet and body image, energy drinks and cosmetic procedures only where the country allows them and never for children; health and medicine need a licensed advertiser.
- The "where every part is built" table 79.10 is added to the build tables. Every price, share and revenue figure for ads stays a placeholder and an assumption.

## v0.51.2 (2026-11-19)
Tracking through every service's API (owner request):
- Every service that has a tracker now shows its steps through its own API: tracking.read gives a record's steps in the five states (queued, sent, accepted, confirmed, failed) and tracking.events sends a notice at each step. Added for LynkPOS (orders, deliveries, leases, agent requests, device requests), LynkAcc (payouts, tax returns), LynkInv (invoices, quotes), LynkCRM (repairs), LynkStock (group orders), LynkMPay (payments, financing), LynkCheckout (standing payments, collections), LynkAttend, LynkQueue and LynkSurvey.
- Outside apps get only the customer view: no address, phone number, rider identity or position. Personal account trackers (sign-up, recovery, data requests, payout changes) are never in an API.
- A test fails if a tracked kind has no API, so new trackers follow automatically. Each API is still built in its own build section.

## v0.51.1 (2026-11-19)
Fixes the owner found on a phone, and a check so they cannot come back:
- Newsletter sign-up in the main footer (every page that has it): the agreement line, the Subscribe button and the note under it touched each other. They now have clear space between them.
- Account sign-in: the "Sign in with a passkey" and "Use another way" buttons touched the line explaining them. Found by the new check and fixed.
- "Find or do anything" (search): the "Ask LynkAssist" button touched the keyboard tip under it. Found by the new check and fixed.
- New rule in tests/test_fit_guard.py (layout job): on every emulator, at every size, in every state and pop-up, a button never touches the text right above or below it (at least 4 px). It fails on the old code.

## v0.51.0 (2026-11-19)
WhatsApp is removed from the whole LynkOmni ecosystem (owner decision, 2026-11-19), so LynkOmni stays focused on its own system:
- LynkAttend: the PIN and IDCN go by email, LynkChat or text message; the WhatsApp choice is gone from the manager's screens.
- LynkQueue: people join by the link or QR code, LynkChat or a basic phone. The plan feature is now "LynkChat" (LynkQueue Plus and up), not "WhatsApp and LynkChat". Prices do not change.
- LynkSurvey: people answer by smartphone, website, LynkChat, basic phone, voice call, kiosk, POS screen, email, field interview or paper; the "one per phone" code goes by text or LynkChat. Prices do not change.
- Invoice reminders: in the app, LynkChat, text message or email.
- Message packs and the messaging partner cover text messages and USSD only; the provider ledger no longer asks for a WhatsApp Business provider.
- Delivery menu on the emulators: "LynkChat, SMS or email", in all 38 languages.
- Contract version 8: the same as version 7 without the WhatsApp values. An older test event that names WhatsApp reads as LynkChat; nothing stored is rewritten.
- Kept on purpose: LynkOmni's own WhatsApp Business account stays in the footer's social links as a marketing channel only, and "WhatsApp" stays a protected name in translations so a brand name typed in a chat is never translated.
- All emulators rebuilt.

## v0.50.1 (2026-11-19)
Font check across the ecosystem (owner request):
- The font register's script rules never reached the emulators: the build copied only the Latin font files from design/fonts.css. Now every emulator carries them: taller lines for Arabic and Indian scripts, and letters that join (Arabic script, Devanagari, Bengali, Tamil, Thai) are never spaced out or capitalised, nor are Chinese, Japanese and Korean spaced. The rule sits on each screen's language and also covers every style of the page that spaces out or capitalises letters, so small labels are safe too, while a tap stays as fast as before.
- The "Try it" controls and event log beside each device carry the screen's language and writing direction, so Arabic and Hebrew read right to left there too.
- The tracking page's code text uses the mono font from the design tokens.
- Checked: no font is loaded from another website; fonts come only from the register and the tokens; every screen sets its language and direction. Emulators carry the Latin brand fonts (Montserrat, Inter); other scripts show in the device's own font, as decided to keep each emulator one small offline file. The real apps load each language's own fonts from the register.
- Also: Chinese, Japanese and Korean brackets keep their width at a line end, so short labels wrap instead of spilling; search results and menu rows keep their small grey text readable when hovered; the tablet's customer welcome wraps long Tamil words.

## v0.50.0 (2026-11-19)
Section 4, part 1c (the build-order tables and a steadier layout check):
- The thirteen "where every part is built" tables of the master blueprint (64.11 to 76.8, 147 rows) are now a register, catalog/build-tables.v1.json, read through core/build_sections.py. Each row names its build sections and records which are done and in which version.
- New check tests/test_build_tables.py: a build section cannot be locked while any of its parts is still to build, nothing is marked done ahead of the build order, and every version named is in this change log. Sections 3A and 3B have all their parts done; section 4 has 13 parts, with the prices and families of parts 1a and 1b recorded as progress.
- The showcase's progress table shows, for every build section, how many of its parts from the updates are done.
- The layout check in CI: each of the 8 parts now stops after 25 minutes, and its set-up after 10, so a stuck part fails fast instead of blocking for an hour. The fit guard is shared across all 8 parts (each takes every 8th emulator) instead of all running in part 1, which took about twice as long as the others.

## v0.49.0 (2026-11-19)
Section 4, part 1b (the eight new families, placed everywhere):
- Eight new billing families, each outside LynkSuite and priced per organisation: LynkExchange $0, $9, $29, $79 (LynkOmni's part 0.50%, 0.40%, 0.30%, 0.20%, and automatic levels by 30-day volume: a customer pays the lower part); LynkVote $0, $9, $29, $99 (voters in a vote 100, 1,000, 10,000, 100,000; extra 1,000 voters $3, $2, $1); LynkHR $0, $9, $29, $79 (staff 5, 50, 250, 1,000; $4 per extra 100); LynkProject $0, $5, $15, $39 (members 5, 25, 100, 500; $3 per extra 50); LynkSchool $0, $19, $49, $129 (learners 100, 500, 2,500, 10,000; $5 per extra 500); LynkProperty $0, $9, $29, $79 (units 5, 50, 250, 1,000; $5 per extra 100); LynkFiles $0, $4, $11, $29 (storage 5 GB, 100 GB, 500 GB, 2 TB; signature requests 5, 50, 500, unlimited; $2 per extra 100 GB); LynkJobs $0, $15, $45, $129 (open jobs 2, 10, 50, unlimited; $3 per extra open job).
- LynkJobs Pass for job seekers $0, $1.99, $3.99, $7.99 (tools only: seekers never pay to search, apply or be hired); featured jobs from $5 a week; freelance work 5%, paid by the client through the provider; paid contest votes 5% capped at $0.10 a vote; government elections by agreement with a guide of $0.10 per registered voter; Plus at no charge for verified schools in LynkSchool and LynkVote; a 20% bundle across the six office services (or one of them with LynkAttend) and a 20% bundle for LynkVote with LynkAttend, LynkQueue, LynkSurvey or LynkBooking. Every number is pinned by the price lock.
- Each family is in the product catalog, the address map (both sides: the workspace path and its Storefront twin; new hosts vote.lynkomni.com and job.lynkomni.com), the placements register (header, launcher, search, help, product page, pricing, sitemap, footer, app menu and, where a person has their own side, the account menu), the API register, the search pages and the footer: LynkExchange joins Products, LynkVote joins People and service, and a new "Work & records" column holds LynkHR, LynkProject, LynkFiles, LynkProperty, LynkSchool and LynkJobs, each with its plain word in all 38 languages.
- Eight new product pictures (no words, faces or people; light, dark and both high-contrast sets).
- The build order now lists sections 4B (LynkFiles, LynkHR and LynkProject in full), 8B (LynkJobs in full) and 9B (LynkSchool and LynkProperty in full); four first automations are registered for them.
- The revenue model shows the eight families and LynkJobs Pass as their own assumed stream, outside the agreed totals: about $2,213, $126,470 and $3,864,361 a month at the three stages. Every figure is an assumption.
- 2026-11-19: The documents and e-signature service is named LynkFiles (owner's choice on 19 November), at lynkomni.com/files and app.lynkomni.com/files. The plural of LynkDoc stays banned as a name and as an address, so it is never confused with LynkDoc, the developer documentation at doc.lynkomni.com.
- 2026-11-19: Leftover adjusted in section 4: the platform's "Business documents API" became the LynkFiles API, because business documents and e-signature moved into LynkFiles as its engine (blueprint 69.7).
- 2026-11-19: The pricing chart's size budget was raised from 32 KB to 44 KB, because it now shows 32 families.

## v0.48.1 (2026-11-19)
Fixes the owner found on a phone, and checks so raw names can never show again:
- LynkQueue on a phone showed "ppl_at_way_whatsapp" and "ppl_at_way_lynkchat" instead of WhatsApp and LynkChat. The queue borrows these two words from LynkAttend, and the page builder left LynkAttend's words out of the queue page. A page now always keeps every word its own code uses.
- The owner's Automations page (laptop) showed three automations by their raw names: the customer order updates, the late-order watch and the LynkDriver update reminder had never been given a name. They now have names in all 38 languages.
- New check without a browser (tests/test_words_guard.py, runs in every check): every word name a page's code uses is packed into that page, in every language. It fails on the old code.
- New on-screen check (tests/test_fit_guard.py, layout job): every emulator is clicked through, every state and every tab, view and choice it offers, and the check fails if a raw word name shows in text or in a label read aloud.

## v0.48.0 (2026-11-19)
Section 4, part 1a (prices first, as agreed when section 4 was planned):
- Office top-up: LynkAcc now $0, $6, $19, $49; LynkInv $0, $5, $15, $39; LynkCRM $0, $6, $19, $49 a month (were $0, $6, $15, $40 for LynkAcc and LynkCRM and $0, $5, $12, $32 for LynkInv). LynkOps stays $0, $20, $49, $129, so buying the four services through LynkOps now saves about 31% on Plus and 40% on Pro and Max. LynkSuite's prices do not change. The price lock, the bill rules, the revenue model and every emulator follow.
- The BOOKING UPDATE prices (made as v0.44.1 in pull request 78, which is folded into this version): the LynkBooking Pass is $0, $1.99, $3.99 and $7.99 a month; the LynkBooking business tiers ($0, $19, $49, $119 per organisation, places 1, 3, 3, 3, extra place $5, $10, $20, extra 1,000 bookings $1), the 20% bundle discount and the commission only on bookings LynkBooking brings are locked in services/billing.py; the flat $0.25 appointment fee is gone and the business side is its own assumed revenue stream.
- Revenue a month is now $21,632, $1,413,452 and $46,046,891 at the three stages. Every figure is an assumption about how many businesses choose each plan.
- 2026-11-19: Leftover adjusted in section 4: LynkBooking counts its devices by its own places (like LynkAttend, LynkQueue and LynkSurvey), so its $6 extra device price from section 3A is removed; extra places are bought at the LynkBooking place price instead.
- 2026-11-19: Leftover adjusted in section 4: the bill test's lowest allowed bundle price (a bundle never drops below 59% of its services bought one by one) was set for the old prices; it now fits the new ones.

## v0.47.4 (2026-11-19)
Fixes the owner found on a phone, and a check so they cannot come back:
- Side menus (Account and every screen built on the shared shell): on a tablet the narrow side menu squeezed 23 items into the screen's height, so labels were cut at the bottom and the sides ("Secur", "Notifi"). A long menu now scrolls, every item keeps its full height, and a long name goes onto a second line. The same for the computer side menu, the phone's bottom tabs (names were cut with "…" on small phones) and the Business app's tablet side rail.
- Pop-ups on the laptop and tablets ("Is this right?", search, help, account, sync, notifications): they used the phone's slide-up sheet, stuck to the bottom edge, so on the laptop the card looked cut off. On anything wider than a phone they now sit in the middle of the screen with every corner rounded; phones keep the slide-up sheet.
- The owner's laptop screen ignored mouse clicks: "no touchscreen" was treated as "buttons only". A screen with a mouse, trackpad, stylus or touch now takes clicks; only buttons-only screens ignore them.
- In the search pop-up of every device the Close button covered the microphone (Speak) button. The search row now ends before Close.
- New check (tests/test_fit_guard.py, in the layout job): every emulator, at every size it offers, light and dark, plus the signed-in Business app on phone, tablet and computer: no menu item squeezed, no menu label cut, no item outside a menu that cannot scroll, every pop-up inside its screen and off the edges on wider screens, every visible pop-up button really pressable, and every screen with a mouse or touch takes clicks. It was run against the old code and caught all four problems.
- Three browser tests (device shell, Business app, placements) were skipped in every automatic run because their job had no browser; they now run in the layout job, and a new rule fails whenever a browser test is not run by a job with a browser.

## v0.47.3 (2026-11-19)
- Checks: the layout check's tests take about 5 minutes in each of its 8 parts, but downloading the fonts and the test browser from Ubuntu took 1 to 27 minutes per part. They are now kept in GitHub's check cache after the first run and restored in seconds (tools/ci/layout_setup.sh), with retries if a download is needed. The test browser's version is pinned so the stored copy always matches.

## v0.47.2 (2026-11-19)
Fixes the owner found on the counter tablet:
- Sell by voice: the microphone picture had no size and filled the whole basket, pushing its words onto the Charge button. The microphone is now a normal-size button beside Charge, with its name for screen readers.
- The basket keeps the total, the microphone and Charge always in view; only the list of lines scrolls.
- A main button that cannot be used yet (Charge with an empty basket) is now solid grey with readable grey text in every emulator, instead of a see-through purple that looked broken. Checked every emulator in every state: no other button picture was oversized.
- Checks: the font and browser download in the layout check now retries by itself, so a short outage of Ubuntu's package servers (as on 19 November 2026) no longer fails a pull request.

## v0.47.1 (2026-11-19)
Fixes the owner found on a phone:
- Counter tablet: the first-launch card ("Is this right?") was cut off below "Yes, continue". A shared rule added with the Emulator Panel (web/device/emkit.css) outweighed the tablet's own screen layout, so the app grew taller than the screen. The rule now has no weight (:where), so every device keeps its own layout. No other emulator was affected (checked on all of them, computer and phone size).
- Counter tablet: the PIN keypad's bottom row (0 and the tick) needed scrolling on the wide, short tablet screen. The keypad now sits beside the name, title and dots, so every key shows; right-to-left mirrors it.
- Main footer: the line under the logo ("Works with or without internet.") had lost its spacing inside the app shell, so it touched the "Products" heading. It now sits close under the logo with a clear gap above the columns, on every page.
- Key sounds, like a real device: every number key now plays its own telephone keypad pair (1 to 9, 0, * and #), and confirm, cancel, clear, moving around (arrows, menu, soft keys), tabs, switches on and off, scanning and printing each have their own tone and vibration. One shared rule (ts/src/keytones.ts, tones from the design tokens) serves every device emulator on the Emulator Panel and the button phone, which also gained Key tones and Vibration switches. A PIN, door code or ID number follows the manager's existing choice: each key its own tone, or one same tone on every key. One sound player is reused for every press.
- Faster checks: the layout check runs as 8 parts at the same time (every language still checked once), a branch is checked once through its pull request, and a newer push cancels the outdated run. About 6 minutes instead of 35.

## v0.47.0 (2026-11-19)
Section 3A, the Emulator Panel (EMULATOR UPDATE, master blueprint section 70):
- One register of every emulator (catalog/emulators.v1.json): 24 built today on 10 device emulators, 9 planned with the section that builds them, and the screens that are not on the panel with the reason. Every emulator states the four checks (touch, buttons only, offline, sides).
- The rules (core/emulators.py, with the TypeScript port ts/src/emulators.ts agreeing on shared vectors): only connected staff screens count against the plan, a till that runs several services counts once, customer screens and practice mode are free; codes work once for 10 minutes; the check before assigning names what is missing and the way round; hardware ways per device (with the honest iPhone and iPad limit); key tones and vibration; the delivery menu; screen fit without stretching.
- Contract version 7: the device only asks (Accept or Deny, Connect request, signing in and out, its own tone settings, its health); the cloud alone offers, connects, disconnects, locks, swaps and approves again. LynkSurvey's "You said, we did" now has its own cloud event and message.
- The panel in the Business app: app.lynkomni.com/business/emulators (also under Branches and devices) and each service's own panel (/sell, /stock, /attendance, /queue and /survey plus /emulators; the Storefront side by the /external rule). Your plan, extra devices priced per service (LynkPOS $8 a month, others $2 to $14) with a note when the next plan costs less, a $1 day pass for events and market days, Add a device with a QR code, a Lynk Code and a link, "Set up" for a whole service, the live list with health, "Why?", connect, disconnect (safe, offline waits as "sent"), mark as lost, swap, approve again, practice here, tones per device, see the screen only with consent, and who used what.
- On every panel device (LynkPOS, counter tablet, Business app, kitchen screen, rider app, customer display, stock scanner, LynkKiosk, LynkCDisplay, LynkDScreen): the connect request with Accept or Deny, "Add to home screen", the disconnected screen with Ask to connect, the locked and waiting-for-approval screens, the practice banner, key tones and vibration from one shared tone set in the design tokens, the hardware helper and the delivery menu. All by touch or by arrows, OK and Back.
- LynkFlow runs the panel's automations (Connect requests and device alerts to the branch's managers, and the daily housekeeping: temporary emulators end, 30 days unseen needs approval, a downgrade's 3 days of grace); LynkAssist explains a device and prepares connect, disconnect, mark lost and practice for a manager's Confirm, with Undo.
- Trackers for an emulator request, a device swap and a device approval; five security controls; the panel in search, help, settings and the app menu; extra devices and day passes as their own assumed revenue stream; every new word in all 38 languages. Bluetooth, Wi-Fi and USB joined the translation glossary, and four older translations that had changed "Wi-Fi" were corrected.

## v0.46.0 (2026-11-19)
Section 3B, part 3 (LynkSurvey in full, on every device); section 3B is locked:
- LynkSurvey's service (people/survey.py): roles and the organisation tree (a viewer sees only their own part), the 13 kinds of survey, "Write it for me", the clear question check, a new version once answers arrived, approval with Approve or Send back, test mode, who can answer (anyone, one per phone with a code, invitation only, signed in), anonymous surveys, groups to fill, "How many people do I need?", asking at the right moment (after a sale, a queue ticket, a chat, an attendance shift), reminders (at most 2), rest periods and "Don't ask me again".
- Answering on every device: the phone page (new emulator, survey-page), LynkKiosk ("Give your opinion"), LynkDScreen (live poll), LynkCDisplay ("Rate us"), LynkPOS, the Business app (field interviews and paper, marked "Entered by staff"), and the basic phone by menu numbers (USSD, text and voice; Python and TypeScript with shared vectors). One question a page; "Why?" only after an unhappy answer; answers made without internet stay queued and are never shown as sent.
- "Real answers only": answers that look too fast, all the same or many from one phone are marked "Please check", never deleted, and a person keeps or sets them aside.
- Results never below 5 answers, each with its margin; the recommend score; goals with words beside the colour; verified results with a check link; research tools by plan (compare groups, "Real difference or chance?", balancing with both results shown, themes in written answers, what matters most and trade-offs, before and after, downloads with labels and never who answered, the research record).
- Closing the loop: Call back tasks with a time limit, and "You said, we did" (shown on the public page for an anonymous survey and in each person's My answers).
- Rewards and the LynkSurvey Panel in sandbox: paid only through a licensed partner after the check ("Coming to your country soon." until one is signed), one per person; the researcher never sees who is on the panel.
- Trackers: attendance correction and survey reward joined the tracking register. LynkAssist: put a ticket back, fix a missing check-out, pause a survey and send reminders joined its register, and the three planned 3B actions are built. Nine LynkSurvey and people automations run on LynkFlow.
- 289 new screen words in all 38 languages.
- 2026-11-19: Leftover adjusted in section 3B: the names of the research file formats (CSV, SPSS, Stata, R) are shown as names in the code, not as words to translate, so no language turns a product name into Latin letters in its own script.
- 2026-11-19: Leftover adjusted in section 3B: "You said, we did" was counted but reached nobody; it now shows in each person's My answers and on the public page. As a message it needs its own event, which joins the next contract version (made in section 3A).
- 2026-11-19: Size and speed budgets raised with their reasons (the demo files carry LynkSurvey in all 38 languages); the survey engine is made only when a survey screen opens.

## v0.45.0 (2026-11-18)
Section 3B, parts 1 and 2 (LynkAttend and LynkQueue in full, on every device; LynkSurvey follows as v0.46.0):
- LynkAttend in full: register a person with their agreement and their set (Face, then Finger, then IDCN; Finger, then IDCN; or IDCN only), PINs made only by LynkOmni in PIN groups (one branch or one event is one group, never given twice), check-in by hand only when every means failed and never for yourself, visitors with the manager's permission, the fire list that works without internet, shifts with "No check-out" after 2 hours, leave, events and courses with certificates anyone can check, door devices that can be locked, the clock check, everything managers did, what is counted this month, and requests from people (delete my details, dispute) with reminders at 7, 14 and 25 days and deletion by itself at 30.
- LynkQueue in full: places, sections with a 3-character code and their hours, counters, priority (1 after every few others), Send to another section with the same ticket number, Put back, Running late (once), Leave queue, closing the day ("Not served today"), the public queue page (ticket numbers only), the busy-hour forecast from the place's own past days, reports by plan, and flags that are never an accusation.
- The queue keeper: one device in the building keeps the queue so the order stays right without internet; each device has its own block of ticket numbers from the cloud, and another added device takes over by itself.
- Ways to join: reception, LynkKiosk, a phone link or QR code, WhatsApp and LynkChat (sandbox, "Coming to your country soon." until the message partner is signed), a basic phone (menu numbers: 8 for Running late, 9 to leave) and appointments. No name, app or account is needed; a phone number is used only for that ticket's messages and deleted after 30 days.
- New real-device emulators: LynkKiosk (check in or take a ticket, with a paper slot that prints), LynkDScreen (the calling screen with the changing QR code and the voice), LynkCDisplay (the small screen above a counter) and the queue page on a phone. The Business app, LynkPOS and the button phone gain the full queue screens.
- A queue ticket is a tracked item (waiting, called, served, missed, left the queue, not served today) in the tracking register; a ticket can be called or missed more than once.
- Six queue automations run on LynkFlow (please come, not served today, open another counter, busy-hour forecast, pickup collection, a check-in opens the person's counter); automations that are off by default can now be switched on per place.
- Plans and limits are read from billing: included tickets, extra tickets per 1,000, places, sections and counters; nobody is turned away when the Free limit is reached that day.
- Fixes found by the layout check: tags, detail panels, counter cards and the phone page's address line now pass the contrast check; ticket numbers wrap instead of spilling when a code has wide letters; long buttons wrap inside their row.
- 347 new screen words in all 38 languages; size budgets set for the new emulators and the default raised to 600 KB (with the reason in web/budgets.v1.json).

## v0.44.0 (2026-11-12)
NEW UPDATE 4, section 3 (Business app and LynkPOS):
- The Business app hub gains Attendance, Queue and Surveys for every business type and workspace, each at its own address (app.lynkomni.com/attendance, /queue, /survey), with How you use it (Just me, One place, Many places: prices, limits and rules stay the same) and Add a device (pick a LynkOmni device from the device register and type a one-time code on it; owner or manager only; offline it waits and is never shown as confirmed).
- Attendance: today at the door (who is in, how they checked in, any backup or flag in words) and where the door runs.
- Queue: sections with the ticket numbers ready on the device, waiting now in the fair order, counters (open, paused, closed; Call next, call again up to three times, served, did not come, send to another section) and reception (Give a ticket, priority for an older person, pregnancy or disability).
- Surveys: the rating after payment switch and the results (average and share, with the margin; nothing shown below 5 answers; sandbox answers are labelled).
- LynkPOS: the door (PIN, then face or finger, then IDCN with a checker who is not the person; dots only, never the digits), reception with the ticket printed on the receipt printer, and the counter, all from the menu and search, by touch or by the keys alone, and all working offline.
- The customer screen asks "How was your visit today?" after a confirmed payment (five answers with their words on a touch screen, the Rate us QR on a screen that only shows); never required, saved offline.
- Fixes found by the layout and speed checks: the rating shows numbered dials 1 to 5 beside the words instead of emoji (emoji look different on every phone and a device without an emoji font slowed the first screen), easy PINs are counted by the tests and no longer at start, the 0 to 10 score keys are now 44 px, Rate us wraps on a 240 px screen, and the words under a chosen setup option keep full contrast.
- One shared engine for all of this (ts/src/peoplehub.ts) with its own tests; 89 new screen words in all 38 languages; size budgets raised for the new words.

## v0.43.0 (2026-11-11)
NEW UPDATE 4, section 2 (LynkOmni Account):
- My details (attendance): opened only after a code to your own contact; your set, your PIN and IDCN (hidden until Show), your attendance, a proof of attendance to download, the "Was this you?" switch, and Delete my details or Raise a dispute with the 30-day date and the manager's reminders at 7, 14 and 25 days.
- My tickets: your ticket with your place and the estimate, Running late (once per ticket) and Leave queue; earlier tickets. No account is needed to take a ticket.
- My answers: surveys you answered that are not anonymous, Delete my answer, and Don't ask me again for each organisation (anonymous surveys are never listed).
- LynkSurvey Panel: join or leave (leaving deletes your panel details); rewards show "Coming to your country soon." until a payment partner is signed.
- Notification settings gain the "Attendance, queues and surveys" area; breadcrumbs on every new page; 56 new screen words in all 38 languages.
- PINs are no longer counted at start (a fixed number, checked by the tests), which kept the first screen within its time on slow phones; the account site's size budget is raised for the new pages in 38 languages.

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
- 2026-11-19: Leftover adjusted with v0.51.0: tests/test_attendance.py, ts/test/peoplehub.test.ts and ts/test/surveydesk.test.ts now check events against the current contract (version 8) instead of version 6.
