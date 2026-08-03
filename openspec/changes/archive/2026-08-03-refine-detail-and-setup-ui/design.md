## Context

Four defects, all frontend, reported from live use (`openspec/enhancements.md`). Three are small and local; one — the tournament detail page — needs its shell restructured, because the current information/register split is expressed as a mode switch behind a text link, and the container it renders into cannot scroll.

Current state of the affected code:

- `TournamentDetail.tsx:578-658` renders `.login-card.wide-card` → a `"back"` link → `.setup-panel`. `.setup-panel` (`index.css:462`) is the console's layout class: `flex: 1` with `overflow: hidden`, designed for a header + independently scrolling body. Used as a plain wrapper inside a card it clips everything past the flex line, which is the "bottom half is invisible" report. `.wide-card` does set `max-height: 88vh; overflow-y: auto`, but the clipping child never lets the card overflow, so nothing scrolls.
- `.setup-panel` sets no `gap`, so the detail page's `.rail-card` sections abut — the "boxes are stacked together" report. The same class is used by `AdminPanel.tsx:216` and `ProfilePage.tsx:288`, which carry the same defect.
- `TournamentFace.tsx:559` — `const legacy = detail.extra_items.length === 0` — makes the hardcoded afterparty row and four weapon-rental rows appear on every tournament that configures no extra services, i.e. every new one.
- `DisciplineDialog.tsx:73-81` — the derivation effect runs on mount with both touched flags false, overwriting the `initial` name and slug it was just handed.
- `.sheet-table thead th` (`index.css:660`) is `position: sticky; z-index: 1`, so each header cell is its own stacking context; `.help-hint-box`'s `z-index: 5` is confined to it and later cells paint over it.

Binding constraint throughout: `CLAUDE.md` / `openspec/squire-design-spec.md` §8 prohibitions — no shadows, no radius above 2px, no animation, no hex outside `tokens.css`, one saturated color.

## Goals / Non-Goals

**Goals:**

- The detail page reads to its end and its sections stand apart.
- Information and registration become two tabs of one page with a close control, replacing two back links and a register button.
- The registration form offers only what the organizer configured.
- The discipline dialog edits what it was opened on.
- A help hint opened from a table header is readable.

**Non-Goals:**

- No change to any API, schema, or migration. Every decision here is presentational or client-state.
- No removal of the legacy fee data, its Setup fields, or its handling in imports, exports, and existing registrations (owner decision, 2026-08-02).
- No redesign of the registration form's contents beyond the legacy rows; its spacing rules are already specified (`registration` → "Registration form as a priced checklist") and this change only brings the implementation into line with them.
- No new tab or route for amendment.

## Decisions

### D1 — The detail page keeps its card and gains a fixed header over a scrolling body

The page stays `.login-page` → `.login-card.wide-card`; `.setup-panel` is dropped from it. The card becomes a two-part column: a `flex: none` header holding name, tabs, and close, and a `.page-card-body` with `flex: 1; min-height: 0; overflow-y: auto` holding the active tab's sections, with a `gap` that separates them.

Alternative considered: rebuild the page on the console's `.app` / `.topbar` / workspace frame, which already solves fixed-header-plus-scrolling-body. Rejected: the detail page is a fencer-facing document card, not a console; adopting the console frame would change its whole character to fix a scroll.

`.page-card-body` is a new shared class rather than a page-local one, because `AdminPanel` and `ProfilePage` reuse the same `.wide-card` + `.setup-panel` pairing and carry the same clipping. Applying it there is a one-line change per page and is included in tasks, explicitly, rather than left as a known-broken neighbour.

### D2 — The tab control is the existing `.stage-control`, not a new component

Fencer Home and the console preview already express "tabs" as `.stage-control` (`index.css:311`) — an inked box of uppercase segments with the active one inverted. The detail header reuses it verbatim, so the page gains no new visual idiom. The close control is `IconX` from the outline set already imported by `TournamentDetail.tsx`, styled as the existing `.row-action`, carrying `title` + `aria-label` from i18n so it is never announced as an unlabelled glyph.

### D3 — Client state: one tab plus an amending flag

The current `screen: "information" | "register" | "amend"` becomes `tab: "tournament" | "registration"` plus `amending: boolean`. Derived, unchanged from today's predicates:

- second tab is offered when `hasActive || canRegister`;
- its label is `Registered` when `hasActive`, else `Register`;
- on a read-only (past) detail, `canRegister` is already false, so the tab appears only for a held registration and holds the read-only summary;
- registering or amending successfully sets `tab = "registration"`, `amending = false`.

