## Context

Validation in Squire is presently backend-only, partial, and untranslated.

- `backend/app/schemas.py` carries pydantic `Field(...)` bounds written inline, one field at a time. Coverage is uneven: `display_name` is bounded to 200 but `description`, `qualification_criteria`, `registration_instructions`, `bank_account`, `fio_token`, `output_sheet_url` and the discipline `name` have no bound at all. The discipline `slug` and `weapon` gained lengths from `discipline-identity-modal` (30 each) but the slug still has no pattern, which is the gap D6 closes.
- `frontend/src/` has no client-side validation whatsoever. `useSectionSaver`'s `validate()` returns `true` in four of six Setup sections, and the two real ones only check for an empty required cell.
- A 422 reaches the user as `t("setup.saveBar.genericError", { status })` — literally "Save failed (422)". Pydantic's own error text is English and phrased for developers.
- Numeric fields use `<input type="number">` and `Number(event.target.value)`. In a Czech locale the browser rejects the typed comma and hands back a truncated or empty string. This is the `bugs.md` entry "exchange rate flips from 25 to 2".
- Localized text already has two independent catalogs: `backend/app/locales/*.json` (emails, documents, via `app/i18n.py`) and `frontend/src/i18n/*.json` (UI, via i18next). Both auto-discover files, so adding a locale needs no code change.
- The error vocabulary already in use across routers is `HTTPException(detail="snake_case_code")` — around fifty codes. Any new error format has to sit alongside that convention, not fight it.

Four decisions were taken by the owner before this design (recorded below as D1–D4).

## Goals / Non-Goals

**Goals:**

- One authoritative statement of every editable field's type and accepted values, with automated protection against the frontend and backend drifting apart.
- A user who types a wrong value learns what is wrong, in their own language, before a request is sent.
- Decimal comma and decimal point accepted interchangeably, end to end.
- Four global rules applied uniformly rather than field by field: whitespace and control-character hygiene, a universal string ceiling, `http(s)`-only links, bounded whole-unit money.
- Closes two open bug reports (exchange-rate comma, extra-item choices comma).

**Non-Goals:**

- No change to what the fields *mean* or to any pricing, matching or payment logic. Bounds are being declared, not invented — where a bound already exists it is moved, not retuned.
- No form-library adoption (react-hook-form, zod, formik). The Setup save-registry pattern stays; it gains a real `validate()`.
- No runtime schema fetch, no build-time codegen step (see D1).
- No cross-field business validation beyond what routers already do (e.g. `amendments_close_after_registration_closes` stays a router check, expressed in the new error shape).
- Import/ETL column parsing is out of scope; this change covers fields a human edits in a form.

## Decisions

### D1 — Python is authoritative; the TypeScript mirror is checked in and drift-tested

`backend/app/constraints.py` holds the table. Every `Field(...)` in `schemas.py` reads from it, so a bound exists in exactly one place on the backend. `frontend/src/constraints.ts` is a hand-maintained mirror, imported statically by the frontend.

The mirror is not trusted to stay correct. `backend/tests/test_constraints_mirror.py` builds the app's OpenAPI schema, walks every request-body property, and asserts that each `maxLength` / `minLength` / `minimum` / `maximum` / `pattern` / enum it finds has an equal entry in `constraints.ts` (parsed as text — the test reads the file, it does not run TypeScript). The same test asserts the converse: every editable string, integer and decimal property in the schema has *some* declared bound, which is what stops a new unbounded field from being added.

*Alternatives considered.* Build-time codegen from OpenAPI removes drift by construction but adds a generated file to review and a codegen step to the frontend build, and makes the frontend build depend on a running or exported backend schema. A runtime `GET /api/field-constraints` is always in sync but costs a boot request and gives up static typing — a max length would stop being a compile-time constant. The drift test buys most of codegen's safety at none of its build cost.

### D2 — Numeric input is text with a tolerant parser, on both layers

Every `<input type="number">` becomes `<input type="text" inputMode="decimal">`. `inputMode` keeps the numeric keypad on mobile; the text type stops the browser from sanitizing the value before React sees it. Native spinners disappear, which the design spec prefers anyway (no browser chrome inside a bottom-ruled field).

A shared `parseDecimal(raw)` in a new `frontend/src/numeric.ts`:

