## Context

The public entrants roster (`frontend/src/entrants/`, fed by `backend/app/entrants.py`)
states nationality as the string the Export row carries: usually an alpha-2 code, since
registration, substitution and the roster editor normalise through
`hr_index.country_code`, but a row bound to a HEMA Ratings profile, or an imported one,
can carry "CZE" or "Czech Republic", and a spelling nobody can read stands as given.

The design system allows one saturated color and no hex outside `tokens.css`. Flags break
both; the owner approved a carve-out naming this one place (memory: nationality flags
owner decisions, 2026-11-11).

## Goals / Non-Goals

**Goals:**
- A flag in place of the code on every public roster row, named in the page's language.
- The country read once, on the server, with the same function every other table uses.
- Flags served by Squire, loaded only when a roster draws them.

**Non-Goals:**
- Flags anywhere else: console, Export, data export, Typst roster print.
- Subdivision flags (England, Scotland): `country_code` maps them to GB, and the flag
  follows that.
- Changing how nationality is stored or normalised.

## Decisions

**The server sends `country` beside `nationality`.** `EntrantRow` and `TeamMemberRow`
gain `country: str | None = country_code(nationality)`. The client renders a flag when
`country` is set and falls back to `nationality` as text otherwise. Alternative: read
the country in the browser. Rejected: it would duplicate `pycountry` and the alias table
in TypeScript, and the two readings would drift.

**Team row.** It keeps stating the shared value as now: `shared()` over the members'
nationalities. Where they all agree, they agree on the country too, so the flag comes
from the first member's `country`. Members spelling one country two ways ("CZ",
"Czech Republic") still read as different, as they do today; the roster editor
normalises what it writes, so this happens only for legacy or imported data.

**`flag-icons`, its 4×3 SVG files, by URL.** `import.meta.glob` over
`flag-icons/flags/4x3/*.svg` with `?url&no-inline` builds a code→URL map at build time.
Vite emits each SVG as its own hashed asset, and the browser fetches only the flags a
roster draws. `no-inline` matters: without it Vite turns every flag under 4 KB into a
data URI inside the main bundle, and every visitor would download about 200 flags.
The `flag-icons` stylesheet is not imported. Alternatives: emoji (prohibited, and
Windows draws two letters instead of a flag); `country-flag-icons` React components (a
lookup by code pulls every component into the bundle); a CDN (a third party learns who
reads which roster).

**The cell.** `NationalityCell` in `frontend/src/entrants/` renders
`<img src alt={name} title={name} class="entrant-flag">`, where name is
`new Intl.DisplayNames([i18n.language], { type: "region" }).of(country)`, falling back to
the code if the runtime knows none. CSS: height 12px (16×12 at 4×3), `vertical-align`
centred on the text, `1px solid var(--hairline)` frame, `border-radius: var(--radius)`,
no shadow. A code with no file in the map renders as text.

**Russia in greyscale.** `NationalityCell` keeps a set of codes drawn without color,
holding only `RU`, and gives those flags the modifier class `entrant-flag-mono`, styled
`filter: grayscale(1)`. A CSS filter on the one image keeps a single SVG per country,
rather than shipping an edited copy of the file. The owner's decision; no other country
is in the set.

## Risks / Trade-offs

- [The flags' own hex values sit in SVG files in `node_modules`, outside `tokens.css`] →
  the carve-out names them, and no stylesheet of ours gains a hex.
- [A flag says less than a code to someone who does not know it] → the name sits in
  `title` and `alt`, so hover and screen readers carry it. The owner accepted this.
- [Asset count: about 270 small files in the build] → each is fetched only when drawn, and
  the build grows by roughly 1 MB of SVG on disk.
