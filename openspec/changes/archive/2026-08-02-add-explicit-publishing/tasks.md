## 0. Sequencing

- [x] 0.1 Confirm `refine-setup-and-preview` is applied first; its `setup-navigation`
      header requirement is superseded by this change's `Per-tab incompleteness markers`,
      and its `Section allocation to tabs` / `One save control per tab` wording is the
      base this change's deltas were written against

## 1. Data model and migration

- [x] 1.1 Add `published_at: Mapped[datetime | None]` (`DateTime(timezone=True)`) and
      `published_by_id: Mapped[int | None]` (FK `fencers.id`) to `Tournament` in
      `backend/app/models.py`, next to `cancelled_at`, with a comment stating that null
      means draft and that publication is one-way (design D1)
- [x] 1.2 Alembic revision adding both columns as nullable, with no backfill; downgrade
      drops them. Note in the revision docstring that every existing tournament becomes
      a draft by design (design Migration Plan)
- [x] 1.3 Run the migration against the dev database and confirm every existing row has
      `published_at IS NULL`

## 2. Publication gate and endpoint

- [x] 2.1 In `backend/app/setup.py`, replace the `setup_missing(tournament)` step of
      `registration_availability()` with `tournament.published_at is None ->
      NOT_PUBLISHED`, keeping the reason string and the gate order (cancelled ->
      published -> opens -> closes); update the module docstring, which currently says
      completeness drives the gate
- [x] 2.2 Add `POST /api/tournaments/{slug}/publish` to `backend/app/routers/tournaments.py`,
      beside `/cancel`: `require_console_access`; `409 already_published` when
      `published_at` is set; `409 cancelled` when `cancelled_at` is set; `422
      setup_incomplete` carrying the missing item keys when `setup_missing()` is
      non-empty; otherwise stamp `published_at = datetime.now(UTC)` and
      `published_by_id = fencer.id`, commit, and return the refreshed `TournamentOut`
- [x] 2.3 Filter `/open` and `/mine/past` on `Tournament.published_at.is_not(None)` in
      the SQL `where` clause and delete their in-Python `if setup.setup_missing(...):
      continue` skips (design D5)
- [x] 2.4 Add `published_at` to `TournamentOut` in `backend/app/schemas.py`; keep
      `setup_missing`, which the `PUBLISH` tab renders from

## 3. The published-completeness guard

- [x] 3.1 Add `guard_published_completeness(tournament)` to `backend/app/setup.py`: no-op
      while `published_at is None`; otherwise raise `422` with detail
      `{"reason": "setup_incomplete", "missing": [...]}` when `setup_missing()` is
      non-empty (design D3)
- [x] 3.2 Call it after the mutation and before `session.commit()` in every endpoint that
      can touch a mandatory item: `PATCH /{slug}`, discipline `POST`/`PATCH`/`DELETE`,
      extra-item `POST`/`PATCH`/`DELETE`
- [x] 3.3 Verify the abort rolls back: a rejected discipline delete on a published
      tournament leaves the discipline in the database

## 4. Frontend API layer

- [x] 4.1 Add `published_at: string | null` to `TournamentDetail` in
      `frontend/src/api.ts`
- [x] 4.2 Add `publishTournament(slug)` calling `POST /api/tournaments/{slug}/publish`,
      surfacing the server's reason (`already_published`, `cancelled`,
      `setup_incomplete`) to the caller

## 5. PUBLISH tab

- [x] 5.1 Extend `SetupTab` and `SETUP_TABS` in `frontend/src/SetupPanel.tsx` with
      `"publish"`, last in the order, always offered
- [x] 5.2 Add the `setup-tabpanel` block for `publish`, matching the existing panels'
      `id`/`aria-labelledby` wiring
- [x] 5.3 Write `PublishSection`: draft state (statement that the tournament is not
      published and invisible to fencers, the blocking-item chips moved from
      `ChecklistSection`, the publish control inert while any chip is present with a
      hint saying so), published state (statement naming the publication date, no
      control), cancelled state (statement, no control)
