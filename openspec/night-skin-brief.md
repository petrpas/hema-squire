# Brief: Night skin for the fencer-facing surface

Input for OpenSpec. Write the proposals, design docs and spec deltas from this
brief first, then implement. Three changes, in this order:

1. `add-fencer-night-skin`: tokens, spec amendments, home page redesign
2. `add-card-familiar-faces`: signed-in only, backend + card footer
3. `add-tournament-short-code` (optional): organizer-set monogram

The mockup lives on a design canvas the agent cannot open. Every value it needs
is in this file. Where this brief and the mockup disagree, this brief wins.

---

## 0. Intent

The organizer side stays Bureau 1952 as it is: light paper, ledger tables,
restraint. The public side (tournament list, detail, entrants, results) gets a
dark skin aimed at a younger audience, with cards instead of rows, bolder
display type and visible fill state.

**The rule that keeps the two from falling apart:** a skin is a second set of
*values* for the same *roles*. Components read `var(--paper)`, `var(--ink)`,
`var(--stamp)`, … exactly as today. The night skin redefines those properties
under `[data-skin="night"]`. No component branches on the skin in TS, and
nothing reads a night-only hex.

What both skins share, and must keep sharing:
- the Plex family; `--font-data` with tabular numerals for every figure
- one saturated color (`--stamp`), lifted for dark
- the Paid stamp with deterministic rotation
- zero-padded ordinals (`001`)
- no gradients, shadows, blur, glow or emoji
- text is the paper color, inverted: night `--ink` equals day `--paper`'s family

What the night skin changes: luminance, card/pill geometry, display face and
weight, body size, imagery (logo plate), static capacity meters.

---

## 1. Change `add-fencer-night-skin`

### 1.1 Binding text that must change first

`CLAUDE.md` currently lists prohibitions "binding for all Squire frontend work"
including `border-radius > 2px (no pills, no rounded cards)` and `weight 600+`.
The night skin breaks both on purpose. **Amend `CLAUDE.md` in the same change,
before touching CSS**, otherwise the implementing agent will (rightly) refuse.

Replace the radius and weight bullets with:

```
- `border-radius` > 2px, EXCEPT through the skin geometry tokens
  (`--radius-card`, `--radius-pill`, `--radius-plate`), which are 2px in the
  day skin and larger only under `[data-skin="night"]`
- weight 600+, EXCEPT `--weight-display` on display headings, which is 500 in
  the day skin and 700 only under `[data-skin="night"]`
```

Add one line under the list:

```
Everything else on this list binds both skins. The night skin is defined in
openspec/specs/design-system (Requirement: Skins) and nowhere else.
```

Also add a "Skins" section to `openspec/squire-design-spec.md` summarising 0.
above. The wink budget rule requires the spec file to change before any new
personality touch; the night skin adds no new winks (see 1.9).

### 1.2 Spec deltas — `design-system`

**ADDED Requirement: Skins**

> The system SHALL have two skins, day and night, that differ only in the
> values of the custom properties in `tokens.css`. The night skin SHALL be
> defined as one block under `[data-skin="night"]` in `tokens.css`. No
> component SHALL read the active skin, and no component SHALL carry a
> skin-specific value.
>
> The night skin SHALL apply to every screen rendered under the fencer layout
> (tournament list, tournament detail and its tabs, and the sign-in screen when
> the fencer layout renders it). Organizer and admin screens SHALL stay day.
> The skin follows the route, not the role: an organizer reading the public
> list sees night.
>
> The night root SHALL declare `color-scheme: dark`, so native controls and
> scrollbars match.

Scenarios to write: a public screen renders with `data-skin="night"` on its
root; an organizer console renders without it; an audit for hex values outside
`tokens.css` still finds none.

**MODIFIED Requirement: Global prohibitions**

Same list, with the radius and weight carve-outs worded as in 1.1. Keep the
"more than one saturated color" rule unchanged: night `--stamp` is the only
saturated color in the night skin.

**ADDED Requirement: A capacity meter is a static figure**

