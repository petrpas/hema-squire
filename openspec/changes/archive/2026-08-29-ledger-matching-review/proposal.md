## Why

After a matching run every row the LLM resolved reads the same: *navržená
shoda*. A confident exact-name hit and a shaky transliteration guess wear the
same yellow badge, and the only way out of yellow is a modal that asks the
organizer to search for the profile the LLM already picked. A rerun will not
clear it — a cached decision is never re-asked — so the yellow is a queue with
no cheap way to serve it.

It is worse than tedious, because the review cannot actually be performed. The
proposal overwrites the row's name, club and nationality with the HR values the
moment it is stored, and the registered club and nationality are then gone. The
organizer is offered the LLM's answer and asked to compare it with the LLM's
answer. The evidence that would settle the question — what the fencer wrote
against what HEMA Ratings holds — is not on the screen and cannot be put there.

## What Changes

- **The Matching row becomes a ledger line**: what the fencer claimed, what HEMA
  Ratings holds, and the verdict we reached, side by side in one row. The
  Matching phase gains the HR columns the `etl-console` spec has always
  required (HRID, HR_Name, HR_Nat, HR_Club) and shows only one of.
- **BREAKING (internal): the proposal overlay is removed.** A stored match no
  longer rewrites the row's `name`, `club` or `nationality`. Those fields stay
  the fencer's words until a verdict is reached. `reg_name` stops being written
  by the matcher, since the name it preserved is no longer displaced.
- **Canonical naming follows the verdict, not the proposal.** The HR spelling
  becomes the display name when an organizer confirms, not when the LLM guesses.
- **A found/proposed split, derived and explainable.** A match whose name key
  equals the registration's, whose nationality names the same country, and whose
  name is unambiguous in the fighters index, reads as *nalezená shoda* (green,
  no work owed). Everything else stays *navržená shoda* (yellow). The tier is
  computed from the stored decision at replay time, so the existing wall of
  yellow re-tiers itself with no rerun and no further LLM spend.
- **Confirming costs one click.** The verdict badge ratifies in place; searching
  for an alternative moves behind its own affordance. `MatchDialog` keeps the
  search it alone can do and loses the comparison it never could.
- **Typing an HR id in the table is a verdict.** The `hr_id` cell already
  accepts an edit but records it as a field edit, leaving the row's verdict
  stale forever. It becomes a match resolution, as the dialog's is.
- **The queue is countable.** The Matching rail states how many rows still owe
  a verdict, as the deduplication rail already does.
- **The ledger idiom is written down** as a requirement over the console, so
  Payments — still unbuilt — inherits the shape rather than inventing a fourth
  one. No shared component is extracted here; the second implementation earns
  that.

## Capabilities

### New Capabilities

None. The idiom is a requirement over the existing console capability, not a
capability of its own.

### Modified Capabilities

- `etl-console`: adds the ledger idiom as a requirement over machine-proposes /
  human-ratifies phases; restates HR matching review in terms of it (the claim
  and evidence registers both visible, one-click ratification, a countable
  queue).
- `table-import`: the LLM matching verdict set gains a derived *found* tier
  between confirmed and proposed, and states the rule that a drawn distinction
  must be explainable from what is on screen.
- `hr-integration`: canonical naming is triggered by an organizer's verdict
  rather than by the existence of a match proposal.

## Impact

- `backend/app/sheet.py` — the overlay at the heart of `_imported_rows`; verdict
  derivation; HR fields carried on the row beside the claim fields.
- `backend/app/rules.py` — `_apply_match_resolution` takes on canonical-name
  promotion.
- `backend/app/hr_match.py` — `_pending_rows` learns the new settled verdict;
  ambiguity of a folded name in the index becomes a tiering input.
- `backend/app/hr_index.py` — a name-key lookup for the ambiguity test.
- New dependency `pycountry` (ISO 3166), so a registration's country code and
  the index's English country name can be compared as the same country.
- `frontend/src/Console.tsx` — `PHASE_COLUMNS.matching`, the verdict cell's
  actions, `saveEdit` routing for `hr_id`.
- `frontend/src/MatchDialog.tsx`, `frontend/src/MatchPanel.tsx`,
  `frontend/src/api.ts` (`SheetRow`), `frontend/src/i18n/{cs,en}.json`.
- No migration: verdicts are replay products, not stored state. Nothing
  persisted changes shape.
