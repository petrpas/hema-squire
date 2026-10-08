## 1. Viewport and tab model

- [x] 1.1 Add `useSetupSplitFits()` (live `matchMedia("(max-width: 1300px)")` via `useSyncExternalStore`, wide when `matchMedia` is unavailable), its comment naming the `index.css` site (design D3)
- [x] 1.2 Add `SetupBarTab = SetupTab | "preview"` in `setup/shared.tsx`; `setupTabTitleKey` maps `preview` to `setup.tabs.preview` (D4)
- [x] 1.3 Add `setup.tabs.preview` to `i18n/cs.json` (`Náhled`) and `i18n/en.json` (`Preview`) (D6)
- [x] 1.4 Capitalize the first letter of every other `setup.tabs.*` tab label and both `preview.tabs.*` labels, cs and en; leave `setup.tabs.incomplete`/`unsaved` lowercase; update any test that queries a tab by its old lowercase name (D6)

## 2. SetupPanel and SetupTabBar

- [x] 2.1 `SetupTabBar` takes `SetupBarTab[]` and `SetupBarTab`; `PREVIEW` never carries a marker; arrow-key cycling includes it
- [x] 2.2 `SetupPanel` holds `previewOpen` beside the settings tab; derives the selected bar tab; clears `previewOpen` when the viewport widens; selecting a settings tab clears it (D4)
- [x] 2.3 Append `preview` to the bar's tabs only on a narrow viewport
- [x] 2.4 Hide `SetupSaveBar` with the body while `PREVIEW` is selected, keeping it mounted so a failure report survives
- [x] 2.5 Add the `previewing` modifier to `.setup-split`; on a narrow viewport give `SetupPreview` the tabpanel role, id and `aria-labelledby` (D1)

## 3. SetupPreview

- [x] 3.1 Accept a `shown` prop and the optional tabpanel ARIA attributes; record `scrollTop` when hidden and restore it when shown (D2)

## 4. CSS

- [x] 4.1 Rewrite the 1300px block: `.setup-split` a non-scrolling column; panel keeps fixed header and scrolling body, full width; `.setup-preview` hidden unless `.previewing`; with `.previewing` the panel body is hidden and the preview fills the column with its own scroll and no side border (D1, D5)
- [x] 4.2 Update the threshold comments in `index.css` and `tokens.css` to name the preview tab and the hook (D3)

## 5. Tests

- [x] 5.1 Narrow (stubbed `matchMedia`): the bar ends with `PREVIEW` after `PUBLISH`; selecting it shows the preview and no save control; other tabs keep their markers, `PREVIEW` has none
- [x] 5.2 Narrow: registration-form selection and a ticked discipline survive `PREVIEW` → `DISCIPLINES` → `PREVIEW`
- [x] 5.3 Widening while on `PREVIEW` returns to the prior settings tab and drops `PREVIEW` from the bar; narrowing again does not select `PREVIEW`
- [x] 5.4 Wide (no `matchMedia`): no `PREVIEW` tab, preview beside the settings as before

## 6. Checks

- [x] 6.1 `npm run typecheck`, `npm run check`, and `npm test` in `frontend/` pass
- [x] 6.2 Check by eye at ~1000px and ~1400px wide: header fixed while scrolling a long tab, preview reachable, nothing in the `CLAUDE.md` prohibitions introduced