> A discipline's fill MAY be shown as a meter: a 4px track in `--paper-shade`
> with a fill whose width is the measured ratio of entered to capacity. The
> meter SHALL be static. No transition and no animation SHALL be attached to
> it or its fill, and it SHALL carry no motion on load. The figure itself
> SHALL also be stated as text beside the meter (`24/32`), and the meter SHALL
> be `aria-hidden`. A full discipline SHALL fill in `--stamp` and state
> `plno · +N čeká` / `full · +N waiting` instead of the fraction.

This sits next to "A live figure is text, not an animation". It does not relax
the prohibition on animated progress bars.

**MODIFIED Requirement: Typography conventions**

Document titles move from `--font-doc` to a new `--font-display` token. Day
value: `var(--font-doc)`, so the day skin renders identically. Night value:
IBM Plex Sans Condensed. Display weight reads `--weight-display`.

### 1.3 `tokens.css`

Add the new role tokens to `:root` **with day values that change nothing**:

| token | day | night |
|---|---|---|
| `--radius-card` | `2px` | `16px` |
| `--radius-pill` | `2px` | `999px` |
| `--radius-plate` | `2px` | `14px` |
| `--radius-chip` | `2px` | `10px` |
| `--font-display` | `var(--font-doc)` | `"IBM Plex Sans Condensed", var(--font-ui)` |
| `--weight-display` | `500` | `700` |
| `--body-size` | `14px` | `15px` |
| `--hairline-strong` | `var(--ink)` | `#4a453c` |
| `--stamp-on-tint` | `var(--stamp)` | `#f0866f` |
| `--plate` | `var(--paper-raised)` | `#ede7d9` |
| `--qr-paper` | `var(--paper-raised)` | `#ede7d9` |
| `--qr-ink` | `var(--ink)` | `#121110` |

Then the night block:

```css
[data-skin="night"] {
  color-scheme: dark;

  --paper: #121110;
  --paper-raised: #1b1a17;
  --paper-shade: #24221e;

  --ink: #ede7d9;        /* 15.3:1 on --paper */
  --ink-soft: #bdb4a2;   /*  9.2:1 */
  --ink-faded: #968d7d;  /*  ≥4.5:1 on --paper and --paper-raised only */

  --hairline: #2e2b26;
  --rule-strong: var(--ink);

  --stamp: #e8644d;      /* 5.7:1 on --paper; text on a filled stamp is --paper */
  --stamp-hover: #f07a63;
  --stamp-tint: #3a1f1a;

  --seal-green: #1f2a22;  --seal-green-ink: #9cc7a4;
  --file-blue: #1e2730;   --file-blue-ink: #a3b9cc;
  --form-yellow: #2c2618; --form-yellow-ink: #dcc38a;

  --radius-card: 16px;
  --radius-pill: 999px;
  --radius-plate: 14px;
  --radius-chip: 10px;
  --font-display: "IBM Plex Sans Condensed", var(--font-ui);
  --weight-display: 700;
  --body-size: 15px;
  --hairline-strong: #4a453c;
  --stamp-on-tint: #f0866f;
  --plate: #ede7d9;
  --qr-paper: #ede7d9;
  --qr-ink: #121110;
}
```

`--radius` (2px) is deliberately **not** redefined. Form fields, tags and table
cells keep 2px in both skins; only cards, pills and plates round.

`--ink-faded` must not be used on `--paper-shade` in night (4.4:1). Note this
in the token comment.

Load IBM Plex Sans Condensed (600, 700). Find where Plex is loaded today and
add it there; do not introduce a second loading mechanism.

### 1.4 Where the skin is applied

- `FencerShell`: `data-skin="night"` on its root `.app` element.
- `FencerLayout` renders `Login` outside `FencerShell` when gated. Wrap that
  branch in the same attribute.
- `body` background: the shell root must paint `background: var(--paper)` at
  full height so no day paper shows on overscroll.

