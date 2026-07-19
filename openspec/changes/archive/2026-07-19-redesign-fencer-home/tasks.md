## 1. Backend — past tournaments endpoint

- [x] 1.1 Add `GET /api/tournaments/mine/past` (declared before slug routes): non-cancelled tournaments with `date < today` where the caller has a non-cancelled registration or is an organizer, date-descending, reusing `OpenTournamentOut` (`registration_status="closed"`, `my_registration_state` folded in) plus an `organized` flag
- [x] 1.2 Backend tests: participation and organizer inclusion, cancelled-registration and unrelated tournaments excluded, drafts/cancelled tournaments excluded, ordering, `organized` flag

## 2. Frontend — Fencer Home screen

- [x] 2.1 Rebuild `FencerHome.tsx` on the console layout: `header.topbar` with logo, center tab nav (Vyhlášené / Otevřené / Proběhlé), fencer identity block, `AccountMenu`; workspace renders the card list per tab
- [x] 2.2 Tab logic: Otevřené default, Otevřené/Vyhlášené filter the `/open` payload by `registration_status`, Proběhlé lazily fetches `/mine/past` (`api.ts` function); per-tab empty states; organizer chip on organized-only past cards
- [x] 2.3 Identity block: display name + `HRID: <id>` external link to `hemaratings.com/fighters/details/{hr_id}/` (new tab), or "no hemaratings" navigating to Profile when unbound

## 3. Frontend — read-only past detail

- [x] 3.1 Add a `readOnly` mode to `TournamentDetail.tsx` (used when opened from the Past tab): info + own registration summary only; suppress registration form, payment panel, and cancel

## 4. Polish & verification

- [x] 4.1 cs/en i18n keys (tabs, empty states, HRID / no hemaratings, organizer chip) and `index.css` additions for the tab nav and identity block
- [x] 4.2 Frontend build + full backend test suite pass
- [x] 4.3 E2E via dev servers: login lands on Open tab; Announced shows a not-yet-open tournament; Past shows only own history and opens read-only detail; HRID link correct for bound and unbound accounts
