## Context

Three things are configured on a tournament that decide what Squire does with
it, and they are currently arranged as two:

| | stored? | changes behaviour? | called |
|---|---|---|---|
| `registrations_kept_by` | yes | yes — closes registration, silences the scheduler | "who keeps the registrations" |
| `feature_payments` | yes | yes — suspends the payment machinery | one of four "mode features" |
| `feature_schedule`, `feature_teams`, `feature_extras` | yes | no — Setup shows fewer controls | the other three "mode features" |
| easy / advanced mode | **no** | no | "the tournament's mode" |

The fourth row is the problem. It is a label derived by `isEasyMode(detail)`,
offered to the organizer as a radio choice, and therefore obliged to answer what
happens when they pick "advanced" and tick nothing — a case invented entirely by
the mismatch between a control and the absence of anything behind it.

The first row is a mode and is not called one. The second is grouped with three
things it does not resemble, which is why `tournament-modes` carries a
requirement whose whole job is to say that one of its four members is different.

This change moves words and one requirement. No stored value changes and no
behaviour changes.

## Goals / Non-Goals

**Goals:**

- One thing is called the mode, and it is the one that is stored and changes
  behaviour.
- Every sentence describing the three remaining features is true without an
  exception clause.
- The organizer configures a tournament on one screen instead of two dialogs in
  sequence, and reads its whole configuration in one section instead of two.
- The change is provably behaviour-preserving: tests pass with mechanical edits
  or the change has done something it did not intend.

**Non-Goals:**

- Changing what any feature or the mode does. Everything the three preceding
  changes built stands.
- Renaming stored columns. `feature_*` and `registrations_kept_by` keep their
  names, and there is no migration in this change.
- Deciding whether payments should become something other than a boolean. It is
  a behavioural axis and this change says so; what it is *shaped* like is
  settled and not reopened.

## Decisions

### Decision 1: Easy and advanced mode are removed, not renamed

Not "basic setup" and "full setup", not a collective noun for the three
features. Removed.

The reason the concept fails is not its name. It is that it was never stored, so
every surface had to derive it and the dialog had to invent an answer for a
choice its model could not hold. Renaming keeps the derivation and keeps the
invented case.

What replaces it in the UI is nothing: the three features are checkboxes, and a
tournament with none ticked is a tournament with none ticked. There is no state
to name because there was never a state.

`isEasyMode` and `EASY_MODE` are deleted rather than kept for compatibility.
Nothing may compute a label from the flags again.

Alternative considered: keeping easy/advanced as purely a *description* on
`OTHER`, with no control. Rejected — a description of four booleans that reads
"advanced mode" tells the organizer less than the four booleans do, and it would
survive as the thing everyone still says.

### Decision 2: Payments moves out of the list conceptually, not structurally

`feature_payments` stays a column beside the other three, written by the same
endpoint. What changes is where it is *stated* and where it is *documented*.

Stated: its own row in the settings surface, between the mode and the
inclusions, because it is a behavioural setting like the mode and unlike the
three below it.

Documented: `tournament-modes`' requirement "The payments feature suspends the
payment machinery" moves to `payments`. It is the only requirement in a
capability about modes that describes what happens to money, reservations and
mail, and it moved there because that is where the flag lived, not because that
is where the behaviour belongs.

Keeping the storage as-is is deliberate. Splitting the column out would mean a
migration, a second endpoint and a second write path, all to express a
distinction that is about how the setting is presented and specified. The
grouping was the mistake, not the storage.

Alternative considered: three tiers in the data too — a `mode` enum, a
`collects_payments` boolean, a `features` set. Rejected as cost without a
payer: nothing reads the four flags as a set, so nothing is simplified by
splitting them.

### Decision 3: The three features get a capability named for what they are

`tournament-modes` becomes `tournament-features`. A technical name, matching the
`feature_*` columns, and not a word the organizer ever reads — because the
organizer does not need one. The screen says what the tournament includes and
lists three things; a collective noun above them would be a word invented for
the spec's convenience.

