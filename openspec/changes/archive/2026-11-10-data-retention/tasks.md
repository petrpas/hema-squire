## 1. Model

- [x] 1.1 Migration: `Tournament.personal_data_pruned_at`
- [x] 1.2 A setting that disables the pruning writes and logs counts instead: `HEMA_SQUIRE_RETENTION_WRITES_ENABLED`, off by default; off, the pass does the work, logs the counts and rolls back

## 2. Pruning

- [x] 2.1 `app/retention.py`: age deletes for outgoing mail, pending signups and password resets
- [x] 2.2 Tournament pruning for bank rows, registrations, manual rows and import rows (design D2, D3). No column mapping is stored, so raw cells go where they equal the row's parsed email, notes or accommodation, or hold an address; parse decisions, rules and the rule journal lose the same fields, since replay would write them back
- [x] 2.3 Tests: balances and revenue identical before and after, statement re-import adds nothing, rosters and Export tab identical, replay and JSON export work on a pruned tournament, second pass changes nothing
- [x] 2.4 Own pass in `run_tick`, outside `tournaments_to_tick`, each tournament isolated

## 3. Rollout

- [ ] 3.1 Confirm the organizer terms and privacy page from `privacy-baseline` state these periods and are live. Text checked 2026-11-10: both state 30 days for mail and 12 months for bank text, addresses, notes, accommodation and import details, rosters kept; not live yet
- [ ] 3.2 Take a verified backup, run with writes disabled, review the counts
- [ ] 3.3 Enable the writes

## 4. Checks

- [x] 4.1 `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
