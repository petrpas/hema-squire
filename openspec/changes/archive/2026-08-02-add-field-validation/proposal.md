## Why

Every edit field in Squire is currently unconstrained on the client: the frontend has no length limits, no numeric bounds, and no type discipline, so the first thing a user learns about a bad value is a bare `Save failed (422)`. The backend's pydantic constraints are real but partial, invisible to the person typing, and their rejection text is untranslated English from pydantic. Two live bugs come straight out of this gap — a `type="number"` field silently discards a typed decimal comma (the exchange rate "flips from 25 to 2"), and a comma cannot be typed into the extra-item choices box at all.

## What Changes

- Introduce a **single authoritative constraint table** in the backend (`app/constraints.py`) that every pydantic `Field(...)` reads from, and a checked-in TypeScript mirror (`frontend/src/constraints.ts`) that the frontend reads from. A test compares the mirror against the generated OpenAPI schema, so drift fails the suite rather than reaching a user.
- Give **every edit field a declared type and accepted range**: strings get a max length (and a min where emptiness is meaningless), integers get min/max, decimals get min/max plus a fixed scale, enumerations get their value set, and patterned fields (tournament slug, discipline slug, e-mail, URL) get their pattern. No field remains unbounded.
- Accept **both decimal separators**. A shared tolerant parser accepts `,` and `.`, tolerates space/NBSP thousands grouping, and rejects genuinely malformed input. Every numeric `<input type="number">` becomes `type="text" inputMode="decimal"` so the browser stops eating the comma before the application sees it. The backend coerces comma decimals too, so a direct API caller obeys the same rule as the UI.
- **Localize every validation message.** The 422 handler returns stable machine codes with parameters (`{field, code, params}`) in the established `snake_case` style; the frontend renders them from `cs.json` / `en.json`. Client-side checks use the same code set, so a message reads identically whether it was caught before or after the request. Both supported languages are complete — a missing key fails a catalog-parity test.
- Validate **on blur and on save**: a field that loses focus with a bad value shows its message immediately, and the Setup save bar refuses to flush a section holding an invalid field, naming how many fields need attention. Nothing is validated on every keystroke.
- Adopt four **global constraints** applying to all fields of a kind:
  - strings are trimmed, inner whitespace runs collapse for single-line fields, and C0/C1 control characters and zero-width joiners are rejected;
  - no string field is unbounded — single-line 200, long text 300–500, markdown bodies 5000;
  - URL fields must parse and carry an `http`/`https` scheme (`javascript:` and `data:` rejected);
  - money is a non-negative whole unit of currency with a ceiling stated per currency — 10 000 CZK, 1 000 EUR — so an extra typed zero is caught rather than mailed to a fencer.

## Capabilities

### New Capabilities
- `field-validation`: the field constraint contract (declared type, range and pattern per field), the global cross-field rules, tolerant decimal parsing on both layers, the machine-code error response format, and validation timing and save-blocking behavior.

### Modified Capabilities
- `design-system`: the form conventions requirement gains the invalid-field visual state (how a field marks itself invalid within the Bureau 1952 vocabulary — no browser default outline, no red glow) and the rule that a blocked save states plainly how many fields need attention.
- `localization`: the "fully localized from the start" requirement gains validation messages as a named surface, complete in every bundled locale, with a parity check rather than a silent fallback.

## Impact

- **Backend**: new `app/constraints.py`; `app/schemas.py` rewritten to source every bound from it; a `RequestValidationError` handler in `app/main.py` translating pydantic errors into `{field, code, params}`; a tolerant decimal type used by `eur_rate` and any future decimal; existing `HTTPException(detail="snake_case")` codes folded into the same response shape.
- **Frontend**: new `constraints.ts`, `validation.ts` (checks + code mapping) and a decimal parser alongside `money.ts`; numeric inputs converted across `SetupPanel.tsx`, `TournamentFace.tsx`, `ParamPanel.tsx`, `Console.tsx`; `useSectionSaver`'s `validate()` implementations become real; error rendering added to `Login.tsx`, `TournamentPicker.tsx`, `ProfilePage.tsx`, `SetupPanel.tsx`.
- **Locales**: a `validation.*` namespace added to `frontend/src/i18n/cs.json` and `en.json`.
- **Styling**: an invalid-field state in `index.css` using existing tokens (`--stamp`, `--stamp-tint`) only.
- **API contract**: the 422 body shape changes from pydantic's default to the code/params form — **BREAKING** for any client parsing 422 bodies today (only Squire's own frontend does).
- **Stored data**: binding a pattern to the discipline slug requires a migration rewriting stored slugs that fail it — **BREAKING** for identifiers already published. The `split-discipline-identity` migration renamed `code` to `slug` in place, so a pre-split plastic discipline still carries the space its taxonomy code had (`Plastic SAW`). Rewriting those invalidates bookmarked console URLs, changes the columns of an existing exported spreadsheet on its next export, and stops a previously downloaded JSON export from resolving its disciplines on re-import; all but the bookmarks recover by re-exporting. The pre-flight query decides whether any of this is real — on the current development database the migration is a no-op.
- **Fixes**: the exchange-rate comma bug and the extra-item choices comma bug from `openspec/bugs.md`.
- **Sequencing**: this follows `discipline-identity-modal`, which is implemented. The discipline table is already in its post-dialog shape — name and slug are text, and the identity controls this change would otherwise have validated no longer exist in the row. That change also bounded `weapon` and gave the slug a length; what it did not give the slug is a pattern, which is where this change picks up.
