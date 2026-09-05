## Context

Two facts about the codebase make this change small, and one makes it delicate.

**Small, first.** Whether a registration submission may proceed is decided in
exactly one function, `setup.registration_availability(tournament, now)`, with
two callers — the register endpoint and the tournament read that tells a client
whether to show the form. It already returns a stated reason from a closed set
(`not_published`, `not_yet_open`, `closed`) rather than a bare boolean, and its
docstring fixes the gate order. A fourth reason is one branch at the top of a
funnel that already exists.

Second, the scheduler's pass over tournaments is one select:
`select(Tournament).where(Tournament.date >= date.today())`. Excluding a whole
class of tournament is one more term. That is what makes the guarantee
structural rather than a per-registration check repeated in four places — no
lifecycle code runs against such a tournament at all, so no future pass can
forget.

**Delicate.** `tournament-modes` is built on a rule this axis breaks: "Disabling
a feature hides its settings without changing them", down to "a hidden extra item
SHALL still be offered on the registration form and still be sold". Four
independent booleans, no stored mode value, easy and advanced merely names for
how many are on. This axis withdraws the registration form and silences the
scheduler; it is not a visibility switch. `payments` is the single existing
exception, carried by a requirement of its own — a precedent for one exception,
not a template for a second.

The preceding change, `unify-lifecycle-dormancy`, exists so this one has a place
to put its third cause.

## Goals / Non-Goals

**Goals:**

- A tournament states who keeps its registrations, as its own stored value.
- A tournament the organizer keeps is invisible to the scheduler as a matter of
  structure, not of per-row checks.
- Its in-app registration never opens, refused with a reason of its own.
- The organizer can choose at creation and change afterwards, warned about what
  the change stops.
- The four features are untouched, and the relationship between the two axes is
  written down once.

**Non-Goals:**

- The external registration URL and the public surfaces that read it. Without
  them an organizer-kept tournament simply offers no way to register, which is
  incomplete but not wrong; the next change completes it.
- Any change to what the console does. Import, matching, deduplication, the
  fencer table and export behave identically on both kinds of tournament, and
  that is the point — the manual path was already built.
- The organizer's ability to override a fencer's own edit, deferred.
- Turning an organizer-kept tournament back into a Squire-kept one as a
  *migration* — reconciling imported rows with accounts, issuing invitations,
  starting clocks on a roster that never had them. The switch itself is
  supported; making the roster behave as if it had always been Squire's is a
  separate piece of work.

## Decisions

### Decision 1: A stored value with two members, not a boolean and not a fifth flag

`registrations_kept_by`, values `SQUIRE` and `ORGANIZER`, stored on the
tournament and defaulted to `SQUIRE`.

An enum rather than a boolean because the two ends are named things an organizer
chooses between, and because a boolean would need a name that reads correctly in
both directions — `squire_keeps_registrations` reads badly when false, and every
call site would carry the negation.

Not a fifth feature flag, for the reason in Context. Beyond the rule it would
break, `tournament-modes` derives easy and advanced from how many features are
on; a fifth would silently make every organizer-kept tournament "advanced",
which says nothing true about it.

Alternative considered: deriving it from the tournament's contents — a tournament
with imported rows and no in-app registrations is organizer-kept. Rejected on the
same grounds `tournament-modes` rejects derivation for its own four: "The
features record what the organizer asked to see." A tournament that has not yet
been imported into is indistinguishable from one that has not yet been registered
for, and the guarantee has to hold from the moment the tournament exists, before
either has happened.

### Decision 2: The scheduler excludes the tournament, not the registrations

`run_tick`'s select gains a term. No pass gains a condition.

This is the difference between a guard and a guarantee. `issue-imported-
registrations` protects one roster with a per-row mark set by one code path; if a
future path creates a registration without it, the mail goes out. Excluding the
tournament means the passes are never reached, so a registration created by any
path on such a tournament is safe by construction.

The per-row mark stays, and is not made redundant by this. It covers the mixed
case it was built for: a club added by import into an otherwise Squire-kept
tournament. Two guards at different granularities, and the change's value is that
the coarse one now exists at all.

### Decision 3: The third dormancy cause is added anyway

Even though the scheduler never reaches such a registration, the predicate from
`unify-lifecycle-dormancy` gains the organizer-kept cause.

Not defensive duplication — the predicate is also what the console reads to state
what settlement would move, and what an organizer's manual settle action consults.
Those are reached by a human clicking, not by the scheduler's select, so the
tournament-level exclusion does not cover them. A tournament the organizer keeps
must demote nobody when its organizer presses settle, for the same reason a
payments-off one must not.

