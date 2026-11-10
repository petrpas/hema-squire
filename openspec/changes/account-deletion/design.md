## Context

`Fencer` is both a login and a person on a roster. Spec `fencer-accounts` already allows a record with no credentials and no address; `_take_over` turns such a record into an account only by matching address. Payment journals name actors as `Name <address>` text, not foreign keys. Rosters read names through the rows pipeline, with organizers' corrections held as rules.

The owner decided that names and HR IDs stay on rosters, with club and nationality, and that the Paid mark is hidden on those rows. See `privacy-baseline` for the legal basis.

## Goals / Non-Goals

**Goals:**
- One function that takes an account to the retained state, idempotent and in one transaction per account.
- Every personal column either handled or explicitly classified, enforced by a test.
- Truthful impact shown before anyone commits.

**Non-Goals:**
- Reaching organizers' Sheets, downloads or printed rosters.
- Automatically deciding that a free-text name match is the same person. Name-only copies are handled by Admin erasure, with a human deciding.
- Time-based cleanup of data unrelated to a deletion: `data-retention`.
- Self-service deletion for guests and organizer-entered people: they use the request channel and Admin erasure.

## Decisions

### D1. Demote to a credential-less record, never delete the row

Mandatory foreign keys and the ledger need the row, and rosters need the name. A blank tombstone was the earlier idea; the owner's decision makes the existing record kind the natural result, with no new concept for rosters to understand. Because `Fencer.email` becomes NULL, `_take_over` cannot reattach the record: a later signup with the same address is a new, unlinked account.

`deleted_at` distinguishes this record from an ordinary credential-less one, for the Paid mark, the shared-HR computation and the admin list.

### D2. Retain identity only where a held roster needs it

If the person has a live registration on a tournament dated before today (by the `day-boundaries` public list boundary), name, HR ID, club and nationality stay. Otherwise they are blanked and `display_name` becomes the fixed label for a deleted account, since no decision justifies keeping them. The organizer notice is what carries the name for settling a cancelled paid entry.

### D3. Grace period is a timestamp and a scheduler pass

`deletion_requested_at` is set after password confirmation. The account works normally for 7 days, because withdrawing needs a session. A pass in `run_tick` executes accounts past the deadline, each in its own try and commit so one failure cannot strand the rest. This runs outside `tournaments_to_tick`.

A blocker that arose during the grace period stops execution, keeps the request pending and shows it in the Admin's pending tasks, rather than silently leaving a tournament without an owner.

### D4. Tournaments today or later are cancelled through `cancel()`

Reusing `cancel()` frees seats and stops clocks by the same path as every other cancellation. A tournament dated today counts as not yet held. `refundable_until` cannot be set, so `cancel()` will normally leave no pending refund; the organizer notice therefore states the credited amount and VS independently of refund state. Whether money is returned stays the organizer's decision, as it is today. Promotion is untouched: a freed seat waits for the organizer.

### D5. Copies are found by exact address

At execution the address is searched for as a whole value in `ImportedRow.raw`, `ManualRow.email`, `Rule.payload`, `RuleJournalEntry.content`, own `Registration.contact_email` and `OutgoingMail.recipient`, and in the `<address>` part of `recorded_by`, `reversed_by`, `granted_by` and `revoked_by`. Journal labels become the name alone, so accountability stays. All earlier addresses from the audit trail are searched as well, before it is deleted.

Own registrations also lose `notes` and `accommodation`. Another person's seat that uses this address as `contact_email` is left: it is that seat's working contact, and a parent's deletion must not silently cut a child off. `data-retention` clears it in time.

### D6. Final mail outlives the scrub briefly

The completion notice is queued after the scrub, so its one outbox row carries the address until `data-retention` removes it. Sending nothing would leave the person unsure, and a special delete-on-send path is more machinery than a bounded window warrants.

### D7. Admin erasure is the same module, one level further

`erase_identity(record)` blanks name, HR ID, club and nationality on any record, removes that record's name-correcting rules and redacts the journal copies. It does not touch money. A held roster then shows the deleted label. It is a deliberate Admin act with confirmation, and covers upheld objections and requests from guests.

### D8. Restore replays a log

`account_erasures` holds only the fencer id, kind and moment. A restore to an earlier point would resurrect people, so the restore script first reads this table from the latest replica and reapplies it to the restored database. No external store is needed for the point-in-time case. After a total replica loss there is nothing old to resurrect from.

### D9. A metadata test keeps the map honest

A test walks `Base.metadata` and fails on any `String`, `Text` or `JSON` column absent from a classification: removed, redacted, kept with a reason, or not personal. It is the same guard idea as `test_tournament_delete.py`, extended from foreign keys to content.

## Risks / Trade-offs

- A name stays linked to payment history → disclosed; never called anonymised; `data-retention` shortens bank text.
- A free-text mention of the address in a note of someone else's row is not found → only exact values are matched; disclosed by the classification and solvable by Admin erasure.
- Roster order remains paid first, so a hidden Paid mark can be partly inferred → accepted for held rosters.
- Paid-mark hiding depends on `deleted_at` surviving a JSON export and restore → covered by a task.
- A fencer on the tournament day loses their entry → the impact dialog states it, and 7 days of notice precede it.
- The Sheet still holds the person → stated in the dialog and the organizer terms.

## Migration Plan

Add nullable columns and the table. Deploy with no accounts affected, since the pass only finds requested deletions. Rollback before any execution is trivial; an executed deletion cannot be rolled back except from backup, by design.

## Open Questions

- The fixed label's wording in both languages.
- Whether the lawyer requires anything further for retained rosters; a change there only alters D2.
