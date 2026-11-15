## Context

`export_json.py` writes and reads the canonical document through two field
lists, `_TOURNAMENT_FIELDS` and `_REGISTRATION_FIELDS`. Since `e0a7806` a restore
reads back only what those lists name, which closed the hole where a document
could set an owner or a feed token. It also made plain what the lists omit:
every setting added since roughly v17 was never added to them, so a restore
falls back to model defaults: automatic, payments off, immediate payment,
no deadlines, clocks running.

A restore is Admin work and lands as a draft without an owner. It exists for
recovering a deleted tournament, moving one between deployments, and taking a
production tournament onto a development machine. It is not disaster recovery;
Litestream is.

## Goals / Non-Goals

**Goals:**
- A restored tournament behaves as the exported one did once it is published
  again.
- An older document can never restore into a tournament that starts clocks.
- A restore beside the original on the same deployment succeeds.

**Non-Goals:**
- Images in the document (owner decision 2026-11-15).
- Carrying deployment-bound state: owner, publication, cancellation, feed
  token, export destination, retention stamp, guest link generation.
- Any change to the Sheets export.

## Decisions

### D1. Add to the field lists, not a second channel

The new fields join `_TOURNAMENT_FIELDS` and `_REGISTRATION_FIELDS`, so the one
rule "a restore reads what an export writes" keeps holding without a second
list to keep in step. Enum and date fields go through the same serialisation
`_record` already applies; `seating_settled_at` is a datetime and is parsed the
way `expires_at` is. `hr_category_map` is JSON and travels as it is.

### D2. Older documents restore manual

For `version < 24` the restore sets `registrations_kept_by = organizer` and
leaves every other new field to the model default. Manual mode is itself a
cause of dormancy under the single dormancy predicate (spec `registration`), so
no registration needs its `clocks_dormant` flag set by hand. The completeness
rule refuses to publish a manual tournament without an external registration
address, which forces the decision a v23 document cannot state.

Alternatives considered:
- *Restore automatic, as today.* This is the bug.
- *Refuse pre-v24 documents.* Too strong: the only thing missing is a decision
  the Admin can make in Setup, and the draft cannot do harm until it is made.

### D3. `source_row_id` rewrite and its uniqueness

The column names the fencer-list row an issued registration stands in for:
`imp:<key>` or `man:<id>`. A `man:` value is rewritten through `man_map`, the
same map the rule targets and row numbers use. An `imp:` key is a content
fingerprint, unique only per tournament (`UniqueConstraint("tournament_id",
"key")` on `imported_rows`), and carries over unchanged.

That means the column's current deployment-wide `unique=True` is wrong. Two
tournaments that imported the same row and issued it collide today. So would a
restored copy beside its original. The constraint becomes
`UniqueConstraint("tournament_id", "source_row_id")`, in a migration. Every
reader already filters by tournament (`sheet.py`, `amendment.py`,
`issuing.py`, `importclear.py`), so no lookup relied on the wider uniqueness.

Registration rows are restored before manual rows in the current order, so the
`man:` rewrite runs as a second pass once `man_map` exists, or registrations
are created after manual rows. The implementation picks whichever keeps the
restore readable.

### D4. `contact_email` travels; guest links do not

The contact address is how an organizer reaches a guest, and the document
already carries every account's address, so it adds no new kind of personal
data. `manage_key_generation` stays out: a restored registration is a new
record, and an old link opening it is not something anyone would expect. The
organizer resends the link from the console.

### D5. `short_code` travels

It is the organizer's own override of the derived monogram, not an identifier,
and is not unique, so it carries over as it stands.

### D6. A taken series is replaced; a taken symbol refuses

Found during implementation (owner decision 2026-11-15). The document carries
the tournament's `(vs_year, vs_series)`, which is unique across the deployment,
so a copy restored beside its original collided on it. Where the series is
taken, the restore takes the lowest free series of that year with
`vs_next_seq = 1`, as a pre-v4 document already does. Matching resolves a VS
whole and never parses the series out of it, so the restored registrations keep
the symbols they were given.

A registration's VS is unique across the deployment too, and is what a fencer
was told to quote, so it is never renumbered. A document whose registrations
hold a symbol the deployment already holds is refused with `409 vs_taken`
rather than failing on the constraint. A manual tournament issues no symbols,
so its copy restores; an automatic one with registrations does not.

## Risks / Trade-offs

- [A document written before this change still restores automatic-looking
  settings it never recorded] → It restores manual (D2); the Admin sets the
  mode in Setup before publishing.
- [The uniqueness migration fails on existing duplicate `(tournament_id,
  source_row_id)` pairs] → Impossible under the current wider constraint; the
  migration only narrows it.
- [A restored `seating_settled_at` in the past on a tournament whose deadline
  is in the future] → It is what the exported tournament held; settlement is
  one-shot by design, and the restore reproduces it rather than re-deciding.

## Migration Plan

One Alembic revision replaces the column's unique index with the composite
constraint. Documents of every older version keep restoring. Rollback is
reverting the commit and the revision; documents written at v24 then refuse to
restore on the older code as an unsupported version, which is the existing
behavior for a newer document.
