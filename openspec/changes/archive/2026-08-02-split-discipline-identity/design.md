## Context

`Discipline.code` is a single string doing three jobs, and the three have been drifting
apart since the taxonomy was written.

```
                    ┌───────────────────────────────────┐
                    │  Discipline.code = "LS"           │
                    └───────────────────────────────────┘
                        │           │            │
        ┌───────────────┘           │            └────────────────┐
        ▼                           ▼                             ▼
  ① IDENTITY                  ② CLASSIFICATION            ③ EXTERNAL KEY
  which row is this?          what kind of fencing?        HEMA Ratings join

  UNIQUE(tournament, code)    taxonomy.is_valid_code()     hr_category_map keys
  PATCH/DELETE .../{code}     weapon × gender × material   HRSnapshotRating
  registration payloads       default_name()                 .discipline_code
  export_json round-trip      importer.ParsedDiscipline    hr_sync.py:249,277
  sheet.py columns
```

Each job wants a different cardinality per tournament: ① as many rows as the organizer
invents, ② one label per row freely repeated, ③ one fetch per distinct facet triple. One
string forces ① = ② = ③, and `UNIQUE(tournament_id, code)` (`models.py:302`) makes it
binding.

The decomposition already exists in the codebase, just not in the database.
`importer.ParsedDiscipline` (`importer.py:64`) models weapon/gender/material and
*derives* the code as a property; `taxonomy._build()` computes the 30-entry `DISCIPLINES`
dict as a cross product at import time. The facets are the real model. The flat code is a
projection that got promoted to primary key.

## Goals / Non-Goals

**Goals**

- A tournament can offer several disciplines sharing a classification (tiers).
- A tournament can offer individual and team competition in the same weapon.
- A tournament can offer a weapon the taxonomy has never heard of.
- Existing tournaments migrate with no change to any URL, export, or stored sheet.

**Non-Goals**

- Eligibility. A tier is a label (D2). No rating cutoffs, no seeding, no automatic
  assignment of fencers to tiers, no cross-tier movement.
- Opening gender or material. Those sets are genuinely closed (D4).
- Recovering tier information from legacy imports. It was never recorded (D8).
- Admitting waitlisted teams, or anything else `add-team-disciplines` left out of scope.

## Decisions

### D1 — Identity is a slug, not a name and not a surrogate id

A discipline is identified within its tournament by a short organizer-visible string.

The obvious alternative — identify by **name** — fails on stability. Names are editable,
localized, and contain spaces; renaming "Longsword Open" to "Longsword Open (Tier A)"
would have to cascade through URLs, exports, stored sheet columns, and cached import
decisions. Identity must not move when presentation does.

The other alternative — identify by **surrogate id**, `/disciplines/47` — fails on
portability. `export_json.py:172,369` writes a discipline token per entry and re-resolves
it on import; `sheet.py:77` writes discipline tokens into the organizer's output
spreadsheet. A row id does not survive an export/import across databases, and does not
survive a human reading the spreadsheet. The export needs a portable, readable token.

So: a slug. Short enough for a spreadsheet column, stable enough for a URL, portable
enough for a JSON round-trip.

### D2 — A tier is a label, and nothing more

"LS tier A" and "LS tier B" differ by name and by nothing else the system understands.
There is no `min_rating`, no `max_rating`, no eligibility check, no seeding, and no
automatic assignment. The organizer decides who belongs where by whatever means they
already use, and enters the result.

This is a deliberate floor, not an oversight. Squire holds HR ratings per fencer per
category (`HRSnapshotRating`), so a rating-cutoff tier would be buildable — but organizers
split brackets by invitation, by club, by prior results, and by judgment at least as often
as by rating. Encoding one of those policies would exclude the rest. A label excludes
nothing, and a cutoff can be added later on top of a label without a second migration.

### D3 — Slugs are generated, overridable, and frozen on reference

The organizer should not have to invent identifiers, because fencers never see them (D6).
The system derives the slug from the classification and disambiguates with a counter:

```
add longsword             → LS
add longsword again       → LS-2
add plastic sabre women   → Plastic-SAW
add "messer"              → messer
```

The organizer MAY override the generated slug — an organizer who prefers `LS-A` / `LS-B`
in their spreadsheet should get it — and the override is subject to the same uniqueness
check.

