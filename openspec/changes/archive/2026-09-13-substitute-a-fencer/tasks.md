## 1. The seat's contact address

- [x] 1.1 Add `contact_email: Mapped[str | None]` to `Registration` in `app/models.py`, with a docstring saying it is the seat's address and not credentials.
- [x] 1.2 Write the alembic migration adding the nullable column; no backfill.
- [x] 1.3 Add `emails.recipient(registration, fencer)` and route every send in `app/emails.py` that holds a registration through it.
- [x] 1.4 Test: a registration carrying a contact address is reminded at that address; one carrying none is reminded at its fencer's.

## 2. The substitution rule

- [x] 2.1 Add the `row_substitute` kind to `app/rules.py`: its constant, its handler in `HANDLERS`, and the projection write for a row with no registration.
- [x] 2.2 Validate the payload in `create_rule`: name non-blank, `hr_id` a whole number or null, `email` well-shaped or null, and the address required when the tournament is automatic.
- [x] 2.3 Resolve the substitute's `Fencer` record per design D4 (existing account / account-less with kept address / account-less with a fresh address), refusing `substitute_already_registered` where that fencer already holds a registration on this tournament.
- [x] 2.4 Reassign `registration.fencer_id` and set `contact_email` where a registration stands behind the row; leave id, VS, totals, clocks, entries, credits and waivers untouched.
- [x] 2.5 Refuse substitution on a deleted row, on a merge-absorbed row, and where the substitute is the fencer already on the row.
- [x] 2.6 Store the `previous` identity block in the payload and implement withdrawal returning name, profile, nationality, club, account and contact address together.
- [x] 2.7 Test: the seat keeps its number, order, VS, total and credits; the queue placement is unchanged; the derived settled state is unchanged.
- [x] 2.8 Test: withdrawal restores the replaced fencer whole, including after a second substitution.
- [x] 2.9 Test: a substitution on a row without a registration writes the projection, and one with a registration is refused as a field edit would be.

## 3. The projection and the log

- [x] 3.1 Carry the substitution onto the row in `app/sheet.py`: the substitute's identity, `match_verdict` confirmed where a profile was chosen and unknown where none was, ratings read from the snapshot by the new `hr_id`.
- [x] 3.2 Render the substitution as one sentence in the manual-edits log (`app/rules.py` audit text and its locale strings), naming the row, the replaced fencer and the substitute.
- [x] 3.3 Mark a substituted row in the fencer table using the existing marker idiom, naming the replaced fencer.
- [x] 3.4 Test: the log line reads as a sentence in both locales; the row's marker names the replaced fencer and does not strike the row through.

## 4. Mail

- [x] 4.1 Add `email.substituteArrived` and `email.substituteDeparted` to `app/locales/cs.json` and `en.json`, with subjects and bodies; keep the locale parity test green.
- [x] 4.2 Add `send_substitute_arrived` and `send_substitute_departed` to `app/emails.py`; the arrival message states the outstanding amount, account, VS and QR codes via `payment_qrs`, or says nothing is owed.
- [x] 4.3 Send both from the rules endpoint after commit — never from replay — gated on published, automatic and an address being known; send one message where the two addresses coincide.
- [x] 4.4 Test: two messages on a new address; one on a kept address; none on a manual tournament; none on a draft; the arrival message carries the outstanding figure, not the total.

## 5. API

- [x] 5.1 Accept the kind in `app/routers/rules_api.py` with its request schema, and return the refusals of 2.3 and 2.5 with their stated reasons.
- [x] 5.2 Test: the endpoint refuses a blank name, a malformed address, a missing address on an automatic tournament, and an already-entered substitute, each with its own reason.

## 6. The dialog

- [x] 6.1 Add the API call to `frontend/src/api.ts`.
- [x] 6.2 Build `frontend/src/substitute/SubstituteDialog.tsx` on `Modal`, titled *Výběr náhradníka*, thin and delegating to its sections.
- [x] 6.3 Build `SubstituteIdentitySection.tsx` around `HRSearchPicker`, allowing confirmation of a typed name with no profile.
- [x] 6.4 Build `SubstituteContactSection.tsx`: the address field, the choice to keep the seat's current address where it has one, and the standing notice that the substitution is mailed there — shown on automatic tournaments only.
- [x] 6.5 Show the endpoint's refusals against the fields they name, keeping everything typed.
- [x] 6.6 Test: required address in automatic mode, optional in manual; nothing to keep on an address-less row; refusals land on their fields.

## 7. The row action

- [x] 7.1 Add the substitution action to the actions column in `frontend/src/SheetArea.tsx` with `IconUserShare`, a title and a visually-hidden label, beside the existing removal action.
- [x] 7.2 Offer it on the fencer list alone — not on Import, not on the phases after — and not on a deleted or absorbed row; wire it in `Console.tsx` beside `onDelete`.
- [x] 7.3 Test: both actions on a live Fencers row; removal alone on Import; neither on Payments; none on a deleted row.

## 8. Finishing

- [x] 8.1 `frontend/`: `npm run typecheck` and `npm run check` clean; add the new strings to both `src/i18n/*.json` with parity.
- [x] 8.2 `backend/`: `uv run ruff check .` and `uv run basedpyright` clean.
- [x] 8.3 Run the touched test scopes and state the result.
