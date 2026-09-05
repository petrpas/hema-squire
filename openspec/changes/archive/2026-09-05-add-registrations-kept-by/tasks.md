Depends on `unify-lifecycle-dormancy`. Section 3 has nowhere to land until that
change has made one place for a dormancy cause to go.

## 1. Backend: the value

- [x] 1.1 Add `RegistrationsKeptBy` enum (`SQUIRE`, `ORGANIZER`) and the `registrations_kept_by` column to `Tournament` in `backend/app/models.py`, via `str_enum` as every other enum column here does, defaulting to `SQUIRE`. Document on it that it is a different axis from the four `feature_*` flags and why it is not one of them (design D1)
- [x] 1.2 Alembic migration adding the column with the default and backfilling every existing row to `SQUIRE` — unconditionally, with nothing derived from the tournament's contents (design D7)
- [x] 1.3 Carry it on the tournament schemas in `schemas.py` — the detail read and the update payload — and accept it in the `PATCH` handler in `routers/tournaments.py` beside where `feature_payments` is written
- [x] 1.4 Not added to `export_json.py`, as decided. `scripts/reset_local_db.py` needed no change either: it dumps `[c.name for c in model.__table__.columns]`, so it carries the new column by construction — the four features are in it for the same reason
- [x] 1.5 Tests: the field round-trips through the API; an existing tournament reads as Squire-kept after migration; a reset dump preserves it

## 2. Backend: the tournament-level exclusion

- [x] 2.1 Extracted the select into `scheduler.tournaments_to_tick(session)` and added the term there. A named function rather than an inline select because `run_tick` was untestable — it opens its own `SessionLocal` — so the exclusion could only have been asserted through the passes it is meant to make unreachable. Added the term to `scheduler.run_tick`'s select over tournaments, so an organizer-kept tournament is never handed to `run_tournament_tick` (design D2). One place, with a comment saying this is the structural guarantee and that per-pass conditions are what it replaces
- [x] 2.2 Leave `run_tournament_tick` itself able to run against such a tournament — the organizer's manual `process` endpoint reaches it directly — and confirm what it does there is nothing, by way of the predicate in section 3 rather than a second check here
- [x] 2.3 Tests: an organizer-kept tournament with registrations aged past every window and its seating deadline, run through `run_tick`, sends nothing, expires nothing, demotes nothing and polls no bank feed. Assert against the collecting mailer and the placements, not against a return count
- [x] 2.4 Test the property the exclusion exists for: a registration created on an organizer-kept tournament **without** the per-row dormancy mark is still untouched by a full lifecycle run

## 3. Backend: the third dormancy cause

- [x] 3.1 Add the organizer-kept cause to `dormancy_cause` in `scheduler.py` — one member of the closed set, one branch, as `unify-lifecycle-dormancy` designed for (design D3)
- [x] 3.2 Confirm no lifecycle pass gains a condition of its own. If one does, the predicate is in the wrong place
- [x] 3.3 Tests for the paths the scheduler's selection does not cover: the organizer's hand-triggered settlement on an organizer-kept tournament demotes nobody and stamps the tournament settled; the console's pending-demotion count reads zero
- [x] 3.4 `test_issuing.py` passes unchanged — the per-row mark keeps its meaning and its behaviour (design D2)

## 4. Backend: registration availability

- [x] 4.1 Add the reason constant beside `NOT_PUBLISHED` / `NOT_YET_OPEN` / `CLOSED` in `setup.py`, and the branch at the **top** of `registration_availability`, before the cancelled check — it is not that the window is shut but that there is no window here (design D4)
- [x] 4.2 Confirm `amendment_availability` inherits it, since it calls through; add the test rather than the code if it already does
- [x] 4.3 Confirm both callers present the new reason rather than falling through to a generic failure: the register endpoint (`routers/registrations.py:433`) and the tournament read (`routers/tournaments.py:216`)
- [x] 4.4 Tests: registration refused with the new reason on a published, in-window, organizer-kept tournament; refused with the new reason even when the tournament is also unpublished and past its close, proving the gate order; amendment refused alike

## 5. Frontend: the section

- [x] 5.1 New component for the choice, following the split `TournamentModeDialog.tsx` already makes — `TournamentModeFields` is exported so `TournamentPicker` can embed it at creation while `setup/ModeSection.tsx` reopens it on `OTHER`. The new section mirrors that shape and does **not** join those fields (design D5)
- [x] 5.2 Embed it in the creation flow beside the mode fields, with Squire-kept preselected
- [x] 5.3 Add it to Setup's `OTHER` tab beside `ModeSection`, stating the current answer in words and applying immediately without a save control, as the mode section does — `OTHER` carries no save bar
- [x] 5.4 Help text stating the consequence, not the label: that fencers cannot register in the application and Squire sends them nothing
- [x] 5.5 Static confirmation in both directions. The count needed a number the API did not expose: added `in_app_registrations` to the tournament detail, counting live registrations with no `source_row_id` — issued rows are excluded, since they stand in for a roster the organizer already keeps and are not what Squire would stop managing
- [x] 5.6 `api.ts` for the field on the tournament detail and the update
- [x] 5.7 **Found during implementation, and not optional.** The fencer-facing list derives `registration_status` from the same gate, and the new reason fell through its `else` into `"open"` — so the card would have announced an open registration and offered a button answering 400. Added `elsewhere` as a fourth status, kept distinct from `closed` for the reason in D4, threaded through `schemas.RegistrationStatus`, `api.ts`, `openingMoment.registrationStatus` (the client-side mirror, which `canRegister` and `amendmentOpen` both read, so both close correctly) and a card badge. Copy states where registration is, never that it is closed. The link out is what `add-external-registration` attaches to this status
- [x] 5.8 Tests (`vitest`): the section renders the current value and changes it; the confirmation states the count and cancelling writes nothing; the mode dialog still offers four features and nothing about ownership

## 6. Localization

- [x] 6.1 English strings for the section, its help text, both confirmations and the new refusal reason
- [x] 6.2 Czech in the same pass, `locale-parity.test.ts` green. **Owner review wanted on the copy** — used *Registrace vede Squire* / *Registrace vede pořadatel* (pořadatel rather than organizátor, matching the rest of the Czech catalogue), with the consequence carried in the hint rather than the label. Decided against the screen, as the design said, but by me rather than by the owner

## 7. Verification

- [x] 7.1 `pytest` 979 passed, `ruff check .` clean
- [x] 7.2 `vitest` 317 passed, `npm run lint` and `npm run build` clean
- [x] 7.3 The test that matters most: an organizer-kept tournament carrying a bank account, an immediate payment mode, a five-day window, a past seating deadline and registrations aged four hundred days, run through the full lifecycle — nothing sent, nothing expired, nothing demoted, every setting still stored
- [x] 7.4 The console is untouched — no import, matching, deduplication, sheet or export code was edited in this change, and their tests pass unchanged. The manual path was already built
