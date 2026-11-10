## Why

A fencer cannot delete their account, and nobody can give a truthful answer to what would happen to their data. Fifteen foreign keys point at `fencers`, several of them mandatory, and copies of a person's address sit in imports, rules, journals and the mail outbox with no link to the account.

## What Changes

- An account holder can request deletion from the Profile page, confirmed by password and after seeing the impact. It takes effect after 7 days, during which it can be withdrawn.
- On execution the account stops existing as a login: address, password, language, sessions, profile audit, pending resets and organizer requests go. Its address is removed from the copies that can be found by that address.
- **The name, HR ID, club and nationality stay on rosters of held tournaments.** The record becomes the existing credential-less fencer record. Where no held roster lists the person, those fields are blanked too.
- Registrations on tournaments not yet held are cancelled. The organizer is told, and credited money is stated so they can settle it outside Squire.
- Deletion is refused while the person owns a tournament, is the last Admin, or is the Deployment Owner.
- A deleted account's row shows no Paid mark on a held roster.
- An Admin can erase a person's identity from a record on request, for an upheld objection or a request from someone without an account.
- A log without personal data lets a point-in-time restore reapply erasures.
- **BREAKING (spec)**: the rule journal stops being strictly append-only, since a personal address inside it can be redacted. A failed outgoing message may be deleted.

## Capabilities

### New Capabilities

- `account-deletion`: request, grace period, execution, what is removed and kept, refusals, Admin erasure and restore.

### Modified Capabilities

- `public-entrants`: a deleted account's row states no payment.
- `profile-page`: the Profile page gains a Privacy tab holding the data download, accepted organizer terms and deletion.
- `edit-rules`: the meta-journal may have a personal address redacted.
- `outgoing-mail`: a message about an erased person may be deleted.

## Impact

- `backend/app`: new `account_deletion.py`, `Fencer.deletion_requested_at` and `Fencer.deleted_at`, new `account_erasures` table, routes in `routers/accounts.py` and `routers/admin.py`, a pass in `scheduler.run_tick`, roster answer in `entrants.py`, shared-HR computation in `routers/admin.py`, `export_json.py`.
- `frontend/src`: `profile/` dialog, `admin/` marking and erasure, `api.ts`, locale keys.
- `deploy/restore.sh` and a new script under `scripts/`.
- New mails: request received, withdrawn, completed, and an organizer notice.
- Depends on `privacy-baseline` being live and on `extend-admin-console` being archived, since it builds on the admin tabs.