- strips spaces, non-breaking spaces and narrow no-break spaces (thousands grouping);
- accepts exactly one separator, `,` or `.`, and normalizes it to `.`;
- rejects two separators, a leading/trailing separator, and any other non-digit character;
- returns a discriminated result (`{ok: true, value}` / `{ok: false, code}`) rather than `NaN`, so the caller cannot forget to check.

`parseInteger(raw)` wraps it and rejects a non-zero fractional part with `must_be_whole` — never rounding, because rounding a capacity or a fee silently is exactly the class of bug this change exists to remove.

On the backend, an annotated type `TolerantDecimal` (a pydantic `BeforeValidator` applying the same normalization to `str` input) is used for `eur_rate` and any future decimal; `TolerantInt` does the same for integers. Posting `"25,5"` to the API therefore behaves identically to typing it in the UI, which keeps one rule for both entry paths.

Display is the mirror image: a Czech UI writes the stored value back with a comma. `money.ts` already formats with `toLocaleString("cs", …)`; the edit controls get the same treatment so a value round-trips through the form unchanged.

*Alternatives considered.* Keeping `type="number"` and fixing only the backend leaves the reported bug in place — the browser eats the comma before any of our code runs. Normalizing in the frontend only leaves a direct API caller with a raw 422 for a value the UI accepts.

### D3 — The API returns machine codes; the client renders the message

A `RequestValidationError` handler in `app/main.py` converts pydantic's error list into:

```json
{"detail": {"errors": [
  {"field": "disciplines.0.fee", "code": "out_of_range", "params": {"min": 0, "max": 1000000}}
]}}
```

`field` is the dotted path pydantic already produces (with the `body` prefix dropped), so a client can address a row inside a list. Pydantic error types map to a small closed code set: `required`, `too_short`, `too_long`, `out_of_range`, `not_a_number`, `must_be_whole`, `bad_pattern`, `bad_email`, `bad_url`, `bad_link_scheme`, `bad_enum`, `bad_date`, `forbidden_characters`. `params` carries whatever the message interpolates.

The existing `HTTPException(detail="snake_case")` codes are wrapped by a small helper into the same envelope (`{"errors": [{"field": …, "code": …, "params": {}}]}`) so the client has one shape to parse; the bare-string form stays accepted on read for anything not yet converted, which keeps the migration incremental.

The frontend maps `code` → `t("validation." + code, params)`. Client-side checks emit codes from the same set, so a value rejected before the request and the same value rejected after it produce byte-identical text. That property is what makes the shared code set worth the indirection.

*Alternatives considered.* Server-side localization via `Accept-Language` would reuse `app/locales` and cover non-browser clients, but hands message wording to the layer that knows least about where the message will appear, and makes the displayed language a server decision. Returning both a code and a fallback text is more robust but maintains the same sentence in two catalogs.

### D4 — Global rules, and where each is enforced

| Rule | Backend | Frontend |
| --- | --- | --- |
| Trim; collapse inner whitespace on single-line fields | `BeforeValidator` on the shared string types | on blur, so the user sees the normalized value |
| Reject C0/C1 controls and ZWJ | shared string validator → `forbidden_characters` | on blur (catches paste) |
| Universal ceiling — 200 single-line, 300–500 descriptive, 5000 markdown | `max_length` from `constraints.py` | `maxLength` attribute + blur check |
| `http(s)` links only | shared `HttpUrlStr` type → `bad_url` / `bad_link_scheme` | blur check with the same codes |
| Money: whole units, `0 … MONEY_MAX[currency]` | `TolerantInt` + per-currency bound from `constraints.py` | `parseInteger` + per-currency bound from `constraints.ts` |

Three tiers rather than a per-field number keeps the table readable and makes "which tier is this?" the only question when a field is added.

The money ceiling is **per currency**, set by the owner: **10 000 CZK** and **1 000 EUR**. A single cross-currency figure would have been too loose for whichever currency it was not chosen for; these two sit just above the largest plausible HEMA entry fee in each, so an extra typed zero on a realistic fee is caught rather than quoted to a fencer. The two are not a conversion of each other and are not expected to stay in ratio — each is the answer to "what is too much in this currency", asked separately.

