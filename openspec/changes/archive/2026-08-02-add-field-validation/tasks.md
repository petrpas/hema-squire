## 0. Sequencing

- [x] 0.1 Applies after `discipline-identity-modal`, which is implemented. The Setup discipline table is already in its post-dialog shape: name and slug are text, the identity controls live in `DisciplineDialog.tsx`, and the row's editable controls are capacity, prices and the optional fields. Section 6 binds to that structure, not to the pre-dialog row
- [x] 0.2 `discipline-identity-modal` bounded `weapon` (1–30) and gave the slug a length (30) but no pattern. Transcribe those bounds rather than retuning them; the pattern is this change's contribution, in section 8a
- [x] 0.3 The discipline slug is the one field where "input bounds never re-validate stored rows" is false — the Setup table resubmits the whole discipline object on every save. Section 8a exists for that reason; do not fold it into section 8

## 1. The constraint table and its drift guard

- [x] 1.1 Create `backend/app/constraints.py`: the three string tiers (`SHORT=200`, `TEXT=300`/`500`, `MARKDOWN=5000`), the per-currency money ceiling table (`CZK: 10_000`, `EUR: 1_000`), and one entry per editable field transcribed from today's `schemas.py` bounds — no bound retuned in this task
- [x] 1.2 Rewrite every `Field(...)` in `backend/app/schemas.py` to read its bounds from `constraints.py`, leaving no inline literal bound behind
- [x] 1.3 Create `frontend/src/constraints.ts` as a flat literal-only mirror (no imports, no expressions) of the same table
- [x] 1.4 Write `backend/tests/test_constraints_mirror.py`: build the OpenAPI schema, walk every request-body property, assert each `maxLength`/`minLength`/`minimum`/`maximum`/`pattern`/enum equals the mirror entry, and assert the converse — every editable string, integer and decimal property has some declared bound
- [x] 1.5 Confirm the mirror test fails when a bound is changed on one side only, and when an unbounded editable field is added

## 2. Backend validation primitives

- [x] 2.1 Add `TolerantDecimal` and `TolerantInt` annotated types (pydantic `BeforeValidator`): accept `,` or `.`, strip space/NBSP/narrow-NBSP grouping, reject two separators, edge separators and stray characters; `TolerantInt` rejects a non-zero fraction with `must_be_whole` rather than rounding
- [x] 2.2 Add the shared string type: trim, collapse inner whitespace for single-line fields, reject C0/C1 controls and ZWJ with `forbidden_characters`
- [x] 2.3 Add `HttpUrlStr`: parse the value, accept only `http`/`https`, emit `bad_url` for a malformed link and `bad_link_scheme` for a rejected scheme
- [x] 2.4 Apply the three types across `schemas.py` — every string field on a shared string type, every money field on `TolerantInt`, `eur_rate` on `TolerantDecimal`, every link field on `HttpUrlStr`
- [x] 2.4a Resolve each money field's ceiling from the currency it carries — EUR-suffixed fields against the EUR row, local-currency fields against the tournament's `local_currency` row — and put the resolved figure into the `out_of_range` params so the message states the right maximum
- [x] 2.5 Tests: each type accepts its valid forms and rejects each invalid form with the expected code, including `"25,5"`, `"1 250"`, `"2,5,5"`, `"3,5"` into an integer field, a pasted ZWJ, and a `javascript:` link

## 3. The error response shape

- [x] 3.1 Add the `RequestValidationError` handler in `backend/app/main.py` producing `{"detail": {"errors": [{field, code, params}]}}`, with `field` as the dotted path minus the `body` prefix and every failing field listed
- [x] 3.2 Map pydantic error types onto the closed code set (`required`, `too_short`, `too_long`, `out_of_range`, `not_a_number`, `must_be_whole`, `bad_pattern`, `bad_email`, `bad_url`, `bad_link_scheme`, `bad_enum`, `bad_date`, `forbidden_characters`), carrying the violated limit in `params`
- [x] 3.3 Add the helper that wraps an existing `HTTPException(detail="snake_case")` into the same envelope, and convert the router codes that name a specific field (`slug_taken`, `qualification_criteria_required`, `discipline_slug_taken`, `discipline_slug_frozen`, `discipline_kind_frozen`, `discipline_name_required`, `amendments_close_after_registration_closes`, `legacy_fixed_fees_block_eur`). The earlier draft named `discipline_exists` and `code_is_immutable`; `split-discipline-identity` removed both, and the four discipline codes above replaced them. `discipline_slug_taken` carries the conflicting slug after a colon in its detail string — the wrapper puts it in `params` rather than leaving it in the code
- [x] 3.4 Tests: two fields failing in one request produce two entries; a limit violation carries its limit in `params`; a converted router code arrives in the same envelope; an unconverted bare-string `detail` still round-trips

