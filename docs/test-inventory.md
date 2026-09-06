# Test inventory

Analysis of `backend/tests/`. Sections 1–6 describe the suite **as inventoried**
(1226 nodes, 139.1 s). Section 7 records what was then applied off the back of it:
the suite now stands at **1221 nodes in 114.7 s**.

Collected **1226 test nodes** from **1106 test functions** in **87 files**; full suite green in **139.1 s** (`pytest --durations=0 -q`, 1226 passed).

## 1. Summary

| bucket | functions | nodes | runtime |
|---|---:|---:|---:|
| `KEEP/invariant` | 480 | 520 | 47.01 s |
| `KEEP/contract` | 598 | 678 | 91.28 s |
| `KEEP/regression` | 22 | 22 | 2.64 s |
| `KEEP/property` | 0 | 0 | 0.00 s |
| `DROP/framework` | 2 | 2 | 0.01 s |
| `DROP/trivial` | 2 | 2 | 0.00 s |
| `MERGE/duplicate` | 2 | 2 | 0.07 s |
| **total** | **1106** | **1226** | **141.01 s** |

### What the numbers say

The brief's premise — ~1000 tests grown against a cap of 40, most of them noise —
does not survive contact with the suite. **1102 of 1106 functions assert a domain
rule, an API/DB contract, or a fixed bug.** Six functions are worth removing, and
they are worth 0.08 s between them. This is a suite that was written against
specs, not a suite that accreted.

Three things carried that conclusion, and each is checkable:

- **Docstrings state intent.** ~40% of the functions carry one, and they name the
  spec clause, the design decision (`design D4`), or the defect
  (*"the bug this covers"*, *"found on the pilot"*). Nothing landed in `UNCLEAR`.
- **Assertions are on observable state**, not on call plumbing. Sweeping every
  function for tests whose only assertions touch mock call args or counts returned
  **zero**. The nearest candidate, `test_hr_match_batching::test_roster_is_asked_in_batches_with_its_own_candidates`,
  fakes at the model boundary (`FunctionModel`) and asserts batch size, the token
  ceiling and candidate scoping — all real contract with the external model, one of
  them pinning a truncation bug. It stays.
- **Framework restatements are nearly absent.** No test asserts plain Pydantic
  type coercion, and the one test that touches the route table
  (`test_tenant_isolation::test_there_are_console_routes_to_sweep`) exists to stop
  the 67-route isolation sweep from silently collapsing to zero assertions, not to
  check that FastAPI registered anything. The validation tests target *custom* types
  (`_TolerantDecimal`, `_SingleLine`, `_Url`) and custom error codes
  (`not_a_number`, `must_be_whole`, `bad_link_scheme`), which are project code.

**`KEEP/property` is empty: the suite uses no Hypothesis at all** (no import of it
anywhere under `tests/`). Section 6 says where property tests would earn their place.

The real cost problem is not test count. It is **30.5 s — 22% of the run — spent
in seven migration files, most of it in `setup`**, re-running `alembic upgrade`
in a subprocess once per test function. See section 5.

## 2. Per-file breakdown

