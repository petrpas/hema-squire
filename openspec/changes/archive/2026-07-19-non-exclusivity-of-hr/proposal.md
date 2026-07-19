## Why

The system enforces one account per HEMA Ratings profile (DB unique constraint + 409 on signup and Profile binding), but a claim is just a self-declared, unverified assertion — we have no way to check that the person claiming a profile is really that fighter. Enforcing exclusivity on unverifiable claims lets the first claimant (even a mistaken or malicious one) lock out the profile's real owner, and gives the rejected fencer a dead end ("directed to account recovery") that does not exist.

## What Changes

- **BREAKING** (behavioral): binding an hr_id already claimed by another account is no longer rejected — signup and Profile binding succeed; the `hr_id_already_bound` 409 and the DB unique constraint on `fencers.hr_id` are removed (migration).
- The fencer is warned, not blocked (per owner decision): HR search candidates indicate when a profile is already claimed by another account, so an honest user can realize they may already have an account — but they may proceed.
- The admin accounts list flags accounts whose hr_id is shared with another account (per owner decision); resolution remains the existing admin hr-unbind action.
- Fencer-side write-once binding is unchanged: an account that has an hr_id still cannot rebind a different one; only admins unbind.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fencer-accounts`: the "One account per HR identity" requirement is replaced by non-exclusive claims — duplicate claims are allowed with a visible warning to the fencer and a duplicate flag for admins; the account-creation requirement loses its implied rejection of already-bound profiles.

## Impact

- Backend: drop the unique constraint on `fencers.hr_id` (alembic migration); remove the two 409 `hr_id_already_bound` checks (signup, bind); add a `claimed` indicator to HR search results; add a shared-hr flag to the admin accounts listing. Tests updated.
- Frontend: HR candidate list and confirmation show the "already claimed" notice (signup window and Profile page); `hr_id_already_bound` error mappings and i18n keys removed/replaced; admin panel accounts table shows the duplicate flag.
- No impact on tournament registration, rating snapshots (keyed by hr_id independently of accounts), or exports.
