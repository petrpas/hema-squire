## 1. Model

- [x] 1.1 Migration: `Fencer.deletion_requested_at`, `Fencer.deleted_at`, table `account_erasures` (fencer id, kind, moment; no personal data)
- [x] 1.2 Column classification and the `Base.metadata` test (design D9); confirm `PaymentEvent.detail` and `last_error` contents while classifying

## 2. Core

- [x] 2.1 `app/account_deletion.py`: impact computation and blockers (owner, last Admin, Deployment Owner)
- [x] 2.2 Execute: cancellations via `cancel()`, credential and audit removal after collecting past addresses, address redaction (design D5), identity rule (design D2), session end, role reset, erasure log, in one transaction
- [x] 2.3 Mails: request received, withdrawn, completed, organizer notice, in `cs` and `en`, respecting mail language rules
- [x] 2.4 `erase_identity` (design D7)
- [x] 2.5 Scheduler pass in `run_tick`, each account isolated; deferred requests stay pending
- [x] 2.6 Tests from the spec: every scenario, including no credits lost, reversal totals unchanged, resignup unconnected, token refused, another seat's contact address kept, idempotent re-execution

## 3. Surfaces

- [x] 3.1 `routers/accounts.py`: impact, request with password, withdraw; `Account` answer states pending date
- [x] 3.2 `routers/admin.py`: deleted marking, exclusion from `hr_shared`, pending-execution tasks, erase endpoint with confirmation
- [x] 3.3 Roster answer: empty Paid and no faded state for a deleted account; test with both modes
- [x] 3.4 Enrolment and matching never select a deleted record; test by name and HR ID
- [x] 3.5 `export_json.py`: deleted state survives export and restore; test the round trip with an account-less record

## 4. Frontend

- [x] 4.1 `profile/`: Privacy tab gathering the notice summary, data download, accepted organizer terms and deletion; deletion dialog on `Modal` with impact, password and refusal states; pending state with withdrawal
- [x] 4.2 `admin/`: deleted marking, pending tasks, erase dialog on `Modal`
- [x] 4.3 `api.ts`, `cs` and `en` keys, sentence case, tests

## 5. Restore

- [x] 5.1 `scripts/reapply_erasures.py`: read the log from the latest restore, apply to the target database, idempotent
- [ ] 5.2 `deploy/restore.sh` runs it before the service starts; rehearse with a point-in-time restore

## 6. Checks

- [x] 6.1 `uv run ruff check .`, `uv run basedpyright`, `uv run deptry .`, scoped `pytest`
- [x] 6.2 `npm run typecheck`, `npm run check`, `npm test`, `npm run build`
- [x] 6.3 Confirm with `privacy-baseline` text that the page states exactly what execution does
