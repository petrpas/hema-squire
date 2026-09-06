No schema change, no migration, no backfill: this is a rule about when a value
may be written, not about the value. Every existing tournament is already valid.

## 1. Backend: the refusal

- [x] 1.1 Refuse `PATCH /registrations-kept-by` where `published_at` is set, with a stated reason in the manner of the router's other refusals, so a client can say what happened rather than reporting a failure
- [x] 1.2 Let it through on a draft, in either direction, unchanged
- [x] 1.3 Accept a request that names the mode the tournament already has, rather than refusing it: a client resending what is already true is asking for nothing, and refusing it would make an idempotent write an error
- [x] 1.4 Confirm no other path writes the value. `registrations_kept_by` is written in exactly one handler today; a second writer would make the rule a guard rather than a guarantee
- [x] 1.5 Tests: a draft switches both ways; a published tournament is refused with the stated reason and its value is unchanged; the payments setting and the four flags still change on a published tournament; a no-op request on a published tournament is accepted

## 2. Frontend: state it rather than offer it

- [x] 2.1 The mode tier in `TournamentSettingsDialog.tsx` renders as a statement on a published tournament and as a radio group on a draft. Not hidden — "which mode is this?" is a question the surface should answer
- [x] 2.2 Say that it is settled, and when it was settled by, so the reading is "manual, and fixed at publication" rather than an inexplicably dead control
- [x] 2.3 Drop the confirmation branch for a mode change along with the requirement it served. `modeChanged` and the `alreadyHeld` count go with it; the feature-hiding warnings stay exactly as they are
- [x] 2.4 `SettingsSection` on `OTHER` already states the mode in words. Confirm it needs no change, and that the control it offers still opens a surface that has something to change
- [x] 2.5 Tests: the tier is a radio group on a draft and a statement on a published tournament; no confirmation is asked for a mode change anywhere; the feature warnings are unaffected

## 3. Localization

- [x] 3.1 English and Czech for the statement, for what it says about being settled, and for the refusal. Delete the mode confirmation's strings — `confirmToManual`, `confirmToAutomatic`, `alreadyHeld` — which nothing will render
- [x] 3.2 `locale-parity.test.ts` covers the drift; `identityLabels.test.ts` is the reminder that parity alone does not prove a key a component asks for exists

## 4. Verification

- [x] 4.1 `pytest` and `ruff check .` clean
- [x] 4.2 `vitest`, `npm run lint`, `npm run build` clean
- [x] 4.3 **Check what relied on the switch being available after publication.** Five in `test_registrations_kept_by.py`. Four were about a manual tournament rather than about the switch: the mode moves above `publish`, with the external registration address the completeness rule then wants. The fifth, `test_manual_settlement_demotes_nobody`, needed rethinking — its strength was a registration RESERVED and *not* dormant, which the API can no longer produce on an organizer-kept tournament, so it is written into the session directly and the test still isolates the organizer-kept cause in `clocks_run` rather than resting on a dormancy the row would have anyway
- [x] 4.4 Confirmed, and one of the three is closed only in part. A published tournament cannot lose its external registration address, and no confirmation counts a number that can only be zero — both asserted. The symbol-less registrations are closed for every published tournament and **not** on a draft: issuing has no publication gate, so a draft may import a roster, issue registrations with `vs = None` (`issuing.py:257`), switch to automatic while still a draft, and publish carrying them. The design's Non-Goals assume "on a draft the switch is free and nothing has happened yet"; issuing is what has happened. Not closed here — the owner's rule is that an unpublished tournament has no business holding participants at all and every data operation should be inactive on a draft, which closes this by removing the source rather than by guarding the switch. Its own change; verified reachable and then reverted, not left as a probe