| file | funcs | nodes | runtime | buckets | spec-referenced |
|---|---:|---:|---:|---|---|
| `test_account_format` | 18 | 18 | 0.00 s | invariant 18 | — |
| `test_accounts` | 16 | 16 | 0.56 s | contract 16 | — |
| `test_admin` | 20 | 20 | 1.31 s | contract 20 | — |
| `test_auth_throttle` | 3 | 3 | 0.10 s | contract 3 | — |
| `test_bank` | 8 | 8 | 0.65 s | trivial 1, contract 7 | — |
| `test_bank_account_validation` | 9 | 9 | 0.46 s | contract 9 | — |
| `test_bounded_field_migration_safety` | 2 | 2 | 0.11 s | contract 2 | file |
| `test_capacity_and_max_qty_ceilings` | 9 | 9 | 0.45 s | contract 9 | — |
| `test_constraints_mirror` | 4 | 4 | 0.20 s | contract 4 | file; bank_account_pattern_enforce |
| `test_currency` | 33 | 35 | 5.27 s | invariant 33 | file |
| `test_dedup` | 12 | 12 | 1.40 s | invariant 12 | file |
| `test_determinism` | 5 | 5 | 0.38 s | invariant 5 | file |
| `test_discipline_amendment` | 19 | 19 | 2.91 s | invariant 18, regression 1 | — |
| `test_discipline_identity_migration` | 4 | 4 | 4.01 s | contract 4 | — |
| `test_discipline_slug_pattern` | 10 | 10 | 5.11 s | framework 1, contract 5, invariant 4 | — |
| `test_dormancy` | 8 | 13 | 1.42 s | invariant 7, regression 1 | file |
| `test_emails` | 11 | 18 | 1.70 s | contract 11 | — |
| `test_error_envelope` | 5 | 5 | 0.25 s | contract 5 | file |
| `test_export_json` | 19 | 19 | 2.86 s | contract 19 | file |
| `test_external_registration` | 15 | 18 | 1.42 s | contract 15 | file |
| `test_fieldtypes` | 13 | 25 | 0.00 s | invariant 13 | — |
| `test_health` | 1 | 1 | 0.00 s | contract 1 | — |
| `test_hr_integration` | 11 | 11 | 0.90 s | contract 11 | file; custom_weapon_contributes_no |
| `test_hr_match_batching` | 2 | 2 | 0.09 s | contract 2 | — |
| `test_hr_verdicts` | 24 | 24 | 0.01 s | invariant 24 | — |
| `test_i18n` | 6 | 6 | 0.00 s | contract 6 | file |
| `test_import` | 20 | 20 | 1.38 s | contract 20 | file |
| `test_import_clear` | 11 | 11 | 1.22 s | contract 11 | — |
| `test_import_operations` | 12 | 12 | 1.06 s | contract 12 | file |
| `test_imported_rows_union_migration` | 5 | 5 | 5.30 s | contract 5 | file |
| `test_issuing` | 61 | 61 | 7.46 s | invariant 56, regression 5 | file; the_dry_run_agrees_with_what |
| `test_item_options` | 13 | 15 | 1.48 s | contract 13 | file |
| `test_ledger_matching` | 12 | 12 | 1.20 s | invariant 12 | — |
| `test_mail_delivery` | 8 | 8 | 0.00 s | contract 8 | file |
| `test_manual_entry` | 18 | 18 | 1.37 s | contract 18 | — |
| `test_manual_matching` | 11 | 11 | 2.16 s | invariant 10, regression 1 | file |
| `test_manual_payments` | 25 | 25 | 3.36 s | contract 24, regression 1 | — |
| `test_manual_settlement` | 19 | 19 | 2.23 s | contract 17, regression 2 | — |
| `test_matching` | 22 | 22 | 4.41 s | invariant 22 | file; vs_in_message_matches_sepa_s |
| `test_mixed_placement` | 7 | 7 | 1.11 s | invariant 7 | — |
| `test_models` | 5 | 5 | 0.02 s | framework 1, contract 4 | — |
| `test_name_ranking` | 15 | 30 | 0.00 s | invariant 13, regression 2 | file |
| `test_name_resolution` | 15 | 15 | 2.72 s | invariant 14, regression 1 | — |
| `test_open_tournaments` | 9 | 9 | 1.05 s | contract 8, regression 1 | file |
| `test_operations` | 15 | 15 | 0.19 s | contract 15 | — |
| `test_participants` | 8 | 8 | 1.12 s | contract 7, regression 1 | file |
| `test_past_tournaments` | 14 | 14 | 1.80 s | contract 13, duplicate 1 | file |
| `test_payment_e2e` | 2 | 2 | 0.35 s | contract 2 | file |
| `test_payment_modes` | 43 | 47 | 4.96 s | invariant 43 | — |
| `test_payments_clear` | 15 | 15 | 1.81 s | contract 14, regression 1 | file; the_stored_readings_go_with_+re_import_after_a_clear_read |
| `test_payments_console` | 14 | 14 | 2.52 s | contract 14 | file |
| `test_payments_off` | 12 | 12 | 1.20 s | contract 12 | file |
| `test_pilot_naduel` | 1 | 1 | 0.47 s | regression 1 | file |
| `test_pricing_itemized` | 23 | 23 | 0.00 s | invariant 23 | file |
| `test_publishing` | 19 | 19 | 1.42 s | contract 19 | file |
| `test_registration_gating` | 11 | 11 | 1.54 s | contract 11 | file |
| `test_registration_open_time` | 26 | 28 | 0.67 s | invariant 25, regression 1 | — |
| `test_registrations` | 37 | 37 | 4.21 s | contract 37 | file |
| `test_registrations_kept_by` | 22 | 22 | 2.19 s | contract 22 | file; manual_settlement_demotes_no |
| `test_registrations_kept_by_migration` | 3 | 3 | 3.21 s | contract 3 | — |
| `test_rental_amendment` | 16 | 16 | 2.21 s | invariant 16 | — |
| `test_reservation_lifecycle` | 21 | 21 | 3.29 s | contract 21 | file |
| `test_roles` | 8 | 8 | 0.52 s | contract 8 | — |
| `test_row_numbers` | 5 | 5 | 0.50 s | invariant 5 | — |
| `test_row_numbers_migration` | 3 | 3 | 3.40 s | contract 3 | — |
| `test_rules` | 20 | 20 | 2.93 s | invariant 20 | file |
| `test_scheduler` | 4 | 4 | 0.53 s | contract 4 | file |
| `test_setup_missing` | 21 | 21 | 0.00 s | invariant 20, duplicate 1 | file |
| `test_setup_suggestions` | 19 | 21 | 0.81 s | contract 19 | file |
| `test_sheet_order` | 2 | 2 | 0.25 s | invariant 2 | — |
| `test_sheets_export` | 6 | 6 | 0.80 s | contract 6 | file |
| `test_sibling_matching` | 2 | 2 | 0.31 s | invariant 2 | — |
| `test_sqlite_pragmas` | 4 | 4 | 0.55 s | contract 4 | — |
| `test_startup_guard` | 3 | 3 | 0.00 s | contract 3 | — |
| `test_statement_import` | 13 | 13 | 3.88 s | contract 12, regression 1 | — |
| `test_taxonomy` | 7 | 7 | 0.00 s | trivial 1, invariant 6 | — |
| `test_team_disciplines` | 32 | 32 | 2.91 s | invariant 32 | file |
| `test_team_lifecycle` | 15 | 15 | 1.23 s | contract 15 | — |
| `test_tenant_isolation` | 2 | 68 | 5.43 s | contract 1, regression 1 | file |
| `test_tolerance_resettle` | 9 | 9 | 1.29 s | invariant 8, regression 1 | — |
| `test_tournament_features` | 9 | 9 | 0.63 s | contract 9 | file |
| `test_tournament_modes_migration` | 6 | 6 | 5.93 s | contract 6 | file |
| `test_tournament_tweaks` | 7 | 7 | 0.49 s | contract 7 | file; discipline_schedule_and_rule |
| `test_tournaments` | 19 | 19 | 1.04 s | contract 19 | file |
| `test_vs_migration` | 3 | 3 | 3.42 s | contract 3 | — |
| `test_vs_series` | 10 | 10 | 1.90 s | invariant 10 | — |

