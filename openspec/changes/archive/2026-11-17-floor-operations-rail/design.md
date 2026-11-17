## Context

`FloorConsole.tsx` draws three things side by side: the icon rail, the current tab's work,
and the schedule. The schedule is `SchedulePanel` beside every tab but Setup. On a narrow
screen it becomes a bar-only ninth tab that never reaches the address. Each tab draws
its own actions inline:
- `WorkingSection` carries the publish gate and re-planning.
- `DisciplineGate` sits inside the check-in list.
- `DrawView`, `RunningView` and `ClosedView` carry the pools' controls, and `RingKeys`
  sits under the pools.
- `BracketTab` and `ResultsTab` carry their buttons beside their tables.

The office console draws its rail in `Console.tsx` as `renderRail(panel)`. That is an
`<aside className="rail">` with a `rail-title` reading "Operace · <phase>", then
`rail-card`s for the phase's operation and its parameters. The owner's decisions of
2026-11-17 make the floor follow that pattern:
- The icon rail stays.
- Rozvrh becomes a tab after Plán, only with a schedule.
- Discipline tabs replace the drop-down, and the choice is kept across tabs.
- On a narrow screen the panel is a drawer over the work.

## Goals / Non-Goals

**Goals:**
- **One shape for every tab.** Work on the left, operations on the right, each tab
  deciding what goes where.
- **No panel where there is nothing to act on.**
- **Rozvrh as an addressable tab**, `floorPath(slug, "schedule")`.
- **One discipline strip** shared by the four step tabs, with the choice kept in the
  console.
- **A narrow drawer** that is a real dialog (`Modal`), with no motion.

**Non-Goals:**
- **Backend.** No backend, API or schema change. No new endpoint.
- **The left rail.** No change to the icon rail beyond the conditional tab.
- **The office console.** It is unchanged. The floor reuses its CSS classes and
  changes none of its components.
- **Remembering across visits.** The discipline is remembered for the session only.
  There is no localStorage.

## Decisions

### D1. The tab composes its own layout through `FloorLayout`

A new `floor/FloorLayout.tsx` takes `head?: ReactNode` (the strip, search), `rail?:
ReactNode` and `children`.
- **Wide.** It renders the work and, where `rail` is given, an `OperationsRail`.
- **Narrow.** It renders the work with an "Operace" control in the head that opens the
  drawer.

Each tab component renders `FloorLayout` itself, because the work and the panel share
the tab's state. For example, the pools view feeds both the sheets and the close gate.

- **Why not two exports per tab?** Exporting `Work` and `Rail` separately and composing
  them in `FloorConsole` would force the tab's state up into the console, or into a
  context per tab. The office solves the same problem by handing `renderRail` the panel.
  Here the tab owns both, which keeps `FloorConsole` thin, as CLAUDE.md asks.

### D2. `OperationsRail` reuses the office's `.rail` markup

`floor/OperationsRail.tsx` renders the same shape as the office: an
`<aside className="rail">`, a `.rail-title` reading `{t("rail.operations")} ·
{t("floor.tabs.<tab>")}`, and the children as `.rail-card`s.

The floor workspace becomes a two-column grid, `.floor-work` and `.rail`, under
`.floor-workspace`. The old `.floor-schedule` aside rules are removed.

- **Why not a floor-specific panel style?** One look across both consoles is the point
  of the change.

### D3. The narrow drawer is `Modal` with a drawer placement

`Modal` gains an optional `placement?: "center" | "drawer"` prop. The default,
`"center"`, keeps every existing dialog as it is. `"drawer"` adds a class that anchors
the dialog's content to the right edge, at the full height of the screen, width
`min(300px, 100vw - 3rem)`.

It is drawn with the panel's own paper and a `--rule-strong` left rule. It has no shadow
and no transition. Focus, Escape and the backdrop come from the native element, as for
every dialog.

The drawer holds exactly the `rail` node the wide layout would draw. The layout chooses
one of the two by `useNarrow()`, so the content is never mounted twice.

- **Why not a CSS-only off-canvas `aside`?** It would have to reimplement focus trapping
  and Escape. CLAUDE.md says a dialog is `Modal`, never a div with a click handler.
- **Why no slide?** `design-system` limits transitions to colour. The owner's "k
  vyjetí" is honoured as placement (from the right edge, over the work) and not as
  motion.

### D4. `DisciplineStrip` and the remembered discipline

`floor/DisciplineStrip.tsx` takes the disciplines, the current slug (or `null`), the tab,
and an optional `all` label for Prezence's "Všichni".
- **Markup.** It renders `role="tablist"` buttons that call
  `navigate(floorPath(slug, tab, d.slug))`. The left and right arrows move along it.
- **Overflow.** `overflow-x: auto` sits on the strip itself.

`FloorConsole` keeps `const [kept, setKept] = useState<string | null>(null)`.
- **Setting it.** An effect sets `kept` whenever the address carries a discipline on a
  step tab.