Its central rule loses its exception and becomes flatly true: turning a feature
off hides the settings it governs, retains every stored value, and changes
nothing a fencer experiences. Hidden extra items are still sold, hidden team
disciplines still take teams, and there is no longer a fourth member that
withdraws a product.

### Decision 4: The settings surface belongs to `setup-navigation`

The screen spans all three tiers, so no capability that owns one tier can
specify it. `setup-navigation` already fixes how Setup is arranged — its tabs,
its section allocation, its save controls — and this is the same kind of
statement.

It fixes both appearances of the same surface: the screen shown once a
tournament has been created, and the section on `OTHER` that states the
tournament's whole configuration and reopens it.

### Decision 5: One screen at creation, replacing two dialogs in sequence

Creation currently shows the create form, then swaps its content to the mode
dialog, then (since `add-registrations-kept-by`) swaps again to the registration
choice. Three panels for one act.

The new second panel carries all of it: the mode as a radio with automatic
preselected, payments, and the three inclusions. It is short enough to read at
once, which the sequence never was, and it puts the two behavioural choices
where an organizer can see they are the consequential ones.

Dismissal keeps its existing meaning exactly: the tournament is created before
the panel is shown, and closing it leaves the tournament as created — automatic
mode, payments off, no features.

### Decision 6: One section on `OTHER`, replacing two

`ModeSection` and `RegistrationsKeptBySection` become one section stating three
lines in words with one control. Two sections describing one configuration is
the same fragmentation this change is removing, and the second only exists
because it was added under the constraint that the first was about something
else.

It keeps `OTHER`'s rule that its actions carry their own controls and that the
tab has no save bar.

### Decision 7: The API renames, the columns do not

`/mode` becomes `/features` and `TournamentModeIn`/`Out` become
`TournamentFeaturesIn`/`Out`. `registrations-kept-by` is untouched, per the
owner's decision that `mode = "manual"` in a column would not say manual what.

So the code carries two names for one user-facing word, which is the same
arrangement `feature_payments` already has with "Platby". The rule is that the
stored name says what it means and the copy says what the organizer calls it.

## Risks / Trade-offs

**[Organizers have learned "easy mode" and it disappears] → Accepted, and it is
the point.** A word for a thing that is not stored is what produced the defect.
The replacement copy has to stand without it: the screen names three concrete
inclusions, which is more informative than a tier label was.

**[A rename this wide hides a behaviour change inside mechanical edits] → The
test suites are the control.** No behaviour changes, so every test should pass
after renaming identifiers and copy. A test whose *assertions* need rethinking
rather than its names is a behaviour change that has to be explained before it
is accepted. This is the same instrument `unify-lifecycle-dormancy` used, and
it worked there.

**[Two unarchived changes already modify these requirements] → Reconcile at
archive time, not in sequence.** `add-registrations-kept-by` creates
`registration-ownership` and modifies `tournament-modes`; this change renames
both. Nothing is archived, so the delta set has to be applied as a whole with
this change last, and the archive order is a task rather than an assumption.

**[`/mode` is a public endpoint] → Renamed rather than aliased.** No client
outside this repository is known, the frontend ships with the backend, and an
alias kept "for safety" would be the second name that outlives its reason.

## Migration Plan

No schema change, no data migration, no deploy ordering constraint beyond the
three changes this one sits on.

The archive order is the only sequencing that matters: the three preceding
changes first, this one last, so that `registration-ownership` and
`tournament-modes` exist to be renamed rather than being created under names
this change removes.

Rollback is the revert. Nothing is written that a previous version would
misread.

## Open Questions

- The Czech copy for the two modes. *Automatický* / *manuální* is the owner's
  word and settles the label; what the help text says under each is written
  against the screen. The consequence — that in manual mode Squire writes to
  nobody and holds no registration form — has to be in the hint rather than
  inferred from the adjective.
- Whether the settings screen at creation should preselect automatic mode
  explicitly or leave both unselected until chosen. Preselecting matches the
  stored default and the old dialog's treatment of easy mode; leaving it blank
  would make the organizer decide. Decided against the screen.