## 3. Drop list, ordered

Six functions, in the order I would remove them. Total reclaimed: **0.08 s**. The reason to remove them is that they mislead a reader about what is covered, not that they cost anything.

| # | test | bucket | justification |
|---|---|---|---|
| 1 | `test_bank::test_incoming_transaction_roundtrip_model` (L183) | `DROP/trivial` | Constructs the dataclass and asserts one field defaults to None. |
| 2 | `test_discipline_slug_pattern::test_required_fields_still_reject_normally` (L67) | `DROP/framework` | Asserts Pydantic raises on an empty required field; the surrounding tests already prove the slug normalizer did not disable validation. |
| 3 | `test_models::test_registration_roundtrip` (L39) | `DROP/framework` | A SQLAlchemy persist/reload plus two column defaults (RESERVED, GREYED); no domain rule can break here that a router test would not catch. |
| 4 | `test_taxonomy::test_is_taxonomy_weapon` (L19) | `DROP/trivial` | Restates `code in WEAPONS` as a predicate over the same constant. |
| 5 | `test_past_tournaments::test_held_counts_team_disciplines_in_teams` (L107) | `MERGE/duplicate` | Same setup and assertion as test_open_tournaments::test_mine_counts_team_disciplines_in_teams; keep one and parametrize the route (/held, /mine). |
| 6 | `test_setup_missing::test_currency_untouched_tournament_is_complete` (L142) | `MERGE/duplicate` | Byte-identical body to test_complete_setup_has_nothing_missing in the same file (same call, same assertion). |

No OpenSpec document names any of the six *by function*, so none is blocked on a
spec edit. Two of them do live in files an OpenSpec document cites by filename
(`test_past_tournaments`, `test_setup_missing`); a file-level citation survives
the removal of one function from that file, so this is a note, not a blocker. Two carry a caveat worth stating rather than burying:

