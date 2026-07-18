# Design — add-pre-tournament-core

## Context

Business rules extracted from petrpas/hema-agent (pre_tournament package). UI structure from the approved wireframe (HEMA Squire ETL, direction B; source saved at `docs/wireframe-b.html` in this repo): top bar with logo and stage control (Pre / In / Post Tournament), tournament name and date on the right, horizontal phase stepper Load → Parsing → Matching on HR → Deduplication → Payments → Export, full-width sticky-header sheet, right operations rail with General rules / Columns for step / Manual edits log. Match verdicts render as ✓ / ? / ✗ badges.

## Decision 1 — Two intake paths, one phase model

Native path: in-app registration produces structured, HR-bound records, so Load, Parsing, and Matching are satisfied at birth and those phase tabs mostly display state. Import path: external tables traverse the full ETL (LLM parse → LLM match → dedup). Phase status is per row, so both populations coexist in one table. A phase tab is a view of the whole fencer list as of after that operation, plus that operation's parameters.

## Decision 2 — Rule-replay data model

Current state = replay(source records, ordered rule set, operation parameters). Every manual action creates a rule; removing a rule recomputes state as if the rule never existed. LLM outputs are materialized as decisions equivalent to rules, so reruns are deterministic and cheap; only new rows invoke the LLM. Default conflict semantics: rules apply in creation order, latest rule touching a field wins. Implementation freedom: event-sourced journal or rule table plus snapshot cache — the spec constrains observable behavior only.

## Decision 3 — Payment engine

Registration = reservation state machine: reserved → (reminded) → paid | expired | cancelled. VS is the payment identity (sequential generation acceptable); the confirmation email carries an SPAYD QR with amount, account, VS, message. Bank adapters: Fio REST polling and manual statement import behind one idempotent ingestion interface keyed by the transaction's natural identity. Matching is strictly VS-first with a configurable amount tolerance (default ±5 %) absorbing FX noise; everything else lands in an unmatched queue for manual linking, which persists as a rule and supports one payer covering multiple registrations. This retires the v1 LLM payment-matching approach — the root cause (matching by name/amount) is designed out.

## Decision 4 — Multi-tenancy

Single deployment, many tournaments. Fencer accounts are global; registrations, rules, parameters, pricing, and exports are tournament-scoped. Organizer authorization is per tournament.

## Decision 5 — Sheets as anti-corruption layer

The app owns canonical data (versioned JSON export). The Google Sheets export reproduces the v1 format so the existing in-tournament tooling and human workflows keep working. Repeat export preserves manually managed sheet columns (Reg., No.) and always refreshes HRating/HRank — the v1 "surgical sync" contract, retained deliberately for the sheet target only.

## Decision 6 — LLM boundary

LLM appears only on the import path (parse, fuzzy HR match, dedup classification and merge proposals). Same-hr_id merges are LLM-proposed but organizer-confirmed (owner's decision, 2026-07-17) — no merge is applied without confirmation. Native-path matching is interactive search at account creation, not LLM. The v1 self-healing HTML parser is downgraded: detect format drift, fail loudly with diagnostics; LLM-assisted repair is an operator tool, not a runtime dependency.

## Decision 7 — Substitute billing and full-discipline choice (owner, 2026-07-17)

Substitutes pay nothing at registration; on admission the fee — at prices frozen to the original registration time — is added and a fresh payment window opens. When part of a selection is full, the server rejects with the list of full disciplines and the fencer chooses: register the open subset, or queue the entire registration as substitute for everything selected. There is no silent split.

## Decision 8 — HR integration shape (owner, 2026-07-18)

The fighters index lives in a DB table, global per deployment: auto-populated in the background when empty at startup, manually refreshable afterwards (spec: on demand); scheduled refresh deferred. Parser drift fails loudly — implausible parse keeps the previous index and surfaces diagnostics; v1's LLM self-healing parser is explicitly not ported (no model-generated code executing in the backend; may return as its own change). Ratings are dated per-tournament snapshots from day one, but the UI exposes only "fetch now" and exports use the latest; a snapshot picker waits for demand. The discipline → HR category mapping ships as the proven v1 keyword table with a per-tournament JSON override parameter (`hr_category_map`).

## Open decisions

- Foreign payment channel: VS-in-message instructions (~80 % success, manual fallback) vs Wise/Revolut vs Stripe payment link (~1.5 % fee, no matching needed). Parameterize per tournament; default undecided.
- Discipline taxonomy: seeded from the v1 21-code set (weapon × gender × material); organizer-defined custom codes are an open question.
- Seeding (Seed column) deliberately deferred — out of scope of this change (owner's decision C9).
- ~~Discipline → HEMA Ratings category mapping~~: resolved by Decision 8 — default keyword table + per-tournament `hr_category_map` override.
- Reservation window defaults: 7–10 days validity, reminder around day 5, expiry at window end; exact defaults TBD.
