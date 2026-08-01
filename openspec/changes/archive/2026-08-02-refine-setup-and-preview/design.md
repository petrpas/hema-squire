## Context

The tabbed Setup phase (`split-setup-into-tabs`) and its preview pane are in place and
synced into `openspec/specs/setup-navigation` and `openspec/specs/setup-preview`. This
change is the polish pass that follows first real use. Every item is confined to the
frontend: `TournamentPicker.tsx`, `SetupPanel.tsx`, `SetupPreview.tsx`,
`TournamentFace.tsx`, `index.css`, and the two locale files. No backend endpoint,
schema, or migration changes.

Three of the items are removals of things that exist and work (the VS-series editor,
the communication-language field, two registration-form fields). The relevant question
for each is how far the removal reaches: the position taken throughout is that the
**stored data and the API stay exactly as they are**, and only what the UI offers
narrows. That keeps the table-import path, the email paths, and every historical
registration reproducible.

One item — content bleeding above the checklist — is a defect that has already been
patched once (`index.css` carries a comment explaining a negative-margin trick meant to
fix it) and is still reported. It gets a structural fix rather than another patch.

## Goals / Non-Goals

**Goals:**

- Fix the six Setup-side and four preview-side defects listed in
  `openspec/enhancements.md`, exactly as scoped by the delta specs.
- Make the settings pane's header structurally un-overlappable rather than patched.
- Keep every removal UI-only: no column dropped, no endpoint narrowed, no data lost.

**Non-Goals:**

