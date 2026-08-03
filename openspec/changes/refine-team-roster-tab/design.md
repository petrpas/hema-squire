## Context

`TournamentDetail.tsx` (712 lines) holds the whole fencer-facing detail page:
the two-value tab state, `RegistrationPanel`, and `RosterEditor`. Each
`RosterEditor` owns its own `members` array, its own `dirty` flag, its own
`busy`/`error`, and its own save button, and `RegistrationPanel` renders one per
team under the amount lines. Moving the editors to a third tab and giving them
one shared save means the per-editor state has to be lifted; the editors become
controlled, and the save becomes the parent's.

Three constraints shape the work:

- **The design prohibitions in `CLAUDE.md`.** No new hex values, no radius, no
  new saturated colour: the visual asks (solid border, gap, link-style add,
  auto-width save, hairline underline) are all expressible in existing tokens.
- **The 300-line file-splitting convention.** `TournamentDetail.tsx` is already
  over twice that; the teams tab must not be added to it.
- **The frontend has no component-test harness** — `vitest` runs pure modules
  (`numeric.test.ts`, `validation.test.ts`) and there is no jsdom or
  testing-library dependency. Anything worth asserting has to be pure.

## Goals / Non-Goals

**Goals:**

- A third `Teams` tab carrying every roster editor, offered exactly when the
  fencer's active registration on an unheld tournament holds a team.
- One save for all teams, saving only what changed, reporting partial failure
  by team name.
- The six visual corrections: solid card border, gap between cards, link-style
  add-member, auto-width save, hairline member underline, HRID column.

**Non-Goals:**

- No backend change. `PUT /registrations/{slug}/teams/{id}/roster` stays
  per-team; the shared save is a client-side fan-out, not a new bulk endpoint.
- No change to the organizer's read-only `TeamsPanel` in the console (it
  already shows the members it needs).
- No change to what roster editing costs, to the amendment window, or to the
  prefill rule.
- No URL for the new tab — the detail page's tabs stay out of the URL, per the
  existing shell requirement.

## Decisions

### D1 — The teams tab lives in its own file, `frontend/src/TeamsTab.tsx`

`RosterEditor` moves there unchanged in behaviour, and `TeamsTab` becomes the
orchestrator holding the shared draft state and the save. `TournamentDetail`
keeps the tab control and passes `slug`, `registration.teams`, and
`onTeamUpdated`.

*Alternative considered:* keep everything in `TournamentDetail.tsx` and just
branch on the third tab value. Rejected — the file is already 712 lines and the
convention splits along component seams; the teams tab is a clean seam.

### D2 — Draft state is lifted into `TeamsTab`, keyed by team id

`TeamsTab` holds `drafts: Map<number, RosterMember[]>` seeded from
`team.members`, or from `team.prefill` when the roster is empty (the existing
`RosterEditor` initialiser, moved up). `RosterEditor` becomes controlled:
`{ team, members, onChange }` — it keeps its row actions and its dialog slot,
but owns no `dirty`, no `busy`, and no save.

Dirtiness is derived, not stored: a team is dirty when its draft differs from
the last-saved `team.members`. Deriving it means a save that succeeds
automatically cleans the team when the new `TeamEntry` flows back down through
`onTeamUpdated`, and an edit that is undone by hand correctly re-disables the
save.

*Alternative considered:* a per-team `dirty` boolean set on every patch.
Rejected — it needs manual clearing on save and would leave the save button
active after an edit was reverted.

### D3 — Dirtiness and fan-out result live in a pure module, `frontend/src/roster.ts`

Two pure functions, unit-testable under the existing vitest setup with no new
dependency:

- `rosterChanged(saved: RosterMember[], draft: RosterMember[]): boolean` —
  order-sensitive comparison over `name`, `hr_id`, `club`, `nationality`.
  Order matters because the roster is an ordered list, so a reorder is a real
  change.
- `summarizeSaves(results: {team, ok}[]): {saved: TeamEntry[], failed: string[]}`
  — turns the settled fan-out into the teams to push down and the names to
  report.

The component keeps only the `await`; everything with a truth value is testable.

### D4 — The save fans out with `Promise.allSettled`, not a loop that throws

