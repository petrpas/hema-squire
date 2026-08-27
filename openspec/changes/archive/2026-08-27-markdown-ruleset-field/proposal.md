## Why

A tournament's rules often exist in two versions — the local-language text an
organizer's own fencers read, and an English translation for visitors — and today
a discipline can point at exactly one: `ruleset_name` holds a short style name and
`ruleset_url` holds the single link it wraps. An organizer who wants
`Barbasetti Right of Way (CZ) · EN` has nowhere to put the second document. The
inline markdown just shipped for the tournament location already solves this, so
the ruleset should reuse it rather than grow a third and fourth column for every
further language.

## What Changes

- The discipline's ruleset becomes **one inline-markdown field**, named `ruleset`,
  holding whatever the organizer writes:
  `[Barbasetti Right of Way](https://…) (CZ) · [EN](https://…)`.
- **BREAKING**: `ruleset_url` is removed from the model, the API and the console;
  `ruleset_name` is renamed to `ruleset` and its bound rises from 100 to 500
  characters, since it now carries link syntax. A migration folds an existing
  name + link pair into `[name](url)` before dropping the column, so no
  organizer's data is lost.
- The information screen renders the ruleset through the inline renderer: each
  link is its own link, the `Pravidla:` label stays plain text, and the whole
  thing no longer hangs off one wrapping anchor.
- The Setup hint under an inline-markdown field states the link form explicitly —
  `supports [link](https://...)` — and becomes one shared key serving both the
  location field and the ruleset field.
- A link typed inside a markdown field is governed by the render-time sanitizer
  (`organizer-prose`) rather than by save-time URL validation, because it is no
  longer submitted as a URL-typed field. `organizer.link` and `output_sheet_url`
  remain URL-typed and keep their scheme check unchanged.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `organizer-prose`: the discipline fields are currently named among the fields
  that are never markdown. The ruleset joins `location` as an inline-markdown
  field, and the Setup affordance requirement gains the shared hint wording.
- `tournament-admin`: a discipline's ruleset is specified as a style name plus an
  optional link, with a help hint for each. It becomes one field.
- `fencer-home`: the information screen states the ruleset as "a short style name
  linking to the external ruleset document when a link is set". It becomes
  rendered inline markdown that may carry several links.
- `field-validation`: `ruleset_name`'s length bound changes and `ruleset_url`
  leaves the set of URL-typed fields, so the requirement's illustrating scenario
  moves to a URL field that still exists.

## Impact

- Backend: `models.py` (drop `ruleset_url`, rename `ruleset_name`), `schemas.py`
  (`DisciplineIn`, `DisciplineOut`), `constraints.py`, `routers/tournaments.py`
  (create and update paths), and one Alembic revision doing fold-then-rename-then-
  drop. Tests referencing either column.
- Frontend: `api.ts` types, `setup/DisciplinesSection.tsx` (one column instead of
  two, `checkUrl` no longer used there), `TournamentFace.tsx` (render through
  `InlineProse` instead of building an anchor), `constraints.ts`, and the
  `setup.disciplines.ruleset*` / shared-hint keys in `cs.json` and `en.json`.
- No change to the inline renderer itself — `renderInline` and `InlineProse` are
  used as they are.