Open questions to settle in the proposal, not in code: `ProfilePage` (a
fencer's page, but under `RequireAuth`, outside the fencer layout) and
`NotFound`. Default: leave both day until decided.

### 1.5 Audit before restyling

Because the detail page, entrants and registration tabs render inside
`FencerShell`, they **go dark automatically** the moment 1.4 lands. That is
intended, but check:

1. `grep` `index.css` for hardcoded `2px` radii and `font-family: var(--font-doc)`
   in rules used by public screens. Leave them; they still read correctly. Only
   rules this change restyles move to the new tokens.
2. **SPAYD QR.** The payment slip QR must stay dark modules on a light plate in
   both skins; inverted QR codes fail in some banking apps. Make the slip's QR
   background and module color read `--qr-paper` / `--qr-ink`, including the
   quiet zone. If the QR is rendered to canvas/SVG with explicit colors, pass
   the computed token values.
3. Tournament logos: every rendering of `logoUrl()` sits on `--plate`.
4. Pastel tags: verify each `-ink` on its tint is ≥4.5:1 in night (all three
   are, by the table above).
5. The Paid stamp reads `--stamp`; nothing to do.

### 1.6 Home page (`FencerHome`, `FencerShell`)

**Top bar.** Keep the current three-column structure exactly: app name at
left, page title truly centred, visitor at right. Night changes only the type:
title in `--font-display` / `--weight-display`, `clamp(22px, 2.4vw, 30px)`;
app name in `--font-display` 20px. Sign-in is a secondary button with
`--radius-pill` and a `--hairline-strong` border. A signed-in visitor gets the
existing account menu, shown as a 40px round monogram.

**Next-opening strip** (new component `NextOpening`, home only, above the tab
band):
- the announced tournament with the earliest `registration_opens_at` in the
  future
- shown only when that moment is within 7 days; otherwise not rendered (the
  live-figure rule: shown only while worth watching)
- left: small logo or monogram, label `příští otevření registrace`, tournament
  name; right: the countdown in `--font-data` 26px tabular, fixed width, and a
  secondary pill button "Ukázat turnaj" linking to `detail(slug)`
- reuse `useOpeningMoment` / `openingMoment.ts`; obey every clause of "A live
  figure is text": ≤1 update/s, no motion, stops at the moment and is replaced
  by the tournament now being open
- container: `--paper-raised`, 1px `--hairline`, `--radius-card`

**Tab band.** A pill-shaped segmented control: container `--paper-raised`,
1px `--hairline`, `--radius-pill`, 4px padding. Tabs are ≥40px high pills.
Active tab inverts: `background: var(--ink); color: var(--paper)`. Counts in
`--font-data` 12px, `--ink-faded` (active: `--ink-soft`). Same tabs, same
logic, same `useTabBand`.

**Card grid.** `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))`,
gap 20px, inside a `max-width: 1240px` column.

**Card** (`TournamentCard`, split into its own file now; `FencerHome.tsx` is at
289 lines). Still a container with the body as the link and Manage as a
sibling link (design Decision 6 stands).

```
┌──────────────────────────────────┐
│ ┌────────┐               001     │  cover: 150px, cover tint
│ │●regist-│     ┌──────┐          │
│ │ race   │     │ logo │          │  plate 84px, --radius-plate
│ │otevřena│     └──────┘          │
│ │do 28.2.│                       │
│ └────────┘                       │
├──────────────────────────────────┤
│ Pražský dlouhý meč 2027          │  --font-display 26px/1.05
│ Kvalifikace na mistrovství ČR    │  --ink-soft 14px
│ 14.–15. 3. 2027 · Praha          │  --font-data 13px
│                                  │
│ Longsword Open            24/32  │  13px; figure --font-data right
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░               │  meter
│ Longsword Women   plno · +3 čeká │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓               │
│──────────────────────────────────│
│ [faces] 3 z tvého klubu  40 · 12 │  footer
└──────────────────────────────────┘
```

- Card: `--paper-raised`, 1px `--hairline`, `--radius-card`, `overflow:
  hidden`. Hover (behind `@media (hover: hover)`): `border-color:
  var(--hairline-strong)` and `background: var(--paper-shade)`, 120ms, off
  under reduced motion. No transform.
- **Cover tint.** Deterministic from the slug: `hash(slug) % 3` selects
  file-blue, seal-green or form-yellow (background = the pastel token, monogram
  ink = its `-ink` token). Reuse the hash `PaidStamp` already uses for its
  rotation. Render as `data-tint="0|1|2"` and select in CSS, so no color lives
  in TSX. The day skin gets the same tints from the same tokens.
- **Plate.** 84×84, `--radius-plate`, centred in the cover. With a logo:
  `background: var(--plate)`, image `object-fit: contain` with 10px padding.
  Without: the monogram (see 1.7) in `--font-display` 26px on `--paper`, color
  from the tint's `-ink`.
- **Ring.** The plate carries `outline: 2px solid var(--stamp); outline-offset:
  4px` while registration is open, `var(--hairline-strong)` otherwise.
- **Ordinal.** Top-right of the cover, `--font-data` 12px `--ink-faded`: the
  card's position in the current list, zero-padded.
- **Status block.** Top-left of the cover, `max-width: calc(50% - 72px)` so it
  can never reach the plate. A block, not a pill: `--radius-chip`, padding 8px 11px, 12px/1.3,
  three lines:

  | status | colors | line 1 | line 2 | line 3 (`--font-data`) |
  |---|---|---|---|---|
  | `open` | `--stamp-tint` / `--stamp-on-tint`, 7px `--stamp` dot | registrace | otevřena | do {closes} |
  | `opens_on` | `--paper` / `--ink` | registrace | od {date} | v {time}, omitted if none |
  | `elsewhere` | `--paper` / `--ink-soft` | registrace | jinde | — |
  | `closed` | `--paper` / `--ink-faded` | registrace | uzavřena | — |

  `open` needs the closing date, which the list payload does not carry today.
  Add `registration_closes_on: string | null` to `OpenTournament` (server
  computes it the same way the detail does). If null, line 3 is omitted.

  On the Mine and Past tabs, `BondBadge` keeps its logic. Its registration
  state uses the same block. A paid registration additionally shows the
  `PaidStamp` on the cover's bottom-left.

- **Disciplines.** One row per discipline: name left, figure right in
  `--font-data` tabular `--ink-soft`; below it the meter from 1.2. Full: fill
  and figure in `--stamp` (figure in `--stamp-on-tint`). Queue length comes
  from the existing `queue_length`.
- **Footer.** Top hairline, `margin-top: auto` so footers align across a row.
  Right side, always: `{fencers} šermířů · {clubs} klubů` in `--font-data` 12px
  `--ink-faded`. Left side: faces, change 2 only.
  The two counts need `entrant_count` and `club_count` on `OpenTournament`:
  distinct seated fencers across disciplines (a fencer in two disciplines
  counts once) and distinct non-empty normalized clubs among them. Both are
  public aggregates; add them in this change.
- **Manage** link for organizers: unchanged, tertiary, bottom-right.

**Footer of the page:** keep the existing table-footer wink: left summary,
right `hemasquire.eu · rev. N`, `--font-data` 12px.

### 1.7 Monogram

`monogram(displayName: string): string` in its own module with tests:

- split on whitespace and punctuation; drop tokens that are all digits, and
  Czech/English function words (`a, i, v, ve, na, z, ze, do, of, the, and,
  &`)
- take the first letter of the first two remaining tokens, uppercased,
  diacritics kept (`Brněnská šavle` → `BŠ`)
- one token left → its first two letters (`Bohemia` → `BO`)
- nothing left → first two visible characters of the raw name
- never empty, never more than 3 characters

Used only when `has_logo` is false. Change 3 lets an organizer override it.

### 1.8 Narrow screens (≤480px)

- Card turns into a compact row: no cover band; plate 56px at left, then name
  (`--font-display` 20px), date · city, status as a single line of text in
  the status colors (no block), meters unchanged below. Ring stays on the
  plate.
- Tab band spans full width, tabs share it equally.
- Next-opening strip stacks: countdown under the name.
- Optional, behind its own task: a horizontal "právě otevřeno" row of 58px
  ringed plates above the tab band, one per open tournament, each linking to
  its detail. Skip it if it takes more than one sitting.

### 1.9 Wink budget

No new winks. The Paid stamp and the footer revision line are the two that
appear here; at most one per screen still holds (the stamp appears only on
Mine/Past, where the footer line counts as the one wink, so on those tabs drop
the revision line).

### 1.10 i18n

New keys in `cs.json` and `en.json` together (`locale-parity.test.ts`):
status block lines, `home.nextOpening.*`, meter full text with plural forms,
footer counts with plural forms (`šermíř/šermíři/šermířů`, `klub/kluby/klubů`).
No Title Case, no exclamation marks.

### 1.11 Tests

Scope: `frontend` tests for `monogram`, tint determinism (same slug → same
tint across renders), status block per status, meter full state and
`aria-hidden`, `NextOpening` hidden beyond 7 days and replaced at the moment,
footer counts. Backend: `entrant_count`/`club_count` dedupe a fencer in two
disciplines, `registration_closes_on` matches the detail. Update
`publicHome.test.tsx` where it asserts the old chip markup. Do not grow the
suite beyond what these need.

---

## 2. Change `add-card-familiar-faces`

Signed-in visitors only. Anonymous visitors see the counts and nothing else.

**Payload.** `OpenTournament.familiar?: { basis: "club" | "country"; total:
number; people: { initials: string; label: string }[] }`. Absent with no
account behind the request, and absent when the selection is empty, for the
same reason `my_registration_state` is absent.

**Selection**, per tournament, server-side, among seated entrants (not
queued, not cancelled), excluding the caller:

1. **Club.** The caller's club comes from their HR identity (HR sync stores
   club as text). Match entrants whose club equals it after normalization:
   casefold, strip diacritics, collapse whitespace, trim. Clubs are free-text
   `String(200)` columns, so this is the best available identity; note the
   limitation in design.md.
   Order: HR rating in the tournament's weapons (max over its disciplines),
   descending, then name. Take 3. `total` = all matches.
