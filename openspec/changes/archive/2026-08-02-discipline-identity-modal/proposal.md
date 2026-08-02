## Why

A discipline row in Setup carries six identity controls — weapon, gender, material, name,
slug, kind — and every one of them is disabled the moment the row is saved
(`SetupPanel.tsx:1067`). Three of them are stacked vertically inside a single table cell,
so the table's widest column is a permanently greyed form whose only remaining job is to
display four short strings. The row is a form pretending to be a table.

The greying is also wrong. `discipline-identity` says a slug and a classification are
editable while no registration references the discipline, and the backend implements
exactly that (`tournaments.py:587-597`). The console freezes them one step earlier, at
first save, so the case the design explicitly blesses — *"an organizer who adds a second
tier and then wants to rename the first for symmetry is doing something harmless if nobody
has registered"* — is unreachable. Tiers were the point of the previous change, and the
console cannot tidy them up.

## What Changes

**Identity moves out of the row and into a dialog**

- A discipline's identity — kind, material, weapon, gender, name, slug — SHALL be entered
  in a dialog, opened by adding a discipline and reopened to edit one.
- The dialog SHALL default kind to individual, material to steel, and gender to open, so
  the common discipline is two choices (weapon, and nothing else) rather than six.
- The dialog SHALL prefill name and slug from the classification above them as it is
  chosen, and SHALL stop prefilling either one once the organizer has typed into it.
- The dialog SHALL warn when a name is already used by another discipline in the same
  tournament — saved or merely drafted — since the name is the only thing a fencer sees.
  The warning SHALL NOT block confirmation.

**The row becomes a row**

- The row SHALL present name and slug as text, and SHALL carry as editable controls only
  capacity, the unit prices, and its existing optional fields. The discipline table drops
  from eight columns to six.
- Confirming the dialog SHALL change only the local draft, exactly as every other row edit
  does under `setup-navigation`; nothing reaches the server until the tab is saved.

**Identity becomes editable while unreferenced**

- A discipline whose identity is not frozen SHALL offer a control reopening its dialog. A
  discipline whose identity is frozen SHALL offer no such control.
- A discipline SHALL report whether its identity is frozen, so the console can withhold
  the control rather than offer an edit the server will refuse. The report SHALL be
  derived from the same references that govern the freeze — any entry or team, regardless
  of state — and SHALL NOT be inferred from occupied seats, which exclude cancelled
  entries, substitutes, and teams entirely.

**Slug generation learns about kind, and normalizes**

- A generated slug SHALL distinguish a team discipline from its individual counterpart
  (`LS` and `Team-LS`), which today it cannot: `generate_slug` never sees the kind, so the
  headline case of the previous change generates `LS` and `LS-2` and says nothing about
  which is which.
- A slug SHALL be normalized to a form safe in a URL path, a spreadsheet column, and an
  import parse — diacritics folded, runs of other characters collapsed to a single `-`.
  Normalization SHALL apply to an organizer's override as well as to a generated slug, so
  that a custom weapon such as `Tešák` cannot put an unencodable identifier into an export.
- Forward-only. Existing slugs are in stored URLs, exports, and spreadsheet columns and
  SHALL NOT be rewritten; an organizer who wants an existing pair tidied can now do it by
  hand, which is the point of the change above.

**A generated name distinguishes a team discipline**

- The name generated for a team discipline SHALL mark it as one. Today both individual and
  team longsword generate the name "Longsword", so a tournament running both shows fencers
  two identical entries — a direct contradiction of `discipline-identity`'s rule that the
  name carries the whole distinction wherever a fencer chooses an entry.

Nothing here is breaking: the discipline payload gains a field, slug generation changes
only for disciplines created after it, and no stored identifier is rewritten.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `discipline-identity`: slug generation folds in kind and normalizes both generated and
  overridden slugs; a generated name marks a team discipline; the frozen state of an
  identity becomes reportable rather than discoverable only by attempting a refused edit
- `tournament-admin`: the discipline row's identity controls are replaced by a dialog; the
  row presents name and slug as text; identity is reopenable while unreferenced

## Impact

**Backend.** `schemas.py` — `DisciplineOut` gains `identity_frozen`. `tournaments.py` —
`generate_slug` gains a kind parameter, both create and update normalize the slug,
`_discipline_referenced` is evaluated once per tournament rather than once per discipline
so serializing the flag does not cost 2N queries. `taxonomy.py` — a slug normalizer, and a
generated name that accounts for kind.

**Frontend.** A new discipline dialog component. `SetupPanel.tsx` — the discipline table is
rewritten, and three call sites that resolve a row against the server by its *current* slug
must resolve by its original one instead (`:774`, `:819`, `:995`); today the slug cannot
change so the defect is latent, and this change makes it reachable. `api.ts` for the new
field, `i18n/{cs,en}.json` for the dialog.

**Sequencing.** This builds directly on `split-discipline-identity`, now archived; both
deltas here are written against the specs as that change left them. No other active change
touches the discipline table.

**Open decision.** The slug normalizer is specified as case-preserving (`LS` stays `LS`,
`Tešák` becomes `Tesak`, an `LS-A` override is kept as typed). A case-folding normalizer
was also considered and would render every generated slug lowercase — `ls`, `team-ls`,
`plastic-lsw` — which is self-consistent but disagrees with every slug already stored and
with the console column as designed. See design D4.
