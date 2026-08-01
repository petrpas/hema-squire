## Context

Two tournament fields carry organizer-written prose: `description` (information
screen) and `registration_instructions` (registration form). Both are `Text` columns
in `backend/app/models.py`, both are edited as textareas in `SetupPanel.tsx`'s
`IDENTITY_FIELDS`, and both are rendered in `TournamentFace.tsx` as a single paragraph
with `white-space: pre-wrap` (`.detail-description`, `.registration-instructions`).
The in-flight `add-setup-registration-preview` change makes the console Setup preview
render through those same `TournamentFace` components, so anything done there appears
in the preview with no extra work.

The frontend has no test runner and only three runtime dependencies
(`react`, `react-dom`, `i18next` family plus `@tabler/icons-react`). It is a Vite +
TypeScript SPA; all rendering is client-side. The design system (`openspec/specs/
design-system/spec.md`, `openspec/squire-design-spec.md`) forbids blue links, radii
above 2px, shadows, and any hex outside `tokens.css` — constraints that bind rendered
prose exactly as they bind hand-written markup.

Owner decisions taken before this design (2026-08-01): markdown applies to
`description` and `registration_instructions`; rendering uses `marked` + `dompurify`;
the Setup editor gets monospace plus a syntax hint, with no highlighting overlay.

## Goals / Non-Goals

**Goals:**

- Organizers author structure — headings, lists, links, emphasis — in the two prose
  fields, and fencers see it formatted.
- One rendering entry point, so the sanitizer cannot be bypassed by a new call site.
- Existing plain-text descriptions render byte-for-byte the same as today.
- Rendered prose is indistinguishable in style from hand-written Squire markup.
- No backend, schema, API, export, or migration change.

**Non-Goals:**

- WYSIWYG editing, toolbar, or paste-to-markdown conversion.
- Syntax highlighting inside the textarea (an overlay technique; deliberately deferred).
- Markdown anywhere else: other fields, email bodies, PDF or export output.
- Server-side rendering or server-side sanitization of the markdown.
- Images or tables inside descriptions.

## Decisions

### D1 — `marked` + `dompurify` over a hand-rolled renderer

`marked` is a mature CommonMark/GFM parser (~40 kB min), `dompurify` (~20 kB min) is
the standard browser sanitizer. Together they cost ~60 kB on a bundle that already
ships React, and both are single-purpose libraries with no transitive dependencies.

*Alternative considered:* a ~150-line hand-rolled subset renderer, zero deps. Rejected:
the escaping and inline-parsing edge cases (nested emphasis, links with parentheses,
code spans containing markup characters) are exactly where hand-rolled renderers grow
XSS holes, and this content is authored by organizers and shown to every fencer. Owning
that risk to save 60 kB is a bad trade.

Both libraries are imported in exactly one module, `frontend/src/markdown.ts`. If
either is ever swapped, that file is the only edit site.

### D2 — Rendering pipeline

```
renderMarkdown(src: string): string
  1. marked.parse(src, { breaks: true, gfm: true, async: false })
  2. DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR: ['href'],
                                ALLOWED_URI_REGEXP: /^(https?:|mailto:|#)/i })
```

- `breaks: true` is what makes legacy plain text render unchanged: a single newline
  becomes `<br>` rather than being collapsed, matching today's `pre-wrap` behavior. A
  blank line still starts a new paragraph.
