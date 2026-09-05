Depends on `unify-lifecycle-dormancy`, `add-registrations-kept-by` and
`add-external-registration`, all implemented and none archived. This change
renames requirements two of them introduce, so the four archive together with
this one last (section 6).

Nothing here changes behaviour. The two test suites are the instrument: they
should pass after renaming identifiers and copy, and a test whose *assertions*
need rethinking rather than its names is a behaviour change to explain before
it is accepted.

## 1. Backend: the rename

- [x] 1.1 `TournamentModeIn` → `TournamentFeaturesIn` and `TournamentModeOut` → `TournamentFeaturesOut` in `backend/app/schemas.py`, with docstrings that no longer describe a mode chosen as a whole — three independent features are exactly what they are
- [x] 1.2 `GET`/`PATCH /api/tournaments/{slug}/mode` → `/features` in `routers/tournaments.py`, and the handlers renamed with them. Rename rather than alias: no client outside this repository is known and the frontend ships with the backend (design D7)
- [x] 1.3 No model change, no migration, no column touched. `alembic heads` is still `e7b25f4a9c31`, where this change found it
- [x] 1.4 `conftest.feature_payload` and `set_features` follow the endpoint. `enable_payments` keeps its name: it is the clearest thing in the fixture and payments is now stated as its own axis anyway
- [x] 1.5 Sweep for the word *mode* in backend comments and docstrings where it means the four flags, and leave it where it means `PaymentMode`, which is a different and legitimate use

## 2. Backend: payments moves house in the specs, not in the code

- [x] 2.1 No code moves. `feature_payments` stays a column beside the other three and is written by the same endpoint (design D2) — what moved is where the behaviour is specified and where it is stated on screen
- [x] 2.2 Check the docstrings that cite `tournament-modes D5` for the payments suspension and point them at `payments` instead. There are several, in `scheduler.py`, `emails.py`, `bank.py`, `setup.py` and `routers/registrations.py`
- [x] 2.3 `models.Tournament`'s comment above the four flags says "the four advanced features this tournament uses" and that only `feature_payments` changes what the system does. Rewrite it to say three features and one behavioural setting stored alongside them, and to name the mode as the third axis

## 3. Frontend: one settings surface

- [x] 3.1 `TournamentModeDialog.tsx` → `TournamentSettingsDialog.tsx`, exporting `TournamentSettingsFields` in place of `TournamentModeFields`. The split it already makes — fields without a shell, plus a shell — is what lets one component serve both creation and `OTHER`, and it stays
- [x] 3.2 Fold `RegistrationsKeptBy.tsx` into it as the surface's first tier, keeping its confirmation behaviour intact: both directions confirmed, the in-app registration count stated, nothing written until accepted
- [x] 3.3b **Payments is a radio, and its copy follows the mode** (owner, mid-implementation). Two named answers rather than a checkbox, each stated by what it gives: a checkbox made one answer the absence of the other, which is the shape this surface stopped using. It also fixed the rhythm — both behavioural tiers now indent their consequence under the control.

  The owner's own diagnosis of why one line could not serve both: **payments mean different things in the two modes, and the code agrees.** `bank.require_payments_enabled` gates reconciliation on `feature_payments` alone and never consults the mode, while `tournaments_to_tick` excludes a manual tournament outright — so manual with payments on is *reconciliation and nothing else*: no instructions, no reminders, no expiry, because the scheduler never sees it and the roster arrived dormant by import. The label, hint and consequence are therefore keyed by mode. His sentence — "Squire ti může pomoct s párováním podle výpisu" — is used verbatim, in the one cell where it is true

- [x] 3.3 Lay out the three tiers per the spec — mode, payments, inclusions — with the first two visibly decisions about what Squire does and the third a plain checklist. Two writes behind one confirm: the mode goes to `registrations-kept-by`, the features to `/features`. Apply the mode first, so a failure on the second leaves the more consequential choice recorded rather than the less
- [x] 3.4 Delete `EASY_MODE`, `isEasyMode` and the "advanced with nothing chosen" handling. Nothing may derive a label from the flags again (design D1) — if a caller wants one, that is the defect returning
- [x] 3.5 `MODE_FEATURES` → `TOURNAMENT_FEATURES`, the three only. Payments is read by name at each of its two sites, which is fewer places than a second constant would create and makes its absence from the array read as deliberate. The type covering all four flags is `TournamentFlags`, since the tab and phase logic genuinely needs all four
- [x] 3.6 `TournamentMode` → **`TournamentFlags`, still four booleans** — deviation from the written task. `offeredSetupTabs`, `offeredPhases` and `setupTabTitleKey` all read `feature_payments`, so a three-boolean type would have broken them for a distinction that is about category, not storage. `TOURNAMENT_FEATURES` is where the three-ness lives
- [x] 3.7 `setup/ModeSection.tsx` and `setup/RegistrationsKeptBySection.tsx` → one `setup/SettingsSection.tsx` stating all three tiers with one control; mount it once in `SetupPanel.tsx` where the two were
- [x] 3.8 `TournamentPicker.tsx`: the two-step creation flow collapses to one panel; the `modeDone` state added by `add-registrations-kept-by` goes with it.