A slug is editable while the discipline is unreferenced and frozen once any
`RegistrationDiscipline` or `Team` points at it. This reuses `_discipline_referenced`
(`routers/tournaments.py:524`) exactly as it stands, which is already the freeze rule for
`kind`. Two frozen-on-reference fields sharing one predicate is cheaper than two rules,
and the reason is the same in both cases: once a fencer has entered, the row's identity
is in emails, exports, and payment records that the system cannot rewrite.

The current rule — `code_is_immutable`, rejecting any change from creation onward
(`routers/tournaments.py:554`) — is strictly stricter than it needs to be. An organizer
who adds a second tier and then wants to rename the first for symmetry is doing something
harmless if nobody has registered.

### D4 — Only weapon opens; gender and material stay closed

Weapon becomes a free string. Gender stays `"" | "W" | "M"` and material stays
`"" | "Plastic"`.

The asymmetry is real, not a compromise. Gender and material are closed in the domain:
there is no third material and no fourth gender category in HEMA Ratings or in practice.
Weapon is open in the domain: Messer, Ringen, staff, mixed-weapon, and club-specific
formats exist and get run. Opening the closed ones would buy nothing and would break the
HR join for no gain; leaving weapon closed keeps rejecting real tournaments.

A discipline whose weapon is outside the taxonomy simply has no HR rating category.
`hr_sync.category_keyword()` already returns `None` for an unrecognized code and the
caller already `continue`s past it (`hr_sync.py:237-239, 277-279`). The open weapon lands
on an existing null path and adds no branch.

One consequence: `taxonomy.default_name()` cannot generate a name for a custom weapon, so
the name becomes required when the weapon is outside the taxonomy. For the five known
weapons it keeps auto-filling as today.

### D5 — The HR join keys on the taxonomy code, which is derived

The taxonomy code survives — as a derived value, not a stored one:

```python
taxonomy_code = f"{material} {weapon}{gender}".strip()   # "LS", "Plastic SAW"
```

It keys `Tournament.hr_category_map` and `HRSnapshotRating.discipline_code`, exactly as
the old `code` did, and it is the unit of work in `take_snapshot`: the snapshot fetches
once per **distinct taxonomy code**, not once per discipline row. Two tiers of longsword
share one category, one override, and one fetch, and cannot drift apart — which they
could if the map were keyed on identity and an organizer edited one tier's override.

Naming matters here. The stored field is `slug`, the derived value is `taxonomy_code`,
and no field is called `code`. The whole defect was two different things sharing that
name; leaving it on either one invites the collapse to happen again.

A custom weapon derives a taxonomy code that no keyword map knows, which is exactly the
null path D4 describes. No special case.

### D6 — Fencers see the name; the slug is an organizer and machine token

Every fencer-facing surface renders the name alone. Five places render `{code} — {name}`
today — `emails.py:16`, `TournamentFace.tsx:202,729,757`, `FencerHome.tsx:99` — and all
five become `{name}`. Nothing is lost: `name` is currently the generated taxonomy name
("Longsword Open"), so the code was a redundant prefix even before tiers existed. With
tiers it becomes actively misleading, since two disciplines a fencer must choose between
would show the same prefix.

"Fencers do not see it" is not "nobody sees it". The slug appears in the console
discipline table, in `sheet.py:77`'s output spreadsheet columns, in the JSON export, and
in API paths — all read by organizers. That is why it stays readable (`LS-2`) rather than
opaque (`47`), and it is the second half of D1's argument against surrogate ids.

`TeamsPanel.tsx:33` is organizer-facing and keeps its slug prefix.

### D7 — The import parser chooses a discipline instead of describing one

`ParsedDiscipline` is a pydantic-ai structured output: the LLM is forced to answer in
weapon/gender/material, and `sheet.py:122` derives a code from the answer to match a
discipline row.

```
raw row: "Jan Novák, longsword"
              │
              ▼  LLM, output constrained to 3 fields
      weapon=LS, gender="", material=""
              │
              ▼  derive code → "LS"
              │
       ┌──────┴──────┐
    LS tier A     LS tier B        ← which?
```

The struct fails on both of this change's axes: `Literal["LS","SA","RA","RD","SB"]`
cannot emit a Messer (D4), and three facets cannot distinguish two disciplines sharing
them (D2). It stops being a viable output type regardless of tiers, because the open
weapon breaks it on its own.

The replacement is smaller than what it replaces: the parse yields a **slug chosen from
the tournament's offered list**. The system prompt already passes
`Disciplines offered by this tournament: {disciplines}` and already instructs *"Only use
disciplines offered by this tournament, nothing else"* (`importer.py:121,125`) — it hands
over codes and accepts facets back, which was always a strange round trip. Handing over
`slug — name` pairs and taking a slug back lets the model match on the name, which is
where "Tier A" and "Messer" live. The derive-code-from-facets step in `sheet.py:122`
disappears.

