## 1. Dependencies

- [x] 1.1 Add `marked` and `dompurify` (plus `@types/dompurify` if the package ships no types) to `frontend/package.json` dependencies, pinned to a major, and install
- [x] 1.2 Confirm `npm run build` still succeeds with the new deps before writing any code

## 2. Rendering core

- [x] 2.1 Create `frontend/src/markdown.ts` exporting `renderMarkdown(src: string): string`, the only module importing `marked` or `dompurify`
- [x] 2.2 Configure `marked` with `{ gfm: true, breaks: true, async: false }` so a single newline renders as `<br>` and legacy plain text keeps its line structure
- [x] 2.3 Add the `marked` renderer override mapping heading depth 1–3 to `<h3>` and 4–6 to `<h4>` (D3)
- [x] 2.4 Sanitize with DOMPurify: `ALLOWED_TAGS` = `p, br, strong, em, del, ul, ol, li, h3, h4, a, blockquote, code, pre, hr`; `ALLOWED_ATTR` = `['href']`; `ALLOWED_URI_REGEXP` restricted to `https?:`, `mailto:` and `#`
- [x] 2.5 Register the one-time `afterSanitizeAttributes` hook adding `target="_blank"` and `rel="noopener noreferrer"` to non-anchor links (D4)

## 3. Prose component

- [x] 3.1 Create `frontend/src/Prose.tsx` with `<Prose source className />`, returning `null` for empty/whitespace-only source
- [x] 3.2 Render through `dangerouslySetInnerHTML` with `renderMarkdown` memoized on `source`; verify this is the only `dangerouslySetInnerHTML` in the codebase (`grep -rn dangerouslySetInnerHTML frontend/src`)

## 4. Presentation

- [x] 4.1 Replace the `.detail-description` paragraph in `frontend/src/TournamentFace.tsx` with `<Prose source={detail.description} className="detail-description" />`
- [x] 4.2 Replace the `.registration-instructions` paragraph in `frontend/src/TournamentFace.tsx` with `<Prose source={detail.registration_instructions} className="registration-instructions" />`
- [x] 4.3 Add the `.prose` block to `frontend/src/index.css` per D6: headings at 15px/14px weight 500 (never `--font-doc`), `--ink` underlined links with `--stamp` hover, hairline-marked blockquote with no fill, `--font-data` code on `--paper-shade`, `--hairline` rule, and first/last-child margins zeroed
- [x] 4.4 Remove `white-space: pre-wrap` from `.detail-description` (and from `.registration-instructions` if set) now that breaks are `<br>` elements
- [x] 4.5 Confirm no hex value was introduced outside `tokens.css` (`grep -n '#[0-9A-Fa-f]\{3,6\}' frontend/src/index.css`)

## 5. Setup authoring

- [x] 5.1 Add a `markdown: true` flag to the `description` and `registration_instructions` entries of `IDENTITY_FIELDS` in `frontend/src/SetupPanel.tsx`
- [x] 5.2 In the `textarea` render branch, apply `className="markdown-input"` and render a `.markdown-hint` line beneath when the flag is set
- [x] 5.3 Style `.markdown-input` (`font-family: var(--font-data)`, larger `min-height`) and `.markdown-hint` (`--ink-faded`, small) in `index.css`
- [x] 5.4 Add the shared `setup.identity.markdownHint` key to `frontend/src/i18n/cs.json` and `en.json`, naming the honored markers in one line, lowercase, no exclamation marks

## 6. Verification

- [x] 6.1 `cd frontend && npm run lint && npm run build` clean
- [x] 6.2 Subset check: save a description using paragraphs, `**strong**`, `*em*`, a bullet list, a numbered list, `###`, `>`, `` `code` ``, `---` and a link; confirm each renders and no markup characters are visible
- [x] 6.3 Demotion check: a description starting with `# Turnaj` and `## Program` renders both at the `h3` style, neither larger than the screen's document heading
- [x] 6.4 Suppression check: `![x](https://…/a.png)` and a pipe table produce no image and no table
- [x] 6.5 XSS check: save `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`, `[click](javascript:alert(1))` and `<iframe src=…>` as a description; confirm nothing executes and none of those elements is in the DOM
- [x] 6.6 Link check: an external link is `--ink`, underlined, opens in a new tab and carries `rel="noopener noreferrer"`
- [x] 6.7 Back-compat check: an existing plain-text description with several paragraphs and single line breaks inside them renders exactly as before this change
- [x] 6.8 Empty check: a tournament with neither field set shows no empty prose block or reserved space on either screen
- [x] 6.9 Preview check: both fields render identically in the console Setup preview and on the fencer-facing screens
- [x] 6.10 Authoring check: both Setup fields are monospace and show the syntax hint, in Czech and in English

## 7. Close out

- [x] 7.1 Run `openspec validate add-markdown-descriptions --strict` and fix any reported issue
- [x] 7.2 Sync the `organizer-prose` and `tournament-admin` deltas into `openspec/specs/` and archive the change
