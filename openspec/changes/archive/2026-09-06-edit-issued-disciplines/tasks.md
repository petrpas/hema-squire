## 1. Backend: one amendment, two callers

- [x] 1.1 Factor the amendment itself out of `routers/registrations.amend_registration` into a function taking the registration, the selection, and what differs between the two callers: whether a full discipline seats or queues, and which notice to send. The HTTP concerns — the window, `get_my_registration`, the response model — stay in the endpoint
- [x] 1.2 The fencer's endpoint calls it and behaves identically. Its existing tests run unchanged and are the guard on the refactor: touching one of them means the refactor moved something it should not have
- [x] 1.3 Placement follows the registration's origin, read from `registration.clocks_dormant` — seated unconditionally for an issued registration (spec `imported-registrations`, Capacity does not apply to an issued registration), substitute-in-place for one made in the application (design Decision 2)
- [x] 1.4 Pricing goes through `pricing.registration_total`, which reads `registered_at`, so a correction never reprices to today's fees

## 2. Backend: the rule kind

- [x] 2.1 A new kind in `rules.py` whose handler amends the registration rather than writing `rows[target][field]` — the first of its sort, and the reason the spec says so out loud
- [x] 2.2 Validate the slugs against the tournament's offered individual disciplines when the rule is created, as `field_edit` already does for `disciplines`, so an unknown slug is refused at the console rather than met later as a row that will not bill
- [x] 2.3 Refuse a `disciplines` `field_edit` where a registration stands behind the row: that shape writes the projection and would produce the very mismatch the change exists to remove
- [x] 2.4 Withdrawal re-applies the remaining rules over the issued selection, on the same terms — not an inverse of the last operation (design Risks)
- [x] 2.5 The rule reaches the manual-edits log of the fencer list's phase and reads there as a decision about disciplines, not as a raw payload

## 3. Backend: who is told

- [x] 3.1 `send_surcharge_due` where the amendment leaves the fencer owing more than before, and nothing otherwise — including for a whole roster corrected at once
- [x] 3.2 A paid registration left having overpaid is marked `RefundState.PENDING`, as the fencer's own amendment marks it
- [x] 3.3 Dormancy does not suppress the notice: what is dormant is the passage of time, not a statement about money
- [x] 3.4 A `PaymentEvent` records the amendment with the totals either side of it, as `registration_amended` already does

## 4. Backend: the properties that matter

- [x] 4.1 **Early bird survives the correction.** A registration made before the early-bird deadline, corrected after it, is repriced at early-bird prices. The test a naive implementation fails: repricing at today's fees also "changes the total", and only this test tells them apart
- [x] 4.2 **An issued registration's correction is seated and billed.** Add a discipline that is genuinely at capacity to an issued registration; assert the placement is seated *and* that the registration's total went up by that discipline's fee. Asserting only the placement would pass against an implementation that seats without billing
- [x] 4.3 **An in-app registration's correction queues.** The same edit against a registration the fencer made themselves; assert a substitute placement, and that the registration's other placements are untouched
- [x] 4.4 **Withdrawal after two amendments.** Two corrections applied, the first withdrawn; assert the state the second alone produces. "Undo the last thing" passes a single-amendment test and fails this one
- [x] 4.5 A correction that lowers the price mails nobody; one that raises it mails once
- [x] 4.6 Forty rows corrected, none owing more: no mail at all
- [x] 4.7 Applied after the amendment deadline, and against a dormant registration; refused for an expired one
- [x] 4.8 A `disciplines` field edit against a row with a registration is refused

## 5. Frontend

- [x] 5.1 `editableHere` opens `disciplines` on the fencer list for every row; the `registration_id` condition goes
- [x] 5.2 `ruleKindFor` returns the new kind for `disciplines` where the row has a registration, and `field_edit` where it does not
- [x] 5.3 The cell keeps the parsing it has (`parseDisciplines`) and the validation it has; the slug check is the backend's
- [x] 5.4 The reported outcome states what changed about the money, since that is the half the organizer cannot see in the cell — and where a notice went out, that it did
- [x] 5.5 Czech and English strings for the edit, its refusals and its report
- [x] 5.6 Tests: the cell opens on an issued row; the edit sends the new rule kind; a refusal states itself

## 6. Verification

- [x] 6.1 `pytest` and `ruff check .` clean; the fencer's own amendment tests untouched
- [x] 6.2 `vitest`, `npm run lint` and `npm run build` clean
- [x] 6.3 Against a real roster: correct a discipline on an issued registration and confirm the fencer list, the outstanding column and the export all state the same thing afterwards
