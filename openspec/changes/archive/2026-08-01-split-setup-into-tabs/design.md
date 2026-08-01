## Context

`frontend/src/SetupPanel.tsx` is 1884 lines holding ten section components, each a
self-contained `<section className="rail-card">` with its own local draft state, dirty
flag, busy flag. The default export renders them in a fixed order inside
`.setup-panel`, the left half of `.setup-split`; the right half is `SetupPreview`,
which already carries a two-tab `nav.stage-control`.

The sections are independent — none reads another's state, all refresh from the same
`detail` prop and call the same `onSaved` — which is what makes a tab shell additive.
They are not, however, consistent about saving:

- **Field sections** (identity, organizers, VS series, currency, discounts) hold a
  draft, track `dirty`, and write on their own bottom `button.secondary.param-save`.
  Discounts writes the entire discount list in one `updateTournament` patch.
- **Row tables** (disciplines, extra items) write per row: `saveRow` on a check icon
  that appears in the row when it differs from `detail`, `addRow` on the `+` icon, and
  `removeRow` on the `✕` icon — the last two firing immediately, with no draft stage.
- **`.param-save` is also used by things that write nothing**: "recalculate missing" on
  three sections, and "add discount" on the discount table.
- `usePriceChangeGuard` wraps individual row saves and field saves, so the warning is
  raised once per write.

Owner decisions taken before this design (2026-08-01): five tabs
`TOURNAMENT / DISCIPLINES / EXTRA / PAYMENTS / OTHER`; discounts belong to `PAYMENTS`;
the payment-lifecycle parameters stay in the Payments phase rail; the checklist sits
above the tab bar and marks the tabs holding unconfigured items; all tabs stay mounted;
the preview stays beside every tab; **one save per tab with row tables deferred to it**;
**deleting a drafted row removes it from the list at once**, recoverable only by
leaving the tab unsaved.

## Goals / Non-Goals

**Goals:**

- Make the Setup phase navigable: at most one screenful of sections per tab.
- Make writing unambiguous: one control per tab writes, everything else does not.
- Show the organizer where the remaining configuration work is, from the tab bar.
- Lose no typed-but-unsaved input when moving between tabs.
- Change no section's fields, validation, or persisted result.

**Non-Goals:**

- Splitting `SetupPanel.tsx` into per-section modules. Worth doing, but a large
  mechanical diff that would bury this behavior change.
- A batch or transactional Setup endpoint. The flush uses the endpoints that exist,
  and the interface is honest about the resulting non-atomicity.
- Moving fields between sections, or moving the Payments phase rail parameters.
- Tabs, or a save bar, in any console phase other than Setup.
- URL-addressable settings tabs.

## Decisions

### D1 — A tab table drives the shell and the marker

```ts
type SetupTab = "tournament" | "disciplines" | "extra" | "payments" | "other";
const SETUP_TABS: SetupTab[] = ["tournament", "disciplines", "extra", "payments", "other"];

const MISSING_TAB: Record<string, SetupTab> = {
  location: "tournament",
  organizers: "tournament",
  disciplines: "disciplines",
  discipline_prices: "disciplines",
  extra_item_prices: "extra",
  discount_prices: "payments",
  legacy_fixed_fees_block_eur: "payments",
};
```

The keys are exactly those `backend/app/setup.py` emits. A key absent from the map
yields `undefined` and marks no tab, so a checklist item added on the backend later
still renders as a chip and cannot break the tab bar. Marked tabs are
`new Set(missing.map(k => MISSING_TAB[k]).filter(Boolean))`.

### D2 — Panels stay mounted, hidden with the `hidden` attribute

```tsx
<div className="setup-tabpanel" role="tabpanel" hidden={tab !== "disciplines"}>
  <DisciplinesSection … />
</div>
```

with `.setup-tabpanel[hidden] { display: none }` in CSS, because the panels are flex
items of `.setup-panel` and the UA default for `[hidden]` is not reliable against a
flex parent.

Every section's draft state therefore lives as long as the Setup phase does. With row
tables now deferring their writes (D8), this is what makes a tab switch safe: an added
row, an edited row and a removal all survive it. `display: none` also keeps hidden
panels out of the flex `gap` computation and removes them from the accessibility tree
and the focus order.

*Alternative considered:* conditional rendering. Cheaper DOM, but it would discard
drafted rows on tab switch — which, once rows are deferred, means silently throwing
away work the organizer believes is pending.

### D3 — Tab bar reuses `.stage-control`

