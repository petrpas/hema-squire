# Project Context

## Purpose

HEMA Squire is a multi-tournament web application for administering HEMA tournaments. It succeeds the Discord-bot prototype (petrpas/hema-agent), which validated the domain logic in live operation but failed as an interface. Current scope: the pre-tournament phase — fencer accounts, in-app registration, the payment lifecycle, and an organizer ETL console over the fencer table. In Tournament and Post Tournament are planned menu sections, out of scope for now.

## Tech Stack

Not finalized. Constraints and inclinations:

- Backend: Python (organizer's primary language); pydantic domain models adaptable from the v1 repo.
- Frontend: web app per the approved wireframe (direction B — top stepper, full-width sheet table, right operations rail).
- Persistence: canonical store owned by the app; RDBMS choice open. Versioned JSON is the canonical export format.
- LLM: Anthropic models via pydantic-ai, used only on the table-import path.
- Integrations: hemaratings.com (fighters index, ratings), Fio bank REST API (+ CSV statement import), Google Sheets (export target), SPAYD QR generation, transactional email.

## Project Conventions

- All user-facing text externalized and localized. Czech is the launch language; English follows. No hardcoded strings.
- Every manual data mutation flows through the edit-rules engine: actions become persistent, replayable, removable rules.
- Deterministic reruns: table state is a pure function of (source records, rule set, operation parameters). LLM outcomes are materialized as decisions and never re-invoked on rerun.
- Specs are behavior-level; visual structure is governed by the wireframe referenced in changes/add-pre-tournament-core/design.md.

## Domain Glossary

- **Fencer** — a person with a portable account, ideally bound to a HEMA Ratings profile (hr_id).
- **Registration** — a fencer's entry to one tournament: disciplines plus billable extras; starts life as a reservation.
- **Reservation** — an unpaid registration with a short validity window; expires automatically when unpaid.
- **VS (variabilní symbol)** — unique numeric payment reference identifying a registration in bank transactions.
- **Rule** — a persisted manual operation replayed on every rerun; removing it reverts its effect.
- **Phase** — one step of the organizer console: Load, Parsing, Matching on HR, Deduplication, Payments, Export.