This makes the ceiling depend on which currency a field is denominated in, which the schema already knows: `fee`/`price`/`value` are local-currency, `fee_eur`/`price_eur`/`value_eur` are EUR, and a tournament in EUR mode carries EUR in its local-currency fields. The bound is therefore resolved per request from the tournament's `local_currency` rather than baked into the field, and the `out_of_range` params carry the resolved figure so the message states the right one. Adding a currency means adding a row to the ceiling table — the same shape as `CURRENCY_UNITS` in `app/i18n.py` and `CURRENCY_SYMBOLS` in `money.ts`.

The fields that today have no bound at all get one in this change: discipline `name` (length, against its `String(100)` column), `description` / `qualification_criteria` / `registration_instructions` (markdown tier), `bank_account` (pattern), `fio_token` (length), `output_sheet_url` (URL rule), `hr_category_map` keys and values (length). The discipline `slug` gains a pattern on top of the length it already has — see D6.

### D5 — Validation timing lives in the existing save registry

`SectionSaver.validate()` stops returning `true`. Each Setup section computes its invalid-field set from `constraints.ts` and reports it; `SetupSaveBar` already collects `validate()` across a tab's sections and can therefore refuse to flush and state the count. Per-field state (touched / error code) lives in the section's own component state — no new global store.

Blur-and-save timing, rather than keystroke validation, matters for the fields being typed into progressively: a slug or a URL is invalid for most of the time it is being typed, and flagging it mid-word is noise. The one exception is the length ceiling, which the `maxLength` attribute enforces continuously by simply refusing further characters.

Fields outside Setup (`Login`, `TournamentPicker`, `ProfilePage`, `Console`, `TournamentFace`) get the same blur check through a small `useFieldValidation` hook, without adopting the save-registry machinery.

### D6 — The discipline slug gets a pattern, and stored slugs are migrated to fit it

The discipline slug is `^[A-Za-z0-9-]{1,30}$`. 30 is the column width (`models.py:315`) and is the figure `discipline-identity-modal` already put on the input schema; 16, proposed in an earlier draft of this design, is too short — a kind-prefixed slug reaches 18 characters at `Team-Plastic-LSW-2`. The underscore that draft permitted is dropped: the shipped normalizer collapses everything outside `[A-Za-z0-9-]` to `-`, so an underscore can never reach storage and permitting it would describe nothing.

Two things follow that are not obvious.

**Normalization has to move ahead of validation.** `normalize_slug` runs in the router today (`tournaments.py:537, 635`), which is *after* pydantic. A `pattern=` on `DisciplineIn.slug` would therefore reject an override before the normalizer could fix it, and `discipline-identity-modal` shipped a scenario that depends on it being fixed: an organizer overriding a slug with `Sword & Buckler (variant)` gets `Sword-Buckler-variant`, not a rejection. So normalization becomes a `BeforeValidator` on the field and the pattern is checked against its output. The pattern is then unfalsifiable for any non-empty input — which is the point. It documents the alphabet, the mirror test holds the frontend to it, and the empty-normalization case keeps the fallback to a generated slug the router already has.

**Stored slugs can fail it, and are migrated.** The `split-discipline-identity` migration renamed `code` to `slug` in place without rewriting, so a discipline created before the split still carries its old taxonomy code — and the plastic codes contained a space (`Plastic SAW`). Those rows would fail the pattern.

This is the one place the "bounds are on input schemas, so stored rows are never re-validated" argument does not hold. The Setup discipline table round-trips the whole discipline object on every save, so an organizer changing nothing but a capacity re-submits the untouched legacy slug and would be rejected on a field they never saw and cannot see a reason for.

The slugs are therefore rewritten by migration. The alternative — leaving them and widening the pattern to admit a space — was rejected as a rule that describes history rather than intent: no new slug can contain a space, and a permanently grandfathered character in the pattern would outlive everyone who remembers why.

The rewrite is not a plain space-replacement. `generate_slug` has always done `.replace(" ", "-")`, so a plastic sabre added *after* the split holds `Plastic-SAW` while a legacy one in the same tournament holds `Plastic SAW`; normalizing the second lands it on the first and trips `UNIQUE(tournament_id, slug)`. The migration therefore disambiguates with the same `-2`/`-3` counter `generate_slug` uses, and its downgrade is a no-op — the pre-split form cannot be restored once two rows have been separated by a counter, and does not need to be.