- **Using it.** `select(next)` in the rail builds `floorPath(slug, next, kept)` for the
  four step tabs, and `floorPath(slug, next)` for the others.
- **"Všichni".** It is the address without a discipline. It never clears `kept`.
- **An address without a discipline** on `pools`, `bracket` or `results` reads `kept`,
  otherwise the first discipline. The console passes `kept` down as `fallback` for
  this. The tab never writes back into the address on its own, so "Všichni" and a bare
  address stay distinguishable.

The `STEP_TABS` set lives in `tabs.ts` beside `FLOOR_TABS`.

- **Why not hold the discipline only in the address?** The address cannot carry it
  through `today` or `plan`, and the owner asked for it to survive the detour.
- **Why not localStorage?** The choice is a working focus for one session. A stale
  discipline on the next day's open would mislead.

### D5. Rozvrh is a `FloorTab`

- **Tabs.** `"schedule"` joins `FLOOR_TABS` after `"plan"`. `barTabs(planned)` drops it
  when `summary.plan_schedule === false`. `SCHEDULE_TAB`, the `scheduleOpen` state and
  the narrow branch are deleted.
- **Route.** `FloorRoute` treats `schedule` without a planned schedule as `!isFloorTab`,
  which lands on the default tab.
- **The component.** `SchedulePanel` becomes `schedule/ScheduleTab.tsx`. It renders in
  `FloorLayout` with no rail and the version and day choices in its head.
- **Freshness.** It reads the plan on mount. The `revision` counter goes away, because
  opening the tab is the refresh.
- **Icon.** `TAB_ICONS.schedule` keeps `IconCalendarTime`.

### D6. What moves where, per tab

| Tab | Work | Operations panel |
|---|---|---|
| Plán | `WorkingSection`'s difference; `VariantsSection` with "Vybrat" per variant; `AssignmentSection`'s table with per-seat setting; the `PinsSection` list with remove; `SensitivitySection` | `PreferencesSection`; "Navrhnout varianty"; "Přeplánovat"; the publish gate with its obstacles and its confirmation; the add-pin form; with officials, the re-run and the prints |
| Prezence | strip with "Všichni"; search; the person list with ticks, withdrawals, lineups, substitutes | `DisciplineGate` for the current discipline, or one compact gate per discipline under "Všichni" |
| Skupiny | strip; the draw table with swaps and scores; pool sheets and standings, each with its own print; the closed ranking | draw and redraw, announce; call list; close and reopen with the refusal stated; `RingKeys` as its own card |
| Pavouk | strip; the bracket with its bouts | confirm; print; reopen |
| Výsledky | strip; the current discipline's standing and its state | publish or withdraw; CSV (standing, bouts); PDF |
| Data | the roster per discipline | the source line and the link to office Import |
| Přehled, Rozvrh, Nastavení | everything | none |

Sections that split are cut along their seams:
- `WorkingSection` → `WorkingDiff` (work) and `PublishGate` (rail).
- `PinsSection` → `PinList` and `PinForm`.
- `AssignmentSection` keeps its table; `AssignmentActions` is new.
- The pools views each export a `…Actions` component next to them.

Files stay under ~300 lines.

### D7. Výsledky filters client-side

`resultsApi` already returns every discipline's row. The tab selects the row whose
`discipline_id` matches the current strip discipline. No endpoint changes.

### D8. Floor boundary

The frontend floor directory keeps importing only what it imports today from outside
`floor/`: `../Modal`, `../routes`, `../api` (types), `../AccountMenu`, `../RequireAuth`
and i18n. `Modal` gains a prop. No backend file is touched, so the backend boundary
(`tests/floor/test_floor_boundary.py`) is unaffected. No import crosses the floor
boundary that did not cross it before.

## Risks / Trade-offs

- **[The 300px rail is narrow for the plan's preferences and the draw's parameters.]**
  → Their fields stack one per line, as the office's `TolerancePanel` does. If a form
  does not fit, that is a finding for review, not a reason to widen the rail beyond the
  office's.
- **[Tests pinned to inline buttons break.]** → `floorConsole`, `planTab`, `assignment`,
  `pools`, `bracket`, `results` and `checkin` tests are updated to find controls in the
  rail by its `aria-label`. Narrow tests open the drawer first.
- **[Under "Všichni", Prezence lists every discipline's gate in a 300px column.]** →
  Each gate is compact (name, counts, one control). Its confirmation with the impact
  opens as the existing `Modal`, not inline.
- **[Rozvrh disappearing with the tick off breaks the "no setting changes tabs" rule.]**
  → The owner approved this as a named exception. It is written into the spec as the
  only one.
- **[A drawer over the work hides what an action changes.]** → The drawer stays open
  after an action and states its result line. Closing it shows the work, already
  reloaded.

## Migration Plan

This is a frontend-only change and ships in one commit. There is no data migration.
Rollback is a revert.