- **`test_models::test_registration_roundtrip`** is the only test in
  `test_models.py` that is not a DB-constraint test. Removing it leaves the file
  as four uniqueness/nullability constraints, which is what it should be. But it
  is also the only place `Registration.state` is asserted to default to
  `RESERVED` at the model layer. Every router test that registers a fencer
  asserts `state == "reserved"` through the API, so the coverage survives —
  verify that before deleting, not after.
- **`test_past_tournaments::test_held_counts_team_disciplines_in_teams`** is a
  merge, not a deletion. `/held` and `/mine` are separate route handlers that
  happen to build the same DTO; the honest fix is one parametrized test over both
  paths, not dropping the `/held` case and losing that route's coverage.

## 4. Tests referenced by OpenSpec documents

Kept out of the plain drop list per the brief. The distinction that matters here
is **where** the reference lives, because `openspec/changes/archive/` is
superseded history rather than current behavior.

| source | distinct `test_*` identifiers | binding? |
|---|---:|---|
| `openspec/specs/` (authoritative) | **0** | — |
| `openspec/payments-spec.md` + active changes | 14 | yes |
| `openspec/changes/archive/` | 50 | no — superseded history |

**The authoritative specs name no test at all.** Every reference is either in an
active change or in the archive. So the protected set is not the 45 files a naive
grep suggests — it is **13 files and 1 function**, cited from `payments-spec.md`,
`changes/gate-data-work-behind-publication/`, and `changes/add-deployment/`:

`test_dedup`, `test_import`, `test_import_operations`,
`test_imported_rows_union_migration`, `test_issuing`, `test_matching`,
`test_payments_clear`, `test_payments_console`, `test_registration_gating`,
`test_registrations`, `test_rules`, `test_sheets_export`, `test_tenant_isolation`
— plus `test_matching::test_vs_in_message_matches_sepa_style`, the only test
named by function outside the archive.

None of the six drop candidates falls in that set, so the drop list stands
unchanged either way.

Two loose ends in the documents themselves, worth a cleanup pass independent of
the tests: `test_wait_for_all_queues_everything_unbilled` is named in an OpenSpec
document but matches no test in the suite, and `test_batch`, `test_concluded`,
`test_tournament_modes` read as prose fragments rather than test names.

## 5. The 20 slowest tests

Summed over parametrize expansion, all phases. `setup` vs `call` is what separates accidental cost from inherent cost here.

¹ *Accidental:* a function-scoped `migrated_db` / `pre_migration_db` fixture shells out to `alembic upgrade` once per test. See the note below the table.