2. **Country**, only if step 1 found nobody: entrants whose nationality equals
   the caller's (`country_code()` from `hr_index`), ordered the same way.
   Take 3. If the caller has no nationality, stop.
3. Nothing found: `familiar` absent.

`initials`: first letter of first name + first letter of surname. `label`:
first name + surname initial (`Kateřina V.`), used as the face's
`aria-label` / `title`. Names are already public on entrant lists; this
exposes nothing new.

Batch the queries for the whole list. No per-card request.

**Card footer, left side.** Up to 3 round 28px faces overlapping by 8px, each
on a tint chosen by its index, 2px `--paper-raised` ring to separate them.
Then the note in 13px `--ink-soft`:
- club: `{total} z tvého klubu` / `{total} from your club`
- country: `nejvýš hodnocení z {country}` / `top-rated from {country}`

**Tests:** club match beats country, caller excluded, queued excluded,
country fallback, no nationality → absent, anonymous → absent, diacritics and
case normalize.

---

## 3. Change `add-tournament-short-code` (optional)

`Tournament.short_code: str | None`, 1–3 characters. One field in tournament
settings, label "Zkratka", help hint: used where the tournament has no logo.
Prefilled in the form with `monogram(display_name)`, stored only if the
organizer changes it. The card uses `short_code ?? monogram(display_name)`.

---

## 4. Acceptance

- Organizer console: pixel-identical to before (new tokens have day values
  equal to the old literals).
- Public pages: dark, no day paper visible anywhere, including overscroll and
  the sign-in screen reached from the list.
- No hex outside `tokens.css`. No component reads the skin.
- QR on the payment slip: dark modules on light, in both skins.
- `prefers-reduced-motion`: card hover transition off; countdown still ticks
  (it is a figure, not motion).
- Keyboard: every card, tab and button shows `--focus`.
- `tsc --noEmit`, Biome, the scoped pytest run, all green.
