
## Why

A tournament can currently be born only through the API or the seed script — the frontend has no creation flow, and even existing tournaments cannot manage disciplines from the console. Real pricing also does not fit the current per-discipline fee model: organizers price by bundle ("30 € for one discipline, 50 € for both"), which the engine cannot express. This change gives organizers a complete self-service setup path: create a tournament from the picker, configure it in a new Setup phase (step 0) of the console, and open registration only once setup is complete.

## What Changes

- "New tournament" entry point on the tournament picker: minimal dialog (name + date, slug auto-derived and editable) that creates the tournament and lands in the console.
- New **Setup phase (step 0)** in the console phase rail, before Load, containing:
  - Mandatory fields: display name, date, location (new freetext field), titular organizers (multi-row freetext table of clubs/entities — display-only, distinct from account-based console access), disciplines (table: taxonomy dropdown + capacity + unit price, add/remove rows).
  - Optional fields: registration opens / registration closes dates (new fields; unset close means open until the tournament date).
  - A pricing section (see below).
  - A completeness checklist showing which mandatory fields are missing.
- **Unified itemized pricing (eshop + discounts)**: every billable item is a priced row with a category. Disciplines are priced on their Setup rows (category `discipline`); extra services are freetext-named rows ("afterparty saturday", "castle visit sunday", "t-shirt") tagged with a category from a fixed enum (`seminar`, `rental`, `afterparty`, `merch`) and an optional quantity limit. An ordered discount list applies on top: fixed amounts first, then percentages sequentially; each discount has an extensible condition (shipping with two kinds: discipline count, registered-before-date) and a category scope (in the data model from day one, no UI picker yet; e.g. later "early bird only on disciplines + seminars"). The final total is rounded half-up to a whole currency unit, once. Totals remain a recomputed pure function; tournaments with no new-style items or discounts keep the legacy computation (per-discipline `fee`/`fee_early` + hard-coded rental/afterparty columns) so historical totals and the pilot replay are preserved.
- **Generalized extras in registration**: the registration API accepts selections of the tournament's configured extra services (per-item quantity up to the item's limit) instead of the hard-coded weapon-rental/afterparty options; selections are stored per item, and the confirmation email and exports list the selected items. Non-billable fields (after-sparring, accommodation, notes) are unchanged. A fencer-facing registration UI does not exist in this repo (registration has always been API-only) and is deferred to a follow-up change (`add-public-registration`).
- **Registration gating**: a tournament accepts registrations only when mandatory setup is complete and the current date is inside the registration window (de-facto draft state; no status enum).
- Organizer-removal endpoint for discipline-style row editing is out of scope for account organizers; account-based access policy is explicitly deferred.

## Capabilities

### New Capabilities

None — all changes extend existing capabilities.

### Modified Capabilities

- `tournament-admin`: tournament definition gains location, titular organizers, and a registration window; the pricing requirement changes from per-discipline fees plus fixed extras to categorized billable items with an ordered, scoped discount list; new requirements for the in-app creation flow and setup completeness.
- `etl-console`: the phase rail gains a Setup phase (step 0) before Load — seven tabs instead of six; Setup hosts the tournament configuration instead of a fencer table.
- `registration`: registration is accepted only when tournament setup is complete and within the registration window; the form offers the tournament's configured extra services and totals are computed from the itemized pricing with discounts.

## Impact

- Backend: `models.py` (Tournament: location, titular organizers, registration window, discounts; new extra-items table; per-registration extra selections; legacy fee/extras columns kept), Alembic migration, `pricing.py` (itemized computation with discounts and legacy fallback), `schemas.py`, `routers/tournaments.py` (setup payloads), `routers/registrations.py` (window + completeness gating, extras selections), `emails.py` (itemized summary), export paths (`export_json.py`, `sheets_export.py` — extras representation).
- Frontend: `TournamentPicker.tsx` (create dialog), `Console.tsx` (phase rail + Setup phase), new Setup panel components (organizer table, discipline table with unit price, extra-services table, discounts table, checklist), `api.ts`, i18n catalogues (cs/en). No fencer-facing UI (see above).
- Seed script and demo data updated to itemized pricing with discounts.
- Existing tests touching per-discipline fees and pricing totals will need updating; determinism/replay tests must stay green (frozen totals unchanged).