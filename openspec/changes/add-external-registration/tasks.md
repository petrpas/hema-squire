Depends on `add-registrations-kept-by`, which introduces the value everything
here branches on.

## 1. Backend: the address

- [ ] 1.1 Add the nullable URL column to `Tournament` in `models.py` and an Alembic migration; no backfill, since every existing tournament is Squire-kept and needs none
- [ ] 1.2 Validate it as an absolute `http`/`https` address using the patterns already in `fieldtypes.py` / `constraints.py`; do not fetch it, do not check that it resolves, do not warn (design D1)
- [ ] 1.3 Carry it on the tournament schemas and the `PATCH` handler, and on the public tournament read the fencer-facing surfaces use
- [ ] 1.4 Tests: it round-trips; a non-absolute or non-http value is rejected with a field error and nothing is stored; a URL pointing at nothing is accepted

## 2. Backend: completeness branches

- [ ] 2.1 Branch `setup.setup_missing` on who keeps the registrations (design D3): require the address; do not require the bank account; do not treat the registration window as mandatory. Add the missing-item constant beside the existing ones
- [ ] 2.2 Leave every other item alone — location, organizers, disciplines, prices, roster bounds, EUR fields. An organizer-kept tournament is no less a tournament
- [ ] 2.3 Confirm `guard_published_completeness` inherits the branch, so a published organizer-kept tournament cannot be saved into having no address
- [ ] 2.4 Tests: the address blocks publication when absent and clears it when supplied; a priced organizer-kept tournament with no bank account publishes; neither registration date is reported missing; a Squire-kept tournament's completeness is byte-for-byte what it was

## 3. Backend: the participant list

- [ ] 3.1 Rework `participants` (`routers/registrations.py:251`) around whether Squire guarantees a payment state — payments on **and** Squire-kept — rather than around `state == PAID` alone (design D2). Where it does not, list every seated entrant with no confirmed/unconfirmed distinction and ignore the unpaid-list setting
- [ ] 3.2 Add the as-of moment for a roster Squire does not maintain: the moment the roster last reached Squire, derived from the tournament's import history. State the moment; state nothing about whether it is current
- [ ] 3.3 A list Squire maintains itself carries no as-of moment
- [ ] 3.4 Tests as a table over the four combinations of payments feature × who keeps the registrations, asserting what each list contains and what each says about payment. The payments-off row is a **fix to live behaviour**, not new ground — assert the entrants appear, which they do not today
- [ ] 3.5 Test that the as-of moment moves when a fresh roster is imported, and is absent on a Squire-kept tournament

## 4. Backend: the deposit mode requires a feed

- [ ] 4.1 Refuse the deposit payment mode where no Fio token is configured, beside the existing payment-parameter validation (design D5). Refuse the setting, do not rewrite it
- [ ] 4.2 Report an existing deposit-mode tournament with no token as incomplete, naming the token. Do not switch its mode and do not un-publish it — completeness attaching later never un-publishes, as `tournament-admin` already fixes
- [ ] 4.3 Have the tournament read state whether the deposit mode is available, so Setup can omit it *and say why* rather than omitting it silently
- [ ] 4.4 Tests: the mode is refused without a token and accepted with one; an existing deposit tournament without a token is reported and keeps its mode and its publication; the other two modes are unaffected in both cases
- [ ] 4.5 Identify any live tournament in this state before deploy and report it to the owner (design, Migration Plan)

## 5. Frontend: Setup

- [ ] 5.1 Offer the address field in Setup, marked mandatory on an organizer-kept tournament. Where it sits — with the identity fields or on the timeline — is decided against the screen (design, Open Questions)
- [ ] 5.2 Stop offering the reminder day on an organizer-kept tournament, following `setup-navigation`'s existing treatment for a section a mode does not offer: hidden, values retained, restored on switching back
- [ ] 5.3 Keep the timeline dates offered and editable, with copy saying they state when the organizer's own registration runs rather than gating anything
- [ ] 5.4 Omit the deposit mode where no token is configured and state that a payment feed is what makes it available — the treatment `IntakePanel` already uses for its missing-token case, so follow it rather than inventing a second

## 6. Frontend: the fencer-facing surfaces

- [ ] 6.1 `FencerHome.tsx`: an organizer-kept tournament's card offers the way out in the Register action's place, never beside it; with no address, state that registration is held elsewhere and offer nothing
- [ ] 6.2 `TournamentDetail.tsx`: the second tab offers the way out instead of the form. `canRegister` today combines availability with free places — the new case is decided before both, since it is not about capacity
- [ ] 6.3 Copy states that registration is held elsewhere and never that it is closed, in every surface (design D4)
- [ ] 6.4 The participant list renders the plain entrant list and the as-of line where one is given
- [ ] 6.5 Present the outward link as a destination that is visibly not part of this site, within the design system — the prohibition on default blue anchors applies (`CLAUDE.md`)
- [ ] 6.6 Tests (`vitest`): the card and the detail page offer the link and no Register action; the address-less case renders without an action; the list renders plainly with its as-of line; no surface says "closed"
- [ ] 6.7 Confirm the Mine tab needs no change — it lists tournaments the account is bound to by registration **or by organizing**, so an organizer-kept tournament already appears for its organizer and is absent for a fencer who never registered. Add a test rather than code

## 7. Localization

- [ ] 7.1 English strings: the address field and its hint, the way-out action, the held-elsewhere line, the as-of line, the deposit-mode explanation, the new missing-item names
- [ ] 7.2 Czech equivalents in the same pass; `locale-parity.test.ts` covers the drift

## 8. Verification

- [ ] 8.1 `pytest` and `ruff check .` clean in `backend/`
- [ ] 8.2 `vitest`, `npm run lint`, `npm run build` clean in `frontend/`
- [ ] 8.3 **Look at the pilot's public page before deploy.** The participant-list change is publicly visible on tournaments that exist today — a payments-off list goes from empty-or-all-grey to a plain list of entrants — and the owner should see it rather than hear about it
- [ ] 8.4 End to end on an organizer-kept tournament: publish it, confirm the address was required, confirm a fencer is sent outward from card and detail alike, confirm the participant list shows the imported roster with its as-of moment, and confirm the lifecycle still does nothing
