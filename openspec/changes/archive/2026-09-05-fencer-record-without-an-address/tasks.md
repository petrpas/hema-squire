## 1. The mail boundary, first

Before the column can hold NULL, the one place that would post it has to refuse.
Done first so that no intermediate commit can send a message with no recipient.

- [x] 1.1 `mail.build_message` raises on a falsy `to` — not a skip, not a log
  line. A message with no recipient is a programming error, and every function
  in `emails.py` sends something a person is meant to receive, so a version that
  quietly sends nothing is the worse bug (design Decision 3)
- [x] 1.2 Tests in `tests/test_mail_delivery.py`: `build_message` refuses an
  empty and a None recipient, and the refusal names what was attempted well
  enough to find the caller
- [x] 1.3 Walk every `emails.py` entry point against a fencer holding no
  address and assert the refusal reaches the caller. Fifteen call sites, one
  test each or one parametrised over them — the point is that the boundary is
  exercised, not that the fencer happened to be dormant. A test asserting
  `clocks_dormant` proves nothing here (design Risks)

## 2. The column

- [x] 2.1 `Fencer.email` becomes `Mapped[str | None]` in `models.py`, keeping
  `unique=True` — NULL is not equal to NULL in either SQLite or Postgres, so the
  index admits any number of them (design Decision 5)
- [x] 2.2 Alembic migration dropping the NOT NULL. No backfill: every existing
  row has an address. Note in the migration that the reverse fails once a record
  created under this change exists, so it is one-way in practice
- [x] 2.3 Restate `TeamMember`'s docstring (`models.py:1134`), which rests design
  team-disciplines D4 on "`Fencer.email` is unique and non-nullable". Half of
  that stops being true; the reason that survives is already in the same
  docstring — identity is local to the roster, and two rosters naming the same
  person produce two independent rows

## 3. Issuing

- [x] 3.1 `_resolve_fencer` creates a record with `email=None` for a row that
  carries none, rather than returning None; `NO_EMAIL` goes
- [x] 3.2 An address is claimed once (design Decision 2). `EMAIL_TAKEN` goes;
  the pre-insert probe **stays**, because it turned out to be answering a second
  question the design had not separated: a registration is unique per
  (tournament, fencer), so a row whose address belongs to somebody who
  registered in the application has nothing to issue. That is not a skip — there
  is nothing wrong with the row — so it is counted as one the pass left alone
  (`ALREADY`), which is what `report.already` means
- [x] 3.3 `would_skip` follows the pass: the e-mail claims it tracked across the
  walk stop being a reason, and the two remaining reasons are `no_name` and
  `no_discipline`. Its faithfulness to `issue` is what the existing test
  `test_the_dry_run_agrees_with_what_the_pass_then_does` holds it to
- [x] 3.4 Delete the `NO_EMAIL` and `EMAIL_TAKEN` constants and the module
  docstring's paragraph explaining the address collision
- [x] 3.5 Tests: two rows of one list sharing an address both issue, the first
  record carries it and the second carries none; a row with no address issues; a
  row whose address belongs to an existing account reuses that record with its
  name, credentials and HR binding untouched; `no_name` and `no_discipline` are
  still refused and still named

## 4. The readers

Each is checked for None-tolerance and made to state absence rather than render
it. The exports matter most: a column reading `None` in a file an organizer
sends onwards is a defect that leaves the building.

- [x] 4.1 `auth.py` — a login is looked up by address; confirm a NULL row cannot
  be reached by any credential path, and that the lookup cannot match on None
- [x] 4.2 `routers/accounts.py:66` — the signup and profile-edit uniqueness
  probe. An address being taken is still an address being taken; confirm the
  probe is unaffected by rows holding NULL
- [x] 4.3 `export_json.py` — **the defect the design predicted would leave the
  building, and worse than a `None` in a cell.** The whole round trip was keyed
  on the address: `{r.fencer.email: r.fencer}` collapsed every addressless
  record onto one `None` key, so a tournament holding three exported one fencer
  and pointed all three registrations at whichever survived; the restore then
  looked rows up by an address that matches nothing in SQL. Schema 12 carries
  `ref` on each fencer and `fencer_ref` on each registration, and the restore
  prefers it, falling back to the address for a document written earlier