- The defects in `openspec/small-layout-tweeks.md` (saves not taking effect, comma
  entry in choices, the `+` button's behavior, exchange-rate corruption). Those are
  behavior bugs on the tab-save path, not layout, and belong to their own change.
- Turning the removed non-billable fields into organizer-configurable questions. The
  owner considered and declined this for now; it would be a new capability.
- Any change to how prices are computed, stored, or displayed as amounts — only the
  column *labels* change.

## Decisions

### D1 — Slug year detection: a four-digit token, not a substring

`deriveSlug` appends the event year unconditionally. The fix tests the *slugified* name
for a year token before appending.

Testing the slug rather than the raw name means diacritics and punctuation are already
normalized, so the token boundaries are the slug's own hyphens. The test is
`/(^|-)(19|20)\d{2}(-|$)/` on the slugified base: a four-digit group in 1900–2099
standing as its own hyphen-delimited token.

Rejected: testing for any four consecutive digits anywhere. That would match a slug like
`turnaj-1000-mecu` and silently drop the year, and it would match the middle of a longer
number. Rejected also: testing the raw display name — `Turnaj 2027!` and
`Turnaj (2027)` would need their own handling, which slugifying already does.

Out-of-range four-digit numbers (`turnaj-3000-uderu`) fall through and get the year
appended, which is the safe direction: an extra year is odd but correct, a missing one
can collide across editions.

### D2 — Settings pane becomes header / scrolling body / footer

Today `.setup-panel` is one scroll container holding a `position: sticky` header, the
tab panels, and the save bar. Two independent sticky layers live in that one
scrollport — the pane header (`z-index: 2`) and the discipline/extra table's
`thead th` (`z-index: 1`) — and the header additionally uses negative margins to reach
the scrollport's padding edge. That arrangement is what has been leaking, and a third
adjustment to it would be a third guess.

Instead the pane is restructured so nothing needs to be sticky at the pane level:

```
.setup-panel            column flex, overflow hidden      ← no longer scrolls
  .setup-panel-header   flex: none, opaque                ← checklist + tab bar
  .setup-panel-body     flex: 1, overflow-y: auto         ← the tab panels + save bar
```

The header is then simply not in the scrolling box, so no scroll position can put
content above or behind it, and no `z-index`, `background` or negative margin is load-
bearing. The table's sticky `thead` keeps working and now sticks to the top of the
body, which is where it belongs.

The save bar stays inside the body, in flow at the bottom of the tab panel, exactly as
now — moving it into a pinned footer would change behavior this change has no mandate
for.

At ≤1300px the pane already stops scrolling on its own (`.setup-split` becomes the
scroller and `.setup-panel` gets `overflow-y: visible`). The body must follow the same
rule: at that width `.setup-panel` and `.setup-panel-body` both go to visible overflow
and the header scrolls away with the rest, which is correct for a stacked layout.

### D3 — VS series: read-only in the UI, unchanged in the API

`VsSeriesSection` loses its input, its saver registration, and its two error strings
(`vs_series_taken`, `vs_series_frozen`), keeping only the statement of the series and
the prefix line. `detail.vs_series_editable` stops being read by the client.

The `PATCH` handler keeps accepting `vs_series` with its collision and frozen guards,
and `vs_series_editable` stays on `TournamentOut`. Removing them would be a breaking
API change bought for nothing: the field is already assigned correctly on creation and
reassigned on a date change before the first registration, so no organizer action is
needed, and leaving the guards in place means a future admin path (or an import) still
cannot corrupt a prefix.

Consequence recorded in the spec: the collision and frozen-series rejections stop being
reachable from the console. Their backend tests stay; their frontend error strings go.

### D4 — Communication language leaves the form, stays on the model

`language` is dropped from `IDENTITY_FIELDS`. `Tournament.language` and its validator
stay; `emails.py` and `dedup.py` read it on eleven paths. Creation continues to default
it to `cs`.

This does mean a tournament that should communicate in English has no in-app way to say
so. That is a real gap, and it is the owner's call to accept it now — the field was
being set wrongly more often than rightly, and the launch language is Czech. When
English tournaments arrive, the right answer is a choice at creation time in the "new
tournament" dialog, not a field buried in Setup; that is a separate change.

### D5 — Field order and the two non-field controls

`IDENTITY_FIELDS` is a flat list rendered in order, but logo and qualification are not
entries in it — they are separate blocks rendered after the loop. The requested order
interleaves them (…date, location, **description**, **qualification**, registration
opens…, with **logo** third).

Rather than teaching the loop about two special blocks, the section is rendered as an
explicit sequence: the loop is split at the insertion points and the two blocks are
placed between the resulting runs. Concretely, three field runs —
`[display_name, subtitle]`, `[date, location, description]`,
`[registration_opens, registration_closes, registration_instructions]` — with the logo
block after the first and the qualification block after the second.

This keeps `IDENTITY_FIELDS` as the single source of what gets patched (the save path
still iterates the whole list) while letting the render order be stated literally. The
alternative — adding `{ kind: "logo" }` sentinels to the array — would put render
concerns into the patch descriptor and make the saver filter them out again.

### D6 — "unit price" everywhere, via the locale files

The disciplines table heads its columns `setup.disciplines.fee` / `.feeEur`, the extras
table `setup.extras.price` / `.priceEur`, and the discount rows their own. The change is
to the *values*, not to a shared key: the column headers stay per-table so a table can
still carry a table-specific hint, but every value becomes "unit price ({{currency}})" /
"jednotková cena ({{currency}})".

Keys named `fee`/`price` holding the string "unit price" is mildly untidy. Renaming them
touches three components for no user-visible gain and risks a missed key rendering as a
raw path; the tidier naming can ride along with any later edit to those sections.

### D7 — Detail line loses its dash; the middle dot keeps its spacing

`.detail-extra::before { content: "\2013\00a0" }` is deleted. The subordinate line is
already marked by `font-size: 12px` and `--ink-faded`, which is enough — the dash was
doing the same job twice and colliding visually with the `DOT` separator inside the
line. The `DOT` constant (`"  ·  "`) and its spacing are unchanged.

### D8 — Registration form spacing and total alignment

Three CSS-only adjustments in `TournamentFace.tsx`'s form:

- `.registration-instructions` gets top margin larger than the inter-section gap.
- `.form-total` gets the same, plus `text-align: right` and the same right padding as
  the checklist's price column, so the amount lands over that column rather than at the
  viewport edge. The label and amount stay in one `<p>`; splitting them into a two-cell
  row would need the checklist's grid, which the total is deliberately outside of.
- The `form.sections.other` heading and its block shrink to the note alone.

Because the checklist is not a table, "aligned to the price column" is achieved by
matching the row's trailing padding, not by sharing a grid track. If the price column's
padding ever changes, the total must change with it — the two values are declared
adjacently in `index.css` with a comment saying so.

### D9 — Removing the two form fields without touching the payload contract

`aftersparring` and `accommodation` state, their controls, and their locale keys are
deleted from `RegistrationForm`. The submit payload keeps both keys, sent as `false` and
`null` — the schema requires them and the amend path compares against them, so sending
them explicitly is cheaper and clearer than making them optional on the server.

`notes` stays, and its English label moves from "Remarks" to "Note"; the Czech moves
from "Poznámky" to "Poznámka" to match the singular. The key `form.remarks` is kept, for
the same reason as D6.

Note that `fencer-home`'s information screen still lists after-sparrings and
accommodation *as organizer-defined actions* — those are extra items in the
`other_action` category and are unrelated to the two fixed fields being removed. Nothing
about that section changes.

### D10 — Preview tab bar

`.stage-control` is a flex row that stretches because `.setup-preview` is a column flex
container with default `align-items: stretch`. The settings tab bar already solves this
with `.setup-tabs { align-self: flex-start }`. The preview bar gets the same treatment
through a `.preview-tabs` class rather than by changing `.stage-control` itself, which
is also used in the console's phase stepper where full width may be wanted.

## Risks / Trade-offs

- **The pane restructure changes the scroll container, and the ≤1300px stacked layout
  depends on the old one.** → The stacked breakpoint is exercised explicitly in the task
  list, at both widths, on a long tab.
- **The header no longer scrolls away, costing vertical space on short viewports.** →
  It costs the same as the sticky header did, since that never scrolled away either. No
  regression, but on a short window the checklist plus tab bar is a real fraction of the
  pane; if it bites, the checklist can collapse to a single line when complete, which is
  a later change.
- **Read-only VS series leaves no recovery path if a series is ever wrong.** → It cannot
  become wrong through any current path: it is assigned as the lowest free value and
  reassigned on a pre-registration date change. The API guard stays for anything that
  reaches it another way.
- **No way to set a tournament's communication language.** → Accepted by the owner; see
  D4. Czech is the launch language and the default.
- **Fencers lose the ability to declare after-sparring interest and accommodation
  needs.** → The note field remains and is the channel the owner considers important.
  Organizers who want these back can define them as `other_action` extra items, which
  is what that category is for.
- **Total alignment is maintained by two values that must agree.** → Declared adjacently
  with a comment; verified visually against a form with a long price.

## Migration Plan

None. Frontend-only, no stored state changes shape, no endpoint changes contract. A
tournament created before this change behaves identically after it, except that its
communication language and VS series are no longer offered for editing.

## Open Questions

None. The two decisions that were open — where the description sits in the new field
order, and how far the registration form's "other" block is cut — were settled by the
owner on 2026-08-01: description after location, and the note kept (relabelled) while
after-sparring and accommodation go.
