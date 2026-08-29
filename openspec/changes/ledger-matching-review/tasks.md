## 1. The evidence register on the row

- [x] 1.1 Remove the proposal overlay from `_imported_rows` in `backend/app/sheet.py` (the block at 232-237): a stored `hr_match` decision no longer writes `name`, `club`, `nationality` or `reg_name`. It supplies `hr_id` and the new evidence fields only; verify with a test that a row with a proposed match still reports the registered name, club and nationality
- [x] 1.2 Carry `hr_name`, `hr_nationality` and `hr_club` on every row shape `sheet.py` builds — imported, registered, manual — beside the existing `hr_id`; the row without a match or an id carries them as `None`
- [x] 1.3 Fill the evidence fields for rows bound by an id rather than a proposal, from the fighters index by `hr_id` per design D4; verify with a test that a fencer-supplied `hr_id` yields HR name, nationality and club, and that an id absent from the index yields a confirmed row with empty evidence
- [x] 1.5 State the evidence register's nationality as an ISO code per design D4a: one `evidence_fields` used by both the sheet projection and the resolution enrichment, and the stored payload resolved again on replay so a rule recorded before the codes still reads as one; the code being the two-letter alpha-2 a registration is written in; verify with tests that an index spelling "Poland" yields "PL", that an old-shape payload spelling "Germany" yields "DE", and that every resolved code is two characters
- [x] 1.4 Add `hr_name`, `hr_nationality`, `hr_club` to `SheetRow` in `frontend/src/api.ts`

## 2. The derived tier

- [x] 2.1 Add a name key to `backend/app/hr_index.py` — a name's words each folded, sorted, so word order does not distinguish — and a lookup answering how many fighters carry a key and returning them; index by the key so the ambiguity veto sees "Jan Novák" and "Novák Jan" as one key; verify with unit tests over an index holding one, two and zero fighters under a key, and that the two orderings collide
- [x] 2.2 Add the tier derivation to `hr_match.py` per design D1 — name keys equal, nationality absent or equal, name key unambiguous — returning `found` or `proposed` for a decision that carries an `hr_id`; verify with unit tests per condition, including that a differing club does not demote (spec table-import, Differing club does not demote an exact hit) and that "Novák Jan" against "Jan Novák" reads found (spec, Surname-first registration)
- [x] 2.6 Resolve both nationalities to an ISO 3166 country before comparing them, per design D1: add `pycountry`, a `country_code` reader over codes and English names, and the alias list for the names ISO records differently ("Russia", "Turkey", "Palestine"); an unresolvable spelling contradicts nothing. Verify with unit tests that "PL" and "Poland" agree, that the aliased three resolve, and that an unidentifiable country demotes nothing
- [x] 2.3 Test that an ambiguous name key yields `proposed` however exact the match (spec, Two fighters share a name key), that a name carrying a word the other does not reads `proposed` (spec, An extra given name is a difference), and that an unavailable index degrades to `proposed` rather than to `found`
- [x] 2.4 Call the derivation from `_imported_rows` where `verdict = "proposed"` is set today; verify with a test that decisions stored before this change take a tier on the next read with no matcher invoked (spec, Existing decisions take a tier without a rerun)
- [x] 2.5 Add `found` to the settled verdicts `_pending_rows` skips in `hr_match.py:160`, and to the `match_verdict` union in `frontend/src/api.ts:387`

## 3. Canonical naming follows the verdict

- [x] 3.1 Move canonical promotion into `_apply_match_resolution` in `backend/app/rules.py` per design D3: a resolution binding an `hr_id` sets the row's `name` to the profile's canonical name and preserves the original in `reg_name`; verify with a test that confirming a proposal promotes the name and that the original stays retrievable (spec hr-integration, Name normalization)
- [x] 3.2 Test that an unratified proposal leaves the registered name, club and nationality untouched on every phase, not only Matching (spec hr-integration, Proposal does not normalize)
- [x] 3.4 Apply a resolution's consequences without auditing them, per design D3a — the promoted name, the displaced `reg_name` and the evidence register are the verdict's consequences, not further decisions — so one confirmation reads as one entry; verify with a test that a ratification promoting a name leaves exactly one log entry for the row
- [x] 3.3 Check the audit suppression at `rules.py:164-166` still holds with promotion added — the resolution's own fields stay out of the log, the promoted name appears once; verify against `ManualEditsRail` expectations in the existing tests

## 4. The Matching table

- [x] 4.1 Add `hr_name`, `hr_nationality`, `hr_club` to `PHASE_COLUMNS.matching` in `frontend/src/Console.tsx:89`, phase-owned so they appear on Matching only, with `column.*` keys in both locales
- [x] 4.2 Add the `found` verdict to the badge in `Console.tsx:464-476` — `tag-seal-green` with its own word, distinct from `confirmed` — and the `match.verdict.found` string to `cs.json` ("nalezená shoda") and `en.json` ("found match"); add it to `VERDICT_KEYS` in `ManualEditsRail.tsx:16`
- [x] 4.3 Make the verdict cell ratify per design D5: click accepts on `proposed` and `found`, a separate control opens the search, and on `unknown`/`none_found` the badge opens the search as today; verify with component tests per verdict that the right action fires
- [x] 4.4 Route `hr_id` edits to `match_resolution` in `saveEdit` (`Console.tsx:290`) per design D6, an emptied cell resolving to no profile; verify with a test that typing an id leaves the row confirmed and promotes the name, and that clearing it leaves the row as having no profile (spec etl-console, A typed id is a verdict)
- [x] 4.5 Confirm the ten-column Matching table scrolls rather than overflowing, and that the HR columns are absent from every other phase

## 5. The dialog and the count

- [x] 5.1 Strip `MatchDialog` to the search it alone can do — the comparison now lives on the row — keeping "Profil neexistuje" and seeding the query from the registered name rather than a promoted one; verify the seeded query is the fencer's own name on an unratified row
- [x] 5.2 Test that the search opens from a row already reading `found` or `confirmed` and that selecting an alternative supersedes the earlier verdict (spec etl-console, Settled rows are still revisable)
- [x] 5.3 Add the outstanding count to `MatchPanel` beside `runResult`, counting rows owing a verdict, in the shape `DedupPanel` already uses (`rail-count`); verify it falls as rows are ratified (spec etl-console, The queue is countable)

## 6. Whole-flow verification

- [x] 6.3 Check the live fighters page for a country code of its own before settling on a derived one, per design D4b: compare the flag element's code against the code derived from the country name over every indexed fighter, and alias to `GB` whatever the page and the fencers call the United Kingdom

- [x] 6.1 Extend `backend/tests/test_hr_integration.py` with a run over a roster mixing an exact hit, a transliteration, an ambiguous name, a fencer-supplied id and a no-match, asserting the five verdicts and that the claim register survived all of them
- [x] 6.2 Run the app and walk Matching on an imported table: yellow only where the row and the profile visibly differ, one click drains a row, a typed id drains a row, the count falls to zero
