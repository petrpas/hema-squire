## Context

`split-discipline-identity` separated a discipline's identity (slug) from its
classification (weapon × gender × material) and its kind, and made all of them editable
until a registration references the discipline. The console did not follow. The Setup
discipline table still renders every identity field as a control and disables all of them
on save:

```
SetupPanel.tsx:1063-1118   weapon / gender / material — .param-fields is a flex
                           COLUMN, so three selects stack inside one <td>
SetupPanel.tsx:1120-1149   name / slug / kind — three more disabled inputs
                           all six:  disabled={!row.isNew}
```

The result is eight columns, of which the first four are inert for every saved discipline,
and no path at all to the edits the backend permits.

Constraints this design inherits and does not revisit:

- `setup-navigation` — "Row tables are drafts until the tab is saved": adding, editing, and
  deleting a row change only the local draft; the tab's single save control flushes them.
- `design-system` — modal framing (double frame, no shadow), form conventions (label above,
  bottom-ruled inputs, framed selects), outline icons only, and the global prohibitions in
  `CLAUDE.md`.
- `discipline-identity` — the freeze predicate is "any entry or team references it", shared
  by slug, classification, and kind.

## Goals / Non-Goals

**Goals:**

- Remove every inert control from the discipline row.
- Make identity editable in the console exactly as far as the backend already permits.
- Give an organizer running individual and team longsword two slugs that say which is which.
- Keep the console's single-save draft model untouched.

**Non-Goals:**

- Rewriting existing slugs. They are in stored URLs, exports, and spreadsheet columns.
- Changing the freeze rule itself, on either side.
- Moving capacity, prices, roster bounds, schedule, or ruleset into the dialog. Those are
  operational fields, edited often, and belong in the table where they can be compared
  across rows.
- Introducing a tier vocabulary. A tier remains a label, per `discipline-identity` D2.

## Decisions

### D1 — The dialog owns identity; the table owns operations

One rule with no overlap: the six fields that are frozen together live in the dialog, and
everything else stays a live control in the row or its subrow.

```
┌─ dialog ─────────────────────┐      ┌─ row ────────────────────────┐
│ kind · material              │      │ name  slug  capacity  fee    │
│ weapon · gender              │  →   │ (text)(text)  (input)(input) │
│ name · slug                  │      ├─ subrow ─────────────────────┤
└──────────────────────────────┘      │ min/max · when · where · ... │
                                      └──────────────────────────────┘
```

The split is not arbitrary — it is the freeze boundary. Every field in the dialog becomes
immutable at the same instant, for the same reason, and every field outside it stays
editable for the tournament's whole life. An organizer who learns "the dialog is the part
that sets in stone" has learned the whole rule.

*Alternative considered:* put the entire row in the dialog and make the table read-only.
Rejected — capacity and price are the fields organizers actually revise, often across
several disciplines at once, and a dialog per row would make comparing them impossible.

### D2 — Confirming the dialog writes to the draft, not to the server

`setup-navigation` already fixes this: row edits are drafts, the tab's save control flushes
them, and a save that fails reports against the row. A dialog that PATCHed on confirm would
put two save semantics inside one tab and make the tab's "discard by leaving" escape hatch
incoherent — the organizer would have discarded some of their edits and not others.

The cost is that server-side rejections (slug taken, name required) would surface at save
time rather than at confirm time. Both are checkable client-side: the dialog holds every
row in the table, so uniqueness is a local check, and "custom weapon requires a name" is a
local check. The dialog validates both on confirm; the server keeps its checks as the
authority, and a rejection still lands on the row through the existing non-atomic flush.

### D3 — Prefill until touched, per field

Name and slug derive from the four fields above them until the organizer types in one, and
then that one stops deriving. Two independent flags, not one:

```
pick LS              → name "Longsword"        slug "LS"
pick women           → name "Longsword Women"  slug "LSW"
type "Ladies sabre"  → name pinned
pick SA              → name "Ladies sabre"     slug "SAW"    ← slug still derives
```