### D8 — Ambiguous legacy rows become organizer decisions, not guesses

A v1 sheet row saying "Jan Novák, longsword" does not say which tier, because v1 had no
tiers. No parser can recover information the source never held.

When the offered list contains several disciplines the row could mean, the parse records
a `problems` entry and leaves the discipline unresolved rather than picking one. This is
the existing escape hatch — `problems` is already surfaced in the console
(`importer.py:281-286`) and organizer verdicts already persist as decisions keyed by row
fingerprint, so a resolved row stays resolved across re-uploads. No new machinery.

Guessing would be worse than failing here: a silently mis-tiered fencer is discovered at
the venue.

## Migration Plan

The split is unusually gentle because the backfill parse is total — 30 known codes, all
generated by `taxonomy._build()`, all parseable back into the facets that generated them.

```
before                       after
──────                       ─────
code = "Plastic SAW"    →    slug     = "Plastic SAW"    (identical — URLs unchanged)
                             weapon   = "SA"     ┐
                             gender   = "W"      ├─ parsed from the old code
                             material = "Plastic"┘
                             name     = unchanged
```

- `disciplines.code` → `disciplines.slug`, values unchanged.
  `UNIQUE(tournament_id, code)` → `UNIQUE(tournament_id, slug)`. The constraint survives
  verbatim; only its meaning narrows, from "one longsword per tournament" to "one row per
  identifier".
- Add `weapon`, `gender`, `material`, backfilled from the old code. Not nullable after
  backfill.
- SQLite needs `op.batch_alter_table` for the rename and the constraint, as
  `a3f7c9d21e08` already does for `disciplines`.
- **No data migration** for `tournaments.hr_category_map` or
  `hr_snapshot_ratings.discipline_code`. Their keys are taxonomy codes today and stay
  taxonomy codes; for every pre-migration row the old code and the derived taxonomy code
  are the same string. The change is in what the key *means*, not what it holds.
- Stored artifacts outside the database — exported JSON files, the organizer's output
  spreadsheet, cached import decisions — keep resolving, because every migrated slug
  equals the code those artifacts recorded.

Down-migration reverses cleanly only while no tournament has taken advantage of the new
freedom. A tournament with two longsword tiers cannot be represented in the old schema;
`downgrade()` should fail loudly on such a row rather than silently dropping one.

## Risks / Trade-offs

**A generated `LS-2` is a poor label in a spreadsheet.** The organizer sees `LS` and
`LS-2` in their export and has to remember which is the top bracket. Mitigated by the
override (D3) and by the name column travelling alongside the slug everywhere the slug
appears — but an organizer who never opens the override will live with `LS-2`. Accepted:
the alternative is forcing every organizer to name identifiers for a feature most of them
will not use.

**Open weapons silently lose HR ratings.** A Messer discipline gets no rating column and
no warning, because the null path it lands on (D4) is the same one that handles a
taxonomy code with no configured keyword. An organizer could reasonably expect ratings
and not notice their absence. The console should say so where the weapon is entered
rather than leaving it to be discovered at export time.

**The parser change is a behavioral change to a cached surface.** Import decisions are
keyed by row fingerprint, not by parser version, so rows parsed under the old struct keep
their stored decisions and are not re-parsed. That is the desired incrementality, but it
means a tournament mid-import will hold decisions in two shapes; the reader in
`sheet.py:_imported_rows` must accept both — old-shape decisions resolve through the
facet derivation, new-shape ones are already slugs. This is a compatibility shim with a
real end date (the next re-upload), not a permanent fork.

**Fencer-facing labels get longer.** The Fencer Home card currently packs discipline
chips as codes — `LS 18/25` — and D6 replaces them with names: `Longsword Open 18/25`.
That is roughly three times the width, for six chips on a card that already collapses on
narrow screens. The slug would fit, but `LS-2 18/25` tells a fencer nothing, which is the
whole point of D6. Accepted, with the discipline row specified to wrap rather than
truncate: a truncated tier name is worse than a tall card, because truncation is exactly
where two tier names stop differing.

**Two tiers with equal capacity look like one discipline in aggregate views.** Anything
that sums or groups by classification rather than identity — participant counts, the
public list — will merge tiers unless it groups by slug. Every such site is enumerated in
the tasks; the risk is one being missed and quietly under-reporting.
