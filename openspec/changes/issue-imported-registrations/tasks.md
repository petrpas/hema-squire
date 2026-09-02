## 1. Backend: dormancy on the registration

- [x] 1.1 Add the dormancy mark to `Registration` in `backend/app/models.py` — a stored boolean, defaulting to clocks-running, documented as "both lifecycle clocks are dormant by origin" and cross-referenced to `registration`'s payments-off dormancy so the two causes are visibly the same concept
- [x] 1.2 Alembic migration adding the column with the clocks-running default; no backfill, since no issued registration exists before this change
- [x] 1.3 Honour the mark in `backend/app/scheduler.py`: the reminder pass, the expiry pass and seating settlement all exclude it. Four places, not three — `pending_demotions` states the count the organizer confirms before settling, and had to gain the same predicate or the console would promise to demote registrations settlement will not touch
- [x] 1.4 Honour the mark wherever a payment window or due date would be opened — `admit_substitute` (`routers/registrations.py:878`) now bills a promotion without opening a window. Defence in depth rather than a live path: since 7.2 seats every issued placement and neither expiry nor settlement demotes one, an issued registration cannot currently become a substitute at all. The guard states the invariant at the one place a due date is set, so a future path that demotes one cannot start its clock by accident
- [x] 1.5 Tests in `tests/test_issuing.py`: the lifecycle run against issued registrations aged 400 days sends nothing, expires nothing, reminds nothing and demotes nothing; changing the payment mode and moving the seating deadline then running again does the same; and a payment quoting an issued VS still credits, because what is dormant is time and not money. All assert against the collecting mailer

## 2. Backend: pricing a row

- [x] 2.1 ~~Add a function that totals a sheet row~~ — **no new function needed.** `pricing.registration_total(registration, tournament)` already prices a registration from its own entries, extras, rentals and afterparty, in both currencies, with discounts, and reads the date from `registration.registered_at`. Creating the registration with the row's own moment and calling it does the whole of 2.1–2.3 through the path an in-app registration is priced by, so the two can never disagree
- [x] 2.2 Take the pricing date from the row's `registration_time` — `issuing._registration_time` parses it onto `Registration.registered_at`, which is what `registration_total` reads. A missing or unreadable moment falls back to now rather than inventing a date that might award an early-bird discount nobody earned
- [x] 2.3 EUR comes with it: `registration_total` returns both columns and `total_eur` is None where the tournament prices in one currency
- [x] 2.4 Tests: an early-registered row priced after the deadline gets the early price while a late one does not; disciplines, rental and afterparty sum; a later fee change does not move an issued total

## 3. Backend: the issuing pass

- [x] 3.1 New module `app/issuing.py` for the pass: select fencer-list rows that have no registration, and for each resolve or create a `Fencer`, create a `Registration`, price it via section 2, freeze the total in `total_amount`, allocate a VS and set the dormancy mark
- [x] 3.2 Reuse the VS allocator — injected as a parameter rather than imported, so a service module does not depend on a router; there is still only one allocator in `routers/registrations.py:106` rather than writing a second one; keep the unique-constraint retry as the backstop it already is
- [x] 3.3 Resolve an existing `Fencer` by email before creating one, and never overwrite an existing record's name, HR binding or credentials — the pilot already has two rows whose fencers exist
- [x] 3.4 Carry an HR id onto a created fencer only where the organizer has confirmed the match; leave a proposed or unresolved match unbound
- [x] 3.5 Create the registration's discipline entries from the row's disciplines so capacity and the seating queue see it as they see any registration
- [x] 3.6 Skip a row that states no discipline, and report it with its reason rather than issuing a zero total. Two more skip reasons found in the code: `no_email` (`Fencer.email` is the account identity and is not nullable, and the pilot has such a row) and `no_name`
- [x] 3.7 Return a report: issued, already had one, skipped with reasons
- [x] 3.8 Tests: 54 rows issue 54 registrations with 54 distinct variable symbols; a rerun issues nothing and changes no VS, total, credited amount or state; a second import after a first pass issues only the new rows; a paid issued registration is untouched by a rerun; a row with no discipline is skipped and named; an existing fencer is reused and not overwritten; an unconfirmed HR match is not claimed

## 4. Backend: the endpoint

- [x] 4.1 Add the endpoint — `POST /import/issue`, synchronous rather than an operation: it asks no model and does bounded local work, so there is nothing an operation record could report that the response cannot on the console's Fencers phase, guarded by `require_console_access` as its neighbours are
- [x] 4.2 Refuse it while duplicate groups are still pending (409 `dedup_pending`), with a stated reason the console can render — a row a merge will collapse must not spend a variable symbol first
- [x] 4.3 `GET /import/issue` states `pending_rows` and `pending_dedup`, or carry the count on the tournament detail, so the confirmation can state how many rows will be issued before the organizer commits
- [x] 4.4 Tests: refused while dedup is pending; refused without console access; the report shape; the count agrees with what the pass then issues

