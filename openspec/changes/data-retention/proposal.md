## Why

Nothing in Squire ages out. The sent-mail table grows without limit with every recipient and subject, and bank rows keep payers' names, account numbers and messages indefinitely, even though storage limitation (Article 5) applies with or without an erasure request. The privacy page has to state periods that are actually enforced.

## What Changes

- Sent and failed outgoing messages are deleted 30 days after they finished. Expired signups and password resets are deleted.
- **12 months after a tournament's date**, its bank rows lose payer name, account, message and every other free-text field. Amounts, dates, variable symbols, matching status and the bank's transaction id stay.
- At the same moment, addresses and free-text personal details are removed from that tournament's import rows, manual rows and registrations, including contact addresses, notes and accommodation.
- Names on rosters are not touched by any period.
- **BREAKING (spec)**: outgoing mail records are no longer kept forever, including failed ones.

## Capabilities

### New Capabilities

- `data-retention`: the periods, what each one removes and what it leaves.

### Modified Capabilities

- `outgoing-mail`: a finished message is deleted after 30 days.

## Impact

- `backend/app`: new `retention.py`, a pass in `scheduler.run_tick`, `Tournament.personal_data_pruned_at` with a migration.
- Organizer payments console: text of old bank rows disappears. The organizer terms from `privacy-baseline` state this, and it has to be live first.
- Rows, exports and rosters of old tournaments must keep working with the blanked fields.
- Builds on the `outgoing-mail` delta in `account-deletion`.
