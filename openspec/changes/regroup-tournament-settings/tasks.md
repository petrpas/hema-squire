Depends on `unify-lifecycle-dormancy`, `add-registrations-kept-by` and
`add-external-registration`, all implemented and none archived. This change
renames requirements two of them introduce, so the four archive together with
this one last (section 6).

Nothing here changes behaviour. The two test suites are the instrument: they
should pass after renaming identifiers and copy, and a test whose *assertions*
need rethinking rather than its names is a behaviour change to explain before
it is accepted.

## 1. Backend: the rename

- [ ] 1.1 `TournamentModeIn` → `TournamentFeaturesIn` and `TournamentModeOut` → `TournamentFeaturesOut` in `backend/app/schemas.py`, with docstrings that no longer describe a mode chosen as a whole — three independent features are exactly what they are
- [ ] 1.2 `GET`/`PATCH /api/tournaments/{slug}/mode` → `/features` in `routers/tournaments.py`, and the handlers renamed with them. Rename rather than alias: no client outside this repository is known and the frontend ships with the backend (design D7)
- [ ] 1.3 No model change, no migration, no column touched. Confirm at the end that `alembic heads` is where this change found it — if a migration appeared, something was done that the design did not decide
- [ ] 1.4 `conftest.feature_payload` and `set_features` follow the endpoint. `enable_payments` keeps its name: it is the clearest thing in the fixture and payments is now stated as its own axis anyway
- [ ] 1.5 Sweep for the word *mode* in backend comments and docstrings where it means the four flags, and leave it where it means `PaymentMode`, which is a different and legitimate use

## 2. Backend: payments moves house in the specs, not in the code

- [ ] 2.1 No code moves. `feature_payments` stays a column beside the other three and is written by the same endpoint (design D2) — what moved is where the behaviour is specified and where it is stated on screen
- [ ] 2.2 Check the docstrings that cite `tournament-modes D5` for the payments suspension and point them at `payments` instead. There are several, in `scheduler.py`, `emails.py`, `bank.py`, `setup.py` and `routers/registrations.py`
- [ ] 2.3 `models.Tournament`'s comment above the four flags says "the four advanced features this tournament uses" and that only `feature_payments` changes what the system does. Rewrite it to say three features and one behavioural setting stored alongside them, and to name the mode as the third axis

## 3. Frontend: one settings surface

- [ ] 3.1 `TournamentModeDialog.tsx` → `TournamentSettingsDialog.tsx`, exporting `TournamentSettingsFields` in place of `TournamentModeFields`. The split it already makes — fields without a shell, plus a shell — is what lets one component serve both creation and `OTHER`, and it stays
- [ ] 3.2 Fold `RegistrationsKeptBy.tsx` into it as the surface's first tier, keeping its confirmation behaviour intact: both directions confirmed, the in-app registration count stated, nothing written until accepted
- [ ] 3.3 Lay out the three tiers per the spec — mode, payments, inclusions — with the first two visibly decisions about what Squire does and the third a plain checklist. Two writes behind one confirm: the mode goes to `registrations-kept-by`, the features to `/features`. Apply the mode first, so a failure on the second leaves the more consequential choice recorded rather than the less
- [ ] 3.4 Delete `EASY_MODE`, `isEasyMode` and the "advanced with nothing chosen" handling. Nothing may derive a label from the flags again (design D1) — if a caller wants one, that is the defect returning
- [ ] 3.5 `MODE_FEATURES` → `TOURNAMENT_FEATURES`, dropping `feature_payments` from the array; give payments its own constant or read it directly, whichever leaves fewer places that must remember it is not in the list
- [ ] 3.6 `TournamentMode` interface → `TournamentFeatures`, now three booleans
- [ ] 3.7 `setup/ModeSection.tsx` and `setup/RegistrationsKeptBySection.tsx` → one `setup/SettingsSection.tsx` stating all three tiers with one control; mount it once in `SetupPanel.tsx` where the two were
- [ ] 3.8 `TournamentPicker.tsx`: the two-step creation flow collapses to one panel. The `modeDone` state added by `add-registrations-kept-by` goes with it
- [ ] 3.9 `setup/PublishSection.tsx` imports `FEATURE_NAMES` to name the feature that restores a hidden item's editor — follow the rename and confirm the message still reads correctly for an extra item hidden by a feature

