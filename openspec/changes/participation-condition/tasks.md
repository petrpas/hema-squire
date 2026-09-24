## 0. Precondition

- [ ] 0.1 Confirm `demotion-hardening`, `queue-rosters` and `manual-entry-registers` are archived (this change's deltas extend their text and code)

## 1. Storage

- [ ] 1.1 `RegistrationDiscipline.conditional` (not null, default false) and Alembic revision
- [ ] 1.2 `export_json`: next schema version carrying `conditional`; older documents import with none

## 2. Placement

- [ ] 2.1 `placement.place(entries, full, settled)` per design D2; replace the submission and amendment inline sites; hand entry uses it
- [ ] 2.2 Schemas: submission, amendment and hand entry accept the tick (sets `conditional` on every individual entry); a condition over fewer than two individual disciplines is refused
- [ ] 2.3 Amendment refuses `amendment_would_queue_paid`; price preview returns the proposed placement
- [ ] 2.4 Tests: met / unmet / no condition; subset condition with an outside discipline; settled → all queued; amendment ticking, unticking, refusing with credit; existing registrations untouched

## 3. Organizer actions

- [ ] 3.1 `admit_substitute` seats the condition set together or refuses `condition_discipline_full` naming the discipline
- [ ] 3.2 `return_to_queue` on a conditional entry returns every seated entry; outside entries alone
- [ ] 3.3 Promotion mail names every discipline seated
- [ ] 3.4 Tests: invariant holds after every action; a later fencer promotable past a blocked conditional one

## 4. Reads

- [ ] 4.1 `sheet.base_rows` carries `conditional`; registration detail and outputs carry it
- [ ] 4.2 Queue roster: the row names the other conditional disciplines; arrow gating per D4; ↓ hint on a conditional row
- [ ] 4.3 Confirmation mail and fencer registration detail state the condition and the full discipline where unmet (backend catalogs cs, en)

## 5. Forms

- [ ] 5.1 Registration form: the tick, shown from two individual disciplines, unticked, with its consequence text
- [ ] 5.2 Amendment form: the tick and the pre-submit statement from the preview
- [ ] 5.3 Manual entry dialog on an automatic tournament: the tick
- [ ] 5.4 i18n cs, en: tick, consequence, marker, refusals

## 6. Checks

- [ ] 6.1 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
- [ ] 6.2 Frontend: `npm run typecheck`, `npm run check`, `npm test`
