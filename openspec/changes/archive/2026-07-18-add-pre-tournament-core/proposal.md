# Change: add-pre-tournament-core

## Why

The v1 Discord bot (petrpas/hema-agent) proved the pre-tournament domain logic at a live tournament, but Discord failed as an interface: no real forms, no table editing, state scattered across channel history, and Google Sheets doubling as both database and UI. The pivot is a web application whose core surface is the fencer table with logged, replayable CRUD operations organized into processing phases. Registration moves from Google Forms into the app (portable fencer accounts), and the payment problem is solved structurally — a registration without payment is a free option, so the free option is removed: short-lived reservations, VS/QR payment identity, automatic expiry.

## What Changes

Adds ten capabilities (greenfield — everything is ADDED):

- **fencer-accounts** — portable fencer identity, HEMA Ratings binding at account creation
- **tournament-admin** — multi-tournament deployment, disciplines, pricing, operational parameters
- **registration** — in-app registration, reservation lifecycle, capacity, public participant list
- **payments** — VS identity, SPAYD QR, bank ingestion, matching, reminders, expiry, refund policy
- **etl-console** — phase-tabbed fencer table (Load → Export), per-row status, parameter panels
- **edit-rules** — action-as-rule engine, audit, deterministic replay
- **table-import** — LLM-assisted import path (parse, HR match, dedup) for external tables
- **hr-integration** — fighters index, profile lookup, dated ratings snapshots
- **data-export** — canonical JSON plus Google Sheets export in the v1 legacy format
- **localization** — fully localized from the start, Czech first

## Impact

- Affected specs: all ten capabilities (new).
- Affected code: new repository. The v1 repo remains the behavioral reference; provenance and dropped v1 behavior are documented in ANALYSIS.md at the deliverable root.
- Downstream contract: the Google Sheets export reproduces the format consumed by the v1 in-tournament bot, keeping the in-tournament phase operational during the transition.
