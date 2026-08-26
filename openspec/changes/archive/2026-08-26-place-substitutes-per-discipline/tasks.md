## 1. The placement rule

- [x] 1.1 Extract the per-discipline placement helper (design D1) beside the existing capacity helpers, returning which of a selected set of disciplines are full at this moment, and rewrite `amend()` (`registrations.py:687`) to call it in place of its inline `full` set. Verify the backend suite still passes unchanged — `amend()`'s behaviour must not move.
- [x] 1.2 Rewrite `register()` (`registrations.py:441-455, 514`) to place each entry from that helper, dropping `as_substitute` and the whole-registration flag. Keep the post-settlement branch, which still queues everything regardless of capacity. Verify a submission mixing one full and one open discipline returns one seated and one queued entry.
- [x] 1.3 Remove `wait_for_all` from `RegisterIn` (`schemas.py:746`) and the `409 full_disciplines` branch from `register()` (design D2). Verify no `wait_for_all` remains under `backend/app/` and that a submission naming a full discipline is accepted rather than refused.

## 2. Queue membership

- [x] 2.1 Extract the live-registration predicate now spelled out inline in `taken_seats()` and `taken_team_slots()` into one reusable clause in `availability.py` (design D3), and use it in both. Verify the capacity tests pass with no behaviour change.
- [x] 2.2 Re-found `queue_length()` and `team_queue_length()` on that predicate instead of `Registration.state == RESERVED`. Verify a paid registration holding a queued placement is counted in its discipline's queue length.
- [x] 2.3 Re-found `queue_position()` (`registrations.py:73`) on the same predicate. Verify that a paid fencer holding a queued placement and a later-registered reserved fencer in the same discipline come back as positions 1 and 2 rather than both as 1.

## 3. Promotion

- [x] 3.1 Replace `admit_substitute()`'s `state != RESERVED` guard (`registrations.py:840`) with a refusal of cancelled and expired registrations only (design D4). Verify promoting a paid registration succeeds and promoting a cancelled one still returns 409.
- [x] 3.2 Leave the registration's state untouched on promotion so a PAID registration stays paid and owes the difference through `outstanding_cents`, and record the audit event as `amend()` does. Verify a registration paid for one discipline and then promoted into another reports the second discipline's fee as outstanding, stays in the paid state, and carries a fresh window.
- [x] 3.3 Add the promotion notice (design D6) naming the discipline whose place opened, the amount now due, and its due date, with the payments-off variant stating the place and no amount due. Verify both variants render in each locale bundle and that no literal reaches the template.
- [x] 3.4 Send the new notice from `admit_substitute()` in place of `send_registration_confirmation`. Verify a promoted fencer who had already paid receives a notice stating the surcharge rather than their full total.

## 4. Lapse

- [x] 4.1 Add the demote-rather-than-expire branch to the expiry pass (`scheduler.py:98`) for a registration holding any substitute placement, with its own `PaymentEvent` kind distinct from `promotion_lapsed` (design D5). Verify a mixed registration whose window lapses stays reserved, keeps its queued placement and its registration order, and frees the seat it did not pay for.
- [x] 4.2 Verify a registration holding no substitute placement still expires exactly as before, on a tournament whose seating has not settled, and that the payments-off dormancy rule is unaffected.

## 5. Frontend

- [x] 5.1 Remove `wait_for_all` from the registration payload type (`api.ts:545`) and stop sending it from the form (`TournamentFace.tsx:765`), dropping `selectedFull` if nothing else uses it. Verify `tsc -b --noEmit` passes.
- [x] 5.2 Remove the now-unreachable `409 full_disciplines` catch block from the form's submit handler, keeping the `not_yet_open` branch beside it intact. Verify the registration flow still handles a rejected submission and that the vitest suite passes.
- [x] 5.3 Confirm the confirmation view states, per discipline, which placements were seated and which were queued with their positions (spec: registration). Verify against a mixed registration; add the strings only if something is missing — `form.full` already promises per-row placement and needs no change.

## 6. Verification

- [x] 6.1 Rewrite `test_wait_for_all_queues_everything_unbilled` (`tests/test_registrations.py:100`) as its mixed-case successor: the open discipline is seated, the full one is queued, the total covers the seated discipline and its extras, and a payment window opens. Verify the rewritten test fails against the pre-change router.
- [x] 6.2 Add the paid-registration-in-queue coverage: queue length, queue position against a later reserved fencer, promotion, and the surcharge it bills. Verify each fails against the pre-change queries.
- [x] 6.3 Add the lapse coverage: a mixed registration demoted rather than expired, keeping its position, and an unmixed one still expiring.
- [x] 6.4 Run the full backend suite, the frontend typecheck, lint and vitest. Confirm no caller passes `wait_for_all`, no queue query still filters on `Registration.state == RESERVED`, and no new hex value or animated property entered the frontend (design prohibitions, `tokens.css`).