- `ALLOWED_TAGS`: `p, br, strong, em, ul, ol, li, h3, h4, a, blockquote, code, pre, hr,
  del`. Everything else — `img`, `table`, `script`, `style`, `iframe`, `h1`, `h2`,
  `h5`, `h6` — is absent from the allowlist and therefore stripped, with its text
  content kept (DOMPurify's default `KEEP_CONTENT`), so no organizer text silently
  disappears.
- `ALLOWED_ATTR` is `href` alone: no `class`, `id`, `style`, and no event handlers can
  survive. Styling is applied by descendant selectors under `.prose`, not by classes in
  the generated HTML.
- The URI regexp restricts destinations to `http`, `https`, `mailto` and in-page
  anchors, which covers `javascript:` and `data:` links.

### D3 — Heading demotion in a `marked` renderer override

Organizers naturally start a document at `#`. Dropping those headings (the pure
allowlist outcome) would lose their structure, so a `marked` renderer override maps
heading depth 1–3 to `<h3>` and 4–6 to `<h4>` before sanitization. The allowlist then
only has to admit `h3` and `h4`, and the rendered prose can never out-shout the
screen's own document heading (`--font-doc`, 19–22px), which is the design-system rule
this protects.

### D4 — External links get `target="_blank"` in a DOMPurify hook, not in markup

`target` and `rel` are not in `ALLOWED_ATTR`, so they cannot be injected by an
organizer. A `DOMPurify.addHook('afterSanitizeAttributes')` sets
`target="_blank"` and `rel="noopener noreferrer"` on any `<a>` whose `href` is not an
in-page anchor. Because the hook runs after sanitization, the values are ours, not the
document's. The hook is registered once at module load in `markdown.ts`.

### D5 — A `<Prose>` component is the only way prose reaches the DOM

`frontend/src/Prose.tsx` exports:

```tsx
export function Prose({ source, className }: { source?: string | null; className?: string })
```

It returns `null` for an empty or whitespace-only source (satisfying "empty field
renders nothing"), and otherwise a `<div class="prose …">` with
`dangerouslySetInnerHTML={{ __html: renderMarkdown(source) }}`. The `renderMarkdown`
call is wrapped in `useMemo` keyed on the source, so re-renders of the registration
form — which re-render on every checkbox tick — do not re-parse.

`dangerouslySetInnerHTML` appears in exactly this one component in the codebase; that
is the invariant reviewers check, and it is what makes "the sanitizer is the last step"
enforceable rather than aspirational.

### D6 — CSS lives in one `.prose` block

A single `.prose` section in `index.css` styles `h3, h4, p, ul, ol, li, a, blockquote,
code, pre, hr` by descendant selector:

- `h3` 15px / weight 500 / `--ink`; `h4` 14px / weight 500 / `--ink-soft`. Never
  `--font-doc` — that font is reserved for document H1s.
- `a`: `--ink`, `text-decoration: underline`, `--stamp` on hover. Never blue.
- `blockquote`: `border-left: 1px solid var(--hairline)`, padding, `--ink-soft` text,
  no background fill.
- `code` / `pre`: `--font-data`, `--paper-shade` background, `--radius` (2px).
- `hr`: `1px solid var(--hairline)`.
- Vertical rhythm via `margin` on children with `:first-child`/`:last-child` margins
  zeroed, so the block sits flush in both its containers.

`.detail-description`'s `white-space: pre-wrap` is removed — line breaks are now `<br>`
elements, and leaving `pre-wrap` on would double the spacing inside list items.

### D7 — Setup editing: a field flag, not a new control

`IDENTITY_FIELDS` in `SetupPanel.tsx` already carries per-field `type` and `hint`. The
two prose entries gain `markdown: true`; the render branch for `type === "textarea"`
adds `className="markdown-input"` (which sets `font-family: var(--font-data)` and a
larger `min-height`) and renders a `.markdown-hint` line beneath, sourced from a single
shared i18n key (`setup.identity.markdownHint`) rather than one key per field.

The hint is one line of copy in cs and en naming the honored markers. It is not a link
to external documentation and not a collapsible help panel — the organizer sees the
result in the preview pane immediately.

### D8 — Nothing changes on the backend

The columns stay `Text`, the schemas stay `str | None`, the JSON export keeps writing
the raw markdown, and no endpoint validates or transforms it. Storing the source and
rendering at presentation time means an export can be re-imported losslessly and a
future non-web presentation (email, PDF) can choose its own rendering. It also means
the sanitizer runs on every presentation, so a sanitizer upgrade protects previously
stored content with no data migration.

## Risks / Trade-offs

- **A markdown parser plus a sanitizer is new attack surface on a page every fencer
  sees.** → The allowlist is a strict deny-by-default set with `href` as the only
  permitted attribute; `dangerouslySetInnerHTML` exists at exactly one call site;
  DOMPurify is the industry-standard implementation rather than our own escaping.
  Verification includes pasting known XSS payloads into a real description.
- **Existing plain text could reflow.** Markdown reinterprets characters that were
  previously literal: a line starting with `- ` becomes a list item, `#` becomes a
  heading, `*text*` becomes emphasis, and `1. ` becomes an ordered list. For nearly all
  existing content this is the improvement being asked for, but an organizer who wrote
  `- 2 * 3` in prose sees a change. → `breaks: true` preserves the line structure that
  matters most; the Setup preview shows the rendered result immediately; and the source
  is never rewritten, so any surprise is fixable by editing text the organizer still
  owns.
- **~60 kB added to the bundle for a field most tournaments fill with two
  paragraphs.** → Accepted (D1). If it ever matters, `markdown.ts` is a clean
  dynamic-import boundary.
- **No frontend test runner, so none of this is covered by automated tests.** →
  Verification is `tsc -b` plus an explicit manual checklist in `tasks.md` covering the
  subset, the XSS payloads, the legacy plain-text case, and the empty case. Adding a
  test runner is out of scope for this change but is the obvious follow-up.
- **`marked`'s renderer API changes across majors**, so D3's heading override is
  version-sensitive. → Pin a major in `package.json` and keep the override inside
  `markdown.ts`, where a version bump is a single-file fix.

## Migration Plan

No data migration. Markdown is a superset of the stored plain text, and every stored
value remains valid input. Deployment is a frontend build; rollback is the previous
build, after which stored markdown renders as literal text again with no data loss.

## Open Questions

None. The three decisions that shaped this change (field scope, renderer choice,
editor affordance) were settled by the owner before the design was written.
