Depends on `add-registrations-kept-by`, which introduces the value everything
here branches on.

## 1. Backend: the address

- [x] 1.1 Add the nullable URL column to `Tournament` in `models.py` and an Alembic migration; no backfill, since every existing tournament is Squire-kept and needs none
- [x] 1.2 Validate it as an absolute `http`/`https` address using the patterns already in `fieldtypes.py` / `constraints.py`; do not fetch it, do not check that it resolves, do not warn (design D1)
- [x] 1.3 Carry it on the tournament schemas and the `PATCH` handler, and on the public tournament read the fencer-facing surfaces use
- [x] 1.4 Tests: it round-trips; a non-absolute or non-http value is rejected with a field error and nothing is stored; a URL pointing at nothing is accepted

## 2. Backend: completeness branches

- [x] 2.1 Branch `setup.setup_missing` on who keeps the registrations (design D3): require the address; do not require the bank account; do not treat the registration window as mandatory. Add the missing-item constant beside the existing ones
- [x] 2.2 Leave every other item alone — location, organizers, disciplines, prices, roster bounds, EUR fields. An organizer-kept tournament is no less a tournament
- [x] 2.3 Confirm `guard_published_completeness` inherits the branch, so a published organizer-kept tournament cannot be saved into having no address
- [x] 2.4 Tests: the address blocks publication when absent and clears it when supplied; a priced organizer-kept tournament with no bank account publishes; neither registration date is reported missing; a Squire-kept tournament's completeness is byte-for-byte what it was

## 3. Backend: the participant list

- [x] 3.1 **Found first: nothing renders this list.** A grep across `frontend/src` finds the participant list only in a Setup hint about the unpaid-list setting — the endpoint exists and is specced, and no page draws it. So the "publicly visible change" flagged in the design and in task 8.3 is not visible to anyone today; the fix is real, its exposure was overstated, and 6.4 has nothing to attach to. The response became an envelope (`ParticipantListOut`) rather than a bare array, since a bare array cannot state how current it is; six test files read `.json()["participants"]` now. Reworked `participants` (`routers/registrations.py:251`) around whether Squire guarantees a payment state — payments on **and** Squire-kept — rather than around `state == PAID` alone (design D2). Where it does not, list every seated entrant with no confirmed/unconfirmed distinction and ignore the unpaid-list setting
- [x] 3.2 Add the as-of moment for a roster Squire does not maintain: the moment the roster last reached Squire, derived from the tournament's import history. State the moment; state nothing about whether it is current
- [x] 3.3 A list Squire maintains itself carries no as-of moment
- [x] 3.4 Covered in `tests/test_participants.py`. Two existing tests there had to gain `enable_payments`: they built an easy-mode tournament and asserted confirmed/unconfirmed, which is exactly the behaviour being fixed — the unpaid-list setting they are about only means anything where Squire collects
- [x] 3.5 Test that the as-of moment moves when a fresh roster is imported, and is absent on a Squire-kept tournament

## 4. Backend: the deposit mode requires a feed

- [x] 4.1 Refuse the deposit payment mode where no Fio token is configured, beside the existing payment-parameter validation (design D5). Refuse the setting, do not rewrite it
- [x] 4.2 Report an existing deposit-mode tournament with no token as incomplete, naming the token. Do not switch its mode and do not un-publish it — completeness attaching later never un-publishes, as `tournament-admin` already fixes
- [x] 4.3 No backend change needed: `fio_token_configured` is already on the tournament detail (added by `add-payments-intake` for the same reason — the intake card omits *poll Fio now* and says why). Setup reads the same field
- [x] 4.4 Tests: the mode is refused without a token and accepted with one; an existing deposit tournament without a token is reported and keeps its mode and its publication; the other two modes are unaffected in both cases
- [x] 4.5 **No live tournament is affected.** Read-only survey of `backend/hema_squire.sqlite`: `na-duel-2026` is in `reservation` mode and `ttt-2027` in `immediate`; neither is in deposit mode, so the constraint reports nothing on deploy

## 5. Frontend: Setup

- [x] 5.1 Offer the address field in Setup, marked mandatory on an organizer-kept tournament. Where it sits — with the identity fields or on the timeline — is decided against the screen (design, Open Questions)
- [x] 5.2 Stop offering the reminder day on an organizer-kept tournament, following `setup-navigation`'s existing treatment for a section a mode does not offer: hidden, values retained, restored on switching back
- [x] 5.3 Keep the timeline dates offered and editable, with copy saying they state when the organizer's own registration runs rather than gating anything
- [x] 5.4 `modesAvailable(fioConfigured)` in `PaymentModeSection.tsx` drops the deposit radio, with a line stating that a feed is what restores it — following `IntakePanel`'s treatment of the same missing token

## 6. Frontend: the fencer-facing surfaces

- [x] 6.1 **Deviates from the delta spec I wrote, and the spec is what should move.** `FencerHome`'s card has no Register action to replace: the whole card is a single `<Link>` to the detail page, so an outward `<a>` inside it would be a nested anchor. The card carries the statement — an `elsewhere` badge saying registration is held elsewhere — and the destination lives one click away on the detail page the card opens, which is where the registration form would have been. Soften the `fencer-home` delta's "in that place" wording before archiving
- [x] 6.2 `TournamentDetail.tsx`: the second tab offers the way out instead of the form. `canRegister` today combines availability with free places — the new case is decided before both, since it is not about capacity
- [x] 6.3 Copy states that registration is held elsewhere and never that it is closed, in every surface (design D4)
- [x] 6.4 **Nothing to do:** no page renders the participant list (see 3.1). When one is built, it reads `payment_state_known` and `as_of` from the envelope
- [x] 6.5 Present the outward link as a destination that is visibly not part of this site, within the design system — the prohibition on default blue anchors applies (`CLAUDE.md`)
- [x] 6.6 Tests (`vitest`): the card and the detail page offer the link and no Register action; the address-less case renders without an action; the list renders plainly with its as-of line; no surface says "closed"
- [x] 6.7 Confirmed and covered by a test rather than code, as expected: an organizer-kept tournament appears in Mine for its organizer and is absent for a stranger

## 7. Localization

- [x] 7.1 English strings: the address field and its hint, the way-out action, the held-elsewhere line, the as-of line, the deposit-mode explanation, the new missing-item names
- [x] 7.2 Czech equivalents in the same pass; `locale-parity.test.ts` covers the drift

## 8. Verification

- [x] 8.1 `pytest` 1002 passed, `ruff check .` clean
- [x] 8.2 `vitest` 323 passed, `npm run lint` and `npm run build` clean
- [x] 8.3 **Withdrawn: there is no public page to look at.** No frontend surface renders the participant list (see 3.1), so the change is visible only to an API consumer. Nothing for the owner to eyeball before deploy on this account
- [x] 8.4 Covered across `test_external_registration.py` (the address is required to publish, cleared by supplying it), `test_registrations_kept_by.py` (the fencer-facing list says `elsewhere`, the lifecycle does nothing), `test_participants.py` (the roster with its as-of moment) and `externalRegistration.test.tsx` (the way out, and never "closed"). Not run against a live server — no deploy was made, per the session's standing constraint
