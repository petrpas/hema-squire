## Context

Three fencer-facing screens, built at different times, now have to read as one.

Current state:

- `FencerHome.tsx` owns the whole shell — `.app` → `.topbar` (title, `.stage-control` tabs, identity block, account menu) → `.workspace` — and holds `tab` in its own state. `TournamentDetail.tsx` is a centered `.login-page` → `.login-card.wide-card` with its own header row (name, `Tournament`/`Register` tabs, close), added by `refine-detail-and-setup-ui`. Opening a tournament therefore swaps one page frame for another.
- The lists behind the tabs: `GET /api/tournaments/open` (published, non-cancelled, `date >= today`, with `registration_status` and `my_registration_state`) and `GET /api/tournaments/mine/past` (`date < today`, filtered to the caller's registrations and organized tournaments). `PastTournamentOut` is `OpenTournamentOut` plus `organized: bool`.
- `CardHeading` renders logo, name, subtitle, then a `.home-card-meta` row where organizers, date and location are sibling `.meta-cell`s in a responsive multi-column layout.
- `RegistrationLines` (`TournamentDetail.tsx`) renders the registration as a `<ul class="detail-list">` with fees inline in the text; `RosterEditor` renders each member as a `.team-row` and offers adding through a `.team-add-row` input plus a `Search` button that opens `HRSearchPicker` inline — which carries its own query field, so the same name is typed in one box and searched from another.
- `RegistrationPanel` stacks `Amend` and `Cancel` as ordinary secondary buttons; only cancel confirms.

Binding constraints: `CLAUDE.md` / design spec §8 — no shadows, no radius over 2px, no animation, no weight 600+, one saturated color (`--stamp`), no hex outside `tokens.css`. "Bold", throughout this change, means the project's weight 500.

Sequencing: `refine-detail-and-setup-ui` is implemented but not yet archived, so its `Tournament detail — page shell` requirement is not in the main specs. This change's deltas are written to compose on top of it (its `Tournament detail — information` text is the base for the modification here) and assume it archives first.

## Goals / Non-Goals

**Goals:**

- One heading across list and detail, so the detail reads as the same page.
- A tab set that answers "what is on" and "what am I in" separately.
- Cards and the detail information block that read as ordered lines rather than meta soup.
- A registration whose amounts form a column and whose roster is edited through one dialog.

**Non-Goals:**

- No pagination, search, or filtering on the new public Past list.
- No change to how registrations, teams, or money are computed — every change here is presentational or a list scope.
- No change to the organizer console, the picker, or the Setup preview.
- No new saturated color for the destructive controls; `--stamp` is the red the request asks for.

## Decisions

### D1 — Three list scopes, one entry shape, three paths

`OpenTournamentOut` absorbs `organized: bool` (default `false`) and `PastTournamentOut` disappears. Three endpoints serve the same model:

| path | scope | order |
| --- | --- | --- |
| `GET /api/tournaments/open` | `date >= today` | date ascending |
| `GET /api/tournaments/held` | `date < today` | date descending |
| `GET /api/tournaments/mine` | either direction, caller registered (any state) or organizing | date descending |

`GET /api/tournaments/mine/past` is replaced by `/mine`, whose predicate is the old one minus the date bound and minus the "non-cancelled registration" filter — Mine holds a cancelled registration too.

Alternative considered: one endpoint with `?scope=`. Rejected: `/open` is referenced by four backend test modules and by the frontend; three named paths keep the existing one untouched and each predicate readable at its own route. The shared body (availability counts, own state, organizer mark) is one helper all three call, so the shapes cannot drift.

Both new lists count team disciplines through the kind-dispatching `_open_discipline_out` helper, so neither can repeat the `taken_seats` assertion failure that made `/open` return 500 on any tournament with a team discipline.

### D2 — The shell is lifted out of `FencerHome`, and the tab lives in `App`

A `FencerShell` component owns `.app` → `.topbar` (title, the four tabs, identity, account menu) and renders its children into `.workspace`. `FencerHome` and `TournamentDetail` both render inside it, which is what makes the heading identical rather than merely similar.

`tab` moves from `FencerHome`'s state into `App.tsx`, beside `view`. Selecting a tab while a detail is open sets the tab and sets `view = "home"` — the detail closes and the chosen list appears, which is the behaviour the shared heading implies. Without lifting, the detail's copy of the heading would either be inert or hold its own tab state and disagree with the list's.

The detail therefore stops being a centered card. Its second row (`name`, `Tournament`/`Register`, close) becomes a band under the topbar, and the scrolling body it already has (`.page-card-body`) becomes the workspace's scrolling body. `.wide-card` and `.login-page` remain in use by the picker, profile and admin pages and are not touched.

### D3 — Card and detail lines are explicit lines, not a meta grid

`.home-card-meta`'s multi-column arrangement is replaced by two stacked lines: date · place in weight 500, then organizers. Both wrap; neither truncates. `.home-card-logo` doubles from 44px to 88px, and the heading column keeps `min-width: 0` so a long name still wraps rather than pushing the card wide.

The detail's `InfoHeader` gets the same treatment with the request's line order — title, subtitle, date · place · qualification, registration window, organizers, description. `DotJoined` already drops absent parts and is what keeps a line with one missing part from showing a stray dot; a line whose every part is absent is not rendered at all.

Keeping organizers on the detail is a deliberate deviation from the request's line list, recorded in the proposal: they are public credit the organizer configured, and the card is otherwise their only home.

The team-event marker gets left margin. It is a `.tag`, so the margin goes on the tag inside the discipline name, not on the row.

### D4 — Amounts become a grid column shared by every line of a registration

`RegistrationLines` moves from `<ul class="detail-list">` to a two-column grid: description in the first column, amount in a right-aligned second column using `--font-data` (the tabular face already used for `.checklist-price`). Disciplines, teams, extras, the total and any outstanding balance all sit on that grid, so the total closes a column that exists rather than one implied by prose.

A team's description reads `<discipline>: <team name>`, per the request's example, which also makes the line self-describing when the roster below it is collapsed.

### D5 — One dialog for naming a member, opened from one control

A `RosterMemberDialog` replaces both inline blocks: it holds one name field, embeds `HRSearchPicker` with `initialQuery` seeded from that field, and confirms in one of two ways — selecting a search result binds the member to that profile; confirming the typed name adds it unbound. `HRSearchPicker` is used without `lockedQuery`, but the dialog passes its own name down, so there is exactly one name field on screen at any moment.

The same dialog serves rebinding, opened on the member and seeded with their name. `RosterEditor` keeps its inline rename input, its reorder and its remove actions — all on the member's single line — and loses `newName`, `searchOpen` and `rebindIndex` in favour of one `dialog: {mode, index} | null`.

Alternative considered: keep the inline block and merely hide the picker's query field with `lockedQuery` (as signup does). Rejected: it leaves the add-row and the results list on the roster, which is the crowding the request objects to.

### D6 — Destructive controls are outlined, not filled

A `.btn-danger` class: `--stamp` border, `--stamp` text, transparent ground — the outlined shape of `button.secondary` in the one saturated color. Filling them would put two filled `--stamp` buttons on a screen that is allowed one primary.

Amend gains the confirmation cancel already has, using the same static `.rail-card.dashed` block rather than a new pattern. The pair sits in a centered row with a gap.

Amend is destructive in the sense that matters here: on a paid registration it can change what is owed. The confirmation states that before the form opens.

## Risks / Trade-offs

- **The public Past list grows without bound** → Accepted for now: the deployment holds single-digit tournaments per year and the entry is small. When it stops being true the fix is a limit on the `held` scope, which does not change the entry shape. Recorded here so it is a decision rather than an oversight.
- **Confirming an amendment adds a step to a non-destructive-feeling action** → Requested explicitly. The confirmation names the consequence (a paid registration may end up owing more) instead of asking a generic "are you sure".
- **Lifting `tab` into `App` couples two pages through it** → It is one string with four values, and it is what makes the heading real rather than decorative. The alternative — a second tab state in the detail — can disagree with the list.
- **Mine overlaps the other three tabs** → By design: the first three partition every published tournament and Mine cuts across them. The spec states the overlap so it is not read as a bug.
- **This change's `fencer-home` delta is written on top of an unarchived change** → If `refine-detail-and-setup-ui` is archived after this one, its edit to `Tournament detail — information` would be reapplied over this one. Archive in order; the tasks note it.
- **Dropping `/mine/past`** → Only `FencerHome` calls it; its backend tests move to `/mine` with the widened predicate.

## Migration Plan

No data migration. The API changes are additive except `GET /api/tournaments/mine/past`, which is replaced by `GET /api/tournaments/mine` in the same commit as its only caller. Rollback is a revert.

## Open Questions

None. The owner settled the tab semantics on 2026-08-02: the third tab holds tournaments already held and is labelled Past, and Mine carries organized tournaments alongside registered ones.
