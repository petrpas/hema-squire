## Why

Squire calls two different things a mode, and only one of them is one.

`tournament-modes` names four boolean features and then says, in its own words:

> There SHALL be no separately stored mode value, so the name a tournament is
> given and the sections its console offers SHALL never disagree.

So "easy mode" and "advanced mode" are not settings. They are labels computed
from four checkboxes — `isEasyMode(detail)` derives one every time it is
needed. But the creation dialog offers them as a radio choice anyway, which
forces this into the spec:

> **Advanced with nothing chosen** — the dialog does not accept the choice as
> advanced, and the tournament remains in easy mode.

That case exists for no reason but the borrowed word. A dialog offering a choice
its data model cannot hold has to invent what happens when the organizer makes
it. Take the word away and the case does not need answering; the dialog becomes
a list of checkboxes and stops arguing with itself.

Meanwhile the tournament acquired something that *is* a mode:
`registrations_kept_by`, stored, two values, and it changes what the system does
— it closes the registration form and takes the tournament out of the
scheduler. It is the thing an organizer will call the tournament's mode, and the
word is spoken for.

And the four are not one kind of thing. Three of them — schedule, team
disciplines, extra services — govern which controls Setup offers and change
nothing a fencer experiences; a hidden extra item is still sold, a hidden team
discipline still takes teams. Payments is not like that at all, and
`tournament-modes` needs a requirement of its own to say so: it suspends the
payment machinery, opens no window, sends no mail, reconciles nothing. Calling
all four the same thing is what obliged the spec to carry that exception.

## What Changes

- **The word "mode" moves to the axis that is one.** A tournament's mode is
  **automatic** — Squire keeps the registrations — or **manual** — the organizer
  keeps them. Easy mode and advanced mode cease to exist, in the specs, the
  code and the copy.
- **Payments stands beside the mode, not among the features.** It is a
  behavioural setting like the mode is, and its stated effect moves from
  `tournament-modes` to `payments`, where the behaviour it governs is already
  described.
- **The remaining three need no collective name.** Schedule, team disciplines
  and extra services are what a tournament includes, and the sentence that
  describes them — they change which controls Setup offers and nothing else —
  becomes true for the first time.
- **One settings surface replaces two.** Creating a tournament asks the mode,
  payments and the three inclusions on one screen instead of stepping through
  two dialogs; Setup's `OTHER` tab states all three tiers in one section with
  one control, replacing the mode section and the registrations section beside
  it.
- **BREAKING (API):** `GET`/`PATCH /api/tournaments/{slug}/mode` becomes
  `/features`, and `TournamentModeIn`/`Out` become `TournamentFeaturesIn`/`Out`.
  The four stored columns are unchanged and there is no migration.
- `registrations_kept_by` keeps its name in the database and its endpoint.
  **Režim** is the word the organizer reads; the column keeps saying which
  registrations it is about, because `mode = "manual"` would not.

Not in scope: any change to what the four features or the mode actually do.
Every behaviour fixed by `unify-lifecycle-dormancy`,
`add-registrations-kept-by` and `add-external-registration` stands exactly as
built. This change moves words, one requirement between capabilities, and two
screens.

## Capabilities

### New Capabilities
- `tournament-mode`: what a tournament's mode is — automatic or manual — how it
  is stored, chosen and changed, and why it is the only thing called a mode.
  Absorbs `registration-ownership` from `add-registrations-kept-by`, which is
  the same capability under the name it should have had.
- `tournament-features`: the three features that govern which controls Setup
  offers — schedule, team disciplines, extra services — and the rule they all
  now obey without exception: turning one off hides settings and changes
  nothing a fencer experiences.

### Modified Capabilities
- `payments`: gains the requirement stating what turning the payments feature
  off does. It described payment behaviour from a capability about modes; it
  belongs where the machinery it suspends is specified.
- `setup-navigation`: fixes the one settings surface — the screen shown when a
  tournament is created, and the single section on `OTHER` that states all
  three tiers and reopens it. Setup's arrangement is what this capability is
  for, and the surface spans capabilities that none of the others owns.

### Removed Capabilities
- `tournament-modes`: renamed to `tournament-features` and reduced. Easy and
  advanced mode are removed outright; the payments requirement moves to
  `payments`.
- `registration-ownership`: renamed to `tournament-mode`, not deleted. Its
  requirements move across unchanged in substance.

## Impact

**Depends on all three unarchived changes** — `unify-lifecycle-dormancy`,
`add-registrations-kept-by`, `add-external-registration` — and touches
requirements two of them modify. Nothing is archived yet, so the deltas must be
reconciled together rather than in sequence.

**Backend** (`backend/app/`): `TournamentModeIn`/`Out` and the `/mode`
endpoint renamed; no model change, no migration, no column touched.

**Frontend** (`frontend/src/`): `TournamentModeDialog.tsx` and
`setup/ModeSection.tsx` become one settings dialog and one settings section
alongside `setup/RegistrationsKeptBySection.tsx`, which folds into it;
`MODE_FEATURES` → `TOURNAMENT_FEATURES`; `EASY_MODE` and `isEasyMode` deleted
along with the case they existed for; `TournamentPicker`'s two-step creation
flow collapses to one screen. 31 `setup.mode.*` keys in each of two locales are
rewritten.

**Scale**: 58 code references, 31 i18n keys per locale, a 250-line spec, six
spec files referring to it, two files renamed, one endpoint. Almost all of it
mechanical.

**Risk**: easy and advanced mode are words organizers may already have learned,
and they disappear rather than being redefined. That is the point — a name for
a thing that is not stored is what caused this — but it is user-visible and the
copy replacing it has to stand on its own.

**Verification**: `pytest` and `vitest` should pass with only mechanical edits,
since no behaviour changes; a test that needs its assertions rethought rather
than renamed is a behaviour change to explain.
