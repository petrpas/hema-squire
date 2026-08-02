## Context

Publication is currently derived, not recorded. `setup.setup_missing(tournament)`
returns the list of unconfigured mandatory items, and everything public reads it:
`registration_availability()` returns `not_published` while it is non-empty,
`GET /api/tournaments/open` and `/mine/past` skip such tournaments in Python after
loading them, and `GET /api/tournaments/{slug}` ships the same list as `setup_missing`
so the Setup checklist can render it. Design D5 of `add-tournament-setup` chose this
deliberately: "one source of truth; no status enum stored."

That choice has aged badly in one specific way — it makes the transition invisible and
symmetric. The organizer never says "go", and an ordinary edit can take a live
tournament off the fencer lists mid-registration. This change keeps `setup_missing()`
exactly as it is (it remains the single definition of completeness) and puts a
recorded, one-way decision on top of it.

The Setup phase reached its tabbed form in `split-setup-into-tabs`, with the checklist
pinned above the tab bar as part of the settings pane header. `refine-setup-and-preview`
is in flight and hardens that header against scroll bleed-through; this change removes
the checklist from it entirely, so the two must be applied in order.

The four owner decisions taken for this change (2026-08-02): guard the invariant after
publication; any console team member may publish; backfill nothing; keep the per-tab
markers.

## Goals / Non-Goals

**Goals:**

- A recorded publication moment, made by a person, confirmed before it happens, and
  never reversed.
- One place in the console — the `PUBLISH` tab — that answers "why can't fencers see
  this yet?".
- The invariant *published ⇒ mandatory setup complete* holds for all time, enforced by
  the server rather than by hope.
- Fencer-facing queries filter on a column instead of loading every tournament and
  discarding some in Python.

**Non-Goals:**

- No change to what mandatory setup *is*. `setup_missing()` keeps its item keys, its
  EUR rules, and its legacy-fee rule verbatim.
- No unpublish, no scheduled publication, no draft-preview links for fencers.
- No new organizer notification, email, or audit trail beyond the timestamp and the
  account that pressed the control.
- No change to cancellation, deletion, or the registration window.

## Decisions

### D1 — A nullable timestamp, not a status enum

`tournaments.published_at: datetime | None` (timezone-aware), mirroring the existing
`cancelled_at`. Null means draft. Publication and cancellation stay orthogonal axes, as
they are today: a published tournament can be cancelled, and cancellation continues to
hide it from listings and close registration without touching `published_at`.

*Alternative rejected*: a `status` enum (`draft | published | cancelled`). It would
force cancellation and publication into one field, breaking the existing meaning of
`cancelled_at` and requiring every cancellation code path to be rewritten. The
timestamp also answers "when", which the `PUBLISH` tab shows.

`published_by_id` (nullable FK to `fencers`) is recorded alongside it, because
publication is a person's decision and "any console team member" now includes accounts
other than the owner. Nothing reads it yet; it exists so the question "who published
this?" is answerable later without a second migration.

### D2 — The gate order gains one step, and `setup_missing` leaves it

`setup.registration_availability()` becomes:

1. `cancelled_at is not None` → `CLOSED`
2. `published_at is None` → `NOT_PUBLISHED`
3. before `registration_opens` → `NOT_YET_OPEN`
4. after `registration_closes` (or the tournament date) → `CLOSED`

The `NOT_PUBLISHED` reason string is unchanged, so clients, i18n keys and the two
existing gating tests keep their vocabulary; only what produces it changes. Step 2
replaces the `setup_missing(tournament)` call outright — completeness is no longer
consulted at registration time at all, because D3 guarantees a published tournament is
complete.

### D3 — The guard: a published tournament cannot be saved into incompleteness

One helper in `app/setup.py`:

```python
def guard_published_completeness(tournament) -> None:
    """422 `setup_incomplete:<item>` when a save would leave a published
    tournament missing a mandatory item."""
```

It is called after the mutation has been applied to the ORM objects and before
`session.commit()`, in every endpoint that can touch a mandatory item:
`PATCH /{slug}` (location, organizers, currency mode, discounts), the discipline
`POST`/`PATCH`/`DELETE`, and the extra-item `POST`/`PATCH`/`DELETE`. Raising inside the
request aborts before the commit, so the session rolls back and nothing is written.
Draft tournaments skip the check entirely and stay freely editable — including deleting
their last discipline.

The error carries the offending item keys, so the frontend can name them with the same
`setup.missing.*` catalogue the `PUBLISH` tab uses.

*Alternative rejected*: validating only at publish time and letting a published
tournament drift (the "publication stands, gaps allowed" option). It permits a fencer
to meet a discipline with no price, which the pricing code has no answer for.

*Alternative rejected*: freezing the whole mandatory field set after publication.
Too blunt — organizers legitimately correct a location or add a discipline after
publishing; only the transition *into* incompleteness is a problem.

### D4 — `POST /api/tournaments/{slug}/publish`

- Authorization: `require_console_access` — the same check every Setup save uses. Not
  owner-only; the danger zone's `require_tournament_owner` stays where it is.
- `409 already_published` when `published_at` is already set. The action is one-time,
  and a double click must not silently re-stamp the timestamp.
- `409 cancelled` when the tournament is cancelled. Publishing a retired tournament is
  meaningless.
