## 1. Model

- [ ] 1.1 Migration: `Tournament.personal_data_pruned_at`
- [ ] 1.2 A setting that disables the pruning writes and logs counts instead

## 2. Pruning

- [ ] 2.1 `app/retention.py`: age deletes for outgoing mail, pending signups and password resets
- [ ] 2.2 Tournament pruning for bank rows, registrations, manual rows and import rows (design D2, D3)
- [ ] 2.3 Tests: balances and revenue identical before and after, statement re-import adds nothing, rosters and Export tab identical, replay and JSON export work on a pruned tournament, second pass changes nothing
- [ ] 2.4 Own pass in `run_tick`, outside `tournaments_to_tick`, each tournament isolated

## 3. Rollout

- [ ] 3.1 Confirm the organizer terms and privacy page from `privacy-baseline` state these periods and are live
- [ ] 3.2 Take a verified backup, run with writes disabled, review the counts
- [ ] 3.3 Enable the writes

## 4. Checks

- [ ] 4.1 `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
