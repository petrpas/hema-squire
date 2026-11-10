## Context

The scheduler's `tournaments_to_tick` deliberately selects current tournaments, so a retention pass needs its own selection. Bank row text is the organizer's evidence, and Squire holds it as processor. Replay reads `ImportedRow.raw` with fingerprints, and a held tournament's Export tab and rosters come through it.

## Goals / Non-Goals

**Goals:**
- Enforce every period the privacy page states.
- Keep money reconcilable and rosters intact after pruning.

**Non-Goals:**
- Per-organizer periods.
- Pruning names. Rosters are kept by decision.
- Pruning logs on the host or backups: 28-day Litestream retention already bounds them, and `privacy-baseline` verifies B2.

## Decisions

### D1. One idempotent pass, one stamp per tournament

A daily-effect pass in `run_tick` selects tournaments dated more than 12 months ago with no `personal_data_pruned_at`, prunes each in its own transaction and stamps it. The stamp makes later passes cheap and states that it happened. Mail and expired tokens are plain deletes by age.

### D2. Blank bank text, keep the row

Blanked: `payer_name`, `payer_account`, `message`, `named_person`, `user_identification`, `comment`, `specification`, `specific_symbol`, `rejected_fencer_ids`. Kept: amounts, currency, date, `vs`, status, matched registration and `external_id`. Keeping `external_id` means a late statement import cannot re-create the row. Deleting rows was rejected, because credits refer to them and revenue reconciliation reads them.

### D3. Import rows: remove addresses and free text, keep what the row needs

Removing `raw` wholesale would break replay and the Export tab of a held tournament. No column mapping is stored, so the pass blanks a cell in `raw` where it equals the email, notes or accommodation of the row's parse decision, and cuts any value shaped like an address out of every cell. The fencer list reads the parse decision, not `raw`, so the decision loses those fields too. A rule that edited one of them, a merge's fields and the rule journal's snapshots lose them as well, because replay would otherwise write them back onto the row. The stored fingerprint is not recomputed, as an already-imported batch is never rehashed. Pruned tournaments must be verified not to re-ingest: Task 2.3 tests it.

### D4. 30 days for mail, no exception for failures

Thirty days is enough to diagnose delivery. The failed row's reason for staying was operational visibility, and the error log keeps that.

## Risks / Trade-offs

- An organizer needs bank text after 12 months → terms say to export first, and the organizer's own bank holds the statement.
- A dispute after 12 months → amounts, date and VS remain, and the bank's record is the primary evidence.
- Unknown column mapping leaves a free-text value in `raw` → the shape-based address scan still applies; the residual is stated in the classification.
- The first run prunes much at once → it runs per tournament and is idempotent; take a verified backup first.

## Migration Plan

Publish the periods and terms, then deploy with the pass disabled by a setting for one tick with counts logged, then enable. Pruning cannot be rolled back after the 28-day backup window.

## Open Questions

- The 30-day mail period and the free-text scope beyond bank rows were proposed defaults, confirmed only as part of this proposal's review.
- Whether a lawyer or accountant wants a period other than 12 months.