The derivation runs client-side, which means porting `taxonomy_code()`
(`backend/app/taxonomy.py:44`, ten lines) and the name composition into the frontend. That
is duplicated domain logic and a place the two can drift.

*Alternative considered:* a preview endpoint that returns the derived name and slug. It
removes the duplication but makes every keystroke on the weapon field a round trip, and the
dialog would show empty fields until it answered. Rejected. The duplication is also not
new: `LEGACY_WEAPONS` (`TournamentFace.tsx:20`) already mirrors `taxonomy.WEAPONS`.

Because the dialog always sends explicit values, the backend's own generators
(`generate_slug`, `taxonomy_name`) become fallbacks for non-console callers — the import
path and tests — rather than the primary route. They stay, and stay correct.

### D4 — Slug normalization is case-preserving

A slug reaches a URL path segment, a spreadsheet column header, and an import parse. An
open weapon field lets an organizer put `Tešák` or `Sword & Buckler (variant)` into it, so
normalization is required. The normalizer folds diacritics to ASCII, collapses every run of
non-alphanumeric characters to a single `-`, and trims leading and trailing `-`. It applies
to an override as well as to a generated slug, because an override reaches exactly the same
places.

It does **not** fold case:

```
Tešák                    → Tesak
Sword & Buckler (var.)   → Sword-Buckler-var
LS                       → LS
Team-LS                  → Team-LS
LS-A  (override)         → LS-A
```

*Alternative considered:* case-folding, so every slug is lowercase. It is more uniform in
the abstract and it is what a slug usually means. It is rejected here because the slug's
alphabet is not free — it is derived from the HEMA taxonomy codes, which are uppercase
(`LS`, `SAW`, `Plastic LSM`) everywhere else in this system, including in
`discipline-identity`'s own scenarios and in the HR join key. Folding would make every new
slug disagree with every stored one and with the code it is derived from, to buy uniformity
in a field fencers never see. This is the change's one genuinely open decision; flipping it
is a one-line change to the normalizer plus the affected scenarios.

### D5 — Kind joins the slug base, forward only

`generate_slug(tournament, weapon, gender, material)` becomes
`generate_slug(tournament, kind, weapon, gender, material)`, prefixing `Team-` for a team
discipline before the collision counter runs:

```
individual longsword           → LS
team longsword                 → Team-LS
second individual longsword    → LS-2
second team longsword          → Team-LS-2
```

This is the case `split-discipline-identity` was written for, and it currently produces
`LS` and `LS-2`. Existing rows keep the slugs they have; nothing is regenerated. The
mismatch that leaves behind — a tournament whose team discipline is called `LS-2` — is
exactly what D6 lets an organizer repair, provided nobody has registered yet. Where someone
has, the slug is frozen and stays frozen, which is correct: it is already in emails and
exports.

"Forward-only" scopes this change, not the system. `add-field-validation` binds a pattern
to the slug and migrates the stored slugs that fail it — the pre-split plastic codes, which
carry a space (`Plastic SAW`) because `split-discipline-identity` renamed `code` to `slug`
in place. That rewrite is deliberate and belongs to that change; nothing here performs it,
and the freeze rule does not apply to a migration.

### D6 — `identity_frozen` is a reported field, not an inferred one

The console must know whether to offer the edit control. `DisciplineOut` gains
`identity_frozen: bool`, computed from `_discipline_referenced`.

It must not be inferred from the `taken` count the detail response already carries, which
is a near-miss in three separate ways:

```
availability.taken_seats()          _discipline_referenced()
├ asserts kind == INDIVIDUAL        ├ both kinds
├ paid + unexpired reserved only    ├ any RegistrationDiscipline row
├ excludes substitutes              ├ includes substitutes
└ ignores Team entirely             └ includes Team
```

