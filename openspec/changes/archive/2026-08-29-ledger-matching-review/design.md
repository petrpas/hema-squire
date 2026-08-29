## Context

See `proposal.md` — Why. Three facts about the current implementation shape
everything below.

**The verdict is a replay product, not stored state.** `_imported_rows` in
`backend/app/sheet.py` recomputes `match_verdict` on every sheet read from the
parse decision, the cached `hr_match` decision and the rule set. Nothing about
the verdict is persisted. A new tier is therefore a change to a pure function of
data that already exists — no migration, no rerun, no LLM spend.

**The overlay is where the review became impossible.** `sheet.py:232-237` writes
the matched name into `name` (demoting the original to `reg_name`), and writes
`matched_club` and `nationality` over `club` and `nationality` outright. The
registered club and nationality do not survive it. This is why the dialog cannot
show a comparison: one side of it has been destroyed by the time the dialog
opens.

**Match resolutions already exist and already work.** `_apply_match_resolution`
in `backend/app/rules.py` sets `hr_id` and derives `confirmed`/`none_found`;
`rules.py:164-166` already suppresses the redundant verdict line from the audit.
The organizer's decision path is sound. What is missing is a cheap way to travel
it and something worth looking at on the way.

## Goals / Non-Goals

**Goals**

- The claim and the evidence are both on the row, always, for every verdict.
- The green/yellow split is a pure function of the stored decision plus the
  index, reproducible and explainable from what is on screen.
- One action ratifies.
- The idiom is stated in the spec; Matching is its first implementation.

**Non-Goals**

- No shared ledger component, hook, or column-group abstraction. Dedup keeps its
  rail card; Payments is untouched. The second implementation earns the
  abstraction — stating the idiom now costs nothing, building for it does.
- No row filtering or sorting by verdict. The rail count answers "how many are
  left"; navigating to them is a separate question, deliberately deferred.
- No change to how matching is run, batched, cached, or keyed.
- No new LLM output fields. The matcher's prompt and `HRMatchResult` are
  unchanged.

## Decisions

### D1 — The tier is derived in the backend, not reported by the model

`found` when all three hold, `proposed` otherwise:

1. `name_key(registered name) == name_key(matched_name)`, where a name key is
   the folded words of a name sorted — so *Jan Novák* and *Novák Jan* agree
2. the registered nationality does not contradict the profile's, both sides
   having first been resolved to an ISO 3166 country
3. the name key is unambiguous in the index — exactly one fighter answers to it

Club is deliberately absent. Club spellings vary too freely ("SHŠ Krkavci" /
"Krkavci" / "Krkavci Praha"); requiring agreement would leave almost everything
yellow and the tier would carry no information.

Nationality is present, but only after both sides are resolved to a country.
Registrations write ISO codes and the index writes English names, and the two
vocabularies never compare equal as strings — "DE" is not a prefix of "Germany".
Measured over the na-duel-2026 roster, comparing the spellings put 17 of 53 rows
in the yellow tier and 14 of those 17 had byte-identical names, demoted purely
by "PL" against "Poland". Resolving first leaves 1. `pycountry` supplies ISO
3166 alpha-2; three names the index spells the common way ("Russia", "Turkey",
"Palestine") are carried as an explicit alias list rather than reached for by
fuzzy search, since a wrongly resolved country quietly demotes a good match.

An unresolvable spelling is treated as no contradiction rather than as one. The
opposite would demote a row for a reason invisible on it — the organizer sees
two nationalities that look alike and a yellow badge explained by neither —
which is exactly what the ledger idiom forbids.

*Alternative considered: drop nationality from the tier, as club was dropped.*
Rejected: with the vocabularies bridged the condition costs nothing and still
catches a genuine mismatch, whereas dropping it would leave the tier resting on
the name alone.

*Alternative considered: ask the model for a confidence score.* Rejected. LLM
self-confidence is poorly calibrated and non-reproducible — the same fencer
tiers differently between runs, and neither tier can be explained to the
organizer. It also fails the spec's rule that a drawn distinction be visible in
the claim and evidence registers. Deriving it costs one prompt-free function and
re-tiers every decision already stored.

