## 1. Data model & migration

- [x] 1.1 Add `subtitle: str | None`, `logo_bytes: LargeBinary | None`, `logo_mime: str | None` to `Tournament` in `backend/app/models.py`
- [x] 1.2 Add discipline schedule/ruleset columns to `Discipline` (`schedule_when`, `schedule_where`, `ruleset_name`, `ruleset_url`, all `str | None`)
- [x] 1.3 Add `schedule_when`, `schedule_where`, `remark` (`str | None`) to `ExtraItem`
- [x] 1.4 Write one Alembic migration adding all new nullable columns; confirm `alembic upgrade head` then `downgrade` runs cleanly on a copy of `hema_squire.sqlite`

## 2. Backend schemas & endpoints

- [x] 2.1 Extend `DisciplineIn`/`DisciplineOut` with schedule + ruleset fields (JSON keys `when`/`where`/`ruleset_name`/`ruleset_url`) in `backend/app/schemas.py`
- [x] 2.2 Extend `ExtraItemIn`/`ExtraItemOut` with `when`/`where`/`remark`; assert these are ignored by pricing (`pricing.py` untouched)
- [x] 2.3 Add `subtitle` to tournament create/update schemas and a `logo` reference (URL/flag) to tournament output schemas
- [x] 2.4 Add `POST /tournaments/{slug}/logo` (multipart): reject uploads over the cap (~512 KB), re-encode/downscale to a bounded PNG, store `logo_bytes` + `logo_mime`; add `DELETE` to clear
- [x] 2.5 Add `GET /tournaments/{slug}/logo` serving the stored bytes with the stored mime (404/no-logo path handled)
- [x] 2.6 Include `subtitle` and a logo reference in the fencer-facing tournament list, open/announced/past, and detail payloads in `routers/tournaments.py`
- [x] 2.7 Backend tests: logo upload cap + re-encode, logo serve, subtitle/schedule/ruleset/remark round-trip through create→read, legacy totals unchanged

## 3. Signup form (fencer-accounts)

- [x] 3.1 In `Login.tsx` signup, reuse the form `name` as the HR search query and remove the second name input in the HR step (suppress `HRSearchPicker`'s own query field for this path)
- [x] 3.2 Add a static ownership-confirmation panel shown after selecting a candidate: name, nationality, club, HR id, and an external `hemaratings.com/fighters/details/{id}/` link (`target="_blank" rel="noreferrer"`); bind only on confirm (no animated modal — Bureau 1952)
- [x] 3.3 Change the confirmed line i18n to include the id, e.g. `HEMA Ratings profile confirmed: {{name}} ({{hrId}})`, in `en.json` and `cs.json`; pass `hrId` at the call site
- [x] 3.4 Verify name-field edits after a failed search still drive the next search; keep the field the single query source

## 4. Tournament list cards (fencer-home)

- [x] 4.1 In `FencerHome.tsx` `TournamentCard`/`PastCard`, render the logo on the left via `GET /tournaments/{slug}/logo` when set, collapsing the column when absent
- [x] 4.2 Render the subtitle beneath the name when set
- [x] 4.3 Replace the single `organizers · date · location` line with a responsive multi-column date/place block (CSS `flex-wrap`/`grid auto-fit`, relative units, no JS breakpoints)
- [x] 4.4 Apply 1 em left/right inner padding to card content; verify cards render cleanly with any combination of missing logo/subtitle/location
- [x] 4.5 Update `OpenTournament`/`PastTournament` types in `api.ts` with `subtitle` and logo reference

## 5. Tournament detail split (fencer-home / registration)

- [x] 5.1 Add an internal screen state (`information` | `register`) to `TournamentDetail.tsx`; information is the default landing, register is a separate view
- [x] 5.2 Build the information screen: header (name, subtitle, logo, date, location, organizers, window), disciplines list (fee, registered/capacity, optional when/where, optional ruleset name linking to `ruleset_url`), and an other-actions group (seminar/afterparty/after-sparring/accommodation) info-only with when/where/remark and no prices/quantities; no gear/merch mention
- [x] 5.3 Offer a "Register" control on the information screen only when registration is open and at least one discipline/item has an open slot (derive from availability)
- [x] 5.4 Build the Register screen: one long list grouped into sections — tournament (disciplines), actions (seminars/afterparties/after-sparrings), gear lending (rentals), merch & other — each selectable/quantity up to limit, plus accommodation note and notes; reuse the existing price-preview + register API calls unchanged
- [x] 5.5 Preserve the full-discipline queue choice and post-submit switch to the registration/payment view
- [x] 5.6 Keep read-only (past) detail on the information screen only (no Register control)
- [x] 5.7 Update `TournamentDetail`/`Discipline`/`ExtraItem` types in `api.ts` with the new fields

## 6. Organizer setup (tournament-admin)

- [x] 6.1 In `SetupPanel.tsx` add subtitle input and logo upload/preview/remove (calls the logo endpoints), within Bureau 1952 styling
- [x] 6.2 Add discipline row inputs for when/where and ruleset name + link
- [x] 6.3 Add extra-item row inputs for when/where/remark
- [x] 6.4 Add i18n keys for all new Setup labels in `en.json` and `cs.json`

## 7. Styling & design-system compliance

- [x] 7.1 Add any needed classes/tokens for the card logo column, subtitle, responsive date/place block, and the two detail screens using only `tokens.css` values
- [x] 7.2 Audit every new/changed element against the `CLAUDE.md` prohibition list (no gradients, shadows, blur, radius > 2px, pure #FFF/#000, default blue links/focus, emoji/filled icons, weight 600+, Title Case, new hex)

## 8. Verification

- [x] 8.1 Run backend test suite (`backend/tests`) and the frontend lint/build; fix regressions
- [x] 8.2 Manually exercise: signup name-reuse + HR confirmation + id in confirmed line; a card with logo/subtitle and one without; information→register split with grouped sections; a full-discipline queue flow
- [x] 8.3 Run `openspec validate tournament-layout-tweaks` and confirm it passes