The settings tabs are a `nav.stage-control.setup-tabs` with `button.active`, the same
element and classes the preview tabs use, so the two panes read as one system.

ARIA: `role="tablist"` on the nav, `role="tab"` with `aria-selected` and
`aria-controls` on the buttons, `role="tabpanel"` with `aria-labelledby` on the panels,
left/right arrow keys moving between tabs. Focus rings come from the existing
`--focus` rule.

### D4 — The marker is a `--stamp` dot, not a count or an icon

Each marked tab renders a 4px `--stamp` square at `--radius`, plus a visually-hidden
localized label (`setup.tabs.incomplete`) so it is announced rather than being
color-only information. `--stamp` is the app's one saturated color and already means
"needs attention". A count was rejected: the chips above enumerate what is missing, and
a digit inside a 10.5px uppercase label is noise.

Note the two markers are different things and must not be confused: the `--stamp` dot
means *the tournament is not fully configured* (from `setup_missing`, a server fact),
while the save control's count means *you have unwritten changes* (a client fact). They
live in different places — dot in the tab bar, count in the save bar — and the copy
keeps them distinct.

### D5 — Checklist and tab bar form a sticky header of the settings pane

`.setup-panel` is the scroll container. The checklist and tab bar are wrapped in a
`.setup-panel-header` with `position: sticky; top: 0; background: var(--paper)` and a
hairline bottom border. If sticky proves fiddly against the pane's `overflow-y: auto`,
a non-sticky header is acceptable — no requirement depends on it.

### D6 — `OTHER` is not offered to non-owners

`TeamSection` and `DangerZoneSection` are already gated on `isOwner`, so for a
non-owner the tab would open onto nothing. The tab list is
`isOwner ? SETUP_TABS : SETUP_TABS.filter(t => t !== "other")`. `account` loads
asynchronously, so `OTHER` may appear a moment after mount; the default selection is
`tournament`, and no tab can be selected before it is offered.

### D7 — Sections register a saver with the shell instead of owning a save button

Lifting every section's draft state into `SetupPanel` would be a rewrite of all seven
editing sections. Instead each section keeps its state exactly where it is and
publishes a handle:

```ts
type SectionSaver = {
  pendingCount: number;         // 0 when clean
  touchesPrice: boolean;        // drives the price-change warning
  validate: () => boolean;      // marks its own invalid rows, returns false to block
  flush: () => Promise<SaveOutcome[]>;  // performs its writes, resolves per change
};

function useSectionSaver(tab: SetupTab, id: string, saver: SectionSaver): void
```

`useSectionSaver` writes into a `Map<string, {tab, saver}>` held in a ref in
`SetupPanel` and removes itself on unmount. Because all sections stay mounted (D2), the
registry is stable for the life of the phase, and ordering is taken from the section
render order rather than from registration timing.

The save bar for a tab reads every saver registered to that tab: it sums
`pendingCount`, calls `validate()` on each before writing anything, and then calls
`flush()` in section order. `onSaved` (the detail refetch) is called **once**, after
the last flush, instead of once per write as today.

This keeps the diff proportional: field sections lose their save button and gain four
lines of registration; only the two row tables change substantially (D8).

### D8 — Row tables keep a full draft list and diff it at flush time

`DisciplinesSection` and `ExtraItemsSection` currently derive `drafts` from `detail`
and treat `detail` as truth for adds and deletes. They change to owning a draft **list**:

- state becomes `rows: Draft[]` plus `removed: Set<id>`, seeded from `detail` and
  reseeded whenever `detail` changes and the section is clean;
- `+` appends a local row with a client-side temporary id and no server call;
- `✕` removes the row from `rows`, adding its id to `removed` when it exists on the
  server (per the owner's decision, the row leaves the list at once — there is no
  strike-through state);
- `pendingCount` = added + edited + removed;
- `flush()` performs, in this order: deletes, then updates, then creates. Deleting
  first frees any uniqueness the new rows may need (a discipline code reused after
  being removed in the same session is the concrete case), and creating last means a
  create that fails leaves nothing half-linked.

`validate()` reuses the conditions that today disable the `+` button — a discipline
needs a code and a capacity, an extra item a name and a price — and marks the offending
row instead of silently refusing.

An important consequence: because the section reseeds from `detail` only when clean, a
refetch triggered by another tab's save cannot stomp drafted rows.

### D9 — The flush is sequential, non-atomic, and reports per change

There is no batch endpoint, and adding one is out of scope, so a tab save is N requests.
They run **sequentially** rather than with `Promise.all`, because D8's delete-then-
update-then-create order matters and because concurrent writes against the same
tournament make the failure story worse.

