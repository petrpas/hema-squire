## Why

The floor console lays out its work differently from the office console. The office
gives every phase a right-hand panel, "Operace · <fáze>", which holds only what that
phase does. The floor keeps the schedule in that place on every tab and scatters each
tab's actions through its content: the publish gate between the variants, the close
gate in the check-in list, the draw, print and close controls inside the pools. The
owner asked for one logic across both consoles. The schedule gets a tab of its own, and
the right panel holds the actions of the tab it stands beside.

This change belongs to the **floor** context only. It touches no office code and no
backend. The office console is the model it copies, not something it changes.

## What Changes

- **Operations panel.** Every floor tab with something to act on SHALL get a right-hand
  panel, "Operace · <tab>", built like the office console's rail. It holds that tab's
  tab-level actions and the operation's parameters:
  - Plán: preferences, ask for variants, re-plan, the publish gate, adding a pin, the
    Obsazení re-run and prints.
  - Prezence: the selected discipline's counts and its close/reopen gate.
  - Skupiny: draw, redraw and announce, the call list, close/reopen, and the piste links.
  - Pavouk: confirm, print, reopen.
  - Výsledky: publish/withdraw, CSV, PDF.
  - Data: the link to the office Import phase.

  Row-level actions stay in their row, as in the office: choosing a variant, setting a
  seat, removing a pin, a tick, a lineup, a substitute. A tab with nothing to act on
  (Přehled, Rozvrh, Nastavení) shows no panel, and its work takes the full width.
- **BREAKING (layout).** The schedule no longer stands beside the work.
  - **Rozvrh tab.** "Rozvrh" becomes a rail tab of its own, placed right after Plán. It
    has its own address, `/floor/schedule`.
  - **Only with a schedule.** The tab exists only with "Plánovat rozvrh" on. This is a
    named exception, approved by the owner, to "no setting adds or removes a tab".
  - **No narrow-only tab.** The narrow-screen ninth "Rozvrh" tab goes away, because the
    tab is now the same on every width.
- **Discipline tabs.**
  - **Tabs instead of the drop-down.** On Prezence, Skupiny, Pavouk and Výsledky, a strip
    of discipline tabs replaces the discipline drop-down. Výsledky changes from listing
    every discipline to showing the selected one, as the other step tabs do.
  - **Prezence's first tab.** Prezence's strip starts with "Všichni", which lists every
    person, as Prezence does today without a discipline.
  - **The choice is kept.** The selected discipline carries over when the organizer moves
    between rail tabs.
- **Narrow screens.**
  - **A drawer.** Below the canonical breakpoint, the operations panel becomes a drawer.
    It opens over the work, on top of it in the z-axis, from a control at the head of the
    work.
  - **No motion.** The drawer appears and disappears without motion, because the design
    system forbids transform transitions.
- **Unchanged.** The rail of icons on the left stays as it is. "Same logic as the
  office" covers the work area and its right panel, not the tab bar (owner decision
  2026-11-17).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `floor-console`:
  - The tab list gains a conditional "Rozvrh" after "Plán".
  - The schedule-panel requirement is replaced by an operations-panel requirement.
  - A discipline-strip requirement is added, with the choice kept across tabs.
  - The rail's narrow-screen rule loses the ninth tab and gains the drawer.
- `floor-plan`:
  - The schedule is drawn on the Rozvrh tab, with the version and day choice there.
  - The scenarios that pointed at "the schedule panel" point at Rozvrh.
  - Plan's tab-level actions sit in its operations panel.
- `floor-officials`:
  - Officials are named on the Rozvrh tab instead of the schedule panel.
  - The Obsazení re-run and prints sit in Plán's operations panel.
- `floor-today`:
  - A step tab's discipline is chosen by a strip of discipline tabs.
  - The selection is kept across tabs. An address without a discipline opens at the one
    last chosen.
- `floor-results`:
  - The tab shows the selected discipline's standing, not all of them.
  - Its export, print and publish gate sit in the operations panel.

## Impact

- **Frontend only.** The change lives in `frontend/src/floor/`.
  - `FloorConsole.tsx`: layout, the remembered discipline, the drawer.
  - `tabs.ts`: `schedule` becomes a `FloorTab`, after `plan`.
  - `FloorRail.tsx`.
  - `schedule/SchedulePanel.tsx` becomes the Rozvrh tab.
  - Each tab component is split into its work and its rail panel: plan, checkin, pools,
    bracket, results, data.
  - A new shared component holds the discipline strip, and another the operations panel.
- **Routes.** `routes.floorPath` gains the `schedule` tab. `FloorRoute` resolves
  `/floor/schedule` to the default tab when no schedule is planned.
- **CSS.** `index.css` gains a floor workspace grid with the right rail, reusing the
  office's `.rail` and `.rail-card`, the discipline strip, and the drawer.
- **Unchanged.** There is no backend, API or migration change.
- **Tests.** Floor console, plan, pools, bracket, results and check-in tests are updated
  for where controls now are.