- [x] 3.8b **Nothing is created until the settings panel is confirmed** (owner, on seeing it). This reverses `tournament-modes` D11, which persisted the tournament *before* the second panel so that dismissing it could not lose the record — the cost being a tournament brought into existence by an act the organizer then backed out of. Cancelling now returns to the naming panel with every field intact and nothing created.

  Two consequences to know. `TournamentSettingsFields` gained an `onConfirm` prop: given one, it reports what was chosen instead of writing it, and asks for no confirmation — the warnings count what a change would hide, and a tournament that does not exist holds nothing. And a taken slug is now answered *after* the second panel rather than before, so the failure path returns to the naming panel and states it there
- [x] 3.9 `setup/PublishSection.tsx` imports `FEATURE_NAMES` to name the feature that restores a hidden item's editor — follow the rename and confirm the message still reads correctly for an extra item hidden by a feature

## 4. Localization

- [x] 4.1 Rewrite `setup.mode.*` as `setup.settings.*` in `en.json`: the surface title, the two modes and their consequence hints, the payments line and its hint, the three inclusions and their existing hints, the warnings. Delete `easy`, `easyHint`, `advanced`, `advancedHint`, `nothingChosen` and `paymentsConsequence` — the last belongs to the payments row now, not to a warning about a mode
- [x] 4.2 Fold `setup.keptBy.*` into the same block rather than leaving a second namespace for the first tier
- [x] 4.3 Czech in the same pass; `locale-parity.test.ts` covers the drift. **Owner review wanted**: *režim: automatický / manuální* is settled, but what the hint under each says is written against the screen, and the consequence — that in manual mode Squire writes to nobody — has to be in the hint rather than inferred from the adjective (design, Open Questions)
- [x] 4.4 Neither catalogue names an easy or advanced mode anywhere; asserted by `noDerivedTierName.test.ts` rather than by a one-off grep, so it stays true

## 5. Tests

- [x] 5.1 `backend/tests/test_tournament_modes.py` → `test_tournament_features.py`, endpoint and payload names updated. Its assertions about easy/advanced mode go with the concept; assertions about what each feature hides stay untouched
- [x] 5.2 `test_tournament_modes_migration.py` keeps its name and its assertions — it exercises a historical revision, and history is not renamed
- [x] 5.3 `registrationsKeptBy.test.tsx` and its neighbours follow the components. The test asserting the mode dialog offers four features and nothing about ownership becomes its opposite: the settings surface offers all three tiers, and nothing else does
- [x] 5.4 `src/noDerivedTierName.test.ts`: no source file contains `isEasyMode`, `EASY_MODE` or `MODE_FEATURES`, and neither locale names an easy or advanced mode. Read through Vite's own `import.meta.glob` rather than `node:fs`, so it typechecks without ambient node types, plus an assertion that the glob matched anything at all — a pattern that silently matched nothing would turn the whole test into no test
- [x] 5.5 Cover the two-write confirm: a failure writing the features leaves the mode applied and says so, rather than reporting success or silently reverting

## 6. Reconciling the four changes

- [x] 6.1 Archive in order: `unify-lifecycle-dormancy`, `add-registrations-kept-by`, `add-external-registration`, then this one. `registration-ownership` and `tournament-modes` must exist to be renamed; archiving this first would remove requirements that had not been created
- [x] 6.2 After archiving, confirm `openspec/specs/` holds `tournament-mode`, `tournament-features` and neither `tournament-modes` nor `registration-ownership`, and that `payments` carries the suspension requirement
- [x] 6.3 Soften `add-external-registration`'s `fencer-home` delta before it archives: it says the card offers the way out "in that place", and the implementation puts the statement on the card and the destination one click away on the detail page, because the card is a single link and cannot nest another (recorded in that change's task 6.1)
- [x] 6.4 Grep the whole of `openspec/specs/` for `tournament-modes`, `easy mode` and `advanced mode` afterwards; six files referred to it and each needs its reference pointed at whichever of the two successors it meant

## 7. Verification

- [x] 7.1 `pytest` 1002 passed — exactly the count this change started from — and `ruff check .` clean
- [x] 7.2 `vitest` 334 passed, `npm run lint` and `npm run build` clean
- [x] 7.3 **None beyond the expected two.** The backend suite passed at 1002 after nothing but identifier and URL edits — no assertion was rethought, which is the evidence that no behaviour moved. On the frontend, only the two files this change rewrote by design: `test_tournament_features.py`'s easy-mode assertion became "turning the last flag off names no state", and the settings test replaced "the mode dialog offers four features and nothing about ownership" with its opposite
- [x] 7.4 **Looked at it, and it caught a defect nothing else could.** The new external-registration field rendered its label as `PARAM.EXTERNAL_REGISTRATION_URL`: identity fields take their label from `param.<key>`, and `add-external-registration` added the field and its hint but not that key. Neither the type checker nor `locale-parity` sees it — parity compares the two catalogues against each other, never against what a component asks for. Added `param.external_registration_url` in both locales and `src/setup/identityLabels.test.ts`, which asserts every identity field's label and hint resolve; verified it fails with the key removed.

  The surface reads as intended: three tiers separated by hairlines, the mode leading, and the section on `OTHER` stating all three in words where two sections used to sit. Checked again after 3.3b, in both modes, and confirmed the live tournament was left untouched — `na-duel-2026` is still automatic with payments on.

  The dialog needed to be wider (owner, on seeing it): at the standard 26rem the three tiers outgrew a 780px viewport and put the surface's own actions below the fold. `.modal-wide` gives it 40rem and 88dvh — wider rather than taller, so the extra room goes to the sentences that distinguish the two answers in each tier, and every one of them now sits on a single line. Verified on screen with no scrollbar and both actions visible
