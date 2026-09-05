Depends on `unify-lifecycle-dormancy`. Section 3 has nowhere to land until that
change has made one place for a dormancy cause to go.

## 1. Backend: the value

- [ ] 1.1 Add `RegistrationsKeptBy` enum (`SQUIRE`, `ORGANIZER`) and the `registrations_kept_by` column to `Tournament` in `backend/app/models.py`, via `str_enum` as every other enum column here does, defaulting to `SQUIRE`. Document on it that it is a different axis from the four `feature_*` flags and why it is not one of them (design D1)
- [ ] 1.2 Alembic migration adding the column with the default and backfilling every existing row to `SQUIRE` — unconditionally, with nothing derived from the tournament's contents (design D7)
- [ ] 1.3 Carry it on the tournament schemas in `schemas.py` — the detail read and the update payload — and accept it in the `PATCH` handler in `routers/tournaments.py` beside where `feature_payments` is written
- [ ] 1.4 Do **not** add it to `export_json.py`. The canonical export is a portable document that deliberately drops the mode flags, the payment mode and the seating deadline (`scripts/reset_local_db.py` states this); the new value is omitted on the same grounds, and consistency with the four features is the point. Add it to `scripts/reset_local_db.py`'s column-level dump instead, where the four features already are, so a local reset does not silently reopen registration
- [ ] 1.5 Tests: the field round-trips through the API; an existing tournament reads as Squire-kept after migration; a reset dump preserves it

## 2. Backend: the tournament-level exclusion

- [ ] 2.1 Add the term to `scheduler.run_tick`'s select over tournaments, so an organizer-kept tournament is never handed to `run_tournament_tick` (design D2). One place, with a comment saying this is the structural guarantee and that per-pass conditions are what it replaces
- [ ] 2.2 Leave `run_tournament_tick` itself able to run against such a tournament — the organizer's manual `process` endpoint reaches it directly — and confirm what it does there is nothing, by way of the predicate in section 3 rather than a second check here
- [ ] 2.3 Tests: an organizer-kept tournament with registrations aged past every window and its seating deadline, run through `run_tick`, sends nothing, expires nothing, demotes nothing and polls no bank feed. Assert against the collecting mailer and the placements, not against a return count
- [ ] 2.4 Test the property the exclusion exists for: a registration created on an organizer-kept tournament **without** the per-row dormancy mark is still untouched by a full lifecycle run

## 3. Backend: the third dormancy cause

- [ ] 3.1 Add the organizer-kept cause to `dormancy_cause` in `scheduler.py` — one member of the closed set, one branch, as `unify-lifecycle-dormancy` designed for (design D3)
- [ ] 3.2 Confirm no lifecycle pass gains a condition of its own. If one does, the predicate is in the wrong place
- [ ] 3.3 Tests for the paths the scheduler's selection does not cover: the organizer's hand-triggered settlement on an organizer-kept tournament demotes nobody and stamps the tournament settled; the console's pending-demotion count reads zero
- [ ] 3.4 `test_issuing.py` passes unchanged — the per-row mark keeps its meaning and its behaviour (design D2)

## 4. Backend: registration availability

- [ ] 4.1 Add the reason constant beside `NOT_PUBLISHED` / `NOT_YET_OPEN` / `CLOSED` in `setup.py`, and the branch at the **top** of `registration_availability`, before the cancelled check — it is not that the window is shut but that there is no window here (design D4)
- [ ] 4.2 Confirm `amendment_availability` inherits it, since it calls through; add the test rather than the code if it already does
- [ ] 4.3 Confirm both callers present the new reason rather than falling through to a generic failure: the register endpoint (`routers/registrations.py:433`) and the tournament read (`routers/tournaments.py:216`)
- [ ] 4.4 Tests: registration refused with the new reason on a published, in-window, organizer-kept tournament; refused with the new reason even when the tournament is also unpublished and past its close, proving the gate order; amendment refused alike

## 5. Frontend: the section

- [ ] 5.1 New component for the choice, following the split `TournamentModeDialog.tsx` already makes — `TournamentModeFields` is exported so `TournamentPicker` can embed it at creation while `setup/ModeSection.tsx` reopens it on `OTHER`. The new section mirrors that shape and does **not** join those fields (design D5)
- [ ] 5.2 Embed it in the creation flow beside the mode fields, with Squire-kept preselected
- [ ] 5.3 Add it to Setup's `OTHER` tab beside `ModeSection`, stating the current answer in words and applying immediately without a save control, as the mode section does — `OTHER` carries no save bar
- [ ] 5.4 Help text stating the consequence, not the label: that fencers cannot register in the application and Squire sends them nothing
- [ ] 5.5 Static confirmation on change, in both directions, naming what starts or stops; where in-app registrations exist, state how many (design D6). No animation, per the design prohibitions
- [ ] 5.6 `api.ts` for the field on the tournament detail and the update
- [ ] 5.7 Where the fencer-facing surfaces meet the new refusal reason, render it without inventing copy about deadlines. Minimal treatment only — the external link and the reshaped public surfaces belong to the next change
- [ ] 5.8 Tests (`vitest`): the section renders the current value and changes it; the confirmation states the count and cancelling writes nothing; the mode dialog still offers four features and nothing about ownership

## 6. Localization

- [ ] 6.1 English strings for the section, its help text, both confirmations and the new refusal reason
- [ ] 6.2 Czech equivalents in the same pass; `locale-parity.test.ts` covers that neither drifts. The working phrasing is *registrace vede Squire* / *registrace vede organizátor*, to be decided against the screen (design, Open Questions)

## 7. Verification

- [ ] 7.1 `pytest` and `ruff check .` clean in `backend/`
- [ ] 7.2 `vitest`, `npm run lint`, `npm run build` clean in `frontend/`
- [ ] 7.3 The test that matters most: an organizer-kept tournament carrying a bank account, an immediate payment mode, a five-day window, a past seating deadline and registrations aged four hundred days, run through the full lifecycle — nothing sent, nothing expired, nothing demoted, every setting still stored
- [ ] 7.4 Confirm the console behaves identically on both kinds of tournament — import, matching, deduplication, the fencer table, export. Any difference is unintended: the manual path was already built and this change does not touch it