- `422 setup_incomplete` with the missing item keys when `setup_missing()` is non-empty.
  The frontend keeps the control inert in that state, so this is a race/API guard, not
  the normal path.
- Otherwise sets `published_at = now(UTC)`, `published_by_id = caller`, commits, and
  returns the refreshed `TournamentOut`.

`POST` (not `PATCH` of a field) because it is an action with preconditions, matching
`/cancel` and `/transfer-ownership` on the same router.

### D5 — Listings filter in SQL; the detail endpoint stays open

`/open` and `/mine/past` add `Tournament.published_at.is_not(None)` to their `where`
clauses and drop the in-Python `if setup.setup_missing(tournament): continue`. This is
strictly cheaper and removes an N-instance completeness computation per request.

`GET /api/tournaments/{slug}` remains reachable for a draft, exactly as a cancelled
tournament's detail is today (design D5 of `add-tournament-setup`): the console needs
it, and the registration gate — not the detail route — is what stops a fencer acting on
it. `TournamentOut` gains `published_at`; `setup_missing` stays on the payload because
the `PUBLISH` tab renders from it.

### D6 — `PUBLISH` is a sixth tab, last, and is an action tab

Order: `TOURNAMENT`, `DISCIPLINES`, `EXTRA`, `PAYMENTS`, `OTHER`, `PUBLISH`. Last
because it is the end of the Setup arc, and because the tab bar then reads as
"configure … then publish". It is offered to every console team member, unlike `OTHER`.

Like `OTHER`, it carries no save control: it holds an action, not settings, which the
existing one-save-per-tab requirement already exempts. Its two states:

- **Draft** — a statement that the tournament is not published and is invisible to
  fencers; the blocking items as chips (the checklist markup, moved verbatim); the
  publish control, inert while any chip is present, with a hint saying so.
- **Published** — a statement naming the publication date, and nothing else. No control,
  no chips; by D3 there can be no chips.

The confirmation follows `DangerZoneSection`'s pattern exactly — an inline two-button
row (`common.cancel` + the publish button) replacing the control in place, no modal, no
animation, per the design prohibitions. Its copy states that fencers will see the
tournament, that registration follows the registration window, and that publication
cannot be undone.

### D7 — The checklist leaves the header; the markers stay

`ChecklistSection` is deleted from the pane header and its chip rendering moves into
`PublishSection`. `MISSING_TAB` and `markedTabs` are untouched: each tab still carries
its `--stamp` marker while it holds an unconfigured item, which is what makes an item
read on `PUBLISH` findable. After publication no marker can appear, so the tab bar goes
quiet for good.

The pane header shrinks to the tab bar alone. The scroll-bleed rules
`refine-setup-and-preview` adds still apply, now to a header of one element.

### D8 — Publishing acts on saved state only

The publish control reads `detail.setup_missing` from the server, so unsaved drafts on
other tabs neither satisfy nor block it. When any tab holds unsaved changes, the
`PUBLISH` tab says so and states that publication uses the saved state — the organizer
is not silently publishing something different from what they are looking at. Leaving
Setup dirty is still confirmed by the existing requirement; publishing is not a leave.

## Risks / Trade-offs

- **[Every existing tournament goes dark at deploy]** → The chosen migration backfills
  nothing, so any tournament currently live disappears from the fencer lists and stops
  accepting registrations the moment the migration runs. Existing registrations, their
  payments, and the console are untouched. Mitigation: the migration is a two-line
  column add and the fix is one click per tournament in the console; the deployment
  step is called out in tasks so the operator publishes affected tournaments
  immediately after migrating. Deployments with live registration open should apply
  this off-hours.
- **[A published tournament with a rejected save reads as a bug]** → An organizer who
  clears a discipline price on a published tournament now gets an error instead of an
  empty field. Mitigation: the message names the item and says the tournament is
  published, so the cause is legible; and the alternative (silently dropping the
  tournament off every fencer's list) is worse.
- **[The guard runs on partly-flushed tab saves]** → Setup's tab save is deliberately
  non-atomic: it flushes row changes one at a time. On a published tournament, a
  sequence that is complete at the end can be incomplete in the middle — deleting the
  only discipline and adding a replacement in one save flushes the delete first and is
  rejected. Mitigation: accepted. The organizer adds the replacement first, saves, then
  deletes; the rejection reports which change failed, which the existing non-atomic
  save requirement already covers.
- **[Tests silently pass by never publishing]** → Any test that builds a complete
  tournament and expects it in `/open` will now get an empty list, which is a visible
  failure, not a silent one. The backend test helpers that build a tournament gain a
  publish step.

## Migration Plan

1. Alembic revision adds `published_at` (nullable `DateTime(timezone=True)`) and
   `published_by_id` (nullable FK) to `tournaments`. No data migration, no backfill:
   every existing row stays null and is therefore a draft.
2. Downgrade drops both columns. Rollback is lossless in the sense that nothing else
   depends on them; a rolled-back deployment returns to derived publication and every
   tournament becomes visible again by completeness.
3. After deploying, the operator publishes each tournament that should be public,
   through its `PUBLISH` tab. Until then those tournaments are invisible to fencers and
   reject new registrations with `not_published`.

## Open Questions

None. The four decisions this change turned on — the post-publication guard, who may
publish, the backfill, and the fate of the tab markers — were settled by the owner on
2026-08-02 and are recorded in D3, D4, the migration plan, and D7 respectively.