| # | test | total | call | setup | verdict |
|---|---|---:|---:|---:|---|
| 1 | `test_tenant_isolation::test_foreign_organizer_is_refused` | 5.43 s | 0.12 s | 5.31 s | Accidental — `two_tournaments` is function-scoped and rebuilt for each of the 67 route params (0.08 s each). A green run mutates nothing, so module scope is safe; a red one may not be. |
| 2 | `test_statement_import::test_progress_is_counted_in_rows` | 1.79 s | 1.78 s | 0.01 s | Inherent — 45 rows through the batching path is the point of the test. |
| 3 | `test_vs_migration::test_migration_downgrade_drops_the_new_columns` | 1.47 s | 0.51 s | 0.96 s | Accidental¹ — plus an inherent half: the downgrade runs alembic a second time. |
| 4 | `test_row_numbers_migration::test_downgrade_drops_the_table_and_restores_the_old_names` | 1.46 s | 0.40 s | 1.06 s | Accidental¹ — plus an inherent half: the downgrade runs alembic a second time. |
| 5 | `test_imported_rows_union_migration::test_downgrade_restores_per_batch_uniqueness` | 1.36 s | 0.38 s | 0.98 s | Accidental¹ — plus an inherent half: the downgrade runs alembic a second time. |
| 6 | `test_discipline_slug_pattern::test_downgrade_is_a_documented_no_op` | 1.36 s | 0.42 s | 0.94 s | Accidental¹ — plus an inherent half: the downgrade runs alembic a second time. |
| 7 | `test_registrations_kept_by_migration::test_the_migration_is_reversible` | 1.29 s | 0.67 s | 0.62 s | Accidental¹ |
| 8 | `test_tournament_modes_migration::test_downgrade_drops_the_flags` | 1.27 s | 0.35 s | 0.92 s | Accidental¹ — plus an inherent half: the downgrade runs alembic a second time. |
| 9 | `test_discipline_identity_migration::test_downgrade_drops_classification_columns_and_restores_code` | 1.18 s | 0.33 s | 0.85 s | Accidental¹ — plus an inherent half: the downgrade runs alembic a second time. |
| 10 | `test_discipline_identity_migration::test_downgrade_raises_on_two_disciplines_sharing_a_taxonomy_code` | 1.15 s | 0.32 s | 0.83 s | Accidental¹ — plus an inherent half: the downgrade runs alembic a second time. |
| 11 | `test_currency::test_migration_renames_currency_and_adds_eur_columns` | 1.13 s | 1.13 s | 0.00 s | Inherent — drives alembic up and down from inside the body over a seeded DB; the cost is in `call`, with no fixture to rescope. |
| 12 | `test_currency::test_migration_adds_and_drops_currency_columns` | 1.12 s | 1.12 s | 0.00 s | Inherent — same shape as row 11. |
| 13 | `test_imported_rows_union_migration::test_a_key_cannot_be_imported_twice_into_one_tournament` | 1.00 s | 0.00 s | 1.00 s | Accidental¹ |
| 14 | `test_imported_rows_union_migration::test_one_row_survives_per_key_and_it_is_the_earliest` | 0.99 s | 0.00 s | 0.99 s | Accidental¹ |
| 15 | `test_vs_migration::test_migration_assigns_a_series_to_every_tournament` | 0.98 s | 0.00 s | 0.98 s | Accidental¹ |
| 16 | `test_imported_rows_union_migration::test_the_numbers_are_untouched` | 0.98 s | 0.00 s | 0.98 s | Accidental¹ |
| 17 | `test_vs_migration::test_migration_leaves_registration_vs_untouched` | 0.97 s | 0.00 s | 0.97 s | Accidental¹ |
| 18 | `test_row_numbers_migration::test_retired_phases_are_rewritten_by_what_the_rule_targets` | 0.97 s | 0.00 s | 0.97 s | Accidental¹ |
| 19 | `test_row_numbers_migration::test_backfill_numbers_registrations_then_the_latest_batch` | 0.97 s | 0.00 s | 0.97 s | Accidental¹ |
| 20 | `test_imported_rows_union_migration::test_the_same_key_in_another_tournament_is_fine` | 0.97 s | 0.00 s | 0.97 s | Accidental¹ |

### The one change worth making

Seven files build a SQLite database and run `alembic upgrade` in a
**subprocess, per test function**:

`test_vs_migration`, `test_row_numbers_migration`, `test_tournament_modes_migration`,
`test_imported_rows_union_migration`, `test_discipline_identity_migration`,
`test_discipline_slug_pattern`, `test_registrations_kept_by_migration`.

(`test_currency` runs alembic too, but from inside two test bodies rather than a
fixture, so there is nothing to rescope there. `test_bounded_field_migration_safety`
is named for a migration but drives the API, not alembic.)

Every one of those fixtures is declared bare `@pytest.fixture` — function scope.
The upgrade costs ~0.95 s and is **identical for every test in the file**; only the
assertions differ. Together these files account for **30.4 s of the
139.1 s run — 22% — most of it in `setup`**.

Migrating the fixture to `scope="module"` and copying the resulting `.sqlite` file
per test (`shutil.copy`, ~1 ms) keeps each test's isolation while paying the
alembic cost once per file: roughly **30.5 s → 8 s**, a **~16% cut to the whole
suite**, with no test removed and no coverage lost. The downgrade tests must keep
their own database, since they mutate schema state — copy-per-test already gives
them that.

That single change is worth more than deleting every droppable test in the suite
by a factor of ~250.

## 6. Proposed final shape

**1100 test functions / ~1220 nodes**, down from 1106/1226.

I am not proposing a path to 40. The 40 in the original brief describes a
system that no longer exists: the suite now covers six substantially independent
subsystems, most with their own spec under `openspec/`. A 40-test suite across
them would average under seven tests per subsystem — roughly one happy path per
subsystem and nothing else. What is actually there, by weight of runtime:

