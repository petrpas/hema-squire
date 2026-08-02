## Why

Today a tournament becomes public by accident: the moment the last mandatory Setup
item is filled, `setup_missing()` goes empty and the tournament silently appears in
every fencer's list and starts accepting registrations. Nobody decides that, nobody is
told it happened, and the same rule works backwards — deleting a discipline price
un-publishes a live tournament just as quietly. The organizer has no moment of "this
is ready, go", and the completeness checklist that governs it all sits in the Setup
phase's global header, permanently in the way of every tab even when there is nothing
to report.

## What Changes

**Publication becomes an explicit, one-time act**

- A tournament carries a publication record. It is a draft until a console team member
  publishes it, and publication is permanent: there is no unpublish. Retiring a
  published tournament stays what it is today — cancellation.
- Publishing is confirmed before it happens. The confirmation states what publication
  does (the tournament becomes visible to fencers and, within its registration window,
  open for registration) and that it cannot be undone.
- Publication requires complete mandatory setup. The action is refused, naming the
  missing items, when anything is unconfigured.
- **BREAKING**: a published tournament can no longer be edited into incompleteness. A
  save that would leave a mandatory item unconfigured — clearing a discipline price,
  removing the last discipline or organizer, enabling EUR while legacy fixed fees are
  in use — is rejected, naming the item. Draft tournaments are unaffected and stay
  freely editable.
- **BREAKING**: fencer-facing visibility and the registration gate key off the
  publication record instead of `setup_missing()`. A setup-complete tournament that has
  not been published is invisible to fencers and rejects registration with the
  not-yet-published reason.
- **BREAKING (deployment)**: no tournament is backfilled as published. Every existing
  tournament — including any currently live and taking registrations — becomes a draft
  at migration and must be published explicitly before fencers can see it again.

**A sixth Setup tab: PUBLISH**

- Setup gains a sixth tab, `PUBLISH`, last in the bar. It is an action tab like
  `OTHER`: no save control, its own control with its own confirmation.
- While the tournament is a draft, the tab states that it is not published, lists every
  item still blocking publication, and offers the publish control — inert while
  anything is missing.
- Once published, the tab states that the tournament is published and when, and offers
  nothing further.
- **BREAKING**: the completeness checklist is removed from the settings pane header. It
  no longer appears above the tab bar on every tab; the `PUBLISH` tab is the only place
  the blocking items are listed. The per-tab `--stamp` markers stay, so an item read on
  `PUBLISH` can be navigated to, and they clear on publication.

## Capabilities

### New Capabilities
- `tournament-publication`: the publication record and its one-time, irreversible
  transition; who may publish; the completeness precondition; the post-publication
  guard that keeps a published tournament complete; the `PUBLISH` tab, its states, and
  its confirmation.

### Modified Capabilities
- `setup-navigation`: six tabs instead of five; `PUBLISH` added with no save control;
  the checklist leaves the pane header and its placement requirement is rewritten
  around the per-tab markers that remain.
- `tournament-admin`: setup completeness stops being what makes a tournament public and
  becomes the precondition for publishing it; the console authorization requirement
  gains the publish action.
- `registration`: the availability gate and the fencer-facing list filter read the
  publication record, not setup completeness.
- `fencer-home`: "published" in the tab definitions means published, not
  setup-complete.

## Impact

- **Schema**: `tournaments.published_at` (nullable timestamp) with an Alembic migration
  that backfills nothing.
- **Backend**: `app/setup.py` (publication gate, new completeness-guard helper),
  `app/routers/tournaments.py` (new `POST /{slug}/publish`; `/open` and `/mine/past`
  filter on the column; every mandatory-item mutation guarded),
  `app/routers/registrations.py` (gate reason unchanged in name, new source),
  `app/schemas.py` (`published_at` on the detail DTO).
- **Frontend**: `SetupPanel.tsx` (sixth tab, `PublishSection`, checklist removed from
  the header), `api.ts` (`publishTournament`, `published_at`), `index.css` (header no
  longer reserves checklist space), `i18n/cs.json` + `i18n/en.json`.
- **Tests**: `test_registration_gating.py`, `test_open_tournaments.py`,
  `test_past_tournaments.py`, `test_currency.py`, `test_item_options.py` — every test
  that reaches an open tournament by completing setup must now publish it.
- **Sequencing**: overlaps `refine-setup-and-preview`, which respecifies the checklist
  header as non-overlappable. Apply this change after it; the header requirement it
  adds is superseded here.