- [x] 5.4 Give the control the inline two-button confirmation from `DangerZoneSection` —
      `common.cancel` plus the publish button, replacing the control in place, no modal,
      no animation — with copy stating fencers will see the tournament, registration
      follows the registration window, and it cannot be undone
- [x] 5.5 On success, refetch the tournament detail so the tab, the tab markers and the
      preview all move to the published state; on failure, show the server's reason on
      the tab and stay a draft
- [x] 5.6 When any tab holds unsaved changes, state on `PUBLISH` that publication uses
      the saved state (design D8); publishing must not flush them

## 6. Settings pane header

- [x] 6.1 Delete `ChecklistSection` and its use above the tab bar; the pane header
      becomes the tab bar alone
- [x] 6.2 Keep `MISSING_TAB` and `markedTabs` unchanged, and mark `PUBLISH` whenever any
      other tab is marked
- [x] 6.3 Adjust `frontend/src/index.css` where the header reserved space for the
      checklist, keeping the non-overlappable sticky header (nothing visible above the
      tab bar at any scroll position, sticky table headers below it)

## 7. Localization

- [x] 7.1 Add `setup.tabs.publish` and the `setup.publish.*` catalogue — draft
      statement, published statement with date, cancelled statement, blocking-items
      lead-in, inert-control hint, unsaved-changes note, publish button, confirmation
      body, failure reasons — to `frontend/src/i18n/cs.json` and `en.json`
- [x] 7.2 Remove the `setup.checklist.*` keys, now unused, from both catalogues; keep
      every `setup.missing.*` key, which the `PUBLISH` tab still uses
- [x] 7.3 Check the copy against the design prohibitions: no Title Case, no exclamation
      marks, no weight 600+, no emoji

## 8. Backend tests

- [x] 8.1 Add a `publish(client, headers, slug)` helper to `backend/tests/conftest.py`
      and use it wherever a test builds a tournament it expects fencers to reach:
      `test_open_tournaments.py`, `test_past_tournaments.py`, `test_currency.py`,
      `test_item_options.py`, `test_registrations.py`, and any other module whose
      registrations start failing with `not_published`
- [x] 8.2 New `backend/tests/test_publishing.py`: setup-complete draft is absent from
      `/open` and rejects registration with `not_published`; publishing makes it appear
      and accept; publishing an incomplete tournament returns `422` naming the items;
      republishing returns `409 already_published` with the timestamp unchanged;
      publishing a cancelled tournament returns `409`; a non-console account is refused;
      a non-owner team member succeeds and is recorded as the publisher
- [x] 8.3 Guard tests in the same module: on a published tournament, clearing a
      discipline price, deleting the only discipline, emptying the location, removing the
      last organizer, and enabling EUR with an unpriced extra item are each rejected and
      write nothing; the same operations on a draft succeed
- [x] 8.4 Update `test_registration_gating.py`: its two `not_published` cases now assert
      the reason for an unpublished tournament rather than an incomplete one, and a new
      case asserts that a complete-but-unpublished tournament is rejected the same way
- [x] 8.5 `test_setup_missing.py` stays green unchanged — `setup_missing()` itself is not
      modified by this change

## 9. Verification

- [x] 9.1 Full backend suite green
- [x] 9.2 Manual pass in the console: create a tournament, watch `PUBLISH` list the
      blocking items and the control stay inert, fill them, publish through the
      confirmation, see the tab switch to its published state and the markers clear,
      then confirm the tournament appears on Fencer Home and accepts a registration
- [x] 9.3 Manual pass on the guard: clear a discipline price on the published tournament
      and confirm the save is rejected naming the item, with the tournament still listed
      for fencers. The server rejects and names the item in the response
      (`{"reason": "setup_incomplete", "missing": ["discipline_prices"]}`); the Setup UI
      surfaces this as the existing generic `setup.saveBar.genericError` message rather
      than a per-item one — accepted as-is, no frontend change made
- [x] 9.4 Deployment note in the change: after migrating, publish every tournament that
      should be public — until then they are invisible to fencers and reject
      registration. Already present verbatim in `design.md`'s Migration Plan step 3 and
      in `proposal.md`'s "BREAKING (deployment)" bullet