*Consequence:* condition 3 needs a name-key lookup over `HRIndex`.
`candidate_profiles` already folds and searches; this is a narrower query
(equality on the key, count of hits) on the same index. The index must be keyed
the same way the comparison is made, or the veto leaks: two fighters indexed as
*Jan Novák* and *Novák Jan* are one ambiguity, not two unambiguous names. Where the index
is unavailable at replay time, the tier degrades to `proposed` — the safe
direction: it asks for a look that may not be needed, rather than skipping one
that is.

### D2 — Ambiguity vetoes `found`, however exact the match

Two fighters named Jan Novák exist. An exact match to one of them is a coin flip
wearing a green badge, and green means nobody will look. This is the single
failure mode where the change could ship a wrong HR id into an export unseen, so
it is a hard veto rather than a heuristic.

### D3 — The overlay is removed; promotion moves to the resolution

`_imported_rows` stops writing `name`, `club` and `nationality` from the match
payload. Those fields stay the parse's. The match payload's values are carried
alongside as evidence fields on the row — `hr_name`, `hr_nationality`,
`hr_club`, beside the existing `hr_id`.

Canonical promotion moves into `_apply_match_resolution`: on a resolution
binding an `hr_id`, the row's `name` becomes the profile's canonical name and
the original is preserved in `reg_name`. This is a behaviour change the
`hr-integration` delta states, and it is what makes the promotion visible — it
becomes an audited consequence of a decision rather than an invisible side
effect of an LLM run.

*Consequence:* `reg_name` stops being written by the matcher. Rows that had it
set only because a proposal displaced their name will show it empty until a
verdict is reached, which is correct — nothing was displaced.

*Alternative considered: keep the overlay and add `reg_club` / `reg_nationality`
to preserve the originals.* Rejected: it doubles the claim register to work
around a write that should not happen, and leaves promotion firing on proposals.
Removing the overlay is strictly less machinery.

### D4 — Evidence for `confirmed` and native rows

The evidence register must not be empty for rows that never went through a
proposal — a fencer-supplied `hr_id`, an in-app registration, a manually entered
row with an id. Their HR columns are filled from the fighters index by id at
replay time. Where the id is absent from the index, the columns read as absent;
the row is still confirmed, on the strength of the id itself.

### D3a — A resolution leaves one line in the log

`_apply_match_resolution` mutates four things beside the id: the verdict, the
evidence register, the promoted name, and the `reg_name` that promotion
displaces. Only one of them is reported.

The rule already in `net_changes` — a resolution's verdict is suppressed while
the id it resolved also stands, "as two entries they say the same thing twice" —
generalizes to all of them. A confirmation that promoted a name was reading as
three lines (verdict, `reg_name`, `name`) for one click. The consequences are
now applied without appending to the audit, exactly as the evidence register
already was, leaving the id where it moved and the verdict where it did not.

Nothing is lost. Undo still works, since the surviving entry carries the rule
id. The promotion is visible on the row, and `reg_name` keeps the registered
spelling retrievable per `hr-integration`.

### D4a — The evidence register states a country as a two-letter code

The register sits beside a claim written in two-letter ISO codes, so it speaks
the same vocabulary — alpha-2, the form a registration is written in, not the
alpha-3 of sport convention. `evidence_fields` resolves the profile's nationality through the
same `country_code` the tier uses, falling back to the source's own words where
no country resolves. Both places that turn a profile into evidence — the sheet's
base projection and the enrichment stored on a match resolution — go through
that one function, so a row cannot disagree with itself.

A resolution's stored payload is resolved **again on replay** rather than
trusted as recorded. A rule written before the register spoke in codes still
carries the index's English spelling, and one row reading "France" beside
another reading "FRA" is a difference the organizer would have to explain to
themselves. Normalizing on read costs one lookup and removes the whole class of
drift, without rewriting a single stored rule.

### D5 — The verdict cell ratifies; search moves behind its own affordance

The badge is already a button (`badge-button`, `Console.tsx:459`) that opens the
dialog. It becomes: click ratifies where there is something to ratify
(`proposed`, `found`), and a separate small control on the cell opens the search.
Where there is nothing to ratify (`unknown`, `none_found`) the badge opens the
search directly, as today.

