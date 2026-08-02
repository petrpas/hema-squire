## 0. Sequencing

- [x] 0.1 Apply after `add-team-disciplines`, which is implemented but not archived. Every
      delta here is written against its post-team wording (`tournament-admin` Tournament
      definition, `registration` Registration form, `data-export` both requirements,
      `fencer-home` Tournament detail). Archive the two in order; if `add-team-disciplines`
      is archived first the base texts match as written, and if it is revised, re-base
      these deltas before syncing
- [x] 0.2 The new `discipline-identity` capability owns slug, classification, and taxonomy
      code. Where another spec needs those rules it references the capability rather than
      restating them — keep it that way when editing the deltas

## 1. Taxonomy: code becomes derived

- [x] 1.1 In `backend/app/taxonomy.py`, add `taxonomy_code(weapon, gender, material) -> str`
      producing the v1 form (optional material prefix, weapon code, gender suffix:
      `LS`, `SAW`, `Plastic LSM`). This is the same expression
      `importer.ParsedDiscipline.code` computes today (`importer.py:73-77`) — move it here
      and make it the one definition
- [x] 1.2 Add `parse_code(code) -> (weapon, gender, material)`, the inverse over the 30
      generated codes, for the migration backfill and for reading pre-migration export
      documents. Assert it round-trips against every key of `DISCIPLINES` in a test
- [x] 1.3 Add `taxonomy_name(weapon, gender, material) -> str | None`, returning the
      generated name for a taxonomy weapon and `None` for any other. `default_name(code)`
      goes away with its last caller (task 3.2)
- [x] 1.4 Keep `WEAPONS`/`GENDERS`/`MATERIALS` and `DISCIPLINES` as they are — the console
      still offers the five weapons as choices and HR still keys on the generated codes.
      Replace `is_valid_code` with `is_taxonomy_weapon(weapon) -> bool`; validation moves
      from the packed code to the weapon alone (design D4)

## 2. Data model and migration

- [x] 2.1 In `backend/app/models.py`, rename `Discipline.code` to `slug` and add
      `weapon: Mapped[str]` (String(30)), `gender: Mapped[str]` (String(1)),
      `material: Mapped[str]` (String(10)). Change `__table_args__` to
      `UniqueConstraint("tournament_id", "slug")`
- [x] 2.2 Add a `taxonomy_code` property on `Discipline` delegating to
      `taxonomy.taxonomy_code`. Comment that it is the join key to everything outside the
      discipline and is never its identity (design D5), and that no field is called `code`
      because that name is what collapsed the two
- [x] 2.3 Update the `Discipline` docstring: identity is the slug, classification is the
      three facets, several disciplines MAY share a classification
- [x] 2.4 Comment `Tournament.hr_category_map` (`models.py:245-246`) and
      `HRSnapshotRating.discipline_code` (`models.py:671`) as keyed by **taxonomy code**,
      not by discipline identity — their contents do not change, only what the key means
- [x] 2.5 New alembic revision on `a3f7c9d21e08`. In `batch_alter_table("disciplines")`:
      add the three classification columns nullable, backfill from `code` via
      `taxonomy.parse_code`, set them non-nullable, then rename `code` to `slug` and
      recreate the unique constraint on `(tournament_id, slug)`. Docstring: every slug
      equals its old code, so URLs, exports, and stored sheet columns keep resolving; the
      constraint survives verbatim and only its meaning narrows (design Migration Plan)
- [x] 2.6 `downgrade()` reverses the rename and drops the classification columns, but
      SHALL raise if any tournament holds two disciplines sharing a taxonomy code — that
      state has no representation in the old schema and must not be silently halved

## 3. Slug generation and the console API

- [x] 3.1 Add `generate_slug(tournament, weapon, gender, material) -> str` beside the
      discipline endpoints in `backend/app/routers/tournaments.py`: the taxonomy code with
      spaces replaced by `-`, then `-2`, `-3`, … until it does not collide with an
      existing slug in that tournament (design D3)
- [x] 3.2 Rewrite `add_discipline` (`tournaments.py:490`): drop the
      `is_valid_code`/`discipline_exists` pair, take `weapon`/`gender`/`material` from the
      payload, validate gender and material against their closed sets, generate the slug
      when the payload omits one and check uniqueness when it supplies one (409 naming the
      conflict), and default the name from `taxonomy.taxonomy_name` — rejecting with 422
      when the weapon is outside the taxonomy and no name was given (design D4)
- [x] 3.3 Route discipline endpoints by slug: `PATCH`/`DELETE /{slug}/disciplines/{slug}`
      (`tournaments.py:542,577`). Rename the path parameter so it does not shadow the
      tournament slug — `discipline_slug` — and update the lookups at `:551` and `:582`
