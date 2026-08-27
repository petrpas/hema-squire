## 1. Backend model and migration

- [x] 1.1 In `backend/app/constraints.py`, replace `DISCIPLINE_RULESET_NAME_MAX_LENGTH` and `DISCIPLINE_RULESET_URL_MAX_LENGTH` with a single `DISCIPLINE_RULESET_MAX_LENGTH = 500` (D3); verify no reference to either removed name survives (`grep -rn RULESET backend frontend/src`).
- [x] 1.2 In `backend/app/models.py`, replace the `ruleset_name` and `ruleset_url` columns on `Discipline` with `ruleset: Mapped[str | None] = mapped_column(String(500))`, updating the comment above them; verify the model imports cleanly (`uv run python -c "import app.models"`).
- [x] 1.3 In `backend/app/schemas.py`, replace both fields on `DisciplineIn` with `ruleset: SingleLineStr(constraints.DISCIPLINE_RULESET_MAX_LENGTH) | None = None` and on `DisciplineOut` with `ruleset: str | None`; verify `HttpUrlStr` is still imported and used by `organizer.link` and `output_sheet_url`.
- [x] 1.4 In `backend/app/routers/tournaments.py`, set `ruleset` on the discipline create and update paths in place of the two fields; verify `grep -rn "ruleset_name\|ruleset_url" backend/app` returns nothing.
- [x] 1.5 Write one Alembic revision that folds `[name](url)` into `ruleset_name`, then renames it to `ruleset`, then drops `ruleset_url`, with a best-effort downgrade that splits the `[label](url)` shape back into two columns (D2); verify `uv run alembic upgrade head` then `uv run alembic downgrade -1` then `upgrade head` runs clean on a copy of the dev database, and that a row seeded with a name and a URL comes back as `[name](url)`.

## 2. Backend tests

- [x] 2.1 Move `test_error_envelope`'s `javascript:` scheme case from the discipline ruleset to a titular organizer's `link` (D7); verify the test still asserts a `bad_link_scheme` error against the field it now names.
- [x] 2.2 Move `test_bounded_field_migration_safety`'s over-long-value case from `ruleset_url` to `schedule_where` (D7); verify the test still shows an over-long stored value blocking a later save of the whole row.
- [x] 2.3 Update `test_tournament_tweaks.test_discipline_schedule_and_ruleset_round_trip` to post and read back one `ruleset` field holding markdown; verify `uv run pytest` passes the whole backend suite.

## 3. Frontend

- [x] 3.1 Replace `ruleset_name`/`ruleset_url` with `ruleset` in `frontend/src/api.ts` (both the discipline read and write types) and regenerate/patch `frontend/src/constraints.ts` so `DisciplineIn.ruleset` carries maxLength 500 and the two old entries are gone; verify `npx tsc -b --noEmit` names every remaining call site.
- [x] 3.2 In `frontend/src/setup/DisciplinesSection.tsx`, collapse the two row fields into one `ruleset` field — one draft key, one dirty comparison, one payload key, one `checkString` bound to `DisciplineIn.ruleset` — and drop the now-unused `checkUrl` import; verify the expanded discipline row shows one ruleset input and the build type-checks.
- [x] 3.3 Add the shared `.markdown-hint` line beneath that input, keeping its existing `HelpHint` marker (D6); verify in Setup that the ruleset field shows both the help marker and the syntax line, matching the location field.
- [x] 3.4 In `frontend/src/TournamentFace.tsx`, render the ruleset as the plain label plus `<InlineProse source={d.ruleset} />` instead of building an anchor from `ruleset_url`, keeping it a `DotJoined` part that is absent (not empty) when the field is blank (D5); verify a blank ruleset leaves no stray middle dot on the discipline's subordinate line.

## 4. Localization

- [x] 4.1 Replace `setup.identity.locationHint` with a shared `setup.inlineMarkdownHint` in `cs.json` and `en.json`, worded to spell the link form as `[link](https://...)`, and point the location field at the new key (D6); verify `npm --prefix frontend test` passes locale parity.
- [x] 4.2 Replace the `setup.disciplines.rulesetName`/`rulesetUrl` label and hint keys with one `ruleset` label and one `rulesetHint` in both locales; verify no `rulesetName`/`rulesetUrl` key or reference remains (`grep -rn "rulesetName\|rulesetUrl" frontend/src`).

## 5. Verification

- [x] 5.1 Run `uv run pytest` in `backend` and `npm --prefix frontend test && npm --prefix frontend run build`; confirm all pass.
- [x] 5.2 Walk it in the app: set a discipline's ruleset to `[Barbasetti Right of Way](https://example.com/cz.pdf) (CZ) · [EN](https://example.com/en.pdf)`, and confirm the Setup preview and the tournament information screen both show two separate links after a plain `Pravidla:` label, that neither link is nested in another, and that a ruleset typed without link syntax still shows as plain text.
