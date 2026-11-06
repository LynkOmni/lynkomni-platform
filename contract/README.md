# LynkOmni Contract v1

The machine-readable contract between LynkDVBox (device) and LynkCCBox (cloud). It implements sections 1B, 1C, 4, 5 and 7 of the Master Build Specification. Both boxes, the mobile app and the server are built against these files, never the other way round.

**Status: v1 draft, ready for review.** It freezes when three things happen: (1) the Phase 0 audit finds no conflict with existing code, (2) you review it, (3) the RRA's written answer is checked against the tax fields (`tax_code`, `tax_mode`, receipt validity). After the freeze, any change needs a new `schema_version` and an upcaster note.

## Files

| File | What it fixes |
| --- | --- |
| `event-envelope.v1.json` | The outer shape of every event, device-origin and server-origin |
| `event-payloads.v1.json` | Every allowed event type and its payload (21 types). Unlisted types are quarantined |
| `permissions.v1.json` | Roles, permissions, channels, recovery-window restrictions |
| `command-policy-register.v1.json` | Every command: class A/B/C, offline rule, permission, outcomes |
| `state-machines.v1.json` | The only statuses and labels the UI may show, and legal transitions |
| `tools/validate_contract.py` | Cross-checks all files, validates events, runs a reference model of server intake |

## Locked rules

1. **Money** is integer RWF. **Quantities** are integer thousandths (1000 = 1 unit). No floating-point number is allowed anywhere in an event.
2. **Rounding:** `line_total = (quantity_milli × unit_price + 500) ÷ 1000 − discount`, integer division. `subtotal = Σ line_total`. `total = subtotal` (plus `tax_total` only when `tax_mode` is `exclusive`). Tax rules stay provisional until the RRA answers.
3. **IDs:** every entity created on a device (event, sale, payment, product…) is a UUIDv7 made on the device. Merchant, branch, device and user IDs are server-issued UUIDs.
4. **Ordering:** within a device, `device_seq` (1, 2, 3, no gaps). Across devices, the server's `server_cursor`. Device clocks are informational only.
5. **Hash chain:** `prev_hash` is `GENESIS` for sequence 1, otherwise the SHA-256 (lowercase hex) of the previous event's signing bytes. Signing bytes are the event without `signature` and without server-stamp fields, serialized as canonical JSON: keys sorted, no spaces, UTF-8, no floats. Production must use an RFC 8785 (JCS) library and cross-check it against this tool's output.
6. **Signatures:** ECDSA P-256 (ES256), raw r‖s, base64url. P-256 is chosen because it is hardware-backed on the widest range of Android phones; Ed25519 is not.
7. **Facts are never rejected.** Class A events are accepted, flagged or quarantined. Quarantine is visible and never blocks later events: the sequence slot is consumed.
8. **Idempotency:** the same `event_id` any number of times produces one stored event. A different `event_id` carrying an already-used entity ID is quarantined as `duplicate_entity_id`.
9. **Stock** is a sum of deltas, so it is independent of event order. It may go negative and is flagged. `StockCounted` stores the device's own view, so a count changes stock by `counted − device_view` and cannot erase a sale made on another device.
10. **Payments:** a device can record cash as received, non-cash as pending, and an owner's manual confirmation (always labeled). Only a provider callback can produce `confirmed`.
11. **Receipts:** devices emit only `provisional` receipts in v1.
12. **Product events are device-origin only in v1** because web editing is read-only until after the pilot.

## How to verify

```
python3 tools/validate_contract.py
```

Current result: **382 checks passed, 0 failed.** It also passed a mutation test: four deliberate breakages (cloud rejecting sales, broken role nesting, devices issuing valid receipts, server ignoring the hash chain) were each caught. The hash-chain mutation was first missed, so a test was added for it.

## What this does not prove

- **Signature verification.** Only the signature format is checked. Real ES256 verification needs the device key and a crypto library.
- **The real server and real phones.** The ingest code in the script is a reference model of the rules, not LynkCCBox. The stack-comparison tests (T1 to T12) still run on real hardware.
- **Revocation and backdating.** After a device is revoked, its later pushes are accepted only if their claimed time is before revocation, and they are flagged for owner review. A thief who knows this can backdate a device clock. The damage is bounded by what the device could do before it was wiped, and is always visible as a flag, never silent. The security review must examine this.
- **Chain integrity is not authenticity.** The hash chain exposes deletion, reordering and edits. Only the signature proves who made an event.

## Changing the contract

1. Edit the JSON.
2. Run the validator. It must pass.
3. Add a new `schema_version` for any payload change and write the upcaster note.
4. Never edit a published version in place.