## 4. Frontend primitives and messages

- [x] 4.1 Create `frontend/src/numeric.ts` with `parseDecimal` and `parseInteger` returning `{ok: true, value} | {ok: false, code}` — never `NaN` — plus the locale-aware formatter that writes a stored value back with the active locale's separator
- [x] 4.2 Create `frontend/src/validation.ts`: per-type checks against `constraints.ts` emitting the same code set as the backend, the global string/URL/money rules, and `apiErrors(err)` mapping an `ApiError` body to `{field, code, params}[]`
- [x] 4.3 Add the `validation.*` namespace to `frontend/src/i18n/cs.json` and `en.json` — one message per code, plain and matter-of-fact, no exclamation marks, every limit interpolated as a parameter, never written into the text
- [x] 4.4 Add the locale parity test: every code in the set has a message in every bundled locale, and no message contains a literal limit figure. (No frontend test runner existed in this project; added `vitest` as a devDependency and `npm test` to run it.)
- [x] 4.5 Tests for `numeric.ts` mirroring the backend cases from 2.5, so both layers are proven to agree
- [x] 4.6 Add the `useFieldValidation` hook: blur-and-save timing, error clears as soon as the value becomes valid, no keystroke validation

## 5. Invalid-field presentation

- [x] 5.1 Add the invalid-field state to `frontend/src/index.css` using `--stamp` and existing tokens only — `1px` bottom rule, `2px` on focus, no outline, glow, fill, icon or animation
- [x] 5.2 Render field errors as 12px `--stamp` text below the control with `aria-invalid` and `aria-describedby` wired to the message (`FieldError.tsx`, wired into surfaces in section 6/7)
- [x] 5.3 Give the blocked-save statement its form: how many fields need attention, same 12px `--stamp` text, no exclamation mark, activating it focuses the first invalid field (`SetupSaveBar` in `SetupPanel.tsx`; per-section `focusFirstInvalid` wired in section 6)

## 6. Setup conversion

- [x] 6.1 Replace every `<input type="number">` in `SetupPanel.tsx` with `type="text" inputMode="decimal"` reading through `parseDecimal`/`parseInteger`, and drop the direct `Number(event.target.value)` calls
- [x] 6.2 Verify the exchange-rate comma bug from `openspec/bugs.md` is gone — typing `25,5` stores 25.5 and reads back `25,5` in a Czech UI. Confirmed live in the browser: typed `30,7`, saved, reloaded, read back `30,7`
- [x] 6.3 Fix the extra-item choices box so a comma can be typed into it at all (the `bugs.md` entry). Verified live in the browser: this does not reproduce against the current code — a comma already types and displays correctly in the choices box (`splitChoices` and the plain-text control were already correct). No code change was needed for the comma itself; the surrounding field still gained the same string/length checks as every other text field
- [x] 6.4 Replace the six `SectionSaver.validate()` implementations with real per-field checks, so an invalid field blocks its section's flush (all seven registry entries: identity, organizers, disciplines, extra, currency, vsSeries, discounts)
- [x] 6.5 Route caught `ApiError`s through `apiErrors()` so a backend rejection lands under the field it names instead of `genericError`

## 7. Remaining surfaces

- [x] 7.1 `Login.tsx` and the signup form: e-mail, password length, display name, club. (No `club` field exists on the signup form itself — only email/password/display_name/language are collected there; `club` is edited elsewhere. Password and display name are wired to `useFieldValidation`.)
- [x] 7.2 `TournamentPicker.tsx`: display name, slug pattern, date; `slug_taken` lands under the slug field
- [x] 7.3 `ProfilePage.tsx`: display name, club, HR id. (`club` and `hr_id` are read-only display fields on this page, not editable here — only `display_name` is an editable input, now wired.)
- [x] 7.4 `Console.tsx` `EditableCell` and `ParamPanel.tsx`: typed cells against `constraints.ts`, no bare `Number(raw)`
- [x] 7.5 `TournamentFace.tsx`: quantity fields and the extra-item option answer

## 8. Newly bounded fields

