No schema change, no migration, no backfill: this is a rule about when a value
may be written, not about the value. Every existing tournament is already valid.

## 1. Backend: the refusal

- [ ] 1.1 Refuse `PATCH /registrations-kept-by` where `published_at` is set, with a stated reason in the manner of the router's other refusals, so a client can say what happened rather than reporting a failure
- [ ] 1.2 Let it through on a draft, in either direction, unchanged
- [ ] 1.3 Accept a request that names the mode the tournament already has, rather than refusing it: a client resending what is already true is asking for nothing, and refusing it would make an idempotent write an error
- [ ] 1.4 Confirm no other path writes the value. `registrations_kept_by` is written in exactly one handler today; a second writer would make the rule a guard rather than a guarantee
- [ ] 1.5 Tests: a draft switches both ways; a published tournament is refused with the stated reason and its value is unchanged; the payments setting and the four flags still change on a published tournament; a no-op request on a published tournament is accepted

## 2. Frontend: state it rather than offer it

- [ ] 2.1 The mode tier in `TournamentSettingsDialog.tsx` renders as a statement on a published tournament and as a radio group on a draft. Not hidden — "which mode is this?" is a question the surface should answer
- [ ] 2.2 Say that it is settled, and when it was settled by, so the reading is "manual, and fixed at publication" rather than an inexplicably dead control
- [ ] 2.3 Drop the confirmation branch for a mode change along with the requirement it served. `modeChanged` and the `alreadyHeld` count go with it; the feature-hiding warnings stay exactly as they are
- [ ] 2.4 `SettingsSection` on `OTHER` already states the mode in words. Confirm it needs no change, and that the control it offers still opens a surface that has something to change
- [ ] 2.5 Tests: the tier is a radio group on a draft and a statement on a published tournament; no confirmation is asked for a mode change anywhere; the feature warnings are unaffected

## 3. Localization

- [ ] 3.1 English and Czech for the statement, for what it says about being settled, and for the refusal. Delete the mode confirmation's strings — `confirmToManual`, `confirmToAutomatic`, `alreadyHeld` — which nothing will render
- [ ] 3.2 `locale-parity.test.ts` covers the drift; `identityLabels.test.ts` is the reminder that parity alone does not prove a key a component asks for exists

## 4. Verification

- [ ] 4.1 `pytest` and `ruff check .` clean
- [ ] 4.2 `vitest`, `npm run lint`, `npm run build` clean
- [ ] 4.3 **Check what relied on the switch being available after publication.** `test_registrations_kept_by.py` switches a published tournament in several places; each is either a draft now or an assertion that it is refused. A test that needs rethinking rather than adjusting is a behaviour this change did not intend
- [ ] 4.4 Confirm the three problems this closes are actually closed: a published tournament cannot reach the state where its external registration address is missing; no registration without a variable symbol can arrive on an automatic tournament; and no confirmation counts a number that can only be zero
