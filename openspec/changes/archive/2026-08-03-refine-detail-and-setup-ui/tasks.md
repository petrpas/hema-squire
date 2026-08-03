## 1. Discipline dialog reopens on stored values

- [x] 1.1 In `DisciplineDialog.tsx`, add a helper that derives the undisambiguated name and slug for a kind + classification (taxonomy code, `Team-` prefix, `normalizeSlug`, no collision counter) — the comparison basis from design D5.
- [x] 1.2 Initialize `nameTouched` / `slugTouched` lazily: `false` for a new discipline; for a reopened one, `true` when the stored value differs from the derived one for its stored classification.
- [x] 1.3 Skip the derivation effect's first run when `initial !== null`, so a reopened dialog never overwrites its loaded name and slug on mount.
- [x] 1.4 Verify by hand in the running app: reopen a discipline whose slug was overridden — dialog shows the stored name and slug; confirm without editing — the row is unchanged and the tab reports no new unsaved changes; reopen a generated one and change its weapon — name and slug follow.

## 2. Help hint above table headers

- [x] 2.1 In `index.css`, open `.help-hint-box` downward (`top: calc(100% + 0.3rem); bottom: auto`) when it sits inside a `.sheet-table thead`, so it is not cut off at the scroll container's top edge.
- [x] 2.2 Raise the header cell while its hint is open: `.sheet-table thead th:has(.help-hint-marker:hover)` and `:has(.help-hint-marker:focus-within)` get a `z-index` above the sibling headers' `1`.
- [x] 2.3 Verify by hand: open the slug hint on the disciplines table — the whole box is readable, over the columns to its right and the rows below; reach it by keyboard and confirm the same.

## 3. Registration form offers only configured items

- [x] 3.1 In `TournamentFace.tsx`, remove the `legacy` flag (line 559) and the rows it gates: the afterparty row in the optional-programme section and the weapon-rental rows in the optional-items section.
- [x] 3.2 Keep `afterparty` and `legacyQty` state seeded from an amended registration and keep sending both in the submit payload (design D4), so amending a registration that carries legacy items does not drop them.
- [x] 3.3 Confirm `LEGACY_WEAPONS` remains exported for `DisciplineDialog.tsx`; remove only the form's use of it.
- [x] 3.4 Remove the now-unused `form.afterparty` and `form.weaponRental` keys from `cs.json` and `en.json`, keeping the two files in step.
- [x] 3.5 Make the already-specified spacing true: vertical space above `.registration-instructions` and above `.form-total` visibly larger than the gap between sections, and `.form-total` aligned to the trailing edge of the price column.
- [x] 3.6 Verify in the console's form preview for a tournament with no extra services: disciplines, note and total only — no afterparty row, no rental rows — and the spacing and total alignment as specified.

## 4. Detail page shell

- [x] 4.1 Add `.page-card-body` to `index.css` (`flex: 1; min-height: 0; overflow-y: auto`, with the section `gap`), and adjust `.wide-card` so the card holds a fixed header over that scrolling body.
- [x] 4.2 In `TournamentDetail.tsx`, replace the back link and the `.setup-panel` wrappers with a header — display name, `.stage-control` tab bar, close control — over a `.page-card-body`.
- [x] 4.3 Replace `screen: "information" | "register" | "amend"` with `tab: "tournament" | "registration"` plus `amending: boolean`, and offer the second tab when `hasActive || canRegister`, labelled `Registered` or `Register` per design D3.
- [x] 4.4 Fall back to the `tournament` tab whenever the second tab is not offered, so a cancellation on a closed tournament cannot leave a selected-but-absent tab.
- [x] 4.5 Move the register entry point onto the tab: drop the information screen's register button, keep the closed/not-yet-open notice.
- [x] 4.6 Open the amendment form on the registration tab in place of the registration, returning to it on submit or abandon; introduce no third tab.
- [x] 4.7 Wire the close control to the page's existing `onBack`, with `title` and `aria-label` from i18n.
- [x] 4.8 Add `detail.tabs.tournament`, `detail.tabs.register`, `detail.tabs.registered` and `detail.close` to `cs.json` and `en.json`; remove `detail.back`, `detail.backToInfo` and `detail.register` once nothing references them.
- [x] 4.9 Enlarge `.detail-logo` to twice its size and remove its border.
- [x] 4.10 Apply `.page-card-body` to `AdminPanel.tsx` and `ProfilePage.tsx` in place of `.setup-panel`, which carry the same clipping (design D1).

## 5. Verification

- [x] 5.1 `npx tsc --noEmit` clean and `npx vitest run` green, including `locale-parity.test.ts`.
- [x] 5.2 Walk the detail page in the running app on a long tournament: scrolls to the last section, sections stand apart, logo is large and unframed.
- [x] 5.3 Walk each tab state: no registration + open registration (`Tournament` | `Register`), held reservation (`Tournament` | `Registered` with payment instructions), closed registration and no registration (`Tournament` alone), past tournament with a paid registration (read-only summary on `Registered`).
- [x] 5.4 Register, amend, and cancel end to end from the tabs, confirming the page lands on the registration tab after each and that an amendment of a registration carrying legacy items keeps them and its total.
- [x] 5.5 Re-read the change against `CLAUDE.md` §8: no shadow, no radius above 2px, no animation, no hex outside `tokens.css`, one saturated color.