Every dirty team is submitted; a rejection on one does not stop the others
(spec: "Save all, report which failed"). Successful teams are pushed up through
`onTeamUpdated` one by one, so each becomes clean as its new `TeamEntry`
arrives; failed teams keep their drafts and stay dirty. The error line names
them: `roster.saveFailedTeams` → "Could not save: {{teams}}."

*Alternative considered:* sequential `await` in a `for` loop with a `try` per
team. Equivalent in outcome but serialises N round-trips for no benefit — the
endpoints are independent per team.

### D5 — Tab offer and fallback

`teamsTabOffered = !readOnly && hasActive && registration.teams.length > 0`,
where `readOnly` and `hasActive` are the values `TournamentDetail` already
computes. The tab state widens to `"tournament" | "registration" | "teams"`.

The existing fallback effect gains the third tab: when `teamsTabOffered` drops
while `tab === "teams"` — an amendment removing the last team, a cancellation —
the page falls back to `"tournament"`. `selectTab` already abandons an
amendment when leaving the registration tab, and that covers the teams tab for
free since the guard is `next !== "registration"`.

### D6 — Save button sizing: a new modifier, not a change to `.param-save`

`.param-save` is `width: 100%` and is used by the setup panels' save controls.
The teams tab gets `.param-save.param-save-inline { width: auto; align-self:
flex-start; }` so the shared rule is untouched and the setup panels are not
disturbed. The tab body is a column flex container, which is what makes
`align-self` bite.

### D7 — The member underline is corrected by scope, not by replacing the class

`.cell-input` carries `border-bottom: 2px solid var(--stamp)` because it is the
sheet-table's editable cell, where the accent rule marks "this is editable". In
a roster row every field is editable, so the accent reads as an error on every
member. Rather than introduce a second input class, the rule is scoped down
inside a roster row:

```css
.team-row .cell-input { border-bottom: var(--border-w) solid var(--hairline); }
.team-row .cell-input:focus { border-bottom: var(--focus); }
```

`--focus` is already `2px solid var(--stamp)`, so a focused member field looks
exactly like a focused form field elsewhere. No token is added.

### D8 — The HRID cell is positional and always rendered

The roster is a row list, not a table, and has no header row; adding one for a
single new value would be a heavier change than the ask. The identifier is a
fixed-width cell between the name field and the row actions, rendered even when
empty so names, identifiers, and actions line up down the roster. It is muted
plain text `#{{hr_id}}` — not a link, so the row keeps no navigation (the
organizer's console view is where an identifier is looked up).

The club cell is currently rendered only when a club is set, which already
misaligns rows; it is given the same always-rendered treatment so the two
columns hold their positions.

### D9 — The registration tab keeps its team lines unchanged

`RegistrationLines` already lists each team as a priced line with its members
as read-only text, and that stays: removing the editors from that tab must not
also remove the fencer's ability to see, on the money screen, who is on the
team they are paying for.

## Risks / Trade-offs

- **A fencer who edited rosters and switches tabs loses the drafts** →
  `TeamsTab` stays mounted only while its tab is selected, so leaving and
  returning re-seeds from the server copy. Accepted: the same is already true
  of the current per-team editors, and the alternative (hoisting drafts into
  `TournamentDetail` so they survive a tab switch) spreads roster state across
  the file the change is trying to thin out. The save control's active state is
  the visible cue that there is something unsaved.
- **`rosterChanged` comparing `club`/`nationality` could report a change the
  server would consider a no-op** if the server canonicalises those on binding
  → harmless: it only means the team is submitted and comes back identical.
  Never the reverse, because every field the editor can alter is compared.
- **Partial failure leaves the registration half-written** → each roster is its
  own resource and roster edits touch no money (spec: "Roster editing changes
  no money"), so there is nothing to roll back; the failed teams stay dirty and
  can be saved again.
- **Three tabs on a narrow window** → the tab control is the existing
  `.stage-control` and already wraps; no new layout rule is needed, but the
  narrow case is worth a look when the change is run.

## Migration Plan

None — frontend-only, no schema, no API, no stored state. The change is visible
on the next page load.

## Open Questions

None. The three decisions that were open (tab visibility, HRID rendering,
partial-failure handling) were settled with the owner before this document:
tab only when a team is held, plain `#<id>` text, save-all-and-report.
