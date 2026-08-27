## 1. Extract the category grouping

- [x] 1.1 Create `frontend/src/extraItems.ts` holding `ACTION_CATEGORIES` (moved out of `TournamentFace.tsx`, comment and all), a new `ITEM_CATEGORIES` tuple in render order `rental, merch, other_item`, an `isAction(item)` predicate, and `groupGoods(items)` returning `{ category, items }[]` for the non-empty item categories in that order; verify `npx tsc --noEmit` passes in `frontend/`
- [x] 1.2 Add the compile-time exhaustiveness assertion in `extraItems.ts` that fails to build if `ACTION_CATEGORIES ∪ ITEM_CATEGORIES` stops covering every `ExtraItem["category"]` value; verify by temporarily dropping one entry and confirming `npx tsc --noEmit` errors, then restoring it
- [x] 1.3 Add `frontend/src/extraItems.test.ts` covering: goods split into rental/merch/other_item sections in that fixed order; a category with no rows omitted entirely; a lending-only tournament yielding exactly one group; row order preserved within a group; action-category items never appearing in any goods group; verify `npm test` passes in `frontend/`

## 2. Render a section per goods category

- [x] 2.1 Point `TournamentFace.tsx` at `extraItems.ts` — drop the local `ACTION_CATEGORIES` and derive `programmeItems` through `isAction`, leaving the programme section's single heading as it is; verify the optional programme still renders unchanged for a tournament with a seminar and an afterparty
- [x] 2.2 Replace the `optionalItems` block at the register form's goods section with a map over `groupGoods(detail.extra_items)`, each group rendering an `h3.register-section` headed by its category and a `.checklist` of `itemRow`; verify a tournament lending three weapons shows one section headed as equipment rental and no "optional items" heading anywhere
- [x] 2.3 Rebase `unanswered` on `detail.extra_items` directly rather than on the concatenated section lists; verify selecting a merch row with a declared but unanswered option still blocks submission with the `form.optionRequired` message

## 3. Fencer-facing headings

- [x] 3.1 Replace `form.sections.items` with `form.sections.goods.{rental,merch,other_item}` in `frontend/src/i18n/cs.json` and `en.json` — "Zapůjčení vybavení" / "Equipment rental", "Merch" / "Merch", "Ostatní zboží" / "Other goods" — leaving `setup.extras.categories.*` untouched; verify `grep -rn "sections.items" frontend/src` returns nothing and `npm test` passes
- [x] 3.2 Check the wording against the design prohibitions — sentence case, no exclamation, no Title Case — and confirm both locales carry the same key set; verify the locale parity test passes

## 4. Verification

- [x] 4.1 Run `npm test` and `npx tsc --noEmit` in `frontend/`; verify both are clean
- [ ] 4.2 Open the register form of a tournament that lends gear and one that also sells merch (Setup preview is enough); verify the first shows one goods heading naming the rental and the second shows the rental section above the merch section, with prices, quantities, options, discounts, and the total unchanged
- [x] 4.3 Run `openspec validate goods-sections-by-category --strict`; verify it reports no errors
