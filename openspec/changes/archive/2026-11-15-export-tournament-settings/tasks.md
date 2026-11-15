## 1. Source row uniqueness

- [x] 1.1 Replace `unique=True` on `Registration.source_row_id` with `UniqueConstraint("tournament_id", "source_row_id")` and write the Alembic revision (design D3)
- [x] 1.2 Test: the same imported row issued in two tournaments creates two registrations

## 2. Export

- [x] 2.1 Raise `SCHEMA_VERSION` to 24
- [x] 2.2 Add the tournament settings to `_TOURNAMENT_FIELDS`: `registrations_kept_by`, `payment_mode`, `deposit_amount`, `deposit_amount_eur`, `seating_deadline`, `seating_settled_at`, `amendments_close`, `expiry_grace_hours`, `external_registration_url`, `feature_payments`, `feature_teams`, `feature_extras`, `feature_schedule`, `subtitle`, `short_code`, `logo_tint`, `cover_tint`, `hr_category_map`
- [x] 2.3 Add `clocks_dormant`, `source_row_id`, `contact_email` to `_REGISTRATION_FIELDS`
- [x] 2.4 Check `_record` serialises the enums, dates and the datetime as the restore parses them

## 3. Restore

- [x] 3.1 Parse the new dates and `seating_settled_at` as the existing ones are parsed
- [x] 3.2 For `version < 24`: set `registrations_kept_by = organizer`; default `clocks_dormant`, `source_row_id`, `contact_email` on registrations (design D2)
- [x] 3.3 Rewrite a `man:` `source_row_id` through `man_map`; carry `imp:` over (design D3)
- [x] 3.4 Update the module docstring and the restore requirement comment to name what stays out

## 4. Tests

- [x] 4.1 Manual tournament with issued registrations round-trips as manual, dormant, rows unduplicated in the sheet
- [x] 4.2 Deposit mode, deadlines, features and `seating_settled_at` round-trip
- [x] 4.3 Tints, subtitle, short code round-trip; logo and cover photo do not
- [x] 4.4 Guest contact address round-trips; the old manage link does not open the restored registration
- [x] 4.5 A v23 document restores manual and its publication is refused without an external address
- [x] 4.6 A restored copy beside its original on one deployment succeeds; a taken series is replaced, a taken VS refuses with 409 (design D6)
- [x] 4.7 Existing older-version restore tests still pass

## 5. Finish

- [x] 5.1 `uv run ruff check .`, `uv run basedpyright`, scoped pytest over the export tests
- [x] 5.2 Mark V3 done in the drift map
