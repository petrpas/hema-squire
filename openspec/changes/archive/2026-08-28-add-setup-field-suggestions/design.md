## Context

See proposal.md — Why. What shapes the approach:

- The three values already live on `Tournament`: `location` (`String(300)`),
  `bank_account` (`String(50)`, stored canonicalized as IBAN by
  `schemas.py:471`'s `_normalize_bank_account`), and `organizers` — a JSON list of
  `{"name", "link"}` objects that, per the model comment at `models.py:210`, may
  still hold **bare strings** on a restored-from-old-export deployment. That
  comment names an `organizers_list()` helper that was never written; the real
  normalizer is `schemas.tolerant_organizers()`, until now used only as a
  pydantic before-validator and promoted from private for this change.
- "The organizer's tournaments" already has one definition in the console:
  ownership on `Tournament.owner_id` checked *alongside* the console-team set from
  `_organized_tournament_ids()` (`tournaments.py:267`). Its docstring is explicit
  that ownership is not folded into that set. Any new endpoint must use the same
  pair, or the console will disagree with itself about whose tournaments these are.
- `Tournament` carries `date` but **no** `created_at` (unlike `Fencer`,
  `OrganizerRequest` and most other tables). There is no record of when a value was
  typed — only of when the tournament it belongs to is held.
- Setup sections are self-contained: each owns its state, validates through
  `useFieldValidation`, and registers a `flush` with the save bar via
  `useSectionSaver`. A suggestion affordance must sit *inside* a section's existing
  state, not beside it, or the save bar's dirty count goes wrong.
- The Bureau 1952 prohibitions (CLAUDE.md, design-system spec §8) rule out shadow,
  blur, radius > 2px and entrance animation. `HelpHint` is the existing precedent
  for a small floating panel done within them: static box on `--paper-raised`,
  `1px solid var(--ink)`, 2px radius, no transition.

## Goals / Non-Goals

**Goals:**

- One suggestion mechanism serving all three fields, so a fourth field later is a
  wiring change rather than a new pattern.
- No new persisted state of any kind — no table, no migration, no write path.
- Correctness under the console's existing notion of tournament access, including
  the bare-string legacy shape of `organizers`.

**Non-Goals:**

- Fuzzy or typo-tolerant matching. Plain case-insensitive substring is the whole
  matching story; recalling a value the organizer half-remembers is worth solving,
  guessing at what they meant is not.
- Suggestions across organizers, or any global "clubs that exist in Squire" index.
  That is a directory feature with its own privacy question, not this.
- Reconciling divergent past values. This change makes consistency *easy*; it never
  rewrites a tournament to achieve it.
- Extending the affordance to the fencer-facing `Fencer.club` field. That field has
  the HR fighters index behind it and belongs to a different problem.

## Decisions

### D1: Derive on demand; store nothing

Suggestions are computed per request from the current values on the caller's
tournaments. The alternative — a `field_value_history` table written on every save —
buys only one thing: values the organizer typed and later deleted. It costs a table,
a migration, a write on every Setup save, and a staleness problem with no good
answer (when does a wrong IBAN typed once stop being offered forever?). Under D1 the
answer is free: correct the source tournament and the suggestion corrects itself,
which the spec pins as a scenario. Derivation also works retroactively, so the
feature is useful on the day it ships rather than after a season of accumulation.

The cost is a query per Setup load. It is bounded by one organizer's tournament
count — tens, not thousands — and is a plain indexed read.

### D2: One endpoint for all three fields, fetched once per Setup load

`GET /tournaments/suggestions` (no slug in the path — these belong to the account,
not to the tournament being edited) returns all three lists in one payload:

```
{ "locations": [...], "bank_accounts": [...], "organizers": [{"name","link"}, ...] }
```

Alternatives: a per-field endpoint with a `?field=` parameter, or a query-as-you-type
endpoint. Both were rejected. The whole payload is bounded at 3 × the cap in D5 —
a few hundred bytes — so fetching it once when Setup mounts is cheaper than three
round trips, and far cheaper than a request per keystroke. It also keeps the
matching client-side (D4), which is where it can be instant.

The endpoint sits in `routers/tournaments.py` beside `/mine`, which already answers
the same "what is mine" question.

### D3: A custom component, not `<datalist>`

Native `<input list>` is the obvious first reach and does not survive contact with
the requirements: its popup cannot be styled at all, so the Bureau 1952 palette and
the no-shadow prohibition are simply unenforceable; and it can only offer a flat
string, which cannot carry the name-and-link pair the spec requires. So a
`SuggestionList` component under `frontend/src/`, rendered beneath the input,
holding: filtered values, an active index for arrow-key navigation, Enter to choose,
Escape to dismiss, blur to close, and the ARIA combobox roles that make it
announceable. Styling follows the `HelpHint` box exactly.

Sections keep ownership of their values. The component receives `value` and calls
`onChoose`; `OrganizersSection`'s `onChoose` sets both `name` and `link` through its
existing `patch(index, …)`, so the pair arrives as one state update and the dirty
flag is set once.

### D4: Match client-side, case-insensitively, on substring

The payload is already in hand (D2), so filtering as the organizer types costs
nothing and has no latency. Case-insensitive substring rather than prefix: an
organizer typing "shbu" should find "Spolek SHBU Praha". Czech diacritics are
compared as typed — no folding — which is a deliberate simplification: an organizer
recalling their own club name types it the way they wrote it.

### D5: Order by tournament date descending, cap at 8

"Most recently used" needs a timestamp that does not exist (see Context), so the
proxy is `Tournament.date` descending — the most recent event carrying the value.
For an organizer's own history this tracks intent well: last year's tournament is
the one whose details are current. The alternative, adding `created_at` to
`Tournament`, is a migration this feature does not otherwise need, and would still
be wrong for a tournament created long before it is held.

Distinct values only, first occurrence in that order winning. Capped at 8 — enough
for any real organizer's history, short enough that the list never scrolls, which is
what the spec's bound requires. For `organizers`, the identity is the
`(name, link)` **pair**, so one club with two links yields two entries per the spec;
`link` is normalized to `null`-vs-empty before comparing so a club never appears
twice for that difference alone.

Reading `organizers` goes through `tolerant_organizers()`, never the raw JSON,
so a legacy bare-string entry yields `{name, link: null}` rather than crashing
the endpoint.

### D6: Scope is ownership ∪ console team, matching the console

The query filters to `Tournament.owner_id == fencer.id OR Tournament.id IN
_organized_tournament_ids(session, fencer)` — the same pair used by `/open`,
`/held` and `/mine`. Cancelled and draft (unpublished) tournaments are **included**:
they are still the organizer's own work, and a draft is exactly where a value the
organizer is about to reuse is likeliest to sit.

### D7: Bank account suggestions are per-account and never widened

An IBAN is the most sensitive of the three. It is offered only to accounts that can
already read it on the tournament detail they have access to, so the endpoint
discloses nothing new — but it makes the scoping rule load-bearing rather than
incidental. The scope filter is therefore in the query itself (never post-filtered
in the response builder), and the endpoint requires an authenticated `FencerDep`
like every other console read. Suggested values are the stored canonical IBANs, so
choosing one round-trips through `_normalize_bank_account` unchanged.

## Risks / Trade-offs

- **A wrong value propagates more easily than before.** An organizer who mistyped
  an IBAN once is now offered the mistake on every later tournament. → The list
  shows values verbatim, never prefills (spec: nothing fills itself in), and
  `bank_account` keeps its full pattern validation on the chosen value. D1 makes
  the fix a single correction on the source tournament rather than a purge.
- **`Tournament.date` is a proxy for recency, not recency.** An organizer editing
  an old tournament today does not float its values to the top. → Accepted; the cap
  of 8 means the intended value is almost always visible regardless of position,
  and the honest alternative is a migration this change does not otherwise need.
- **The organizer pair suggestion can fill a link the organizer did not want.** →
  The pair is offered as a visible pair, and a name used without a link yields
  `link: null` rather than borrowing another entry's, per the spec.
- **A custom combobox is an accessibility surface.** Done badly it is worse than a
  plain input. → It is built on the standard combobox roles with keyboard parity
  required by the spec, and the input remains fully usable if the list never opens
  — the affordance is strictly additive.
- **One more request on Setup mount.** → Bounded, cached for the mount, and a
  failure is non-fatal: if the fetch fails the sections render as plain fields,
  since a missing suggestion list is indistinguishable from having no history.

## Migration Plan

None required. No schema change, no migration, no backfill, no data to move. The
change is additive on both sides: an older frontend against the new backend simply
never calls the endpoint, and the new frontend against a backend without it degrades
to plain fields via the failure path above. Rollback is a revert.
