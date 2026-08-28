## Why

An organizer who runs the same event every year retypes the same values into every
new tournament: their club's name and link, the venue, the account the money lands
in. The typing is not just tedious — it is where drift enters. "Sdružení pro
studium historických bojových umění" becomes "SHBU" in the next year's tournament,
one IBAN loses a digit, and the public pages of two events by the same organizer
disagree about who is running them. The values the organizer needs are already in
the database, in their own previous tournaments; nothing offers them back.

## What Changes

- Three Setup fields gain a suggestion list drawn from the values the signed-in
  organizer has used before, offered as they type and dismissible without choosing:
  - the titular organizer entry in ORGANIZERS (name and link suggested **as a pair** —
    choosing a remembered club fills its link too, since the two always travel together)
  - `location` in IDENTITY
  - `bank_account` in the bank-account section
- Suggestions are **derived on demand** from the tournaments the account owns or has
  console access to. No new table, no write path, no staleness: a value that was
  corrected in the source tournament stops being suggested, and the feature works
  retroactively over tournaments that already exist.
- Suggestions are scoped to the requesting account. One organizer never sees another
  organizer's venues or account numbers, and the endpoint carries no tournament in
  its path — it is a property of the account, not of the tournament being edited.
- A new frontend component provides the suggestion affordance for all three fields:
  a static list beneath the input, keyboard-navigable, under the Bureau 1952
  prohibitions (no shadow, no rounded panel, no entrance animation).
- Nothing is ever filled in automatically. A suggestion is offered; the organizer
  is always free to type a value that appears nowhere in the list.

## Capabilities

### New Capabilities
- `setup-field-suggestions`: what an organizer is offered from their own prior
  tournaments as they fill in a Setup field — which fields carry the affordance,
  how the values are derived and ordered, the per-account scoping, and the
  interaction contract (offer, choose, dismiss, override).

### Modified Capabilities
<!-- None. The three fields' own requirements — validation bounds, IBAN
     normalization, the organizer list's shape — are unchanged; this change adds an
     input affordance over them and takes nothing away. -->

## Impact

- **Backend**: new read-only endpoint under `backend/app/routers/tournaments.py`
  (or a sibling router) returning the signed-in account's distinct prior values.
  Reuses `_organized_tournament_ids()` (`tournaments.py:267`) for the scope — the
  same definition of "the user's tournaments" the rest of the console already uses.
  New response schema in `schemas.py`. No model change, no migration.
- **Frontend**: new suggestion component under `frontend/src/`; wiring in
  `setup/OrganizersSection.tsx`, `setup/IdentitySection.tsx` and
  `setup/BankAccountSection.tsx`; one `api.ts` client method.
- **Styling**: new rules in `index.css` using existing `tokens.css` values only.
- **Localization**: new keys in `i18n/cs.json` and `i18n/en.json`.
- **Not affected**: the database schema, the edit-rules engine, the ETL table
  path, and every validation rule the three fields already carry — a chosen
  suggestion is validated exactly as a typed value is.
