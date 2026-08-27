## Context

See `proposal.md` — Why. The pieces this design has to fit between already exist:

- `frontend/src/markdown.ts` is the one place markdown becomes HTML: a `Marked`
  instance (gfm, breaks, a heading-demoting renderer) followed by
  `DOMPurify.sanitize` with `ALLOWED_TAGS` / `ALLOWED_ATTR` / `ALLOWED_URI_REGEXP`
  and a module-load `afterSanitizeAttributes` hook that stamps `target="_blank"`
  and `rel="noopener noreferrer"` on external anchors.
- `frontend/src/Prose.tsx` is the only file in the codebase using
  `dangerouslySetInnerHTML`, which is what makes the sanitizer unbypassable.
- The location reaches fencers in exactly two places: `TournamentFace.tsx`, where
  `DotJoined` already accepts `React.ReactNode` parts (the ruleset link goes
  through it), and `FencerHome.tsx`, where `CardHeading` builds
  `[date, location].filter(Boolean).join(" · ")` — a string, inside a `<Link>`
  that wraps the whole card.
- Setup edits `location` as a `{ key: "location", type: "text" }` entry in
  `IDENTITY_FIELDS`; the `markdown: true` flag on the two textarea entries drives
  both the `markdown-input` class and the `setup.identity.markdownHint` line.
- `location` is `String(300)`, required for publication (`setup.MISSING_LOCATION`),
  and is echoed by the public detail and open-tournaments payloads and by
  `export_json`. Nothing in the backend interprets its content.

## Goals / Non-Goals

**Goals:**

- One rendering entry point. Inline rendering shares the sanitizer configuration
  and the anchor hook with long-form prose; the guarantee in `organizer-prose`
  ("the sanitizer is the last step") keeps holding by construction.
- `dangerouslySetInnerHTML` stays confined to one file.
- The card's date-and-place line stays one line of text inside one link.

**Non-Goals:**

- Making any other field markdown, or widening the long-form subset.
- Validating markdown at save time, or storing anything but the source.
- Recognizing a bare URL typed without link syntax — link syntax is the contract.
- Backend work of any kind.

## Decisions

**D1 — Inline rendering is `marked.parseInline`, not `parse` with the wrapper
stripped.** `parseInline` tokenizes the source as inline content, so block
constructs never become tokens: `# Praha` and `- Praha` come out as their literal
characters, which is exactly the spec's "block syntax stays literal", and there is
no `<p>` to strip and no `breaks: true` line break to suppress. Alternative
considered: `parse()` then remove the outer `<p>`. Rejected — it would render a
heading or a list when an organizer typed one, then leave the caller to cope with
block markup on a middle-dot line.

**D2 — `markdown.ts` gains `renderInline(src, { links })` beside
`renderMarkdown`.** Both call the same `DOMPurify.sanitize` with the same
`ALLOWED_ATTR` and `ALLOWED_URI_REGEXP`; the inline path passes a narrower
`ALLOWED_TAGS` — `strong`, `em`, `del`, `code`, and `a` only when `links` is true.
Dropping `a` from the allowlist relies on DOMPurify's default `KEEP_CONTENT`, so a
forbidden anchor is replaced by its own text: the label-only rendering falls out of
the sanitizer rather than needing a second markdown pass or a regex over the
source. The `afterSanitizeAttributes` hook is registered once at module load and
applies to both paths unchanged, so external links keep their `target`/`rel`
wherever they render.

**D3 — A sibling component `InlineProse` in its own file, rendering a `<span>`.**
`Prose` renders a `<div class="prose">`, which cannot sit inside a paragraph or a
middle-dot line. `InlineProse` takes `source` and a `links` prop and renders
`<span class="prose-inline">`; it returns `null` for an empty or whitespace-only
source, which is what keeps the absent-location case free of a stray middle dot
(`DotJoined` already drops `null` parts). Alternative considered: a `variant` prop
on `Prose`. Rejected — the project keeps one component per file, and the two
differ in element, class and allowlist, not just in styling.

**D4 — The card passes `links={false}`; the information screen passes
`links`.** This is the spec's "inline links inside a link target" rule, decided at
the call site because only the call site knows it is inside a `<Link>`. The
alternative — teaching the renderer to detect an ancestor anchor — needs a context
or a DOM read for a rule that two call sites can state in a word.

**D5 — `DotJoined` and `DOT` move to `frontend/src/DotJoined.tsx`.** `CardHeading`
currently joins strings; once the location is a node it needs the same
null-dropping join `TournamentFace` has, and duplicating a five-line join in two
files is how the two lines drift apart. `TournamentFace.tsx` imports it back
(it is ~300 lines already, so this is a split along an existing seam, per
`CLAUDE.md`). The card's `<p class="home-card-when">` keeps its class, so its
13px/500 weight is unchanged.

**D6 — Styling reuses the existing link rules rather than adding hexes.**
`.prose-inline a` gets the same `color: var(--ink)` + underline and
`:hover { color: var(--stamp) }` as `.prose a`, written as a shared selector list
so there is one definition. `.prose-inline` itself sets no font, size or spacing —
it inherits from the line it sits on, so a card place line and a detail facts line
each keep their own type. `code` inside it takes `--font-data` like `.prose code`.
No new value enters `index.css` and no token is bypassed.

**D7 — The Setup hint is a new key, not a reuse of `markdownHint`.** The existing
hint names headings, lists, quotes and rules, none of which render here; showing
it under the location field would document behavior the field does not have. A
`setup.identity.locationHint` naming links, strong and emphasis is added to both
`cs.json` and `en.json` (the locale-parity test enforces the pair). The field
stays `type: "text"`; the hint is driven by a new `inlineMarkdown: true` flag on
the `IDENTITY_FIELDS` entry, so the single-line control and the monospace
`markdown-input` class stay separate concerns.

**D8 — The 300-character bound stays.** Link syntax spends the same budget as any
other characters, and `TournamentUpdate.location`'s existing maxLength check and
message are already correct about it. Raising the bound would be a backend change
for a case no organizer has hit.

## Risks / Trade-offs

- **An organizer types a URL bare and expects a link** → The Setup hint states the
  syntax and shows the bracket form; the Setup preview renders the field the way a
  fencer sees it, so the mistake is visible before publication.
- **A stored location contains stray `[`, `*` or `_` that now changes meaning**
  (e.g. `Hala *U Sokola*`) → Real risk in principle, none in practice: the app is
  pre-launch with no organizer data, and unmatched brackets render literally under
  `parseInline` anyway. Covered by a test over plain-text locations.
- **The label-only path silently drops a destination on cards** → Intended and
  specified; a fencer reaching the tournament page gets the real link one tap
  away, and a nested anchor would be invalid markup with browser-dependent
  behavior.
- **The narrower inline allowlist drifts from the prose allowlist** → Both are
  defined in `markdown.ts` from one shared base list, and the inline list is
  expressed as a subset of it rather than as a second literal.

## Migration Plan

None. No stored value changes, no column changes, no API or payload change; a
deploy of the frontend is the whole rollout, and reverting the frontend restores
the literal rendering with the same stored sources intact.
