## 1. Pure roster helpers

- [x] 1.1 Add `frontend/src/roster.ts` with `rosterChanged(saved, draft)` — an order-sensitive comparison over `name`, `hr_id`, `club`, `nationality` (design D3)
- [x] 1.2 Add `summarizeSaves(results)` to the same module, turning settled per-team results into `{ saved: TeamEntry[], failed: string[] }` of team names
- [x] 1.3 Add `frontend/src/roster.test.ts` covering: unchanged roster, renamed member, reordered members, added member, removed member, rebound member (hr_id/club/nationality), and a partial-failure summary

## 2. Teams tab component

- [x] 2.1 Create `frontend/src/TeamsTab.tsx` and move `RosterEditor` into it out of `TournamentDetail.tsx`
- [x] 2.2 Make `RosterEditor` controlled — props `{ team, members, onChange }`; drop its `dirty`, `busy`, `error`, `save()`, and its own save button, keeping the row actions, the shortfall hint, and the `RosterMemberDialog` slot
- [x] 2.3 Hold the drafts in `TeamsTab` as a map keyed by team id, seeded from `team.members` or from `team.prefill` when the roster is empty (design D2)
- [x] 2.4 Render one `RosterEditor` per team in registration order, each in its own bordered block
- [x] 2.5 Add the single save at the foot of the tab: active when any team is dirty per `rosterChanged`, fanning out over dirty teams with `Promise.allSettled`, pushing each success up through `onTeamUpdated` (design D4)
- [x] 2.6 On partial failure, keep the failed teams' drafts, leave them dirty, and render one message naming them
- [x] 2.7 Turn the add-member control into a `link-button`, still withheld once the roster holds `team_max` members
- [x] 2.8 Add the HRID cell to each member row — `#{{hr_id}}` as muted plain text, rendered empty for an unbound member; give the club cell the same always-rendered treatment so the columns align (design D8)

## 3. Detail page tab control

- [x] 3.1 Widen the tab state in `TournamentDetail.tsx` to `"tournament" | "registration" | "teams"`
- [x] 3.2 Compute `teamsTabOffered = !readOnly && hasActive && registration.teams.length > 0` and render the third tab last in the tab control
- [x] 3.3 Render `<TeamsTab>` as the body of the new tab, wired to `slug`, `registration.teams`, and the existing `onTeamUpdated` handler
- [x] 3.4 Remove the `RosterEditor` loop from `RegistrationPanel`, leaving its amount lines, payment panel, amend and cancel controls untouched
- [x] 3.5 Extend the fallback effect so a selected `teams` tab that stops being offered falls back to `tournament`; confirm `selectTab` still abandons an amendment when leaving the registration tab

## 4. Styling

- [x] 4.1 Draw each team block with a solid hairline border (drop `dashed`) and separate consecutive blocks with vertical space
- [x] 4.2 Add `.param-save-inline` (width auto, `align-self: flex-start`) and use it for the shared save; leave `.param-save` alone (design D6)
- [x] 4.3 Scope the member name field's underline: `.team-row .cell-input` takes the hairline rule at rest and `var(--focus)` on focus (design D7)
- [x] 4.4 Style the HRID cell with a fixed width and muted ink so identifiers, names, and row actions line up down the roster
- [x] 4.5 Re-read the change against the prohibitions in `CLAUDE.md` — no new hex, no radius, no shadow, no second saturated colour

## 5. Localization

- [x] 5.1 Add `detail.tabs.teams` to `frontend/src/i18n/en.json` and `cs.json`
- [x] 5.2 Add `roster.saveAll` (the shared save label) and `roster.saveFailedTeams` (naming the teams that did not save) to both files
- [x] 5.3 Remove `roster.save` if the per-team label is left with no caller, and check `roster.saveFailed` is still used

## 6. Verification

- [x] 6.1 `cd frontend && npm run test` — the new roster tests pass alongside the existing ones
- [x] 6.2 `cd frontend && npx tsc --noEmit` and `npm run build` are clean
- [x] 6.3 Run the app and walk a registration holding two teams: the `Teams` tab appears, both editors show, one save covers both, an edit to one team saves only that team
- [x] 6.4 Check the withheld cases: an individual-only registration shows no `Teams` tab, and neither does a past tournament that held a team
- [x] 6.5 Check the visual asks in the running app — solid borders with a gap, link-style add, save sized to its text, no red underline on an unfocused member row, HRIDs aligned in their own column
