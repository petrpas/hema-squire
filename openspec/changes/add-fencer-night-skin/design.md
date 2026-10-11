## Context

The fencer-facing screens and the organizer console share one token file and
one stylesheet, both written for Bureau 1952's light paper. The design source
for this change is `openspec/night-skin-brief.md` §1; owner decisions taken while
proposing it (2026-10-11) override the brief where they differ: the Profile page
and the not-found screen go night too, the skin never follows
`prefers-color-scheme`, organizer names stay on the card as plain text, and the
card carries no Register action.

What the code looks like today:

- `tokens.css` holds every color and font on `:root`; `index.css` reads them.
- `FencerLayout` renders either `Login` (gated Mine, or a sign-in prompt) or
  `FencerShell`, whose root is `<div className="app">`. `ProfilePage` sits under
  `RequireAuth`; `NotFound` is a top-level route.
- `FencerHome.tsx` is 289 lines and contains `CardHeading`, `TournamentCard`,
  the status chips and the tab band. Organizer names are links nested inside the
  card's `<Link>` — invalid markup this change removes.
- Modals are native `<dialog>` elements rendered in place, so they inherit the
  skin from their DOM ancestor. Their `::backdrop` is painted with a literal
  `rgba(43, 42, 38, 0.35)`.
- The SPAYD QR is a PNG produced by the backend (`qr_png_base64`), already dark
  on light; only the frame around it is styled by the page.
- Plex is loaded by one Google Fonts `<link>` in `index.html`.
- `stampRotation` in `PaidStamp.tsx` holds the only string hash in the frontend.
- The list payload's discipline rows carry `entered`, `capacity`,
  `queue_length`; the tournament carries nothing about closing or totals.
  `setup.py` resolves the close as `registration_closes or date`.

## Goals / Non-Goals

**Goals:**
- A night skin that is a second set of token values, never a branch in a
  component.
- The organizer console pixel-identical to today.
- The home page rebuilt as a card grid with meters, status blocks and the
  next-opening strip.
- Every public screen dark, with nothing light showing through: overscroll,
  sign-in, modal backdrop, profile, not-found.

**Non-Goals:**
- Redesigning the detail page, entrants rosters or registration form. They go
  dark through the tokens and keep their ledger geometry.
- A user-facing skin toggle or a `prefers-color-scheme` follow.
- Familiar faces on the card footer (`add-card-familiar-faces`) and the
  organizer-set short code (`add-tournament-short-code`).
- The optional "právě otevřeno" plate row on phones (brief §1.8) — left out
  unless it fits one sitting at the end; it has no requirement in this change.

## Decisions

### D1. A skin is an attribute on a layout root, read only by `tokens.css`

`data-skin="night"` is set on the root element of `FencerShell`, on the wrapper
`FencerLayout` puts around `Login`, and on the roots of `ProfilePage` and
`NotFound`. `tokens.css` has one `[data-skin="night"] { … }` block. Nothing else
mentions the attribute.

*Alternative considered:* setting it on `<html>` from an effect keyed to the
route. Rejected: it introduces a component that knows the skin, flashes day on
first paint until the effect runs, and must be undone on every organizer route.
An attribute on the layout root is correct from the first render.

*Consequence:* `body` keeps day `--paper`. The night root therefore sets
`min-height: 100dvh` and `background: var(--paper)`, and the night block sets
`color-scheme: dark`. Overscroll on iOS can still reveal `body`; the root also
gets `html:has([data-skin="night"]) { background: … }` — a `:has()` selector in
the token file, still a value decision rather than a component branch. Where
`:has()` is unsupported the fallback is the root's own full-height paint.

### D2. New tokens land on `:root` first, with day values equal to today's literals

Every new role token (`--radius-card`, `--radius-pill`, `--radius-plate`,
`--radius-chip`, `--font-display`, `--weight-display`, `--body-size`,
`--hairline-strong`, `--stamp-on-tint`, `--plate`, `--qr-paper`,
`--scrim`) is first added with its day value and wired into the rules that need
it; only then is the night block added. Two commits' worth of steps, so the
"console unchanged" claim can be checked at the boundary: after step one the
whole app must render exactly as before.

`--scrim` day value is `rgba(43, 42, 38, 0.35)` (today's literal); night is
`rgba(10, 9, 8, 0.6)`. `--radius` (2px) is not redefined in night: fields, tags
and table cells keep it.

### D3. Binding text changes before CSS

`CLAUDE.md`'s prohibition list currently forbids both the night radii and
weight 700, and says it takes precedence over everything. It is amended first,
word for word with the `Global prohibitions` delta. (`squire-design-spec.md`,
which the brief also names, was removed in 5d8943b; the `design-system` spec is
the binding text.) An implementing agent reading `CLAUDE.md` mid-task must
not meet a contradiction.

### D4. Contrast, measured

Computed for the night values (WCAG 2.x): `--ink` 15.3 / 14.1 / 12.9 on
paper / raised / shade; `--ink-soft` 9.2 / 8.5 / 7.7; `--ink-faded` 5.75 / 5.31 /
4.84; `--stamp` 5.7 / 5.3 / 4.8; `--stamp-on-tint` on `--stamp-tint` 6.0; the
pastel inks on their tints 7.5–8.7. The brief's warning that `--ink-faded` fails
on `--paper-shade` (4.4:1) does not reproduce: it is 4.84:1, so the card's hover
ground keeps its faded ordinal and footer legible. The token comment records the
measured figures instead.

`--hairline-strong` on `--paper-raised` is 1.8:1. It draws the closed-state ring
and the secondary pill's border; neither is the sole carrier of its meaning (the
status block and the button label are), so it is decoration under WCAG 1.4.11.

