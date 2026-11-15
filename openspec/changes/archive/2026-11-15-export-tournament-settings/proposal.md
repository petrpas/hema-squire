## Why

The canonical JSON document promises round-trip fidelity, but it carries none of
the settings that decide what Squire does with a tournament: its mode, its
payment mode and deposit, its deadlines, its features, and on each registration
whether its clocks are dormant. A manual tournament restored from it comes back
automatic with live clocks, and once published the scheduler would start
windows, reminders and expiries against people who were never meant to receive
them. Found as V3 in the spec-vs-code drift map of 2026-11-12.

## What Changes

- The document (schema version 24) carries the tournament's settings:
  `registrations_kept_by`, `payment_mode`, `deposit_amount`,
  `deposit_amount_eur`, `seating_deadline`, `seating_settled_at`,
  `amendments_close`, `expiry_grace_hours`, `external_registration_url`,
  the four `feature_*` flags, `subtitle`, `short_code`, `logo_tint`,
  `cover_tint` and `hr_category_map`.
- Each registration carries `clocks_dormant`, `source_row_id` and
  `contact_email`. A `man:` source row id is rewritten to the restored manual
  row, as rule targets already are; an `imp:` one carries over as it stands.
- The logo and the cover photo stay out of the document; the organizer uploads
  them again (owner decision 2026-11-15).
- A document older than v24 says nothing about the mode and restores as a
  **manual** tournament: Squire runs nothing against it, and it cannot be
  published until someone gives it an external registration address, which is
  a decision about the mode.
- Still out by design, and now stated: owner, publication moment and author,
  cancellation moment, bank feed token, export destination, retention stamp and
  guest link generation.
- `registrations.source_row_id` becomes unique per tournament rather than
  across the deployment, so a restore beside the original, or the same file
  imported into two tournaments and issued in both, no longer collides.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `data-export`: the canonical document carries the tournament's settings and
  each registration's dormancy, source row and contact address; an older
  document restores as manual.

## Impact

- `backend/app/export_json.py`: field lists, `SCHEMA_VERSION`, the pre-v24
  defaults, the `man:` rewrite of `source_row_id`.
- `backend/app/models.py` and an Alembic migration: the uniqueness of
  `registrations.source_row_id`.
- `backend/tests/`: export round-trip tests.
- No API shape change and no frontend change. Documents written before this
  change still restore.