A discipline with one cancelled entry reports `taken == 0` and is frozen. Inferring from
`taken` would offer an edit control that leads to a 409.

`_discipline_referenced` is two queries per discipline. Serializing it per row would make a
tournament detail 2N queries, so the flag is computed for the whole tournament in one pair
of grouped queries and looked up per row.

### D7 — The row must stop identifying itself by its current slug

Three call sites resolve a draft row against the server state by `row.slug`:

```
SetupPanel.tsx:774   disciplineRowDirty      → find(d => d.slug === row.slug)
SetupPanel.tsx:819   disciplineRowTouchesPrice → find(d => d.slug === row.slug)
SetupPanel.tsx:995   api.updateDiscipline(slug, row.slug, …)
```

All three are correct today only because the slug field is disabled on saved rows. Once D1
makes it editable, changing `LS` to `LS-A` makes the lookup at `:774` return `undefined`,
`disciplineRowDirty` return `false`, and the change vanish from the pending count without
ever being saved — a silent data loss, not an error. And `:995` would PATCH a path segment
that does not exist yet.

The row therefore carries `originalSlug` (set from the server value, unchanged by editing)
alongside the editable `slug`. Lookups and the PATCH path use `originalSlug`; the body
carries the new `slug`. `rowId` is already stable across a save (`:1029`) and stays the
React key.

### D8 — A generated name marks a team discipline; duplicates warn but do not block

`taxonomy_name(weapon, gender, material)` does not know the kind, so individual and team
longsword both generate "Longsword". `discipline-identity` says the name carries the whole
distinction wherever a fencer chooses an entry, so this is a live contradiction the moment
a tournament runs both — which is the configuration the previous change existed to enable.
The generated name gains a kind marker.

Duplicate names remain possible and legitimate — two tiers may reasonably start from the
same generated name before the organizer differentiates them. So the dialog warns and lets
the organizer proceed. The check covers drafted rows as well as saved ones; comparing only
against saved disciplines would let someone add two identical names in one sitting and hear
nothing.

## Risks / Trade-offs

- **Derivation logic now exists on both sides and can drift** → the frontend port is
  ten lines with a fixed, closed input space; backend tests pin the generator and frontend
  tests pin the port against the same table of cases stated in the spec scenarios.

- **An organizer edits identity, then a fencer registers before the tab is saved** → the
  flush PATCHes and the server refuses with `discipline_slug_frozen`. The existing
  non-atomic save already handles exactly this: the row is marked with the reason and stays
  pending. No new machinery, but the message must read as "someone registered while you
  were editing", not as a generic failure.

- **Withholding the edit control on a frozen row explains nothing** → chosen deliberately
  over a read-only dialog. The organizer sees a control on some rows and not others with no
  stated reason. Cheapest mitigation if it bites: the row's help hint states the rule.

- **Two forward-only generators mean a tournament can hold both conventions** → a
  long-running tournament may end up with `LS-2` and `Team-LS` side by side. Correct but
  untidy. D6 makes it repairable by hand while unreferenced, which is the most that can be
  offered without rewriting stored identifiers.

## Migration Plan

No schema change and no data migration. `identity_frozen` is derived at serialization time,
`generate_slug` changes affect only disciplines created afterwards, and no stored slug is
rewritten.

Deployment is ordinary: backend first (the added field is additive and the old console
ignores it), then frontend. Rollback is the reverse; a discipline created or edited under
the new console is indistinguishable from any other once stored.

## Open Questions

- **D4's case handling.** Specified case-preserving. Flipping to case-folding changes the
  normalizer and the slug values in `discipline-identity`'s generation scenarios, and
  should be settled before the specs are treated as fixed.

- **Whether the dialog's closed choices are radios or selects.** Radios show all options
  without a click and suit two- and three-way closed sets, which is what kind, material,
  and gender are; `design-system` frames selects but says nothing about radios, so
  introducing them may need a token-level answer first. Selects are the safe default and
  match what the row uses today.
