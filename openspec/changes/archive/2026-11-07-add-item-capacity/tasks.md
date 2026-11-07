## 1. Data

- [x] 1.1 Add `ExtraItem.capacity` with a migration on the current head, and accept it in the item schemas with a constraint in `constraints.py` and `frontend/src/constraints.ts`
- [x] 1.2 Add `item_taken` to `availability.py` and return free places per capped item from a separate `/item-availability` endpoint, since `/availability` is a list of disciplines
- [x] 1.3 Carry capacity in `export_json.py`, raise the schema version, test a round trip and an older document

## 2. Enforcement

- [x] 2.1 Check before writing, claim capped items in id order after the flush, and refuse with `item_sold_out` on registering (design D3, D4)
- [x] 2.2 Apply the same check to an amendment, on increases only (design D5)
- [x] 2.3 Extend `seats_free` to items for reinstatement (design D6)
- [x] 2.4 Leave hand entry and issuing unrefused, and test that they count (design D7)
- [x] 2.5 Test every spec scenario, including two concurrent submissions for the last place and a queued fencer's admission

## 3. Frontend

- [x] 3.1 Add the capacity field and taken count to `setup/ExtraItemsSection.tsx`
- [x] 3.2 Show free places and sold out on the form, in `TournamentFace.tsx`, including the amendment form and the preview
- [x] 3.3 Count only items with room in `hasOpenSlot` in `TournamentDetail.tsx`
- [x] 3.4 Map `item_sold_out` to a message naming the items, in `cs.json` and `en.json`

## 4. Checks

- [x] 4.1 `uv run ruff check .`, `uv run basedpyright`, and scoped pytest for `tests/registration`, `tests/payments`
- [x] 4.2 `npm run typecheck`, `npm run check`, `npm test`, `npm run build`
