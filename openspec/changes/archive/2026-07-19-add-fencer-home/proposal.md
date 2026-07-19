## Why

Fencers have no surface of their own: registration exists only as an API (explicitly deferred in the registration spec), payment QR codes live only in emails, and after login everyone lands on the organizer-oriented tournament picker. A fencer cannot browse open tournaments, register, see their price, or retrieve payment instructions in the app.

## What Changes

- New **Fencer Home** page — the default post-login landing for every account:
  - List of published upcoming tournaments: name, organizer names, date, location, disciplines with registered numbers (e.g. LS 18/25, SA 25/16), and a registration status badge (open / opens on date / closed).
  - Per tournament a **Register** button, or **Manage registration** when the fencer already has one.
- New **Tournament detail** page (fencer view), opened from either button:
  - Full tournament information (date, location, organizers, disciplines with fees and free places, extra services with prices).
  - **Registration section**: select disciplines and extra services with quantities plus the non-billable fields; live total price calculated server-side while selecting.
  - After registration (and for any existing unpaid registration): payment instructions — SPAYD QR code and full transfer details (IBAN, amount, VS, message with VS for foreign payers) shown together; registration state (reserved/expiry, paid, substitute queue positions), and cancellation per policy.
- **Landing/navigation rewiring**: Fencer Home becomes the post-login landing; the tournament picker becomes an organizer surface reached via the account menu's "To Organizer"; its plea section is removed (the plea lives on the Profile page); the "To Fencer" menu item becomes active.
- **Backend additions**: fencer-facing tournament list with per-discipline counts and own-registration status; registration price-preview endpoint reusing the pricing engine; payment-instructions endpoint (QR PNG + transfer data) for one's own reservation.
- Past-tournament results are out of scope (later change).

## Capabilities

### New Capabilities
- `fencer-home`: the fencer-facing GUI — post-login landing with the open-tournaments list, the tournament detail with registration flow, in-app payment instructions, and registration management (view, cancel).

### Modified Capabilities
- `registration`: the deferred fencer-facing UI arrives; API gains a price preview (compute the total for a hypothetical selection without registering) and in-app payment instructions (QR + transfer data, previously email-only); the fencer-facing tournament list exposes per-discipline registered counts and hides unpublished drafts.
- `profile-page`: account menu's "To Fencer" placeholder becomes an active entry to Fencer Home, which also replaces the picker as the post-login landing; the picker's plea section is removed (depends on `add-profile-management` being implemented first).

## Impact

- **Backend**: `routers/tournaments.py` or new fencer router (published-upcoming list + discipline counts + my-registration flag), `routers/registrations.py` (price preview, payment instructions endpoint reusing `spayd.py`), `pricing.py` (preview entry point for an unsaved selection).
- **Frontend**: new `FencerHome.tsx`, new `TournamentDetail.tsx` (fencer view) with registration form and payment panel; `App.tsx` view union gains `home` + `tournament` views and changes the default view; `AccountMenu` "To Fencer" activation; `TournamentPicker.tsx` plea section removal; `api.ts`; cs/en i18n keys.
- **Dependencies**: builds on `add-profile-management` (AccountMenu, view-union refactor, PleaSection on profile). No schema migration; no breaking API changes (additive endpoints only).
