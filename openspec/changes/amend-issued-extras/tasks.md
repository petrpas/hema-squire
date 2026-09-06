## 1. Backend: the kind becomes general

- [x] 1.1 Rename the rule kind to `registration_amendment` in `rules.py`, its handler, `rules_api.py` and the tests that name it; the kind carries the field it amends and validates it against the fields that may be amended (`disciplines`, `weapon_rentals`)
- [x] 1.2 One Alembic revision migrating stored `discipline_amendment` rules to the new kind, reversible on downgrade — an unmigrated rule stops being replayed and leaves a total nothing explains
- [x] 1.3 `amendments_for` and `issued_selection` answer per field: the amendments standing against this field of this row, and what the registration was issued with for that field
- [x] 1.4 `base` is recorded on the first amendment of each field and read from the earliest amendment of that same field

## 2. Backend: amending what a registration borrows

- [x] 2.1 A rentals amendment passes the whole extras set to `apply_amendment`: the registration's non-rental selections unchanged, plus one selection per named rental item the tournament lends
- [x] 2.2 The legacy `weapon_rentals` list is written to match through `fields`, including any name nothing lends — it is what the fencer list and the confirmation mail read
- [x] 2.3 A name the tournament lends nothing by is accepted, billed nothing, and left in the list for `pricing.unpriced_rentals` to name (design D4)
- [x] 2.4 A `weapon_rentals` field edit is refused where a registration stands behind the row, as a disciplines field edit already is
- [x] 2.5 `reapply_amendments` rebuilds every amendable field at once — last amendment standing per field, issued value for a field with none — because `apply_amendment` states a whole registration

## 3. Backend: the problem the row states

- [x] 3.1 The unpriced names stay data on the row (`unpriced_rentals`); no sentence is composed in `sheet.py` (design D5)
- [x] 3.2 A registration row carries its parse problems as before and its unpriced rentals as well, so the two can be shown together

## 4. Backend: the properties that matter

- [x] 4.1 **The money follows the item.** Adding a rental to an issued registration on an itemized tournament raises its total by that item's price, and the selection is there to explain it
- [x] 4.2 **Two fields, one row.** Amend disciplines, then rentals; assert both stand and the total accounts for both. Then withdraw the disciplines amendment and assert the rentals amendment survives it — the test a per-row (rather than per-field) replay fails
- [x] 4.3 **Other extras are not collateral.** A registration holding an afterparty selection keeps it, and keeps it priced, through a rentals correction
- [x] 4.4 **Early bird survives the correction**, as it does for disciplines: the correction prices at the registration's own moment
- [x] 4.5 A rentals correction that costs the fencer mails the surcharge notice once; one that lowers the price mails nobody
- [x] 4.6 An unlendable name is applied, bills nothing, and appears in the row's unpriced rentals
- [x] 4.7 A `weapon_rentals` field edit against a row with a registration is refused
- [x] 4.8 The existing discipline-amendment tests pass unchanged but for the kind's name — they are the guard on the generalization

## 5. Frontend

- [x] 5.1 `editableHere` opens `weapon_rentals` on the fencer list; `ruleKindFor` returns the amendment kind where the row has a registration and `field_edit` where it does not
- [x] 5.2 The cell's draft is the item names joined by commas, and saving parses on commas — names hold spaces, so nothing else separates them
- [x] 5.3 `problems` joins the fencer list's columns, and the marker's text names the unpriced items before any parse problem the row carries
- [x] 5.4 Czech and English strings for the problem's sentence and for the edit's refusals
- [x] 5.5 Tests: the cell opens on an issued row; the edit sends the amendment kind with the parsed list; the problem marker names an unpriced item on the fencer list

## 6. Verification

- [x] 6.1 `pytest` and `ruff check .` clean; the fencer's own amendment tests untouched
- [x] 6.2 `vitest`, `npm run lint` and `npm run build` clean
- [ ] 6.3 Against the pilot roster: correct a rental on an issued registration and confirm the fencer list, the outstanding column and the export all state the same thing afterwards