What this costs, stated plainly: bookmarked console URLs for a renamed discipline stop resolving, an existing exported spreadsheet gains new columns on its next export, and a JSON export downloaded before the migration no longer resolves its disciplines on re-import. The last two recover by re-exporting. Whether any of it is real is decided by the pre-flight query in task 8.1 — on the current development database, no stored slug fails the pattern and the migration is a no-op.

## Risks / Trade-offs

- **The mirror test parses TypeScript as text** → It reads a deliberately flat, literal-only `constraints.ts` (no expressions, no imports). The test fails loudly if the file stops matching that shape, which is cheaper than adding a Node step to the Python suite.
- **The 422 body shape changes** → Only Squire's own frontend parses 422 bodies today, and it is changed in the same commit. The old bare-string `detail` form stays readable by the client for the router codes not yet converted, so nothing breaks mid-migration.
- **Bounds newly applied to previously unbounded fields could reject stored data** → The bounds are on *input* schemas, so existing rows are never re-validated. A description already over 5000 characters keeps rendering and only blocks on the next edit. A pre-flight query over the current database is part of the task list so any real case is known before deploy, not discovered by an organizer. The discipline slug is the exception — the Setup table resubmits the whole discipline object on every save, so a legacy slug is re-validated whether or not it was touched. That is why D6 migrates it rather than relying on this argument.
- **The slug migration rewrites published identifiers** → Accepted deliberately (D6) over grandfathering a space into the pattern. Bookmarked console URLs break; spreadsheets and JSON exports recover on re-export. The pre-flight query in 8.1 establishes the blast radius before the migration is written, and on the current database it is empty.
- **Text inputs lose native number affordances** (spinner, browser step validation) → Deliberate; the design spec forbids browser chrome inside a bottom-ruled field, and `inputMode="decimal"` preserves the mobile keypad, which is the affordance that actually matters.
- **Two locale catalogs still exist** (backend for emails, frontend for UI) → Unchanged by this design; validation messages live only in the frontend catalog, since only the UI displays them. The parity test covers the frontend catalog across its bundled locales.
- **Around 60 call sites change** → Mechanical, but wide. Tasks are ordered so the shared primitives land and are tested first, then each surface converts against a stable contract.

## Migration Plan

1. `constraints.py` + `constraints.ts` + the mirror test, with bounds transcribed from today's `schemas.py` — no behavior change yet, the test just starts guarding.
2. Tolerant numeric types and the shared string/URL types on the backend; the 422 handler; backend tests for each code.
3. `numeric.ts`, `validation.ts`, the `validation.*` locale namespace in `cs.json` and `en.json`, and the parity test.
4. Surface-by-surface frontend conversion, Setup first (it holds most fields and both open bugs).
5. Newly bounded fields last, after the pre-flight query over existing data.
6. The slug pattern last of all, behind its own migration (D6): pre-flight query, then the rewrite with collision counters, then the `BeforeValidator` and the pattern in the same deploy — the pattern must not reach production while a row that fails it is still stored.

Rollback is per-step: steps 1–3 are additive and safe to leave in place; step 4 is a UI revert; step 5 is a schema revert. Step 6 is the one that does not fully roll back — reverting the pattern is trivial, but the rewritten slugs stay rewritten, since restoring a space to a slug that has since been disambiguated with a counter would reintroduce the collision it was rewritten to avoid.

This change follows `discipline-identity-modal`, which is implemented. The discipline table is already in its post-dialog shape, so the Setup conversion in step 4 binds to the controls that remain rather than to identity fields that no longer exist in the row.

## Open Questions

- **The 10 000 CZK ceiling against a team entry.** No longer hypothetical: team disciplines are live, and a team fee is charged per team rather than per fencer, so a four-person roster at 2 500 Kč a head reaches the ceiling exactly. Task 8.3 checks the stored fees; if a real team fee sits at or above it, the CZK ceiling moves rather than the rule.
- **Whether the discipline `name` needs a minimum, not just a maximum.** It is required for a weapon outside the taxonomy and generated otherwise, so an empty name is already refused by the router (`discipline_name_required`) — but as a router code, not a field bound, which means it does not appear in the constraint table or the mirror test.
