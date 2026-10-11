## 1. Backend

- [ ] 1.1 `Tournament.short_code: Mapped[str | None]` (String(3)) and Alembic migration
- [ ] 1.2 Settings schema: accept null or a trimmed NFC string of 1–3 code points, reject otherwise with a field error
- [ ] 1.3 `OpenTournamentOut.short_code`; export/import field if the tournament export carries identity fields
- [ ] 1.4 Tests: length validation, null clears, trimmed value stored

## 2. Frontend

- [ ] 2.1 "Zkratka" field with help hint in the settings identity section, prefilled with `monogram(display_name)`, sent as null when unchanged or cleared
- [ ] 2.2 Card plate reads `short_code ?? monogram(display_name)` when there is no logo
- [ ] 2.3 i18n keys in both locales; test that an unchanged prefill is not sent

## 3. Finish

- [ ] 3.1 `npm run typecheck`, `npm run check`, `npm test`; `uv run ruff check .`, `uv run basedpyright`, scoped pytest