The tab must survive a state change that removes it: cancelling a registration on a closed tournament drops both `hasActive` and `canRegister`. Whenever the second tab is not offered, the page falls back to `tournament`, so no tab can be selected but absent.

### D4 — Legacy fee rows are removed from rendering but preserved on amendment

The `legacy` flag and its rows go. The `afterparty` and `legacyQty` state stays, seeded from the amended registration as it is today, and is still sent in the submit payload.

This matters: an old registration that carries a weapon rental would otherwise lose it the moment its owner amends anything, because the form would submit a selection that no longer mentions it. Keeping the state unrendered means an amendment preserves what it does not offer, and the server's total stays right. New registrations send an empty rental list and `afterparty: false`, exactly as they would if the rows were untouched.

`LEGACY_WEAPONS` stays exported — `DisciplineDialog.tsx:8` builds the weapon taxonomy list from it; only the form's use of it goes.

### D5 — The dialog decides "typed" from the stored values, once, at open

`nameTouched` / `slugTouched` are initialized (lazily, at mount) rather than always starting false:

- for a new discipline (`initial === null`), both start false, as today;
- for a reopened one, each starts `true` when the stored value differs from what derivation would produce for the discipline's **stored** classification, and `false` when it matches.

The derivation effect additionally skips its first run for a reopened dialog, so the stored values survive mount regardless.

The comparison uses the undisambiguated derived slug (`Team-`-prefixed taxonomy code, no collision counter), not `generateDraftSlug`. `generateDraftSlug` disambiguates against the other rows' slugs, so a legitimately generated `LS-2` would compare unequal to `LS` and be misread as an override — which would be harmless for display but would wrongly freeze derivation when the organizer then changes the weapon.

Consequence, and it is the intended one: a discipline whose name and slug were left as generated still tracks a classification change made in the reopened dialog; one whose values were overridden keeps them.

Alternative considered: persist an explicit "overridden" flag per discipline on the server. Rejected as a schema change for a display bug, and the comparison recovers the same answer for every case that matters.

### D6 — Table-header hints open downward, and their cell is raised while open

Two independent problems, two fixes:

- **Clipping.** A hint in a sticky header opens upward (`bottom: calc(100% + 0.3rem)`) into the area above the scroll container's top edge, where it is cut off. Inside `thead`, the box opens downward over the rows instead.
- **Stacking.** The cell's own `z-index: 1` traps the box. The cell is raised while its marker is hovered or focused: `.sheet-table thead th:has(.help-hint-marker:hover)`, and the same with `:focus-within`.

Alternative considered: render the hint in a portal at document level with computed coordinates. Rejected — it needs scroll and resize listeners and would make a static, animation-free element the most complex thing on the page.

`:has()` is available in every browser the project targets (the app already ships `:focus-within` and container-free modern layout); no fallback is added, and without `:has()` the hint degrades to today's behaviour rather than breaking.

### D7 — The rest is token-level CSS

`.detail-logo` goes from 64px to 128px and loses its border. Section spacing comes from `.page-card-body`'s `gap`. The form's instruction and total spacing and the total's right alignment are already required by the `registration` spec and are implemented against `.registration-instructions` and `.form-total` — no new rule beyond making the existing ones true.

## Risks / Trade-offs

- **An amendment silently carries legacy items the fencer cannot see or remove** (D4) → Accepted and deliberate: losing a paid-for rental on an unrelated amendment is worse than not offering to drop it. The items remain visible on the registration summary, and the organizer can still remove them in the console.
- **The comparison in D5 misreads an override that happens to equal its derived value** → It reads it as generated, so a later classification change moves it. Indistinguishable from the organizer's own intent in every case the dialog can observe.
- **`.page-card-body` applied to Admin and Profile changes two pages this change did not set out to touch** → The change is one class swap per page, fixing the identical clipping defect; both are checked visually in tasks. Rolling back means restoring one class name.
- **Tab labels add i18n keys while old detail keys are removed** → `locale-parity.test.ts` fails loudly if `cs` and `en` disagree, so a half-done rename cannot ship.
- **`:has()` unsupported** → hint degrades to current behaviour; no crash, no layout change.

## Migration Plan

None. Frontend-only, no persisted state, no API contract touched. Rollback is a revert of the commit.

## Open Questions

None. The two decisions the owner was asked for on 2026-08-02 — keep the free-text note, leave the legacy fee data and its Setup fields alone — are settled and recorded above.