## 4. Localization

- [ ] 4.1 Rewrite `setup.mode.*` as `setup.settings.*` in `en.json`: the surface title, the two modes and their consequence hints, the payments line and its hint, the three inclusions and their existing hints, the warnings. Delete `easy`, `easyHint`, `advanced`, `advancedHint`, `nothingChosen` and `paymentsConsequence` — the last belongs to the payments row now, not to a warning about a mode
- [ ] 4.2 Fold `setup.keptBy.*` into the same block rather than leaving a second namespace for the first tier
- [ ] 4.3 Czech in the same pass; `locale-parity.test.ts` covers the drift. **Owner review wanted**: *režim: automatický / manuální* is settled, but what the hint under each says is written against the screen, and the consequence — that in manual mode Squire writes to nobody — has to be in the hint rather than inferred from the adjective (design, Open Questions)
- [ ] 4.4 Grep both catalogues for the words for easy and advanced mode outside this block; `home.*` and `detail.*` may carry them

## 5. Tests

- [ ] 5.1 `backend/tests/test_tournament_modes.py` → `test_tournament_features.py`, endpoint and payload names updated. Its assertions about easy/advanced mode go with the concept; assertions about what each feature hides stay untouched
- [ ] 5.2 `test_tournament_modes_migration.py` keeps its name and its assertions — it exercises a historical revision, and history is not renamed
- [ ] 5.3 `registrationsKeptBy.test.tsx` and its neighbours follow the components. The test asserting the mode dialog offers four features and nothing about ownership becomes its opposite: the settings surface offers all three tiers, and nothing else does
- [ ] 5.4 Add the test the removal is for: nothing derives a name from how many features are enabled. A grep-shaped assertion is legitimate here — no source file may contain `isEasyMode`
- [ ] 5.5 Cover the two-write confirm: a failure writing the features leaves the mode applied and says so, rather than reporting success or silently reverting

## 6. Reconciling the four changes

- [ ] 6.1 Archive in order: `unify-lifecycle-dormancy`, `add-registrations-kept-by`, `add-external-registration`, then this one. `registration-ownership` and `tournament-modes` must exist to be renamed; archiving this first would remove requirements that had not been created
- [ ] 6.2 After archiving, confirm `openspec/specs/` holds `tournament-mode`, `tournament-features` and neither `tournament-modes` nor `registration-ownership`, and that `payments` carries the suspension requirement
- [ ] 6.3 Soften `add-external-registration`'s `fencer-home` delta before it archives: it says the card offers the way out "in that place", and the implementation puts the statement on the card and the destination one click away on the detail page, because the card is a single link and cannot nest another (recorded in that change's task 6.1)
- [ ] 6.4 Grep the whole of `openspec/specs/` for `tournament-modes`, `easy mode` and `advanced mode` afterwards; six files referred to it and each needs its reference pointed at whichever of the two successors it meant

## 7. Verification

- [ ] 7.1 `pytest` and `ruff check .` clean in `backend/`, at the same count this change started from plus whatever section 5 adds
- [ ] 7.2 `vitest`, `npm run lint`, `npm run build` clean in `frontend/`
- [ ] 7.3 State plainly which tests needed more than a rename, and why each one did. The expected answer is none beyond the easy/advanced assertions in 5.1 and 5.3
- [ ] 7.4 Read the settings surface on screen before calling it done. Three tiers on one panel is a layout claim, and the design's own open question — whether the mode reads as the consequential choice — is answerable only by looking at it
