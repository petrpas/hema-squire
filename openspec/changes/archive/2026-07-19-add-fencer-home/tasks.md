## 1. Backend — fencer-facing API

- [x] 1.1 Refactor `pricing.py` to expose a preview-capable entry point (total for an unsaved selection at a given date) used by both `register` and the new preview; keep `registration_total` behavior identical
- [x] 1.2 Add `POST /api/t/{slug}/price-preview` (billable subset of `RegisterIn` → `{total}`) in `routers/registrations.py`
- [x] 1.3 Add `GET /api/t/{slug}/my-registration/payment` returning amount, IBAN, VS, message, expires_at, SPAYD string, and base64 QR PNG via `spayd.py`; owner-only, unpaid reservations only (404/409 otherwise)
- [x] 1.4 Add `GET /api/tournaments/open`: published (`setup_missing` empty), non-cancelled, `date >= today`, ordered by date; per-discipline `{code, name, fee, taken, capacity, queue_length}` and the caller's `my_registration_state`; registration status open/opens_on/closed
- [x] 1.5 Backend tests: preview == registered total (itemized with discount and legacy), payment endpoint auth + content parity with the confirmation email inputs, open-list hides drafts/cancelled/past and carries counts + own state

## 2. Frontend — Fencer Home

- [x] 2.1 Add `home` and `tournament` views to the App view union; login lands on `home`; `api.ts` functions for open list, price preview, payment instructions
- [x] 2.2 Create `FencerHome.tsx`: tournament cards with name, organizers, date, location, per-discipline "CODE taken/capacity", status badge (open / opens on date / closed), Register or Manage registration button per `my_registration_state`
- [x] 2.3 AccountMenu: activate "To Fencer" → `home`; `TournamentPicker`: remove the plea section (shared `PleaSection` remains on profile)

## 3. Frontend — tournament detail

- [x] 3.1 Create `TournamentDetail.tsx` (fencer view): info header (date, location, organizers, registration window) + disciplines with fees and free places/queue + extras with prices
- [x] 3.2 Registration form: discipline checkboxes, extras with qty steppers (≤ max_qty), legacy weapon-rental/afterparty controls for legacy tournaments, non-billable fields; debounced server price preview shown as the total
- [x] 3.3 Submit flow: create registration; on 409 `full_disciplines` offer join-queue (`wait_for_all`) vs drop-full-disciplines; on success switch to the registration panel
- [x] 3.4 Registration panel: state (reserved + expiry, paid, substitute queue positions, cancelled), selected items with total; payment instructions for unpaid reservations — QR image + IBAN, amount, VS, VS-in-message note; cancel with refundability confirm dialog
- [x] 3.5 cs/en i18n keys for home, detail, form, payment, and cancellation; style per existing `index.css` patterns

## 4. Verification

- [x] 4.1 Frontend build + full backend test suite pass
- [x] 4.2 E2E via `dev.sh`: log in, land on Fencer Home, see seeded demo tournament with counts, register with an extra service (watch total change), see QR + IBAN + VS, verify Manage registration on home, cancel and re-register; picker shows no plea and is reachable via To Organizer