- [x] 3.4 In `update_discipline`, replace the `code_is_immutable` rejection (`:554`) with
      the freeze rule: a slug change is accepted while `_discipline_referenced` is false
      and refused with 409 `discipline_slug_frozen` once it is true. A changed slug is also
      checked for uniqueness. `_discipline_referenced` (`:524`) is reused unchanged — it is
      already the freeze predicate for `kind` (design D3)
- [x] 3.5 Allow classification edits under the same freeze rule, since changing a weapon
      changes which HR category a discipline joins. Frozen classification is refused with
      the same 409
- [x] 3.6 In `backend/app/schemas.py`, replace `code` with `slug`, `weapon`, `gender`,
      `material` in `DisciplineIn` (`:102`) and `DisciplineOut` (`:136`); make
      `DisciplineIn.slug` optional so creation can omit it. Update the discipline blocks in
      the tournament payloads at `:465`, `:481`, `:514`, `:554`, `:656`, `:804` and
      `AvailabilityOut` (`:594`)
- [x] 3.7 Update the three `code=d.code` construction sites at `tournaments.py:175`,
      `:270`, `:644`, and the `team_codes` set at `:409`

## 4. Registration API

- [x] 4.1 In `backend/app/routers/registrations.py`, rename the `by_code` maps at `:265`
      and `:297` to `by_slug` and key them on `Discipline.slug`. Update the docstring at
      `:296` — it currently says "nothing here reads more than `.code`"
- [x] 4.2 Update the wire fields at `:117`, `:176`, `:196`, `:210`, `:242` and the full/
      substitute sets at `:424`, `:616`, `:629`, `:753` from code to slug
- [x] 4.3 `backend/app/availability.py` needs no change: it already joins on
      `discipline_id` throughout. Confirm and leave it alone
- [x] 4.4 `backend/app/pricing.py` needs no change: it reads fee fields off `Discipline`
      rows and never touches the code. Confirm and leave it alone

## 5. HEMA Ratings

- [x] 5.1 In `backend/app/hr_sync.py`, change `category_keyword` (`:237`) to take a
      taxonomy code, and `take_snapshot`'s `codes` (`:249`) from one entry per individual
      discipline to the **distinct** taxonomy codes among them (design D5). The per-fencer
      loop at `:277` is otherwise unchanged, and `HRSnapshotRating.discipline_code` keeps
      storing a taxonomy code
- [x] 5.2 Confirm the null path at `:238-239` and `:277-279` handles a custom weapon with
      no further branch — `category_keyword` returns `None` and the caller `continue`s.
      Covered by `test_custom_weapon_contributes_nothing_without_failing_snapshot` (9.6)
- [x] 5.3 In `backend/app/sheets_export.py:145`, group the per-discipline worksheets by
      **slug** (one worksheet per discipline, so tiers get one each) while reading ratings
      by taxonomy code. Worksheets for disciplines with no category get empty HRating and
      HRank columns
- [x] 5.4 Key the console's HR category map editor on taxonomy code, offering one row per
      distinct classification among the tournament's individual disciplines rather than one
      per discipline — no-op: no console editor for `hr_category_map` exists in the
      frontend (grepped, none found); the field is already `dict[str, str]` keyed by
      taxonomy code end to end, unaffected by this change

## 6. Table import

- [x] 6.1 Delete `importer.ParsedDiscipline` (`importer.py:64-77`) and change
      `ParsedFencer.disciplines` to `list[str]` holding offered slugs (design D7)
- [x] 6.2 Change the `ImportParser.parse` signature (`:109`, `:143`) to take the offered
      disciplines as `(slug, name)` pairs, and the `_SYSTEM_PROMPT` (`:112-129`) to list
      them as `slug — name` and to instruct that the answer is one of those slugs. Drop the
      weapon/gender/material explanation at `:117-119`: the model no longer classifies
- [x] 6.3 Add the ambiguity instruction to the prompt: where the row does not say which of
      several offered disciplines is meant, record a problem and omit the discipline rather
      than choosing (design D8)
- [x] 6.4 Update the call site at `importer.py:269-270` to pass slug/name pairs
- [x] 6.5 In `backend/app/sheet.py:122`, read the new shape directly (the values are already
      slugs) and add the compatibility shim for stored decisions in the old shape: a
      `{weapon, gender, material}` dict resolves through `taxonomy.taxonomy_code` to the
      offered disciplines sharing that classification — to the one when there is exactly
      one, and to unresolved-with-a-problem when there are several (design Risks). Comment
      that the shim expires with the next re-upload of each row

## 7. Exports and email

- [x] 7.1 In `backend/app/export_json.py`, export `slug`, `name`, `weapon`, `gender`,
      `material` per discipline and reference disciplines by slug at `:172` and `:187`.
      Raise the document version
- [x] 7.2 At `:369`, resolve team entries by slug, and reject a document referencing an
      undefined slug with the slug named — currently a `KeyError`
- [x] 7.3 Read pre-version documents by taking each discipline's `code` as its slug and
      parsing its classification with `taxonomy.parse_code`, which is exactly what the
      migration does to stored rows
