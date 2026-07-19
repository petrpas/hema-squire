## Context

The registration backend is complete: `POST /api/t/{slug}/register` (disciplines, extras, non-billables, wait_for_all), `GET /my-registration`, `POST /my-registration/cancel`, `GET /availability` (per-discipline taken/free/queue), `GET /participants`, pricing in `pricing.py` (itemized + discounts + legacy), SPAYD/QR in `spayd.py` (email-only today), and `setup.registration_availability()` returning the distinct rejection reasons. `GET /api/tournaments` returns all non-cancelled tournaments including unpublished drafts and has no per-discipline counts. The frontend after `add-profile-management` is a view-union SPA (`picker | console | admin | profile`) with a shared `AccountMenu` ("To Fencer" disabled) and `PleaSection` on both picker and profile. This change builds on that change and must be applied after it.

## Goals / Non-Goals

**Goals:**
- Fencer Home as post-login landing: published upcoming tournaments with per-discipline counts, status, register/manage actions.
- Fencer tournament detail: info, registration form with server-computed live total, in-app payment instructions (QR + transfer details), registration management with cancellation.
- Rewire navigation: landing → Fencer Home, picker organizer-only via menu, plea removed from picker.

**Non-Goals:**
- No results of past tournaments (later change); past tournaments not listed at all.
- No payment-state push/polling beyond refetch on page open; no email changes; no pricing-rule changes.
- No public (logged-out) tournament browsing; Fencer Home requires login.

## Decisions

- **D1 — Fencer list endpoint.** New `GET /api/tournaments/open` (same router): published (`setup_missing == []`), non-cancelled, `date >= today`, ordered by date. Returns a trimmed fencer DTO: slug, name, date, location, organizer_names, registration status (`open | opens_on(date) | closed` from `registration_availability`), per-discipline `{code, name, fee, taken, capacity, queue_length}` (reusing the availability logic), and `my_registration_state` (`none | reserved | paid | substitute | cancelled`) for the authenticated fencer. One endpoint avoids N+1 availability calls from the list. Alternative (enrich `GET /api/tournaments`) rejected: that DTO is organizer-shaped and leaks drafts and config (fio token URL fields are absent, but reminder/tolerance noise remains); a separate fencer view keeps both stable.
- **D2 — Price preview.** `POST /api/t/{slug}/price-preview` taking the `RegisterIn` billable subset (disciplines, extras, weapon_rentals, afterparty) and returning `{total}`. Implemented by refactoring `pricing.registration_total` to accept a lightweight selection object (or building a transient unsaved `Registration`), evaluated at today's date. Frontend debounces calls on selection change. Alternative (client-side pricing) rejected per owner decision: one source of truth.
- **D3 — Payment instructions.** `GET /api/t/{slug}/my-registration/payment` returning `{amount, iban, vs, message, expires_at, spayd, qr_png_base64}` for the caller's own unpaid reservation (404/409 otherwise), reusing `spayd.spayd_string`/`qr_png` with the same inputs as the confirmation email. QR embedded as a data URI; both QR and transfer details always rendered together (owner decision).
- **D4 — Views.** App view union gains `home` and `tournament` (with selected slug); initial view after login becomes `home`. `FencerHome.tsx` renders the list; `TournamentDetail.tsx` renders info + one of three states: registration form (no registration, window open), payment/management panel (has registration), or a closed/not-open notice. Manage and Register both navigate to the same detail view; it derives its state from `my-registration`.
- **D5 — Registration form behavior.** Disciplines as checkboxes with fee and free-places labels; extras grouped by category with qty steppers up to `max_qty`; non-billable fields below. On 409 `full_disciplines`, show the choice dialog: resubmit with `wait_for_all: true` or drop the full disciplines. Legacy tournaments (no extra_items) render the fixed weapon-rental/afterparty controls from the legacy fee fields.
- **D6 — Picker demotion.** `TournamentPicker` loses the plea section (component call deleted; shared `PleaSection` stays for the profile) and is reachable only via AccountMenu "To Organizer"; "To Fencer" menu item navigates to `home` and loses its disabled state. Login lands on `home` for every role.
- **D7 — Cancellation UX.** Cancel button opens a confirm dialog stating refundability computed from `refundable_until` vs today (data already in the fencer DTO); on confirm calls the existing cancel endpoint and refetches.

## Risks / Trade-offs

- [Preview vs. registration drift if pricing refactor forks logic] → preview and `register` MUST call the same `pricing` entry point; covered by an equality test (preview total == registered total for the same selection).
- [`/open` list computes counts per discipline per tournament] → same queries as `/availability`, bounded by a handful of upcoming tournaments; optimize with an aggregate query only if it shows.
- [QR as base64 in JSON inflates payload] → single small PNG (~1 KB); acceptable; switching to a binary endpoint is trivial later.
- [Ordering dependency on add-profile-management] → apply strictly after it; tasks assume `AccountMenu`, view union, and shared `PleaSection` exist.
- [Substitute-only registrations get no expiry (no payment due until admitted)] → payment panel shows queue state instead of QR when all entries are substitutes; existing behavior, surfaced in UI copy.

## Migration Plan

Additive only: new endpoints, new views; no schema migration. Deploy backend then frontend together; no data changes. Rollback = revert.

## Open Questions

- None blocking. Past-results section and public (logged-out) browsing are future changes.