| area | funcs | what it holds |
|---|---:|---|
| Payments: matching, credit, tolerance, manual entry, settlement | 236 | VS format and routing, SPAYD/QR construction, multi-currency lanes that never sum, partial credit, deposit thresholds, waivers |
| Intake: import, parse, dedup, issuing, row identity | 168 | replay determinism, rule journal, dedup verdict bands, issuing as an intake step, stable row numbers |
| Tournament setup, publication, modes, features | 167 | completeness gates, the auto/manual axis, field bounds mirrored to the frontend, the error envelope |
| Registration lifecycle, seating, scheduler | 305 | timezone-correct opening gates, substitute queues, amendment repricing, itemized pricing and discounts |
| Identity: accounts, roles, HEMA Ratings | 111 | HR import mapping and match tiers, tenant isolation swept over every console route, IBAN normalization |
| Platform: migrations, persistence, mail, i18n, export | 113 | schema up/down reversibility, JSON export back-compat to v1, mail delivery and refusal, the pilot replay |

(Every one of the 87 files is accounted for above.)

### Where the suite is actually thin

Pruning is the wrong instrument here. Three gaps are worth more than any deletion:

1. **No property tests at all.** Four areas are genuinely combinatorial and are
   currently covered by hand-picked examples: VS allocation under concurrency
   (`test_vs_series` asserts two racing registrations; the invariant is *no
   duplicate symbol under any interleaving*), the replay engine
   (`test_determinism` — rule order, removal and re-application should commute to
   the same rows), name ranking (`test_name_ranking` already asserts
   `0.0 <= score <= 1.0` over 7 hand-written queries — that is a property test
   wanting a generator), and IBAN/domestic account round-tripping. These would
   *add* tests, and they are the tests most likely to find something.
2. **`test_tenant_isolation` guards console routes; nothing guards fencer-facing
   ones.** The sweep asserts a foreign organizer gets 403 on 67 console routes.
   There is no equivalent sweep asserting a fencer cannot read another fencer's
   registration, payment instructions, or profile. That is the same class of bug
   on a larger blast radius.
3. **Migration *forward* correctness is well covered; migration *ordering* is
   not.** Each migration file tests its own upgrade in isolation from a
   hand-seeded DB. Nothing runs `alembic upgrade head` from an empty database and
   asserts the result matches `Base.metadata` — the check that catches a
   migration that drifted from the models.


## 7. What was applied

Two of the six recommendations in sections 3 and 5, both no-coverage-change work.
Items 2 and 3 of the recommendation list (the fencer-facing isolation sweep, the
metadata-vs-migrations drift test) are **not** done — they add tests and want a
change document first.

### The fixture rescope

Each of the seven files above now builds its database **once per module** and
hands each test a copy:

- a module-scoped `_migrated_template` (and, where the file had a two-stage
  build, a module-scoped `_pre_migration_template` feeding it) holds the
  alembic run, keyed off `tmp_path_factory` rather than the function-scoped
  `tmp_path`;
- a function-scoped `migrated_db` / `pre_migration_db` returns a copy via a new
  `migration_db_copy` fixture in `conftest.py`, which also carries `-wal`/`-shm`
  sidecars across if any survive.

Every test still gets a private database it may migrate, downgrade or corrupt.

| | before | after |
|---|---:|---:|
| the seven migration files | 30.4 s | 9.8 s |
| full suite, wall clock | 139.1 s | 114.7 s |

**20.5 s off the migration files; 24.4 s (18%) off the suite.** The gap between
the two is run-to-run variance, not a second effect — the migration files are
where the saving is.

Isolation was verified beyond the suite passing: each of the seven runs green
alone, and all seven run twice in a single session (66 executions against 7
shared templates, including the schema-mutating downgrade tests) stays green. A
downgrade corrupting a template would fail the second pass.

### The six removals

Applied as listed in section 3, with one deviation. The `/held` merge was
**not** a deletion: `test_open_tournaments::test_mine_counts_team_disciplines_in_teams`
and the removed `test_past_tournaments::test_held_counts_team_disciplines_in_teams`
became one test parametrized over both routes,
`test_past_scope_counts_team_disciplines_in_teams[mine|held]`. Both handlers are
still asked, which is why the net node count is 1221 and not 1220.

Before deleting `test_models::test_registration_roundtrip` I checked the caveat
in section 3: `Registration.state` defaulting to `RESERVED` is asserted through
the API by `test_registrations::test_registration_computes_total_and_assigns_vs`
and others, so the coverage survives the removal.

`ruff check tests/` passes; the removals orphaned five imports, which were
cleaned up in the same pass.
