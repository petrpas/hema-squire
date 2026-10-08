## Why

Below the 1300px content threshold the Setup preview falls beneath the settings,
so on a laptop or tablet it sits at the bottom of one long scroll: past every
section of the selected tab and its save bar. To check what a saved change looks
like, the organizer scrolls the whole tab away, and the tab bar — the one
fixed point of the pane — scrolls away with it. A preview that has to be
scrolled to is a preview nobody looks at.

## What Changes

- Below the 1300px threshold the preview SHALL no longer stack under the
  settings. It becomes the last tab of the settings tab bar — `PREVIEW`,
  after `PUBLISH` — and its content moves into that tab's panel.
- The narrow layout keeps the settings pane's fixed header and its own
  scrolling body, as on wide screens; nothing scrolls the tab bar away.
- The `PREVIEW` tab carries no save control, no incompleteness marker and no
  unsaved marker, and is never offered on a wide screen, where the preview
  stays beside the settings exactly as today.
- The preview keeps its own face/form tabs, its selection and its scroll
  position whether it is shown in the side pane or in the `PREVIEW` tab, and
  across switching to it and away.
- Crossing the threshold while `PREVIEW` is selected returns the settings pane
  to the settings tab that was selected before it.
- **BREAKING (spec only)**: the "narrow viewport stacks the panes" scenario of
  `setup-preview` and the "preview present on every tab" guarantee of
  `setup-navigation` are replaced for the narrow layout.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `setup-preview`: below the threshold the preview is reached through its own
  settings tab instead of falling below the settings.
- `setup-navigation`: the tab bar gains a layout-dependent last tab, `PREVIEW`,
  outside the mode's fixed order and with no save control or markers; the
  "preview beside the settings on every tab" guarantee holds on wide screens
  only.

## Impact

- `frontend/src/SetupPanel.tsx` — reads the viewport against the threshold,
  adds the `PREVIEW` tab and panel, renders the preview once in whichever
  place the layout calls for.
- `frontend/src/setup/shared.tsx`, `frontend/src/setup/SetupTabBar.tsx` — the
  tab type and title for `PREVIEW`.
- `frontend/src/setup/SetupSaveBar.tsx` — not rendered on `PREVIEW`.
- `frontend/src/index.css` — the 1300px block stops stacking `.setup-split`
  and instead hides the side pane; `tokens.css`'s note on that threshold is
  reworded.
- `frontend/src/i18n/{cs,en}.json` — one new tab label; every settings and
  preview tab label unified on an initial capital (rendered uppercase anyway,
  so only the accessible names change).
- A new viewport hook that follows the threshold live (the existing
  `useWideViewport` reads once at mount, on purpose, and is not reused).
- No backend, API or data change.
