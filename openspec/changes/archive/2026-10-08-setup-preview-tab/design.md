## Context

`SetupPanel` renders `.setup-split` with two children: `.setup-panel` (a fixed
`.setup-panel-header` holding `SetupTabBar`, and a scrolling `.setup-panel-body`
holding one `.setup-tabpanel` per tab and the `SetupSaveBar`) and `SetupPreview`
(its own scroll container, with its own face/form tab bar and state).

Below 1300px the CSS turns `.setup-split` into a scrolling column and sets both
panes' `overflow-y: visible`. The preview then follows the save bar, and the
header — no longer the top of a scroll container — scrolls away with the
sections. That already falls short of `setup-navigation`'s "the header SHALL stay
in place while the selected tab's sections scroll beneath it".

The 1300px threshold is documented in `tokens.css` and at its site in
`index.css` as a content threshold, outside the 480/768/1024 set on purpose.

The tab is not in the URL: `SetupPanel` holds it in `useState`, starting on
`tournament`.

## Goals / Non-Goals

**Goals:**
- Below the threshold, the preview is a last tab `PREVIEW` of the settings bar,
  shown beneath the fixed header like every other tab.
- The preview is never remounted by the layout: its face/form selection and
  form selections survive tab switches and threshold crossings.
- The fixed header holds in the narrow layout too.

**Non-Goals:**
- No change to the wide layout, to the preview's content, or to the 1300px value.
- No change to the settings tabs' order, markers, saves or sections.
- Putting the selected Setup tab in the URL.
- The phone layout of Setup in general (the settings sections at 480px are
  untouched by this change).

## Decisions

### D1. The preview stays where it is in the tree; CSS decides where it shows

`SetupPreview` keeps its place as the second child of `.setup-split` in both
layouts. On a narrow viewport `.setup-split` is a column: while a settings tab is
selected, `.setup-preview` is hidden and `.setup-panel` fills the column; while
`PREVIEW` is selected, `.setup-panel-body` is hidden, `.setup-panel` shrinks to
its header, and `.setup-preview` takes the rest of the column as its own scroll
container, at full width, with the side border replaced by nothing (the header's
bottom hairline already separates them). A modifier class on `.setup-split`
(`previewing`) selects between the two.

*Alternative:* render the preview inside a `setup-tabpanel-preview` in the body.
Moving an element between parents remounts it in React, losing the face/form
selection and every ticked box on each threshold crossing; keeping it alive
would mean lifting `RegistrationForm`'s internal state into `SetupPanel`, which
the shared fencer-facing component (`setup-preview`: one implementation) must not
grow for the console's sake. A portal has the same remount problem when its target
changes.

ARIA: on a narrow viewport `.setup-preview` carries `role="tabpanel"`,
`id="setup-tabpanel-preview"` and `aria-labelledby="setup-tab-preview"`, and the
`PREVIEW` tab's `aria-controls` points at it. On a wide viewport it carries none of
them — it is a pane, not a tab's panel.

### D2. The preview remembers its own scroll position

A `display: none` element's `scrollTop` is not reliably kept across browsers.
`SetupPreview` takes a `shown` prop; it follows its `scrollTop` on every
scroll event and restores it when `shown` turns true. It is not read on hiding:
by the time an effect learns of it the element is out of layout and may report 0. On a wide viewport `shown` is
always true. Across a threshold crossing the scroll position is not promised
(spec), since the column it was measured in changes width.

### D3. The threshold is read live, by a hook of its own

`useWideViewport` reads 768px once at mount on purpose (a fencer's form must not
re-layout under them mid-typing) and is not reused. A new
`useSetupSplitFits()` subscribes to `matchMedia("(max-width: 1300px)")` through
`useSyncExternalStore`, so the bar gains and loses `PREVIEW` as the window is
resized. It answers "wide" when `matchMedia` is unavailable (jsdom), so the
existing Setup tests keep the layout they were written for.

The number lives twice, in the hook and in `index.css`. Each site names the
other in its comment; `tokens.css`'s note on the 1300px threshold is reworded
from "the panes stop fitting side by side" to say the preview then moves into
its own tab, and that the hook reads the same value.

### D4. `PREVIEW` is outside `SetupTab`

`SetupTab` stays the settings tabs: `MISSING_TAB`, the `SaverRegistry`,
`dirtyTabs`, `markedTabs` and `SetupSaveBar` are all typed by it, and none of them
has anything to say about the preview. The bar takes
`SetupBarTab = SetupTab | "preview"`. `SetupPanel` holds the selection as the
settings tab (`tab`, as today) plus a `previewOpen` boolean:

- selected = `narrow && previewOpen ? "preview" : settings tab`;
- selecting a settings tab sets it and clears `previewOpen`;
- selecting `PREVIEW` sets `previewOpen` and leaves the settings tab as it was,
  which is what the widening fallback returns to;
- when `narrow` turns false, `previewOpen` is cleared, so narrowing again does
  not reselect `PREVIEW` on its own.

`SetupSaveBar` stays mounted while `PREVIEW` is selected and is hidden with
the rest of `.setup-panel-body` (the `hidden` attribute, with a
`[hidden] { display: none }` rule since the body sets its own `display`).
Unmounting it would discard its report of a failed save the moment the
organizer looked at the preview. `setupTabTitleKey` gains `preview → setup.tabs.preview`.

### D5. The narrow CSS keeps the fixed header

The 1300px block stops setting `overflow-y: visible` on the panes and the body.
`.setup-panel` keeps its column with the header `flex: none` and the body
scrolling, exactly as on a wide viewport; `max-width: 60rem` is lifted so the
pane takes the full width. This brings the narrow layout into line with the
existing "header stays in place" requirement as a side effect.

### D6. Label

`setup.tabs.preview`: cs `Náhled`, en `Preview`.

The bar's labels are unified on an initial capital (owner decision): today they
are lowercase except `Zveřejnění` / `Publish`. Every `setup.tabs.*` label
(`Turnaj`, `Disciplíny`, `Doplňky`, `Termíny`, `Platby`, `Ceny`, `Ostatní`,
`Zveřejnění`, `Náhled`, and their English counterparts) and both preview tab
labels (`preview.tabs.face`/`form`: `Turnaj`, `Přihláška`; `Tournament`,
`Registration form`) take it, since `setup-preview` fixes the two bars as the
same control. Only the first word is capitalized — `Registration form`, not
Title Case. The marker labels `setup.tabs.incomplete` and `setup.tabs.unsaved`
are not tab labels and stay lowercase.

`.stage-control` renders its labels `text-transform: uppercase`, so nothing
changes on screen; the source text is what screen readers announce and what
tests query by, and it is now consistent. The preview's own heading
("náhled: co vidí šermíři") stays inside the panel.

## Risks / Trade-offs

- [The threshold number is duplicated in CSS and TS] → cross-referencing
  comments at both sites and in `tokens.css`; a mismatch shows as a preview
  hidden with no tab to reach it, which a test stubbing `matchMedia` at the
  narrow width catches on the TS side only.
- [Resizing across the threshold mid-edit] → the settings tab and its draft are
  untouched by the switch; only `PREVIEW`'s presence changes.
- [jsdom has no `matchMedia`] → the hook's wide default; new tests stub it.