Mis-click safety comes from the rule model, not from a confirmation step: every
resolution is a rule, `undoEdit` deletes rules, and the log shows what happened.
A modal guarding a one-click undoable action would cost more than the mistake.

### D6 — `hr_id` typed in the table routes to `match_resolution`

`saveEdit` (`Console.tsx:290`) sends `field_edit` for every editable column. For
`hr_id` it sends `match_resolution` instead, which is the same payload shape
(`{field, value}`) and picks up the verdict derivation and canonical promotion
for free. Clearing the cell resolves to `none_found`, consistent with the
dialog's "Profil neexistuje".

`EDITABLE_COLUMNS` keeps `hr_id`; only the rule kind changes. The remaining HR
columns are evidence and are not editable.

### D7 — Column budget

Matching goes to ten columns: index, name, nationality, club, HRID, HR_Name,
HR_Nat, HR_Club, verdict, actions. The table wrapper already scrolls
horizontally (`index.css:439`), so this fits without new layout machinery. The
HR columns are phase-owned (`col-phase`) and appear on Matching only; other
phases are unaffected.

## Risks / Trade-offs

**Green rows export HR ids no human ever read** → Accepted, and it is the point.
It holds only because of D1 and D2: an unambiguous exact-name hit with no
contradicting nationality is a lookup the LLM merely performed, not a judgment
it made. If the tier ever becomes model-reported, this risk becomes real and the
decision must be revisited.

**Name-key equality is stricter than a human's idea of "the same name"** → Word
order is handled; a differing word count is not. *Jan Petr Novák* against *Jan
Novák* demotes to yellow, as does a hyphenation the two spell differently. Extra
given names are vanishingly rare in Central European registration, so this is
accepted rather than solved: the cost is a look that was not needed, and a
subset test would trade that for greens that are genuinely two people. Loosening
it further is a later, evidence-driven change.

**Removing the overlay changes what other phases display** → Rows with an
unratified proposal will show the registered name on Fencers, Dedup, Payments
and Export rather than the HR spelling. This is the intended correction, but it
is visible outside Matching and worth stating: until someone decides, the
tournament shows what the fencer wrote.

**Existing tournaments re-tier on first read** → A console mid-review will find
rows that were yellow now green. Since no verdict is destroyed — `confirmed` and
`none_found` are rules and outrank any derivation — the change can only reduce
outstanding work, never silently undo a decision.

## Migration Plan

None required. Verdicts and evidence fields are replay products; no stored shape
changes, no data is rewritten, no backfill runs. Deploying the code re-tiers
every tournament on its next sheet read. Rolling back returns every row to the
old two-tier display with every organizer resolution intact, since resolutions
are rules and were never touched.


## Open Questions

None. The one that stood — whether the two-letter code should come from HEMA
Ratings rather than from ISO — was settled against the live page; the finding is
recorded in D4b.

### D4b — The code is derived, not harvested, though the source carries one

The fighters page does publish a two-letter code per fighter, in the flag
element's class:

```html
<td data-search="United States"><i class="flag-icon flag-icon-us" title="United States"></i></td>
```

Harvesting it was rejected on the evidence of the page itself, over all 20,377
fighters:

| | |
|---|---|
| carry a flag code | 20,314 |
| carry a `data-search` country name | 20,377 |
| both present and agreeing with the derived code | 19,217 |
| both present and disagreeing | 1,097 |
| resolvable from the flag but not from the name | 0 |

Every disagreement is the same one: the index spells the United Kingdom `UK`,
which is not an ISO 3166 code — ISO has `GB`. Taking the flag code verbatim
would put a non-ISO value in the register for 1,097 fighters and make it
disagree with a registration written `GB`, reintroducing exactly the false
mismatch the country resolution exists to remove.

The flag code also buys no coverage. The 63 fighters carrying no flag are the 63
whose `data-search` is `&nbsp;` — they have no nationality at all, so there is
nothing either source could supply. Harvesting would cost a parser change, a
column, and a full index refresh to gain nothing and lose ISO conformance.

What the finding did earn is an alias: `UK` now resolves to `GB`, along with
`Great Britain` and the four home nations, since those are what a fencer writes
and what the index's own flag code says.
