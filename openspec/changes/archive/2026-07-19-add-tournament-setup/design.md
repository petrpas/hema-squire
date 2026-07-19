## Context

Tournaments exist only via the seed script or raw API calls: `POST /api/tournaments` works (any signed-in fencer becomes organizer of the tournament they create), disciplines/organizers have CRUD endpoints, but the frontend has no creation flow and no configuration UI beyond `ParamPanel`, which patches a few scalar parameters per phase. Pricing is per-discipline (`Discipline.fee`/`fee_early`) plus two hard-coded extras (`weapon_rental_fee`, `afterparty_fee`, each with early variants), computed in `pricing.py` as a **pure function of (tournament, item, as-of date)** — totals are recomputed, never stored. Registrations carry hard-coded extras fields (`weapon_rentals`, `afterparty`; non-billable `aftersparring`, `accommodation`, `notes`). The pilot replay test reproduces v1 totals through this path. Migrations run through Alembic (`dev.sh` → `alembic upgrade head`).

## Goals / Non-Goals

**Goals:**
- Self-service tournament creation from the picker; full configuration in a new console Setup phase (step 0).
- New tournament attributes: location, titular organizers, registration window.
- Unified itemized pricing: categorized billable items (disciplines + freetext-named extra services) with an ordered, scoped discount list; legacy totals stay bit-for-bit reproducible.
- Registration API accepting selections of the configured extra services.
- Registration gated on setup completeness and the registration window.

**Non-Goals:**
- Fencer-facing registration UI — discovered during implementation: the frontend is exclusively the organizer console and registration has always been API-only in this repo, so there is no form to extend. Deferred to a follow-up change (`add-public-registration`: public routing, fencer auth flow, the form itself).
- Clone-from-previous-tournament (follow-up change).
- Account-based access policy (who may create, organizer account management UI, removal endpoint) — explicitly deferred by owner.
- Discount conditions beyond discipline count and early-bird date (club member, women, manual grants — the condition enum is built to receive them later).
- Scope picker in the discounts UI (scope is stored per discount; UI exposure is a follow-up).
- Merch variants (t-shirt sizes etc.) — the notes field covers it until merch matters.
- Suggestions of previously used titular organizers (schema allows it later; UI ships freetext only).

## Decisions

**D1 — Setup is a console phase, not a separate page.** Extend the frontend `Phase` union with `"setup"` as the first rail entry. The console already switches panel content per phase; Setup renders configuration forms instead of the fencer table. Alternative (standalone settings route) rejected: duplicates console chrome and breaks the owner's "step 0 in the data flow" mental model.

**D2 — Titular organizers as a JSON list on Tournament.** `Tournament.organizer_names: list[str]` (JSON column), ordered, edited as a whole in the Setup PATCH. Alternative (separate table) rejected: no relations, no per-row identity needed; "previously used values" can later be served by querying distinct values across tournaments.

