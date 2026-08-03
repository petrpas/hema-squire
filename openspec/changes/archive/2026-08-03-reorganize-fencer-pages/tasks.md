## 1. Backend list scopes

- [x] 1.1 Move `organized: bool = False` onto `OpenTournamentOut` and delete `PastTournamentOut`, updating its references.
- [x] 1.2 Extract the per-tournament body of `open_tournaments` (availability counts through `_open_discipline_out`, registration status, `my_registration_state`, `organized`) into one helper the three scopes share.
- [x] 1.3 Keep `GET /api/tournaments/open` at `date >= today`, date ascending, now also reporting `organized`.
- [x] 1.4 Add `GET /api/tournaments/held`: published, non-cancelled, `date < today`, date descending, listed for every account regardless of involvement.
- [x] 1.5 Replace `GET /api/tournaments/mine/past` with `GET /api/tournaments/mine`: published, non-cancelled, either direction of today, where the caller holds a registration in any state — cancelled included — or owns the tournament or sits on its console team; date descending.
- [x] 1.6 Update the backend tests that call `/mine/past`, and add coverage for the three scopes: held is public and returns an unrelated tournament with no state and no organizer mark; mine spans both directions; mine carries a cancelled registration and an organizer-only tournament; every scope counts a team discipline in teams.

## 2. Shared shell and tabs

- [x] 2.1 Extract `FencerShell` from `FencerHome`: `.app` → `.topbar` with title, tab control, identity block and account menu, rendering children into `.workspace`.
- [x] 2.2 Lift `tab` into `App.tsx` beside `view`, pass it and its setter into the shell, and make selecting a tab from the detail set the tab and return to `home`.
- [x] 2.3 Extend the tab set to `announced | open | past | mine`, with Announced and Open keeping today's partition of the upcoming list, Past served by `/held`, Mine by `/mine`.
- [x] 2.4 Keep the entry counts on Announced and Open only; do not count Past or Mine.
- [x] 2.5 Give each of the four tabs its own empty-state message in `cs.json` and `en.json`, and add the Mine tab label.
- [x] 2.6 Render Mine's entries with their registration state, or an organizer mark where `organized` is the only bond, and open a held entry read-only.

## 3. Card layout

- [x] 3.1 Replace `.home-card-meta`'s multi-column arrangement with two stacked lines: date · place at weight 500, then organizers.
- [x] 3.2 Double `.home-card-logo` to 88px, keeping the heading column's `min-width: 0` so long names wrap instead of widening the card.
- [x] 3.3 Verify a card degrades with no logo, no subtitle, no location and no organizers — no blank line, no stray middle dot.

## 4. Detail page in the shared shell

- [x] 4.1 Render `TournamentDetail` inside `FencerShell`, dropping its `.login-page` / `.login-card.wide-card` framing and its own `.page-menu-corner` account menu.
- [x] 4.2 Move the tournament name, the `Tournament` / `Register` tabs and the close control into a second row under the topbar, and keep the existing scrolling body beneath it.
- [x] 4.3 Reorder `InfoHeader` to title, subtitle, date · place · qualification, registration opens · closes, organizers, description — omitting a line whose every part is absent.
- [x] 4.4 Give the team-event tag a left margin so it stands off the discipline name.

## 5. Registration presentation

- [x] 5.1 Convert `RegistrationLines` to a two-column grid with amounts right-aligned in `--font-data`, covering disciplines, teams, extras, the total and any outstanding balance.
- [x] 5.2 Render a team's line as `<discipline>: <team name>` against its per-team fee in the amount column.
- [x] 5.3 Add `.btn-danger` (outlined `--stamp`, transparent ground) to `index.css` and a centered, spaced row for a destructive pair.
- [x] 5.4 Present amend and cancel as that pair, each behind the existing static confirmation block; state on the amend confirmation that a paid registration may end up owing more.

## 6. Roster member dialog

- [x] 6.1 Add `RosterMemberDialog`: one name field, `HRSearchPicker` seeded from it, confirming either a selected profile (bound) or the typed name (unbound), cancelling with no effect.
- [x] 6.2 Replace `RosterEditor`'s `team-add-row` and inline pickers with one `Add member` control opening that dialog, and route rebinding through the same dialog seeded with the member's name.
- [x] 6.3 Collapse `newName`, `searchOpen` and `rebindIndex` into one dialog state, and keep each member on exactly one line — name input, club, reorder, rebind, remove.
- [x] 6.4 Add and remove the i18n keys this moves, keeping `cs.json` and `en.json` in step.

## 7. Verification

- [x] 7.1 `npx tsc --noEmit` clean, `npx vitest run` green including `locale-parity.test.ts`, and the backend suite green.
- [x] 7.2 Walk the four tabs in the running app: Announced and Open partition the upcoming tournaments, Past lists a held tournament the account was never part of, Mine lists a registered one and an organized one with the right marks.
- [x] 7.3 Open a tournament from each tab and confirm the heading is unchanged, the second row carries name/tabs/close, and selecting a filter tab leaves the detail for that list.
- [x] 7.4 On a registration holding two disciplines, a team and an extra: amounts align on one column, the team line names discipline and team, amend and cancel are centered and confirm.
- [x] 7.5 Add a member through the dialog — bound and unbound — rebind one, and confirm each member holds one line and the roster carries no inline search.
- [x] 7.6 Re-read against `CLAUDE.md` §8: no shadow, no radius over 2px, no animation, no weight 600+, one saturated color, no hex outside `tokens.css`.
- [ ] 7.7 Archive `refine-detail-and-setup-ui` before archiving this change, so its edit to `Tournament detail — information` is not reapplied over this one.
