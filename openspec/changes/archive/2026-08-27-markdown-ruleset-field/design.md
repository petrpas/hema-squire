## Context

See `proposal.md` — Why. What the change lands on:

- A discipline carries `ruleset_name` (`String(100)`, `SingleLineStr`) and
  `ruleset_url` (`String(500)`, `HttpUrlStr`). `TournamentFace.tsx` renders them
  as one anchor: `<a href={ruleset_url}>Pravidla: {ruleset_name}</a>` when the URL
  is set, and the same label as plain text when it is not. The pair sits on the
  discipline's subordinate `detail-extra` line, joined by `DotJoined` with
  `schedule_when` and `schedule_where`. That line is not inside a link.
- Setup renders the two as two `param-field` inputs in the expanded discipline
  row, each with its own `HelpHint`; `ruleset_url` is the only place
  `DisciplinesSection` calls `checkUrl`.
- The inline markdown machinery from `markdown-link-in-place` is already in
  place and needs no change: `renderInline(src, { links })`, `InlineProse`,
  `.prose-inline`, and the shared `.markdown-hint` line under a field.
- `ruleset_url` is currently the illustrating URL field in two backend tests —
  `test_error_envelope` (a `javascript:` value must be refused) and
  `test_bounded_field_migration_safety` (an over-long stored value must block the
  next save). Both prove properties of URL-typed and bounded fields in general,
  not of the ruleset.

## Goals / Non-Goals

**Goals:**

- One field where there were two, with no capability lost: an organizer can still
  name a ruleset, still link it, and can now link several.
- No new rendering code — the ruleset reaches the screen through the same
  `InlineProse` the location uses.
- Nothing an organizer already typed is thrown away by the migration.

**Non-Goals:**

- Making the discipline's `when`/`where` or any further field markdown.
- Any change to `renderInline`, `InlineProse`, or the inline CSS.
- Structured multi-language rules — a language column, a per-language URL table,
  or anything that models "language" as data. The organizer writes the languages
  as text; the system does not know what a language is.

## Decisions

**D1 — The column is renamed `ruleset`, not left as `ruleset_name`.** Once the
field holds `[Barbasetti Right of Way](…) (CZ) · [EN](…)`, "name" is a lie about
its content, and the rename costs nothing that the migration is not already
paying: the same revision touches the table anyway, and the app is pre-launch.
The alternative — keeping `ruleset_name` and just dropping `ruleset_url` — leaves
every later reader wondering where the name ends and the link begins.

**D2 — One Alembic revision doing fold, rename, drop, in that order.**
`UPDATE disciplines SET ruleset_name = '[' || ruleset_name || '](' || ruleset_url
|| ')' WHERE ruleset_url IS NOT NULL AND ruleset_name IS NOT NULL`, then a row
with a URL but no name becomes the bare URL as its own label, then rename
`ruleset_name` → `ruleset`, then drop `ruleset_url`. Doing the fold before the
drop is what makes the change non-lossy; doing it in SQL rather than in Python
keeps it inside the one transaction. Downgrade splits a value of the exact
`[label](url)` shape back into the two columns and otherwise leaves it in the
name — a downgrade is best-effort by nature, and the pre-launch database has
nothing at stake.

**D3 — The bound rises from 100 to 500, and the type becomes `SingleLineStr`.**
The field now has to hold what the URL column used to hold plus its labels; 500
is what `ruleset_url` was already allowed and leaves room for two labelled links.
`HttpUrlStr` disappears from `DisciplineIn` — the value is no longer a URL and
must not be parsed as one, or `[EN](…)` would be rejected outright.

**D4 — Save-time URL validation is not replaced by a markdown-aware check.** The
sanitizer already refuses every scheme outside `https?:`, `mailto:` and `#` at
render time, and `organizer-prose` makes that guarantee independent of anything
done at save. Adding a second, parser-based check over the markdown source would
duplicate a guarantee, and would have to re-implement link tokenization to do it.
The delta on `field-validation` says this explicitly, so the requirement's "not
filtered at render time" is not read as covering prose.

**D5 — The `Pravidla:` label stays outside the rendered field.** Today the label
is inside the anchor; with the field carrying its own links, keeping it inside
would mean either nesting anchors or swallowing the label into one of them. So
`TournamentFace` renders the label as text and the field beside it:
`{t("detail.rulesetLabel")}: <InlineProse source={d.ruleset} />`. The discipline's
subordinate line is not inside a link, so `links` stays at its default — the
card's label-only case does not arise here.

**D6 — One shared hint key, `setup.inlineMarkdownHint`, replaces
`setup.identity.locationHint`.** Two fields now want the same sentence, and a
third will. It is lifted out of `setup.identity` because it no longer belongs to
one section, and reworded per the request to spell the scheme:
`supports markdown: **strong**, *emphasis*, [link](https://...)`. The Setup
ruleset field gets the `.markdown-hint` line beneath it, exactly as the location
field does, alongside the `HelpHint` marker it already carries — the hint marker
says what the field is for, the line beneath says what syntax it accepts.

**D7 — The two backend tests move to another field rather than being deleted.**
`test_error_envelope`'s scheme case moves to `organizer.link`, which is still
`HttpUrlStr`; `test_bounded_field_migration_safety`'s over-long case moves to
`schedule_where`, which is still a bounded `SingleLineStr` on the same discipline
row and so keeps the "whole row is resubmitted" point the test was making. Both
properties still need a guard; only the field illustrating them has gone.

## Risks / Trade-offs

- **An organizer had a name and a link and now sees markdown source in Setup** →
  That is the intended trade for a field they can put two links in, and the
  migration writes the exact syntax the hint describes, so the value they see is
  a working example of what to type.
- **A stored ruleset name containing `[`, `]` or `*` changes meaning** → The fold
  does not escape such characters. Pre-launch there is nothing to escape, and a
  ruleset name containing bracket syntax is not a case worth carrying escaping
  code for.
- **Losing the `javascript:` rejection at save** → Mitigated by D4: the sanitizer
  is the guarantee, it is tested in `markdown.test.ts`, and a delta scenario now
  states the expectation for this field explicitly.
- **The downgrade cannot always undo the upgrade** → Accepted and stated in D2.

## Migration Plan

One Alembic revision, deployed with the frontend that reads `ruleset`. Order
matters only within the revision (fold before drop). Rollback: `alembic
downgrade` restores the two columns on the `[label](url)` shape; anything else
stays in `ruleset_name` as text, which the old frontend renders as an unlinked
label rather than failing.