- [x] 8.1 Run the pre-flight query over the current database for values that would fail the new bounds (over-long descriptions, links without a scheme, discipline slugs outside `^[A-Za-z0-9-]{1,30}$`) and record what it finds. The expected failing form is a pre-split plastic discipline whose slug still carries the space its taxonomy code had — `Plastic SAW` — because the `split-discipline-identity` migration renamed `code` to `slug` in place. On the current development database there are none; the query is run against whatever database is actually being deployed to. **Finding**: no discipline slug, no over-long string, and no fee over its ceiling in the current dev database — but one discipline (`na-duel-2026`, slug `LS`) carries `ruleset_url = "blaaa"`, which fails the new URL rule (no scheme). It keeps rendering; it will block on that discipline's next save until fixed (see 8.4's test)
- [x] 8.2 Add bounds for the fields that have none today: discipline `name`, `description`, `qualification_criteria`, `registration_instructions`, `bank_account`, `fio_token`, `output_sheet_url`, `hr_category_map` keys and values. `weapon` and the discipline `slug` already carry lengths from `discipline-identity-modal` — transcribe them into `constraints.py` rather than retuning them, and carry `gender`, `material` and `kind` in as enumerations
- [x] 8.3 Confirm no stored fee exceeds its currency's ceiling, checking team-discipline fees specifically — a team fee is charged per team, so four fencers at 2 500 Kč reaches the 10 000 CZK ceiling exactly (design Open Questions). **Finding**: the two stored team fees are both 3000 CZK, well under 10 000; the ceiling stays as designed
- [x] 8.4 Confirm existing over-limit rows still render and only block on their next edit

## 8a. The discipline slug pattern and its migration (design D6)

- [x] 8a.1 Move `normalize_slug` from the router (`tournaments.py:537, 635`) to a `BeforeValidator` on `DisciplineIn.slug`, keeping the router's fallback to a generated slug for the case where normalization yields the empty string. Validation must run *after* normalization or the pattern rejects overrides that `discipline-identity-modal` shipped as accepted
- [x] 8a.2 Confirm the shipped scenario still holds end to end: an override of `Sword & Buckler (variant)` is stored as `Sword-Buckler-variant`, not rejected. This is a regression test on a spec that is already in `openspec/specs/discipline-identity`
- [x] 8a.3 Add `pattern=^[A-Za-z0-9-]{1,30}$` to the discipline slug in `constraints.py` and its mirror, after 8a.1 and not before
- [x] 8a.4 Write the migration rewriting stored slugs that fail the pattern. Normalize with the same function, then disambiguate collisions with the `-2`/`-3` counter `generate_slug` uses — a legacy `Plastic SAW` and a post-split `Plastic-SAW` can coexist in one tournament today, and normalizing the first onto the second trips `UNIQUE(tournament_id, slug)`
- [x] 8a.5 Test the collision case explicitly: a tournament holding both forms migrates to two distinct slugs, and the constraint holds
- [x] 8a.6 Make the downgrade a documented no-op — the pre-split form cannot be restored once two rows have been separated by a counter
- [x] 8a.7 Deploy the migration and the pattern together; the pattern must not reach production while a row that fails it is still stored. Both land in this same change/commit set, so there is no window where the pattern is enforced without the migration having already run
- [x] 8a.8 Record in the change what the rewrite invalidated: bookmarked console URLs, the columns of any existing exported spreadsheet on next export, and disciplines in a JSON export downloaded beforehand. Recorded in the migration's own docstring (`alembic/versions/c61e07c3fe54_...py`); on the current dev database the migration is a no-op (8.1), so nothing is actually invalidated by this deploy

## 9. Verification

- [x] 9.1 Full backend suite green (483 passed); full frontend build and typecheck clean (`tsc -b`, `vite build`, `vitest run` — 50 passed)
- [x] 9.2 Walk the Setup tabs in both languages, confirming every message reads naturally in Czech and English and no exclamation mark or Title Case slipped in. Verified live in the browser in both Czech and English (the `ruleset_url` "must start with http(s)" message, in each language) — no locale file contains `!`
- [x] 9.3 Check the invalid state against the design prohibitions — no shadow, no glow, no default blue outline, no hex outside `tokens.css`. Confirmed: `index.css`'s new rules use only `var(--stamp)`/`var(--border-w)`/`var(--focus)`, no hex literal added outside `tokens.css`
- [x] 9.4 Post a malformed value directly to the API and confirm the response carries the same code the UI would have shown. Covered by `test_error_envelope.py` and `test_constraints_mirror.py::test_bank_account_pattern_enforced_despite_schema_blind_spot`, and observed live: the stored `ruleset_url="blaaa"` (found by 8.1) produces `bad_url` both from a direct blur-check and from the backend on save
- [x] 9.5 Strike the two fixed entries from `openspec/bugs.md`