**D3 — Pricing model: categorized items + ordered scoped discounts.**
- *Items.* Disciplines keep their price on `Discipline.fee` (category `discipline` is implicit). Extra services are a new tournament-scoped table `extra_items` (`id`, `tournament_id`, `name` freetext, `category` enum: `seminar` | `rental` | `afterparty` | `merch`, `price`, `max_qty` default 1). A real table, not JSON, because registrations must reference items stably.
- *Discounts.* `Tournament.discounts: list[{name, condition: {kind, …}, effect: {kind: fixed|percent, value}, scope: [category, …]}]` (ordered JSON column). Condition kinds shipped: `discipline_count` (equals N) and `early` (registered on/before date). JSON is fine here: nothing references a discount row, order matters, and the two enums are the extension axes.
- *Computation* (in `pricing.py`, still a pure function of tournament config, registration content, and `registered_at`): sum selected item prices → subtract applicable fixed discounts from their scoped category subtotals (floor 0) → apply applicable percentage discounts sequentially to their scoped subtotals → round half-up to a whole unit exactly once. The rounding rule is normative (spec'd) because replay determinism depends on it.
- *Legacy fallback.* If a tournament has no `extra_items` rows and no `discounts`, the existing computation (per-discipline fees + `fee_early` + hard-coded rental/afterparty parameters) runs unchanged — historical totals and the pilot replay stay intact. New-style tournaments never set `fee_early` or the hard-coded extras columns; those stay as a legacy read path. A tournament with only discipline prices and no extras/discounts computes identically under both paths, so the flag is unambiguous where it matters.
- *Alternatives rejected:* count-keyed bundle table (superseded — counts are just fixed discounts conditioned on `discipline_count`; early-bird shadow price columns collapse into one percent discount); freetext categories (discount scopes reference categories, so they must be a closed enum).

**D4 — Registration extras as a link table.** New `registration_extras` (`registration_id`, `extra_item_id`, `qty`) replaces `weapon_rentals`/`afterparty` for new-style tournaments; the legacy columns keep serving legacy tournaments. Registration validation enforces `qty ≤ max_qty`. Confirmation email and exports itemize from the link table when present.

**D5 — Completeness as one backend helper.** `setup_missing(tournament) -> list[str]` (stable item keys: `location`, `organizers`, `disciplines`, `discipline_prices`, …) used by (a) the registration gate in the registrations router, (b) the tournament detail payload (`setup_missing` field) that drives the Setup checklist and the public page's "not yet published" state. One source of truth; no status enum stored.

**D6 — Registration window checked at submission time.** Two nullable `date` columns, `registration_opens` / `registration_closes`; gate order: setup complete → opens ≤ today → today ≤ (closes or tournament date). Enforced server-side in the registration endpoint; the frontend only renders the reason.

**D7 — Creation stays the existing endpoint.** The picker dialog collects display name + date; the slug is derived client-side (slugified name + year), shown editable, and `POST /api/tournaments` is unchanged (409 on collision surfaces inline). New fields are all optional at creation and filled in Setup. Any signed-in user can create — unchanged current behavior, accepted until the deferred access-policy change.

**D8 — Seed keeps both pricing worlds.** The demo tournament adopts itemized pricing (extra services in several categories + a count discount + an early-bird percent discount, exercising the new path); the pilot replay fixture keeps per-discipline fees and hard-coded extras, doubling as a regression test for the legacy fallback.

## Risks / Trade-offs

- [Recomputed totals change when pricing is edited mid-flight] → a reservation's due amount is recomputed, so edits to items/discounts move what unpaid reservations owe versus their emailed QR. Mitigation: Setup warns when editing pricing on a tournament that already has registrations; documented as organizer responsibility (same exposure as editing any price today).
- [Rounding drift breaks replay] → the half-up-once rule is normative in the spec and covered by unit tests; percentage math happens on exact values, rounding only at the end.
- [Sheet export (v1 format) has fixed columns for rental/afterparty] → new-style extras must map into that format; items in `rental`/`afterparty` categories map to the v1 columns, other categories land in a summary column. Verify against `sheets_export.py` during implementation; canonical JSON export just itemizes.
- [JSON discounts are invisible to SQL constraints] → validate shape in Pydantic (known condition/effect/scope values, `value ≥ 0`, percent ≤ 100); `setup_missing` revalidates.
- [Seven tabs crowd the rail] → Setup uses the same tab affordance; if crowding bites, iconography/collapse is a UI-only follow-up.
- [Slug derived from user text] → reuse the existing server-side slug pattern validation as the source of truth; the client only suggests.

## Migration Plan

1. One Alembic revision: add `location`, `organizer_names`, `discounts`, `registration_opens`, `registration_closes` to `tournaments`; create `extra_items` and `registration_extras` tables. All nullable/defaulted — existing rows remain valid and, having no items/discounts, keep legacy pricing.
2. No data backfill. Existing tournaments show an incomplete checklist (missing location/organizers) but **gating must not lock out tournaments with existing registrations**: the gate applies only to *new* registration submissions, and the seeded demo is updated to be complete.
3. Rollback: drop the columns and tables; no behavior depends on them once removed.

## Open Questions

- Should the public tournament page show titular organizers immediately (touches the public list template) or is console+registration-page display enough for this change? Default: registration page only.
- Currency display is implicitly CZK today; pricing examples were quoted in EUR. Assumed: amounts stay currency-agnostic integers as today, display unchanged. Flag to owner if a currency field is wanted (ties into the deferred foreign-payment-channel question from v1).
- Category enum start set (`seminar`, `rental`, `afterparty`, `merch`): additions are code changes by design — confirm the four cover the near term.
