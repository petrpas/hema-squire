Refactor: split SetupPanel.tsx
This is a behaviour-preserving refactor, not an OpenSpec change — no capability's observable behaviour changes, so there is no spec delta and nothing to archive. Do not create an openspec/changes/ entry for it. The one durable artifact is a convention added to CLAUDE.md (last task below).

Why
SetupPanel.tsx is 2,549 lines — three times the next-largest component. Every agent task touching any setup tab loads the whole file into context, edits invalidate large re-reads, and str_replace-style edits fail more often on ambiguous strings. The file already has clean internal seams: nine section components with explicit props, each used exactly once by a thin (~150-line) orchestrator.

Target layout
Create frontend/src/setup/ and move each seam into its own file. The seams, with their private helpers that move along with them:

setup/shared.ts — the cross-section infrastructure, and nothing else: SetupTab, SETUP_TABS, MISSING_TAB, SECTION_ORDER, SaveOutcome, SectionSaver, SaverRegistry, useSectionSaver, usePriceChangeGuard, PriceChangeWarning, splitChoices, recalculateMissing, CURRENCY_MODES, LOCAL_CURRENCY, EXTRA_CATEGORIES, ACTION_EXTRA_CATEGORIES, isActionCategory, TAXONOMY_WEAPON_CODES, OTHER_WEAPON. (If something here is used by only one section, it belongs in that section's file instead — check before placing.)
setup/IdentitySection.tsx — IdentitySection + IDENTITY_FIELDS, IDENTITY_RUN_1..3, and VsSeriesSection (12 lines, rendered only within the identity tab; do not give it its own file).
setup/CurrencySection.tsx — CurrencySection + PLAUSIBLE_RATE.
setup/OrganizersSection.tsx
setup/DisciplinesSection.tsx — DisciplinesSection + the whole discipline-row cluster: DisciplineDraft, DisciplineRow, disciplineToRow, disciplineRowDirty, disciplineRowInput, disciplineRowTouchesPrice, blankDisciplineRow.
setup/ExtraItemsSection.tsx — ExtraItemsSection + ExtraRow, extraItemToRow, blankExtraRow, extraRowDirty, extraRowTouchesPrice, extraRowInput.
setup/DiscountsSection.tsx — DiscountsSection + emptyDiscount.
setup/TeamSection.tsx
setup/DangerZoneSection.tsx
setup/PublishSection.tsx
setup/SetupTabBar.tsx, setup/SetupSaveBar.tsx — or one setup/chrome.tsx if they share helpers; keep it to one decision, don't deliberate.
SetupPanel.tsx stays where it is, keeps its default export and exact props signature, and shrinks to imports + the orchestrator. No file outside frontend/src changes; no import of SetupPanel elsewhere in the app changes.

Rules
Pure moves only. No renames of components, props, CSS classes, or i18n keys; no logic edits, no dependency-array "fixes", no dead-code removal, no reformatting beyond what moving requires. If you spot a genuine bug while moving, note it in the final summary — do not fix it in this diff.
Types imported from ../api move with their consumers; widen imports per file rather than re-exporting through shared.ts.
Every moved symbol is exported from its new file only if something outside that file uses it. Section-private helpers stay unexported.
Work section by section, running npx tsc -b --noEmit in frontend/ after each move, so a mistake is localized to one step.
Verification
npm run lint (which is tsc -b --noEmit) and npm run build pass.
git diff --stat shows SetupPanel.tsx shrinking to roughly the orchestrator plus imports (~200 lines) and no changes outside frontend/src.
Sanity check that the diff is move-only: the multiset of non-import, non-whitespace lines across the touched files should be unchanged. A quick way: git show :frontend/src/SetupPanel.tsx | grep -v '^import' | sort > /tmp/before; cat frontend/src/SetupPanel.tsx frontend/src/setup/*.ts* | grep -v '^import' | grep -v '^export {' | sort > /tmp/after; diff /tmp/before /tmp/after — investigate anything beyond export keywords added to moved declarations.
Drive the setup panel once per tab in the running app: open, edit a field, save, confirm the save bar and missing-field markers behave as before.
Follow-up (part of this task)
Add to CLAUDE.md, under the frontend conventions:

Components live one per file; a file approaching ~300 lines should be split along component seams. Panels composed of sections keep the orchestrator thin and give each section its own file under a directory named after the panel (see frontend/src/setup/).