### D5. Cover tint and ordinal

`stampRotation`'s hash is lifted into `slugHash(s: string): number` in its own
module; `stampRotation` and the card both call it. The card renders
`data-tint={slugHash(slug) % 3}` and the stylesheet maps `0|1|2` to file-blue,
seal-green, form-yellow. The ordinal is the index in the rendered array, padded
to three digits, reusing the ledger tables' padding helper where one exists.

### D6. Status block replaces `StatusChip`; bond block on Mine/Past

`StatusChip` and `BondBadge` keep their decision logic and change their
markup to the three-line block. The open state needs the closing date, which the
payload gains (D8). A line whose value is absent is not rendered, never rendered
empty.

### D7. `NextOpening` reuses the detail page's clock

The strip picks, from the already-fetched `announced` list, the tournament with
the earliest future `registration_opens_at`, and renders only within 7 days of
it measured on the server-corrected clock. It reuses `useOpeningMoment` /
`openingMoment.ts` unchanged, so skew correction, visibility re-evaluation and
the stop-at-moment rule are shared with the detail. At the moment it calls the
layout's existing list refresh once (the same single refetch the detail does),
after which the tournament has moved to Open and the selector picks the next.

### D8. Three aggregates, one query each for the whole list

`registration_closes_on` reuses the `registration_closes or date` resolution
(exposed from `setup.py` rather than spelled again) and is `None` for
`elsewhere`. `entrant_count` and `club_count` are computed for all tournament
ids of a list response in one grouped query over seated, non-cancelled,
publicly-listed registrations: `COUNT(DISTINCT person)` and
`COUNT(DISTINCT normalized_club)`. Normalization (casefold, strip diacritics,
collapse whitespace) runs in Python over the distinct `(tournament, club)` pairs
rather than in SQL, since SQLite and PostgreSQL disagree on unaccent; the pairs
are few. The same normalizer is what `add-card-familiar-faces` will match clubs
with, so it lives in its own module.

"Seated" and "publicly listed" reuse the predicates the public roster uses, so
the card's count and the roster's count never disagree.

### D9. Card markup

`TournamentCard.tsx` takes the card out of `FencerHome.tsx`, with
`StatusBlock.tsx`, `CapacityMeter.tsx` and `NextOpening.tsx` beside it.
The card remains an `<li>` container with the body as one `<Link>` and Spravovat
as a sibling `<Link>` (existing Decision 6). Organizer names render as text.
The narrow row is the same markup re-laid by a `max-width: 480px` rule in the
card's own CSS section.

### D10a. Deviations found while implementing

- **The strip's figure outside the last day.** `useOpeningMoment` ticks once a
  second only inside the last day, as the detail does. Rather than a second
  ticking mechanism for days 2–7, the strip states the opening day and hour
  there and counts down only on the last day.
- **The account menu stays `⋯`.** A 40px monogram of the account's name would
  change what the shared `AccountMenu` renders on organizer screens too, and
  only a branch on the skin could avoid that. The trigger rounds through
  `--radius-pill` instead.
- **`--title-size`.** The top bar's title is shared with the console, so its
  night size (`clamp(22px, 2.4vw, 30px)`) is a role token whose day value is
  the old 19px.
- **Active tab count.** `--ink-soft` on the inverted (`--ink`) tab reads at
  about 1.5:1; the count inherits the tab's own ink instead.
- **`--qr-ink` dropped.** The QR is an opaque PNG from the backend carrying its
  own dark-on-light modules and quiet zone; only its surrounding ground is a
  token.
- **Detail titles.** The detail page's two title headings had no font rule;
  they now read the display tokens.
- **Focus rings inset** on the card link and the pill tabs, whose containers
  clip.

### D10. Fonts

Plex Sans Condensed 600 and 700 are appended to the existing Google Fonts URL.
600 is loaded for the narrow row's 20px name if 700 reads too heavy there; if
unused at the end it is dropped from the URL.

## Risks / Trade-offs

- [Every public screen goes dark at once, including ones this change does not
  restyle] → An audit task walks detail, entrants, register, payment slip,
  modals, sign-in, profile and not-found in the night skin before the home
  redesign starts, and fixes any rule that reads a literal instead of a token.
- [An `index.css` rule hardcodes a day color as `rgba()`] → The audit greps for
  `rgba(` and named colors as well as hex; each is moved to a token.
- [Organizer console drifts] → D2's two-step order plus a before/after
  screenshot of a console phase at the step boundary.
- [The `:has()` overscroll rule is unsupported somewhere] → The night root's own
  full-height paint covers everything except rubber-band overscroll.
- [Club counts read differently from what a fencer would call one club]
  → Normalization is deliberately loose but not fuzzy; a typo is a second club.
  Recorded as a known limitation.

## Migration Plan

Frontend and an additive API change; no data migration. The new payload fields
are additive, so the deployed frontend and backend may roll out in either
order. Rollback is a revert.

## Open Questions

None blocking. The "právě otevřeno" row (brief §1.8) is deferred unless cheap.
