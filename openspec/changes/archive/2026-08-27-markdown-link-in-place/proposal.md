## Why

The tournament location is the one identity field a fencer wants to act on — they
want to know where the hall is on a map — and today it is plain text, so an
organizer either leaves the address unlinkable or pastes a bare URL that reads as
noise on the card. Organizers already author markdown in the description and
registration instructions; typing `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)` in
the location field is the obvious thing to reach for, and it currently shows the
brackets verbatim.

## What Changes

- The tournament `location` becomes an inline-markdown field: it is rendered
  through the existing sanitizer rather than presented literally.
- The honored subset for `location` is **inline only** — links, emphasis, strong
  emphasis, inline code. Block constructs (headings, lists, quotes, rules,
  paragraphs) do not apply; the field stays one line wherever it appears.
- The tournament information screen renders a location link as a real link:
  `--ink`, underlined, `target="_blank"`, `rel="noopener noreferrer"` — the same
  presentation the description already gives links.
- On a Fencer Home card, whose whole card is already a link to the tournament,
  the location renders as its **label text only** (`ZŠ Bílá`), never as a nested
  link. Emphasis inside the label still renders.
- The Setup location field carries the same localized syntax hint the markdown
  fields carry, worded for the inline subset.
- Plain-text locations keep rendering exactly as before. **Not breaking**: the
  stored value stays the organizer's source, the column and its 300-character
  bound are unchanged, and no migration is needed.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `organizer-prose`: the markdown contract currently names `location` among the
  fields that are explicitly *not* markdown. It becomes a markdown field with a
  narrower, inline-only honored subset, and the spec gains the rule for rendering
  an inline field inside a container that is itself a link.
- `fencer-home`: the date-and-place line on a card and the `date · place ·
  qualification` line on the information screen gain their rendering rules — a
  link on the information screen, label text on the card.

## Impact

- `frontend/src/markdown.ts` — a second entry point for inline rendering beside
  `renderMarkdown`, sharing one sanitizer configuration, plus a plain-text
  reduction for link-inside-link contexts.
- `frontend/src/Prose.tsx` — a sibling inline renderer (`<span>`, no block
  wrapper); `dangerouslySetInnerHTML` stays confined to this file.
- `frontend/src/TournamentFace.tsx` — the `detail-facts` line renders the
  location through the inline renderer.
- `frontend/src/FencerHome.tsx` — `CardHeading` renders the location's label text.
- `frontend/src/setup/IdentitySection.tsx` and `frontend/src/i18n/{cs,en}.json` —
  the inline syntax hint under the location input.
- `frontend/src/index.css` — inline-prose link styling reusing the `.prose a`
  rules; no new hex values.
- Backend: none. No model, schema, API, migration, or export change; `location`
  remains `String(300)` and is still required for publication.