### Decision 4: Availability answers with its own reason, and it is not `closed`

A fourth member of the reason set rather than reusing `closed`.

`closed` means "the window has passed", and clients present it as such — a fencer
seeing it reasonably concludes they were too late. Here nothing was ever open and
nothing is late; the registration is somewhere else. The reason has to be
distinguishable so the next change can attach the external link to it, and so the
fencer is not told a falsehood in the meantime.

The gate order becomes: organizer-kept → cancelled → published → opens → closes.
First, because it is the most fundamental — it is not that this tournament's
window is shut, it is that this tournament has no window here.

### Decision 5: Its own section beside the mode section, not inside the mode dialog

`TournamentModeDialog.tsx` already splits its body out as `TournamentModeFields`
so that `TournamentPicker` can embed the same fields at creation and
`setup/ModeSection.tsx` can reopen them on `OTHER`. The new section follows that
split — its own component, embedded in both places — rather than joining those
fields.

The reason is the same one that keeps it out of the flag set: the mode dialog's
copy, its warnings and its easy/advanced framing are all about which settings are
visible. Putting a switch that closes registration inside that dialog would make
the dialog's own explanation wrong.

Alternative considered: a step in the creation flow of its own, asked before the
mode dialog. Rejected as one dialog too many at creation; the tournament-mode
dialog is already the second thing an organizer sees.

### Decision 6: Switching is confirmed and names what stops

Turning it to organizer-kept on a live tournament closes the registration form
and stops the clocks. `tournament-modes` already has the shape for this — a
warning that counts what will be hidden and requires confirmation, with turning a
feature *on* never warned.

Here the asymmetry is different, because both directions have consequences:
switching to organizer-kept closes registration; switching back opens it and puts
the roster under clocks it has never been under. Both are confirmed, and each
states its own effect. Where the tournament already holds in-app registrations,
the confirmation says how many, because those are the people whose registration
Squire will stop managing.

### Decision 7: Backfill is unconditional

Every existing tournament is Squire-kept. Unlike the four features, there is
nothing to derive and no generosity to exercise: a tournament that was imported
into is still one whose registration form is open and whose scheduler runs, which
is precisely what Squire-kept means. Turning any of them organizer-kept is an
organizer's decision, taken in the UI, with the confirmation.

## Risks / Trade-offs

**[An organizer switches a live tournament and closes registration under people
who are mid-signup] → The confirmation states the count of in-app registrations
already taken and says the form will close.** The switch is not blocked — there
are legitimate reasons to take registration elsewhere mid-flight — but it is not
something anyone should do without seeing the number.

**[The tournament is unreachable for fencers until the next change lands] →
Accepted, and sequenced.** Between these two changes an organizer-kept tournament
publishes and shows no way to register. That is a strictly better failure than
the alternative sequencing, where the external link exists while the scheduler is
still armed. The two changes should land close together.

**[`clocks_dormant` looks redundant and someone removes it] → Decision 3 and the
proposal both say why it stays.** It covers the mixed case, which the
tournament-level exclusion does not reach. Its own tests must pass unchanged as
the evidence.

**[The scheduler exclusion hides a bug rather than fixing one] → It is both, and
that is intended.** If a lifecycle pass mistreats organizer-kept registrations,
excluding the tournament means nobody finds out. The mitigation is Decision 3:
the predicate carries the cause too, so the console paths that *are* reachable
exercise the same rule, and a test asserts the predicate directly rather than
only through the scheduler.

## Migration Plan

One Alembic migration adding the column with `SQUIRE` as the default and
backfilling existing rows to it. Following `str_enum`'s existing treatment in
this codebase — `native_enum=False`, no check constraint — the value is a short
string column and adding a third member later needs no migration.

Deploy order: `unify-lifecycle-dormancy` first, since the third cause has nowhere
to land otherwise.

Rollback is the revert plus a column drop; no tournament will have been switched
to organizer-kept before the UI ships, and any that has simply becomes
Squire-kept again — which reopens its registration and restarts its clocks, so a
rollback after real use needs the same warning the switch itself carries.

## Open Questions

- What the two ends are called *for the organizer*, in Czech and English. The
  stored name is settled; the label is copy, and copy is decided against the
  screen. "Registrace vede Squire / vede organizátor" is the working phrasing
  from the brief, and the section's help text has to carry the consequence —
  that Squire will not write to anyone — rather than only the label.
- Whether an organizer-kept tournament should be publishable at all before the
  external link exists. Deferred to the next change, which introduces the link
  and is the right place to decide whether it is mandatory for publication.
