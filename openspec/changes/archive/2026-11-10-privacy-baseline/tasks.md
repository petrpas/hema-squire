## 1. Facts and owner decisions

- [x] 1.1 Inventory browser storage and confirm nothing non-essential is set
- [ ] 1.2 Verify retention and terms: Anthropic in the organization's settings for the model in use, Scaleway TEM logs, Hetzner, Backblaze B2 lifecycle, Google; collect each processor's data processing agreement and transfer basis. Owner, 2026-11-10: not pursued
- [x] 1.3 Owner chooses the request mailbox and what address is published; make the mailbox receive mail and test delivery from outside. Done 2026-11-10: `privacy@hemasquire.eu` on Czechia.com's free mail (Zoner), forwarded to the owner; MX `1 relay`, `10 10mx`, `15 15mx.zoner.com` replace Scaleway's blackhole, SPF is one record with both includes, DMARC unchanged; a message from outside arrived
- [x] 1.5 Access log: uvicorn wrote client IP and path to an unrotated Docker log; turned off with `--no-access-log` (owner decision 2026-11-03), and the page states the IP is held in memory only
- [x] 1.4 Confirm the state of the leaked dump recorded in `security_tbd.md`; the page must not contradict it. Owner, 2026-11-03: the dump came from the local database and held only test accounts and test passwords; no third person's data, so nothing to rotate, record or notify

## 2. Records

- [x] 2.1 `docs/privacy/records-of-processing.md`: activities, roles, bases, periods, processors
- [x] 2.2 `docs/privacy/roster-balancing-test.md`: legitimate interest for retained rosters (design D2)

## 3. Text

- [x] 3.1 Draft privacy page and organizer terms in `cs` and `en`, sentence case, no exclamation marks; retention periods match `data-retention` and `account-deletion`
- [ ] 3.2 Owner has the role split, the roster retention and both texts legally reviewed; record the outcome in `docs/privacy/`. Owner, 2026-11-10: not pursued

## 4. Backend

- [x] 4.1 Migration and columns on `Fencer` for accepted terms version and moment; a version constant
- [x] 4.2 `POST /api/account/organizer-terms`; the account's answer states whether acceptance is due
- [x] 4.3 `GET /api/account/export` (design D5)
- [x] 4.4 Tests: the export holds the account's own data and no payer field, password hash, team member or other account's audit entry

## 5. Frontend

- [x] 5.1 Public route built from `routes.ts`, privacy page, persistent link in the shell
- [x] 5.2 Collection notice on signup, guest and registration forms
- [x] 5.3 Terms `Modal` on the console for the owner, with tests for owner and team member
- [x] 5.4 Data download on the Profile page, with `api.ts` addition and locale keys

## 6. Checks

- [x] 6.1 `uv run ruff check .`, `uv run basedpyright`, `pytest tests -q --maxfail=3 --tb=short --show-capture=no` scoped to accounts
- [x] 6.2 `npm run typecheck`, `npm run check`, `npm test`
