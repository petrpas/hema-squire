## 1. Frame: tabs, layout, rail, drawer

- [x] 1.1 `tabs.ts`: add `"schedule"` to `FLOOR_TABS` after `"plan"`. Delete `SCHEDULE_TAB` and `FloorBarTab`. `barTabs(planned)` drops `schedule` when no schedule is planned. Add `STEP_TABS` (`checkin`, `pools`, `bracket`, `results`).
- [x] 1.2 `FloorRoute.tsx`: resolve `schedule` with `summary.plan_schedule === false` to the default tab, as an unknown tab is resolved.
- [x] 1.3 `Modal.tsx`: add `placement?: "center" | "drawer"`, defaulting to `"center"`. Add the `.modal-drawer` CSS: right edge, below the top bar, `--paper-raised`, a `--rule-strong` left rule, no shadow, no transition.
- [x] 1.4 Add `floor/OperationsRail.tsx`: an `<aside className="rail">` with a `rail-title` reading "Operace · <tab label>", an `aria-label`, and its children.
- [x] 1.5 Add `floor/FloorLayout.tsx`:
  - Props: `head`, `rail` and `children`.
  - Wide: the work plus `OperationsRail` where `rail` is given.
  - Narrow: an "Operace" control in the head, only where `rail` is given, that opens the rail content in `Modal placement="drawer"` with a close control.
- [x] 1.6 Add `floor/DisciplineStrip.tsx`:
  - A horizontal `tablist` of the disciplines, with an optional leading "Všichni".
  - Navigates by `floorPath`; the left and right arrows move along it.
  - The current tab is marked by tokens, not by colour alone; it scrolls sideways within itself.
- [x] 1.7 `FloorConsole.tsx`:
  - Remove `SchedulePanel`, `scheduleOpen`, `revision` and the narrow schedule branch.
  - Keep the discipline last chosen on a step tab, and build the rail's step-tab addresses with it.
  - Pass it down as each step tab's fallback.
  - Keep the leave-Setup confirmation working with the kept discipline.
- [x] 1.8 CSS: make `.floor-workspace` a two-column grid of work and `.rail`. Remove the `.floor-schedule` aside rules. Add the strip's styles and the head row with the "Operace" control, all from tokens.
- [x] 1.9 Add i18n keys (cs/en): `floor.tabs.schedule` stays "Rozvrh"; the "Operace" control; "Všichni"; the close control of the drawer; each panel's one-line "nothing to do now" statements.

## 2. Rozvrh tab

- [x] 2.1 Move `schedule/SchedulePanel.tsx` to `schedule/ScheduleTab.tsx`:
  - Rendered in `FloorLayout` with no rail.
  - The version and day choices sit in its head.
  - It reads the plan, setup and officials on mount.
  - It keeps the "no plan yet" line.
- [x] 2.2 Wire `tab === "schedule"` in `FloorConsole`, and check that `IconCalendarTime` stays in `TAB_ICONS`.

## 3. Plán

- [x] 3.1 Split `WorkingSection` into `WorkingDiff`, the difference for the work, and `PublishGate`, holding publish with its obstacles and confirmation, and re-plan, for the rail.
- [x] 3.2 Split `PinsSection` into `PinList`, the work's list with remove, and `PinForm`, the rail's add form.
- [x] 3.3 Move the officials' re-run and prints out of `AssignmentSection` into `AssignmentActions`, for the rail. The seat setting stays in the table.
- [x] 3.4 Recompose `PlanTab` in `FloorLayout`:
  - Rail: `PreferencesSection`, ask for variants, `PublishGate`, `PinForm`, and `AssignmentActions` where officials are planned.
  - Work: `WorkingDiff`, `VariantsSection` with its per-variant choice, the assignment table, `PinList` and the sensitivity.
  - With setup missing, the work states it and the rail keeps the preferences.

## 4. Prezence

- [x] 4.1 `CheckinTab`: add `DisciplineStrip` with "Všichni" leading, and search in the head.
  - Under a discipline, list only its entrants.
  - Under "Všichni", list everyone.
- [x] 4.2 Move `DisciplineGate` into the rail.
  - Under a discipline: its counts and its close or reopen gate.
  - Under "Všichni": one compact gate per discipline.
  - The confirmations stay `Modal`.

## 5. Skupiny

- [x] 5.1 `PoolsTab`: replace the `<select>` with `DisciplineStrip` and use the console's fallback discipline. Keep the "taken over" and "check-in open" statements in the work, with the rail's one-line "nothing to do now".
- [x] 5.2 Add `DrawActions`: draw and redraw, and announce, in the rail. Swaps and scores stay in `DrawView`.
- [x] 5.3 Add `RunningActions`: print, the call list and close, in the rail. Add `ClosedActions`: reopen, with the refusal stated, in the rail.
- [x] 5.4 Move `RingKeys` into the rail as its own card, on every state of the tab.

## 6. Pavouk and Výsledky

- [x] 6.1 `BracketTab`: replace the `<select>` with `DisciplineStrip`, and move confirm, print and reopen into the rail.
- [x] 6.2 `ResultsTab`:
  - Add `DisciplineStrip` with the console's fallback, and show only the current discipline's standing and state.
  - Move publish or withdraw, CSV and PDF into the rail.
- [x] 6.3 `DataTab`: move the source line and the link to office Import into the rail. With nothing to link, there is no rail.

## 7. Tests and checks

- [x] 7.1 `floorConsole.test.tsx`:
  - Rozvrh is fourth with a schedule and absent without one, and `/floor/schedule` without a schedule lands on the default tab.
  - No ninth tab exists only on narrow.
  - `today` has no rail.
  - The discipline kept from `pools` is opened on `bracket` after a detour through `today`.
- [x] 7.2 Narrow drawer test: "Operace" opens a `dialog` holding the rail's content, Escape closes it, and focus returns to the control. A tab without a rail shows no control.
- [x] 7.3 Update the `planTab`, `assignment`, `pools`, `bracket`, `results` and `checkin` tests to find the moved controls inside the operations panel by its accessible name. Add one test per tab that a row-level action, such as "Vybrat" or a swap, stays in the work.
- [x] 7.4 Add a `results` test: with three disciplines, only the current one's standing shows, and the publish gate acts on it.
- [x] 7.5 From `frontend/`, `npm run typecheck`, `npm run check`, `npm test` and `npm run build` all pass.
- [ ] 7.6 Check by hand in the running app, wide and at 375px:
  - each tab's panel, and the drawer;
  - the strip scrolling within itself;
  - no horizontal page scroll;
  - none of the CLAUDE.md design prohibitions present, in particular no shadow on the drawer and no motion.