On rejection the flush does not stop the other sections: it collects
`{change, error}` outcomes, keeps every failed change pending in its own section,
marks the offending row with the server's reason, and the save bar reports "n of m
written, k still unsaved". Nothing claims success while anything is pending. The
already-written changes stay written — that is inherent to N requests without a
transaction, and the copy says so rather than implying a rollback that did not happen.

*Alternative considered:* abort the whole flush on first failure. Rejected: it makes a
single bad row block ten good ones with no way to proceed, and the already-written
prefix would still not roll back.

### D10 — The price-change warning moves to the save bar

`usePriceChangeGuard` currently wraps each individual write. With one writer per tab,
the guard wraps the flush: the bar asks each saver whether its pending changes
`touchesPrice`, and if any does and `hasRegistrations` is true, `PriceChangeWarning` is
shown once; confirming flushes, cancelling writes nothing. This is strictly better than
today, where an organizer editing five priced rows is warned five times.

### D11 — Non-saving controls drop to the tertiary style

"Recalculate missing" (three sections) and "add discount"/"add row" lose
`.secondary.param-save` and become underlined text actions with no frame, which is the
design system's tertiary treatment. The tab's save control is the only outlined or
filled control in the settings pane. This is the smallest change that fixes the
"which button saves?" problem, independently of everything else here.

### D12 — Leaving Setup dirty is confirmed via one boolean lifted to `Console`

`SetupPanel` already knows the total pending count across tabs (D7), so it passes a
`onDirtyChange(dirty: boolean)` up to `Console`, which intercepts a phase change while
dirty and asks for confirmation. Only a boolean crosses the boundary; `Console` learns
nothing about sections. Tab switches within Setup are never intercepted, because they
discard nothing.

Browser-level navigation (reload, closing the tab) is deliberately left alone — a
`beforeunload` handler is a blunt instrument and this change does not need it.

### D13 — The preview pane is not touched

`SetupPanel`'s return stays `<div className="setup-split">` with `.setup-panel` and
`<SetupPreview>`; only `.setup-panel`'s inner content becomes header + panels + save
bar. The preview keeps its own tab state and keeps rendering `detail`, so it shows
saved state only — with deferred rows this is now visible and useful: the preview is
literally "what fencers see now", against which the tab's pending count reads as "what
they would see after you save".

## Risks / Trade-offs

- **A tab save is not atomic.** A rejected row leaves earlier writes applied. → The
  order (delete, update, create) is chosen so a partial flush leaves a coherent
  tournament, every failure is reported against its row and stays pending, and the copy
  never claims a rollback. A transactional endpoint is the real fix if this becomes a
  practical problem.
- **Deferring deletes changes a destructive interaction's timing.** Today `✕` deletes
  on the server; after this change it removes a row locally and deletes on save. An
  organizer who clicks `✕` and then saves gets the same outcome, but one who clicks `✕`
  and walks away no longer deletes anything. → This is the safer direction, and the
  owner chose it; the save bar's count makes the pending removal visible.
- **Row deletion is not undoable within the tab.** Per the owner's decision, `✕` drops
  the row at once, and recovery means leaving the tab unsaved, which discards the tab's
  other pending changes too. → Accepted deliberately; a strike-through-and-undo state
  was the alternative and was rejected as extra state for a rare misclick.
- **Hidden panels still render, so all ten sections mount on entry.** → Unchanged from
  today. If a table ever grows large enough to matter, virtualize inside it rather than
  unmounting tabs.
- **The saver registry is an indirection.** A reader of `DisciplinesSection` no longer
  sees where its save button is. → One hook name (`useSectionSaver`), one registry, both
  in the same file as every section that uses them, and the alternative was lifting all
  seven sections' state.
- **The tab↔checklist mapping is client-side and can drift** from `setup_missing`. →
  Unknown keys mark no tab instead of throwing; the chip is still shown.
- **`SetupPanel.tsx` grows well past 1900 lines.** → The shell is ~120 lines; the row
  tables get smaller in places (no per-row save button) and larger in others (draft list
  and diff). Splitting the file stays a separate change.

## Migration Plan

No data, API, or storage change. Deployment is a frontend build; rollback is the
previous build, which restores the single scrolling column and immediate row writes,
with no state to reconcile — anything saved under the new build was saved through the
same endpoints.

## Open Questions

None. Tab set, section allocation, checklist placement, tab-state retention, preview
placement, the one-save-per-tab model and the row-deletion behavior were all settled by
the owner before this design was written.
