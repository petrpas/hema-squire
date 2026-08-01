## Why

A tournament description is the organizer's one chance to say what the event is —
schedule notes, what to bring, house rules, a link to the venue. Today it is stored
and rendered as verbatim plain text, so everything an organizer writes arrives as one
undifferentiated grey block: no headings to separate "Getting there" from "Equipment
checks", no lists, no clickable link. Organizers already write markdown by reflex
(`## Program`, `- longsword`, `[map](…)`) and today those markers appear literally on
the fencer's screen, which reads as a mistake rather than as text.

The same applies to `registration_instructions`, the second field where an organizer
writes prose for fencers to read.

## What Changes

- The tournament `description` and `registration_instructions` fields are authored in
  **markdown** and presented as **formatted HTML** wherever they are shown to a
  fencer: the tournament information screen, the registration form, and — through the
  same components — the console Setup preview.
- **BREAKING (spec-level, not data-level):** `tournament-admin` today requires the
  description to be presented verbatim with "no markup interpreted". That requirement
  is replaced. Stored data is unaffected: markdown is a superset of plain text, and
  rendering uses soft line breaks, so every description written before this change
  keeps its paragraph and line structure exactly as it renders today.
- A **restricted subset** of markdown is honored. Paragraphs, soft line breaks,
  emphasis, strong emphasis, bullet and numbered lists, level-3 and level-4 headings,
  links, block quotes, inline code, and horizontal rules render. Everything outside
  that set — images, tables, raw HTML, script or style content, headings above level 3
  — is removed by a sanitizer allowlist before the content reaches the DOM. Rendering
  is a pure client-side transform; the stored value is always the organizer's original
  markdown.
- Rendered prose obeys the Bureau 1952 design prohibitions: `--ink` underlined links
  (never blue), headings on the existing type scale at weight 500, no color other than
  the tokens already in `tokens.css`. External links open in a new tab with
  `rel="noopener noreferrer"`.
- In the console Setup phase, the two markdown textareas switch to `--font-data`
  (monospace) so the markup the organizer types lines up, and each carries a one-line
  syntax reminder beneath it. No syntax-highlighting overlay is part of this change.
- Backend, database, export, and API are untouched. The fields stay `Text`, the JSON
  export keeps carrying the raw markdown, and no endpoint changes shape.

Non-goals: no rich-text/WYSIWYG editor; no syntax highlighting in the textarea; no
markdown in any other field (`subtitle`, `location`, `qualification_criteria`, extra
item descriptions stay plain text); no markdown in outgoing email; no server-side
rendering or server-side sanitization.

## Capabilities

### New Capabilities

- `organizer-prose`: The markdown contract for organizer-authored long-form text —
  which fields are markdown, the honored subset, the sanitizer allowlist and the
  guarantee that no organizer input can inject markup, the link and heading
  presentation rules, plain-text back-compatibility, and the monospace authoring
  affordance in Setup.

### Modified Capabilities

- `tournament-admin`: the `Tournament definition` requirement's "description is
  optional free-form plain text … SHALL NOT be interpreted as markup of any kind" and
  the `Registration instructions` requirement's "no markup interpretation" are
  replaced by markdown authoring and rendering, delegating the subset and safety rules
  to `organizer-prose`.

## Impact

Frontend only; no backend, database, API, or migration change.

- New dependencies: `marked` (markdown → HTML) and `dompurify` (allowlist sanitizer),
  both added to `frontend/package.json`.
- New `frontend/src/markdown.ts` — a single `renderMarkdown()` entry point holding the
  parser options and the sanitizer allowlist; the only place either dependency is
  imported.
- New `frontend/src/Prose.tsx` (or equivalent) — the component that renders a markdown
  string into a styled prose block, used by every call site.
- `frontend/src/TournamentFace.tsx` — `detail.description` and
  `detail.registration_instructions` render through the prose component instead of a
  `pre-wrap` paragraph. The console Setup preview inherits this automatically, since it
  renders through the same components (`add-setup-registration-preview`).
- `frontend/src/SetupPanel.tsx` — the two markdown textareas get a monospace class and
  a syntax-hint line.
- `frontend/src/index.css` — a `.prose` block: heading, list, link, blockquote, code
  and rule styling inside rendered descriptions, plus the monospace editor rule.
- `frontend/src/i18n/cs.json`, `en.json` — the syntax hint copy for both fields.
