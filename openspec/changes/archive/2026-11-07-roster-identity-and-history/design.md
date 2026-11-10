## Context

See proposal.md — Why. What constrains the approach:

- **The save is a replace.** `routers/registrations.py:1664` deletes every
  `TeamMember` of the team and inserts the request's list with fresh ordinals.
  The editor's own `_team_for_roster_edit` is deliberately ungated by the
  amendment window (design team-disciplines D6).
- **The frontend already has member identity, client-side only.**
  `TeamsTab.tsx:13` keeps `DraftMember = RosterMember & { rowId: string }`
  precisely because "two members may share every field, and a row that is
  removed or moved up must not hand its open name field to whichever member
  takes its place" — and then "the save sends the four stored fields and nothing
  else". The editor's shape is right; the id it already needs just has to become
  the server's.
- **Nine places read `Team.members`** (`entrants.py:319`, `emails.py:1297`,
  `export_json.py:411`, `scheduler.py:559`, `routers/tournaments.py:1405/1407/1510`,
  `routers/registrations.py:151/181`), every one of them meaning *the roster as it
  stands*. A removal mark must not quietly change what any of them says.
- **Order carries no meaning**: "A roster SHALL NOT record which member is the
  team's captain, which members fence, or which member is the reserve" — so
  `ordinal` is storage order, never identity and never seniority.
- **The organizer's corrections have a precedent for silence**:
  `amendment.SURCHARGE_ONLY` exists because "a letter per corrected row would
  make the correction cost more than the error".
- `openspec/specs/team-disciplines` requires the organizer's teams view to state
  a bound member's HEMA Ratings identifier. `TeamsPanel.tsx` does not render it,
  although `routers/tournaments.py:1401` sends it — a pre-existing gap this change
  closes while it is in that file.

## Goals / Non-Goals

**Goals:**

- A member's identity survives any save, so a rule or a rating may later be hung
  on it (next piece of work) without the entrant's next edit orphaning it.
- A roster's history answers "who changed this, and to what" for the entrant and
  the organizer in one place.
- The organizer can act for a team that cannot act for itself, at the venue.

**Non-Goals:**

- Members do not become rows of the console's sheet; matching, deduplication and
  the ratings snapshot are untouched. That is the next piece, and it is what this
  one exists to make possible.
- No change to the console's phase order or to which tab owns which agenda.
- No team cancellation, no admission from the teams view: admission stays the
  Queue phase's, which states the money it moves (`seating-queue`).
- No history for teams themselves (entering, renaming, removing a team is already
  an amendment of the registration), and none for roster order.

## Decisions

**D1 — The save stays one PUT of the whole roster, applied as a diff.**
`RosterMemberIn` gains an optional `id`; the handler reads the team's stored
members, updates those the request names, inserts those it does not, marks
removed those it omits, and rewrites `ordinal` from the request's order.
*Alternatives:* a PATCH per member — rejected, the editor is a draft the entrant
saves once and "One save commits every roster on the tab" is already a
requirement; a diff computed client-side into add/remove/update commands —
rejected, it puts the invariant (what the roster now is) on the weaker side of
the wire.

A member id in the request that does not belong to this team SHALL be refused
rather than ignored: the request is then not a statement about this roster, and
ignoring it would silently add a member the entrant meant to move.

**D2 — Removal is a mark on the member, and `Team.members` keeps meaning "the
roster".** `TeamMember` gains `removed_at` and `removed_by_fencer_id`. The
relationship `Team.members` is filtered to live members and ordered by ordinal,
so all nine read sites keep saying what they say today with no edit. The removed
ones are reachable as `Team.removed_members`. *Alternative:* rename the
relationship to `all_members` and make every site filter — rejected: nine call
sites, each of which wants the same thing, and the one that forgets is a bug
nobody sees until a count is wrong. The filtered relationship is stated loudly in
the model's docstring, which is where a reader of `Team` looks.

**D3 — One log table, modelled on `PaymentEvent`, with the actor
`FencerProfileAudit` lacks.** `RosterChange`: team id, member id, kind
(`added` | `removed` | `restored` | `edited`), field with before and after for an
edit, `actor_fencer_id`, `by_organizer`, `after_deadline`, `created_at`.
*Alternatives:* `FencerProfileAudit`'s field/old/new shape — rejected, it cannot
say "added" or "removed" and records no actor; `PaymentEvent`'s kind + free-text
detail — rejected, "what changed" would be prose and no surface could render the
before and after as the console renders a manual edit. The new table is the two
existing idioms' intersection, which is also what a reader will expect from
either direction.

`by_organizer` is stored rather than derived from whether the actor holds the
registration: the organizer may also be the entering fencer on their own
tournament, and "the organizer did this" is a fact about the act, not about who
the actor happens to be.

`after_deadline` is stored rather than recomputed: the deadline is a tournament
setting the organizer may move afterwards, and an entry that silently changed its
meaning when the setting moved would be worse than no entry.

**D4 — Rules are not the home for this, and that is deliberate.** The console's
manual-edits log is `Rule` + `RuleJournalEntry`, keyed on a sheet row id and
replayable over the projection. A member is not a sheet row in this change, so a
rule has nothing to target. Once members become rows (next piece), the
organizer's *corrections* may move onto rules and this log keeps what rules
cannot hold: the entrant's own edits, which are not console acts at all. The two
are not duplicates — one records what the organizer decided about a projection,
the other what anybody did to the stored roster.

**D5 — The backup document carries removed members and the log**;
`SCHEMA_VERSION` 21 → 22. A restore that dropped the history would make the
history worth less than the paper it is not printed on. The restore path reads a
v21 document unchanged — members arrive live, the log arrives empty.

**D6 — The organizer edits through the console's own endpoint**, not through the
entrant's. `/my-registration/teams/{id}/roster` is reached by a manage key or an
account and is about *my* registration; the organizer's route is under the
tournament's console prefix and gated by `require_console_access`. Same diff,
same log, different gate and a different actor recorded. *Alternative:* widening
the entrant's endpoint to accept an organizer — rejected: `_team_for_roster_edit`
exists to refuse exactly that, and ownership is the one thing it checks.

## Risks / Trade-offs

- **A filtered `Team.members` hides rows from a reader who does not know**
  → stated in the model docstring and in the relationship's own comment; the
  companion `removed_members` makes the filter visible at the only place anybody
  would look for the others.
- **The log grows without bound on a tournament whose rosters churn** → one row
  per field change, bounded by what organizers and entrants actually do; the same
  shape `PaymentEvent` already carries for every tournament without trouble.
- **The organizer's silent edit surprises the entrant** → the decision the owner
  took, with the `SURCHARGE_ONLY` precedent; the change is visible on the detail
  page where their roster already is. If it proves wrong, a notice is additive.
- **A restore of a v21 backup loses nothing but has no history to show** → an
  empty log on an old document is honest; it says nothing rather than something
  false.
- **Soft-deleted members make the maximum-roster check read the live ones only**
  → the check is already `len(data.members) > team_max` on the request, and a
  restore has its own check. Both count live members, which is what the maximum
  is about.

## Migration Plan

One alembic revision: `team_members.removed_at`, `team_members.removed_by_fencer_id`,
and the `roster_changes` table. Existing members are live (`removed_at` null) and
have the identity they always had — their primary keys — so nothing is backfilled
and no roster changes shape. The log starts empty: the history begins when it is
first kept, which the organizer's view should say rather than implying the
rosters were never touched. Rollback is the down revision; a roster saved in the
meantime is unaffected, since the diff writes the same rows a replace would have.
