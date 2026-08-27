## Context

See `proposal.md` — Why. The relevant current state is in
`frontend/src/TournamentFace.tsx`: `ACTION_CATEGORIES` (a three-element const
tuple mirroring the backend's frozenset) is used twice at line 659–664 to split
`detail.extra_items` into `programmeItems` and `optionalItems` by set
membership, and each list is rendered by the shared `itemRow` under a heading
from `form.sections.*`. `unanswered` — the guard that blocks submission when a
selected row's declared option is unanswered — walks both lists concatenated.

Two constraints shape the approach. The frontend has no component-render
tests: everything under `frontend/src/*.test.ts` is pure-logic (`vitest` with
`jsdom` but no testing-library). Anything worth testing therefore has to be a
pure function taking data and returning data. And `TournamentFace.tsx` is
already far past the ~300-line seam the project's frontend conventions name, so
this change should not add more logic to it.

## Goals / Non-Goals

**Goals:**

- The category classification the organizer already made survives all the way
  to the fencer's screen instead of being collapsed on the last hop.
- The grouping is a pure, testable function over `ExtraItem[]`, not a filter
  expression inline in JSX.
- Adding a seventh `ExtraCategory` later forces a decision at one visible
  place rather than silently landing in a catch-all bucket.

**Non-Goals:**

- Splitting `TournamentFace.tsx` along its component seams. That is real and
  overdue, but it is its own change; this one only avoids making it worse.
- Changing the programme grouping, the information screen's `OtherActionsInfo`,
  or the Setup screen's organizer-facing category names.
- Any ordering control for the organizer over goods rows within a category.

## Decisions

**Grouping lives in a new `frontend/src/extraItems.ts`, with
`ACTION_CATEGORIES` moving there.** The module gets `ACTION_CATEGORIES`, a
matching `ITEM_CATEGORIES` (`["rental", "merch", "other_item"]` — the render
order, so the order is data rather than a sequence of JSX blocks), an
`isAction` predicate, and `groupGoods(items)` returning
`{ category, items }[]` with empty categories already dropped.
`ACTION_CATEGORIES` is exported from `TournamentFace.tsx` today but imported by
nothing outside it, so the move needs no re-export shim.

Alternative considered: keep everything in `TournamentFace.tsx` and write the
grouping as a `reduce` in the component body. Rejected — it would be untestable
under the current test setup, and it adds to the file the conventions already
say is too big.

**The two category tuples are exhaustive over `ExtraCategory`, checked by the
type system.** `ITEM_CATEGORIES` is not defined as "everything that is not an
action"; both are spelled out, and a type-level assertion in `extraItems.ts`
fails to compile if their union stops covering the category union. Today's
`!ACTION_CATEGORIES.includes(...)` silently swallows any new category into the
goods bucket; naming both halves turns that into a compile error at the one
place that has to decide.

**Headings are new fencer-facing keys under `form.sections.goods.<category>`,
not the organizer's `setup.extras.categories.*`.** The Setup labels answer "what
kind of row am I adding to this table" for someone who already knows the
tournament's offer; the form heading has to answer "what am I looking at" for
someone who does not. So `rental` reads "Zapůjčení vybavení" / "Equipment
rental" rather than the bare "Zapůjčení" / "Rental" the setup table uses, while
`merch` and `other_item` read "Merch" / "Merch" and "Ostatní zboží" / "Other
goods". `form.sections.items` is removed rather than left orphaned.

Alternative considered: reuse `setup.extras.categories.*` for both. Rejected —
it couples two audiences' wording, and the first time one needs to change the
other would have to be split off anyway.

**`unanswered` walks `detail.extra_items` directly.** It concatenates the two
lists today only because those lists happened to be the partition; with the
goods split three ways that becomes a needless join of a thing that was never
about sections. Every extra item is a candidate regardless of where it renders.

## Risks / Trade-offs

- A tournament offering all three item categories now shows three headings
  where it showed one, which is more vertical furniture on an already long
  form → each heading is `.register-section`, the same rule the existing
  headings use, and this is the uncommon case: the ordinary tournament lends
  gear and sells nothing, so it sees one heading exactly as today.
- "Ostatní zboží" / "Other goods" as a heading is only as informative as the
  organizer's row names beneath it → accepted; `other_item` is the escape hatch
  category and no heading can rescue a row named badly. The two categories that
  carry real meaning, `rental` and `merch`, are the ones that gain from this.
- Moving `ACTION_CATEGORIES` out of `TournamentFace.tsx` moves a public export
  → nothing outside that file imports it today, so the move is confined to the
  two files and the compiler catches it if that ever stops being true.

## Migration Plan

None. No stored data, API payload, or URL changes; the change is entirely in
how one screen groups rows it already has.