- [x] 4.4 `sheet.py`, `routers/admin.py`, `routers/manual_api.py`,
  `routers/registrations.py`, `routers/tournaments.py` — read and fixed. Three
  output schemas declared `email: EmailStr` for a fencer that can now hold none:
  `AdminAccountOut` was the live one — the admin listing selects *every* fencer
  record, so it would have failed validation the moment one existed —
  and `TeamMemberOut` and `PleaQueueOut` are guarded on the same ground
- [x] 4.5 Tests for whichever of the above render a fencer: an addressless
  record appears with an empty address and nothing else changed

## 5. What the console says

- [x] 5.1 `i18n/{cs,en}.json` lose `issue.reason.no_email` and
  `issue.reason.email_taken`
- [x] 5.2 `api.ts` — narrow the skip reason if it is typed as a union; the
  surfaces that name skipped rows need no other change, having fewer to name
- [x] 5.3 Checked, and it was **not** true: `no_name` was fixable in the table,
  `no_discipline` was not. The owner's answer was to make disciplines editable
  (section 7), after which the sentence is true and says where — "until the row
  is corrected on the Fencers phase" 
- [x] 5.4 `vitest` for the strings that remain

## 6. Verification

- [x] 6.1 `pytest`, `ruff check .`
- [x] 6.2 `vitest`, `npm run lint`, `npm run build`
- [x] 6.3 The pilot, on a copy: 51 issued and 2 pending before, **53 issued and
  0 pending after**, both Pekáreks among them, both records holding no address,
  no zero totals, 49 550 CZK owed, no variable symbol allocated and
  `vs_next_seq` still 1 (a manual tournament mints none), all 53 dormant with no
  due date. The lifecycle passes then ran against it and built **no message at
  all** — the risk this change turns on, checked against real data rather than
  against a fixture
- [x] 6.4 Both Pekáreks are in the link dialog's roster, beside Milan Diviš —
  the surface this was found missing from

## 7. Correcting a row's disciplines (owner decision, follow-on to 5.3)

A row that entered no discipline cannot be issued, and the console named a
remedy it did not offer. Editable on the fencer list **and nowhere else**.

- [x] 7.1 `ROW_ONLY_COLUMNS` — a set beside `EDITABLE_COLUMNS`, for a column a
  row owns only while it is still a row. `editableHere` takes the row to decide
  it, so disciplines open on the Fencers phase and only where
  `registration_id` is null: an issued registration's entries decide what it is
  billed and where it is seated, and a cell edit would move the table without
  moving the money
- [x] 7.2 `parseDisciplines` reads slugs out of the typed text — commas,
  semicolons and spaces alike, duplicates dropped, the slug's own case kept
  because a slug is an identity rather than a word. `SheetArea` edits the cell
  as the text it is shown as, so an untouched draft round-trips to itself
- [x] 7.3 The edit becomes a list in the rule payload, not the text it was typed
  as: the row's own shape, which pricing, seating and issuing all read
- [x] 7.4 `cellCheck` refuses an emptied cell (`required`) and an unknown slug
  (`bad_enum`), both from the existing closed code set
- [x] 7.5 **Server-side too**, in `rules.create_rule`: a `field_edit` on
  `disciplines` must carry a non-empty list of slugs the tournament offers as
  individual disciplines. Not merely a mirror of the client check — issuing
  filters unknown slugs out silently, so without this the organizer would meet a
  typo as a row that mysteriously will not bill
- [x] 7.6 Tests: a row given a discipline then issues; a corrected row is priced
  for what it now enters; an unknown slug and an empty list are refused; the
  cell opens on Fencers while the row is a row, closes once a registration
  stands in its place, and opens on no other phase

## 8. What the pilot found (2026-09-05)

- [x] 8.1 **An address was reused as an identity, and it is not one.** The first
  run issued one of the two brothers, not both: `_resolve_fencer` matched
  Jindřich Pekárek's row to the record holding `divis.m9@gmail.com` — which is
  **Milan Diviš**, their father, himself on the roster — found he already had a
  registration, and left Jindřich off the list entirely under `already`.

  Decision 2 said a row whose address a record already holds reuses that record.
  That is right where the address names the person and wrong where it names the
  payer, which is the whole case this change exists for. An existing record is
  now reused only where its name agrees with the row's, compared with the
  fighters index's own key — diacritics, case and word order disregarded, and
  not a subset test, so "Novák Jan" is Jan Novák and "Jan Petr Novák" is not.
  Otherwise the row gets its own record with no address.

  Two tests: the pilot's own shape — father and two sons on one address, three
  people and three records — and its converse, a row whose address belongs to
  the fencer it names, reused whatever spelling the roster used