- [x] 7.4 In `backend/app/sheet.py:77,80`, write slugs into the Disciplines column
- [x] 7.5 In `backend/app/emails.py:16`, drop the code prefix: the summary line becomes the
      discipline name alone (design D6)

## 8. Frontend

- [x] 8.1 In `frontend/src/api.ts`, replace `code` with `slug` and add `weapon`, `gender`,
      `material` on the discipline types (`:124`, `:145`, `:318`, `:350`, `:365`, `:388`,
      `:438`, `:480`) and on the team entry shape (`:459`); update the endpoint paths at
      `:581-587`
- [x] 8.2 In `SetupPanel.tsx`, add a slug field and a weapon field to the discipline row
      (`disciplineToRow` `:736`, `disciplineRowInput` `:772`, the blank row at `:804`). The
      weapon field offers the five taxonomy weapons and accepts another; the slug field is
      prefilled from the server's generated value and read-only once frozen
- [x] 8.3 Change the row identity in `SetupPanel.tsx` from code to slug: `rowId` (`:738`),
      the dirty and price comparisons (`:756`, `:793`), and the removal set (`:900`)
- [x] 8.4 Add the slug help hint ("names the discipline in exports and spreadsheets; fencers
      never see it") alongside the existing per-field hints
- [x] 8.5 State at the weapon field that a weapon outside the taxonomy carries no HEMA
      Ratings figures (spec `hr-integration`), and require a name when one is chosen
- [x] 8.6 In `TournamentFace.tsx`, key the maps and sets on slug (`:172`, `:458`, `:465`,
      `:493`, `:501`, `:528`, `:563`, `:620-622`, `:686`, `:723-732`, `:754-794`) and drop
      the `{code} — {name}` prefix at `:202`, `:729`, `:757` in favour of the name alone
- [x] 8.7 In `FencerHome.tsx:99`, label the chip with the discipline name and let the chip
      row wrap; verify at the narrowest supported width that no name truncates and the card
      does not widen (design Risks, spec `fencer-home`) — `.chips`/`.chip` already wrap with
      no truncation styling, confirmed in `index.css`
- [x] 8.8 `TeamsPanel.tsx:31,33` is organizer-facing: key on slug and keep the
      `{slug} — {name}` heading
- [x] 8.9 Add the new strings to `frontend/src/i18n/{cs,en}.json` and any backend copy to
      `backend/app/locales/{cs,en}.json` — no discipline-facing backend copy found

## 9. Tests

- [x] 9.1 `taxonomy`: `taxonomy_code`/`parse_code` round-trip over all 30 generated codes;
      `taxonomy_name` returns `None` for a weapon outside the taxonomy
- [x] 9.2 Console: two disciplines with the same classification are both accepted and get
      `LS` and `LS-2`; an individual and a team discipline in one weapon are both accepted;
      an organizer override to `LS-A`/`LS-B` is accepted; a colliding override is refused
      with the conflict named
- [x] 9.3 Console: a slug edit is accepted before any registration, refused after an
      individual entry, and refused after a team entry — the three scenarios of
      `discipline-identity`'s freeze requirement
- [x] 9.4 Console: a custom weapon is accepted with a name and refused without one
- [x] 9.5 Registration: a fencer entering one of two same-classification disciplines is
      counted against that one only, and capacity of the other is untouched
- [x] 9.6 HR: two tiers of one weapon produce one fetch and one shared rating; a custom
      weapon contributes nothing and does not fail the snapshot
- [x] 9.7 Export: tiers round-trip; individual-plus-team in one weapon round-trips; a
      document with a dangling slug is rejected; a pre-version document loads with codes
      taken as slugs and classification parsed
- [x] 9.8 Sheets: two tiers produce two worksheets; a custom-weapon discipline produces a
      worksheet with empty rating columns
- [x] 9.9 Import: an unambiguous row resolves to a slug; a row naming a bracket resolves to
      that bracket; a row naming only the weapon in a split tournament is left unresolved
      with a problem; an old-shape stored decision resolves when unambiguous and is
      reported unresolved once the weapon is split
- [x] 9.10 Migration: an existing database upgrades with every slug equal to its old code
      and classification backfilled; `downgrade` raises on a tournament holding two
      disciplines of one taxonomy code
- [x] 9.11 Update `backend/tests/test_registrations.py` and
      `backend/tests/test_team_disciplines.py` for the field rename — plus every other test
      file in the suite that built a discipline through the old `code` shape, since this is
      a breaking wire-format change across the whole backend

## 10. Validation

- [x] 10.1 `openspec validate split-discipline-identity --strict` — valid
- [x] 10.2 Backend test suite (424 passed) and frontend typecheck (`tsc -b --noEmit` clean)
- [x] 10.3 Grep for surviving `\.code\b` on discipline objects across
      `backend/app/` and `frontend/src/` — the rename is only done when none remain and no
      field anywhere is called `code` on a discipline (design D5) — none found