## 3b. Backend: the row an issued registration stands in (found during implementation)

- [x] 3b.1 Issuing put the fencer in the list **twice** — once as `imp:<key>` and once as `reg:<id>`, since `base_rows` keys registrations separately from source rows. 54 rows would have become 108. `Registration.source_row_id` now carries the row's identity, and the registration is drawn under it, so the fencer keeps the fixed number the row was born with (spec etl-console, Fixed fencer number) and appears once. Source rows are added with `setdefault`, so claiming the id is what removes the duplicate
- [x] 3b.2 Unique index on `source_row_id`: one registration per row, the backstop that keeps issuing idempotent even under a concurrent pass
- [x] 3b.3 `sheet.source_rows` had identified source rows **by id prefix**, which the above broke — an issued registration carries an `imp:` id, so it was handed back to issuing (which tried to issue it again, caught by the rerun test) and would have been handed back to matching and deduplication to work a second time. It now selects on `state`: the prefix says where a row came from, the state says what it is now
- [x] 3b.4 Moved that helper out of `routers/import_api.py` into `sheet.py` as `source_rows`. A service module must not import from a router, and duplicating the definition of which rows are source rows in two places is exactly the drift that caused 3b.3

## 5. Frontend: the action

- [x] 5.1 Add the API calls to `frontend/src/api.ts`
- [x] 5.2 Add the action to the Fencers phase (`IssuePanel.tsx`), offered only once dedup has concluded and stating plainly why it is unavailable otherwise, as `IntakePanel` does for a missing Fio token
- [x] 5.3 Confirmation before it runs, stating the number of rows and that no mail will be sent — a static confirmation, per the design prohibitions
- [x] 5.4 Report the outcome afterwards: issued, already had one, skipped with reasons
- [x] 5.5 Refresh the sheet when it concludes, so the `outstanding` column fills without the organizer reloading
- [x] 5.6 Czech and English strings for the action, its unavailable reason, its confirmation and its report
- [x] 5.7 Tests (`issuePanel.test.tsx`, 7): the action is absent while dedup is pending and says why; the confirmation states the count and the no-mail promise; the report renders each outcome

## 6. Verification

- [x] 6.1 `pytest` 926 passed, `ruff check .` clean
- [x] 6.2 `vitest` 301 passed, `npm run lint` and `npm run build` clean
- [x] 6.3 Trialled against the pilot **on a copy of the database**, not on the live one: the action allocates variable symbols that are never reclaimed, so the owner runs it on their own data from the console. 53 rows pending, **51 issued**, 51 distinct variable symbols, every one dormant with no due date and every placement seated, no zero totals, **47 700 CZK** owed in total (42 900 before 7.2, the difference being the five fencers capacity was writing off). Two findings below
- [ ] 6.4 Confirm the 43 waiting transactions become linkable — a manually typed VS now resolves where it previously answered `404 unknown_vs`. Waits on the owner running 6.3 for real
- [ ] 6.5 Run the lifecycle passes by hand against the pilot afterwards and confirm no mail is sent and nothing expires. Waits on 6.3; covered by tests in the meantime

## 7. Found by the pilot trial

- [x] 7.1 **`Registration` is unique on (tournament, fencer)**, which no test had exercised. The pilot has one e-mail address covering *three different fencers* — Milan Diviš entered himself and both Pekáreks — so they resolve to one fencer record and only the first can be issued. The pass now asks before inserting rather than catching the `IntegrityError` after, which was indistinguishable from a variable-symbol collision and would have spent five symbols discovering the row could never be issued. Reason reported as `email_taken`, phrased about the address rather than calling the row a duplicate, because on a real roster this is usually one person entering several others
- [x] 7.3 **`clear_imports` let an issued registration outlive its row.** The clear asserts no file was ever uploaded — "no batch, no source row … survives it" — but a registration issued for a cleared row survived, and being drawn under that row's id kept the fencer in the table after a total clear. Issued registrations are now deleted with their rows, children first and explicitly (SQLite has no cascade here); a transaction that had been linked to one returns to the unresolved queue rather than vanishing. The clear is **refused** where such a registration holds credit, mirroring `delete_tournament`'s rule that financial history is never deletable
- [x] 7.2 **Capacity applied to the roster and left five fencers owing nothing.** The pilot's SA holds 42 against 48 entrants and SB 28 against 30, so eight placements queued — and a substitute placement is not billed. **Owner decision: capacity does not apply to an imported roster; everyone is seated.** A fencer list records who competed, not who applied, and the fencers on it were admitted by whoever ran the event. Every issued placement is now seated, issuing may leave a discipline over capacity, and that capacity keeps governing everyone who registers afterwards (design Decision 7)
