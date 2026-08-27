## 1. Inline rendering entry point

- [x] 1.1 In `frontend/src/markdown.ts`, split the tag allowlist into a shared inline base (`strong`, `em`, `del`, `code`, `a`) and the block tags that only long-form prose uses, and rewrite `ALLOWED_TAGS` for `renderMarkdown` as base + block; verify `npm --prefix frontend run build` type-checks and the existing prose rendering is unchanged in the app.
- [x] 1.2 Add `renderInline(src, { links })` in `markdown.ts` using `marked.parseInline` and the same `DOMPurify.sanitize` call, passing the inline allowlist with `a` omitted when `links` is false (D1, D2); verify by unit test that `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)` yields an anchor with that href, and yields the bare text `ZŠ Bílá` with `links: false`.
- [x] 1.3 Add `frontend/src/markdown.test.ts` covering the inline subset: `**strong**`/`*em*`/`` `code` `` render; `# Praha`, `- Praha` and a pipe table stay literal with no block element and no `<br>`; `<script>`, `<img onerror>` and `[x](javascript:alert(1))` produce no script, no such element and no `javascript:` href; a plain `Sportovní hala, Praha 6` round-trips unchanged; empty and whitespace-only sources yield `""`. Verify with `npm --prefix frontend test`.

## 2. Inline prose component

- [x] 2.1 Add `frontend/src/InlineProse.tsx` rendering `<span class="prose-inline">` via `dangerouslySetInnerHTML` from `renderInline`, with a `links` prop and a `null` return for an empty or whitespace-only source (D3); verify no other file gains a `dangerouslySetInnerHTML` by grepping the frontend for it.
- [x] 2.2 In `frontend/src/index.css`, add `.prose-inline` to the existing `.prose a` and `.prose a:hover` selector lists and give `.prose-inline code` the `--font-data` treatment `.prose code` has, adding no new hex value and no font-size or spacing on `.prose-inline` itself (D6); verify by grepping the diff for `#` hex literals and for `box-shadow`/`border-radius`.

## 3. Shared middle-dot join

- [x] 3.1 Move `DOT` and `DotJoined` from `frontend/src/TournamentFace.tsx` into `frontend/src/DotJoined.tsx` unchanged and import them back (D5); verify the build type-checks and the detail identity line renders as before.

## 4. Rendering the location

- [x] 4.1 In `TournamentFace.tsx`, render `detail.location` on the `detail-facts` line through `InlineProse` with links enabled; verify in the app that a location holding link syntax shows the label as an underlined `--ink` link opening in a new tab with `rel="noopener noreferrer"`, and that a location with no link renders as plain text on the same line.
- [x] 4.2 In `FencerHome.tsx`, replace `CardHeading`'s `dateAndPlace.join(" · ")` with `DotJoined` over `[date, <InlineProse links={false}>]` inside the existing `<p class="home-card-when">`; verify in the app that the card shows the label text only, that the whole card is still one working link with no nested anchor in the DOM, and that the line keeps its 13px/500 weight.
- [x] 4.3 Verify the absent-location case on both screens: a tournament with no location shows the date with no middle dot before or after it and no empty element, on the card and on the information screen.

## 5. Setup affordance

- [x] 5.1 Add an `inlineMarkdown: true` flag to the `location` entry in `IDENTITY_FIELDS` in `frontend/src/setup/IdentitySection.tsx` and render `setup.identity.locationHint` beneath the field, leaving it a single-line `type: "text"` control without the `markdown-input` class (D7); verify the hint appears under the location input in Setup and the two textarea fields keep their own hint.
- [x] 5.2 Add `setup.identity.locationHint` to both `frontend/src/i18n/en.json` and `frontend/src/i18n/cs.json`, naming only links, strong and emphasis; verify `npm --prefix frontend test` passes the locale-parity test.

## 6. Verification

- [x] 6.1 Run `npm --prefix frontend test` and `npm --prefix frontend run build`, and confirm the backend is untouched (`git diff --stat backend` is empty).
- [x] 6.2 Walk the change end to end in the app: set a location to `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)` in Setup, confirm the Setup preview, the Fencer Home card and the tournament information screen each present it as specified, and confirm the stored value comes back into the Setup field as the exact source typed.
