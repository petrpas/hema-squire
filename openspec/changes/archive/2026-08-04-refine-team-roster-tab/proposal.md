## Why

Roster editing is currently stacked underneath the money on the registration
tab: every team the fencer entered opens its own dashed card, its own "Add
member" button and its own full-width save button, so a two-team registration
shows two save buttons below the amount lines and the fencer has to scroll past
the price to reach the people. The member rows also carry the sheet-table cell
underline — a 2px `--stamp` rule — which reads as an error on every single
member, and a member bound to an HR profile shows nothing to say so.

## What Changes

- The tournament detail page offers a third tab, `Teams`, beside `Tournament`
  and `Registration`. It appears only when the fencer's active registration
  holds at least one team, and it carries every roster editor; the registration
  tab keeps the money lines and loses the editors.
- Each team's card is drawn with a solid hairline rather than a dashed one, and
  consecutive team cards are separated by a gap so they read as distinct
  blocks.
- "Add member" becomes a `link-button`, matching how every other add control on
  the setup panels is offered.
- One save button serves all teams on the tab: it is enabled while any roster
  is dirty, sits at the tab's foot sized to its own text rather than the full
  width, and saves each dirty team in turn — successes stick, and the error
  names the teams that did not save.
- The member name field drops the `--stamp` bottom rule at rest; it carries the
  ordinary hairline underline and turns `--stamp` only on focus, exactly as
  other text fields do.
- Roster rows gain an HRID column showing `#<id>` as muted plain text for
  members bound to an HR profile, empty for unbound ones.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `team-disciplines`: where the roster editor lives (its own tab rather than
  the registration panel), that one save covers every team, and that a bound
  member's HR id is shown on their row.
- `fencer-home`: the tournament detail page shell — its tab control gains a
  third tab and the rule for when it is offered.

## Impact

- `frontend/src/TournamentDetail.tsx` — tab state widens to a third value, the
  roster editors move out of `RegistrationPanel` into a new tab body; the file
  is already 712 lines, so the teams tab is extracted to its own file.
- New `frontend/src/TeamsTab.tsx` (roster editors + the shared save).
- `frontend/src/index.css` — team card gap, solid border, scoped member-input
  underline, an auto-width save variant, HRID column.
- `frontend/src/i18n/en.json`, `frontend/src/i18n/cs.json` — the `Teams` tab
  label, the combined save label, the partial-failure message, the HRID column
  header.
- No backend change: `PUT` roster stays one call per team.
