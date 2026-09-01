## Context

Squire's frontend is a single Vite/React app whose styles live in one 2917-line
`index.css`, organised by component block, over a token file that is the only place a
hex value may appear. The organizer console drove every layout decision so far: it is
a desktop instrument, and the fencer's screens inherited its assumptions — fixed
widths in `rem`, `100vh` frames, a single-row topbar, 14px controls.

The fencer's screens are the ones that are actually opened on a phone. This design
covers making them work at 360–430px without a second stylesheet, a framework, or a
device-detection branch in the component tree.

Two constraints shape everything below:

1. **`CLAUDE.md` / `squire-design-spec.md` are unchanged.** No shadows, gradients,
   radius > 2px, spinners, shimmer, emoji, no saturated colour but `--stamp`, no hex
   outside `tokens.css`. A narrow viewport is not a licence for a "material" look.
2. **No new dependencies.** Vanilla CSS in `index.css`; hooks and DOM APIs already
   available in the browser.

Current state verified against `14d9f6e`. Facts the design leans on:

| Fact | Location |
|---|---|
| `.login-card { width: 22rem }`, `.login-page { padding: 2rem 1rem }` | `index.css:187`, `:194` |
| `.app { height: 100vh }`, `.login-page { min-height: 100vh }` | `index.css:338`, `:187` |
| `.modal { max-height: 70vh }`, `.wide-card { max-height: 88vh; max-width: 92vw }` | `index.css:1407`, `:1519` |
| `.stage-control { overflow: hidden }` | `index.css:366` |
| `.topbar { display: flex; gap: 2rem }` | `index.css:342` |
| Six input blocks at 13–14px | `:228 :877 :1427 :1558 :1589 :2376` |
| No `autoComplete`/`name` anywhere in `src/` | verified by grep |
| `RequireAuth` swallows `api.account()` rejection | `RequireAuth.tsx:24` |
| Markdown allowlist excludes `img`, `table` | `markdown.ts:22-24` |
| Existing width queries: 640 (`.match-results`), 1300 (`.setup-split`) | `index.css:1470`, `:639` |

## Goals / Non-Goals

**Goals:**

- A fencer can sign in, create an account, browse, register and pay on a 360px phone
  without pinching, sideways scrolling, or an unexplained blank shell.
- Credential managers fill and save both auth forms.
- One breakpoint vocabulary the whole codebase shares.
- Responsive rules live beside the component they govern, so they move when it moves.
- The organizer console keeps working on desktop.

**Non-Goals:**

- A mobile organizer console. Group 1 reaches it; nothing else does.
- PWA, service worker, offline mode, bottom navigation.
- Any colour or type-scale change beyond the 16px control size.
- Any backend change.
- Playwright or any visual-regression harness.

## Decisions

### D1 — Breakpoints are literals, documented in `tokens.css`, not stored as tokens

**480 / 768 / 1024**, recorded as a comment block in `tokens.css` next to the geometry
tokens.

They are deliberately *not* custom properties. A `@media` **condition** is evaluated
before the cascade, so `var()` is not substituted there: `@media (max-width:
var(--bp-sm))` does not error, it is silently dropped, and the page renders as though
the breakpoint were never written. A comment that cannot be referenced is the honest
representation; a token that looks referenceable but fails silently is a trap.

*Alternative considered:* a build-time CSS preprocessor (Sass/PostCSS custom-media) to
give breakpoints a real name. Rejected — a new build dependency for four numbers used
in one file, against the no-dependency constraint.

*Alternative considered:* container queries, which would bind rules to the component's
own width rather than the window's, and which the brief's group 0 preference for
container-independent layout points toward. Rejected as the general mechanism because
the topbar and login card are laid out against the viewport, not a sized container,
and adopting `container-type` on their ancestors changes their layout containment.
Kept in reserve for a later change.

Existing queries are reconciled:

- `@media (min-width: 640px)` on `.match-results` **moves to 768px** (owner decision).
  HR result rows therefore stay stacked from 640–767px, one band wider than today.
  This is the only intentional behaviour regression in the change; it touches one
  list, reachable from sign-up and Profile.
- `@media (max-width: 1300px)` on `.setup-split` **stays at 1300px** and is annotated
  as a *content threshold* — the width at which the console's two side-by-side panels
  stop fitting — not a device breakpoint. It is console-only and out of scope.

### D2 — `--field-size`: 14px at desktop widths, 16px below 768px

iOS Safari zooms the viewport when a control smaller than 16px takes focus, and never
zooms back out. The countermeasures are: raise the control to 16px, or add
`user-scalable=no` to the viewport meta. The second is an accessibility regression —
it disables zoom everywhere, including where a fencer genuinely needs it — and is
rejected outright.

The size is applied **under `max-width: 768px` only**, leaving desktop controls at the
14px they have always been.

This reverses the original decision here, which applied 16px unconditionally on the
reasoning that a value differing by viewport drifts, and that 14px against 16px is
optically negligible on a desktop. The owner saw the change in the console's Setup
panel and said so, which settles the second half: it is not negligible. The measured
cost had been +2.5px per field and +42px down the 27-field panel.

The drift risk is answered by where the switch lives. `--field-size` is redefined once,
in `tokens.css`, inside a `@media (max-width: 768px)` block; the six call sites keep
reading the token and none carries a query of its own. There is one value in one place
per width, so there is nothing for a component to disagree with.

Redefining a custom property inside a media *block* is ordinary CSS and works. What
does not work is `var()` inside a media *condition* (D1). The two are easy to conflate
and the token file now says so at both sites.

*Known gap:* the query is width-based, so a touch device wider than 768px — an iPad in
landscape — takes the 14px branch and can still zoom on focus. A pointer-based
condition (`@media (pointer: coarse)`) would follow the actual failure mode rather than
a proxy for it, since focus-zoom is a property of touch, not of width. Left as-is
because width is what was chosen; it is a one-line change if the iPad case matters.

The token reaches **six** blocks, not the four the brief names:

| Block | Now | Surface |
|---|---|---|
| `.login-card input/select` | 14px | sign-in, sign-up, Profile, Admin, Picker |
| `.form-field` + `.param-field` input/textarea/select | 14px | registration, Profile, HR search, all Setup |
| `.modal input` | 14px | dialogs |
| `.plea-form textarea` | 14px | organizer plea |
| `.inline-form input` | 14px | console — Setup team section |
| `.checklist-control input/select` | **13px** | **`TournamentFace` — the registration checklist** |

`.checklist-control` is the one the brief missed and the one that matters most after
sign-in: it is where a fencer types quantities while registering, and at 13px it
triggers the zoom mid-form.

`.cell-input` (EditableCell, console) uses `font: inherit` and takes its size from the
sheet table. It is deliberately **left alone** — raising it would change every console
row's height. Console fields are edited with a mouse on a desktop; the zoom fault does
not arise there.

*Consequence:* `.form-field`/`.param-field` are shared with the console's Setup panel,
which is why the unconditional version was visible there at all. Under the width-gated
version the console is untouched at the widths it is actually used at, and the
cross-cutting cost the proposal accepted is now paid only below 768px.

`.checklist-control` gains 1px at desktop widths (13px → 14px) by joining the common
token. That is deliberate: it was the one control set below the common size, for no
reason recorded anywhere.

The design-system spec's *Typography conventions* requirement is amended in the same
change, with the rationale recorded, so a later audit reads the 16px as intentional
rather than as drift from the 14px body rule.

### D3 — `dvh` for frames, `env()` for edges

`.app`, `.login-page`, `.modal` and `.wide-card` move from `vh` to `dvh`. On mobile
browsers `vh` resolves against the viewport *without* the address bar, so a `100vh`
frame extends below the fold and its bottom edge is unreachable.

`dvh` has no fallback ladder here: every browser that lacks `dvh` (pre-2022) also
predates the toolbar behaviour that makes `vh` wrong, and would take the `vh`
declaration that precedes it if we wrote one. We write `dvh` alone rather than a
`vh`-then-`dvh` pair, because the pair implies a fallback we are not actually
maintaining.

Edge-pinned chrome — the sticky topbar's top, the modal's bottom action bar — takes
`env(safe-area-inset-top/bottom)` added to its existing padding via `calc()`, so the
declaration degrades to the plain padding where `env()` is unsupported.

### D4 — Touch targets grow by padding only

Below 768px, `.stage-control button/a`, `.link-button`, `.row-action` and `.chip`
gain vertical padding toward 44×44px. `font-size` and `letter-spacing` are held
exactly. Growing the type would break the typographic hierarchy the design spec sets
(11px uppercase labels against 14px body) and would make the tab band wider still.
The result is the same official register, more airily set.

`.row-action` is the tightest case at `padding: 0.2rem` around an 18px icon — roughly
26px. It reaches 44px through padding alone without disturbing anything around it,
because it sits in a flex row that is taller than the icon already.

### D5 — Hover is split by *why the rule exists*, not by breakpoint

All 18 `:hover` rules were read. Hover does not exist on touch, and mobile Safari
emulates it stickily: the first tap applies the hover state, only the second fires the
action. The split is by function:

**Decorative — wrapped in `@media (hover: hover)`.** The element is fully visible and
legible at rest; hover only acknowledges the pointer.

`button.secondary` (69), `.btn-primary` (91), `.btn-danger` (116), `.login-card
button[type=submit]` (278), `.picker-list a` (316), `.sheet-table tbody tr` (735),
`.note-marker-button` (792), `.note-marker-problem` (801), `.row-action` (1296),
`.account-menu-trigger` (1631), `.account-menu-dropdown button/a` (1677/1678),
`.home-card` (1719), `.identity-hrid` (1819), `.conclusion-choice` (2843).

**Sole affordance — needs a persistent form.** Only one qualifies:

- `.match-results button` (1466). The HR result rows are borderless transparent
  buttons; the background change on hover is the only signal they can be tapped.
  Below 768px they take a persistent affordance from the existing vocabulary — the
  hairline rule each row already carries, plus a `--stamp` left rule on the row —
  rather than a new colour or a chevron icon (icons are reserved for where text will
  not do).

**Already handled — no change.** `.help-hint-marker:hover + .help-hint-box` (1106)
and `.sheet-table thead th:has(.help-hint-marker:hover)` (1130) each already pair the
hover selector with a `:focus`/`:focus-within` twin, and the marker is a `<button>`,
so a tap opens the hint. They are also console-only (every `HelpHint` call site is a
Setup section or an organizer dialog), so they are out of scope twice over.

### D6 — Credential managers: attributes first, form identity second

The brief attributes the autofill failure to sign-in and sign-up sharing one `<form>`.
They do not share one: `SignupForm` is a separate component, so at the `div.login-page`
child position React compares a *function* element type against the host `"form"` type,
finds them different, and unmounts and rebuilds the subtree. The DOM node is genuinely
replaced on every mode switch.

The actual cause is simpler and total: **no input in `frontend/src/` carries `name` or
`autocomplete`.** Password managers key on those; without them there is no username
field to fill and no credential pair to offer to save. So the attribute table is the
fix, and the stable form `id`s are reinforcement — they give Safari's heuristics a
durable identity across the remount, which is worth having but is not the cause.

Sign-in: `name="email" type="email" autoComplete="username" autoCapitalize="none"
autoCorrect="off" spellCheck={false} inputMode="email"`; password `name="password"
autoComplete="current-password" enterKeyHint="go"`.

Sign-up: e-mail as above; password `autoComplete="new-password"`; name
`name="display_name" autoComplete="name" autoCapitalize="words"`. `username` is
carried on sign-up's e-mail too — it is the signal that says "this is the account
identifier", and without it managers will not offer to save the new pair.

### D7 — An expired session ends at Login, a flaky network does not

`RequireAuth` currently seeds `authed` from `getToken() !== null` and discards the
`api.account()` rejection in `() => {}`. On a phone, whose token is typically weeks
old, that yields a signed-in shell with an empty identity block and an empty list —
which reads as a broken app, not as being signed out.

The rejection handler is narrowed to the status: **401 only** calls `setToken(null)`
and drops to `Login`. Every other rejection — offline, DNS, 502 — is left alone,
because signing someone out for a dropped connection loses their session for a reason
that will fix itself.

`Login` continues to render **in place, at the current URL**, per `routing`'s
"Unauthenticated visits keep their destination". Expiry must not redirect to `/`, or
a fencer whose token dies on `/t/spring-open-2026` loses their destination as well as
their session.

*Alternative considered:* a global 401 interceptor in `api.ts` covering every call.
Rejected for this change — it changes error handling for the console's many endpoints
too, which is beyond a fencer-layout change and deserves its own proposal. `RequireAuth`
is the one gate every fencer screen passes through.

### D8 — The narrow tab band is one shared mechanism, used twice

Both `FencerShell`'s four filter tabs (3.1) and `TournamentDetail`'s three detail tabs
(5) need the same treatment below 768px: a full-width, horizontally scrollable,
scroll-snapped strip. It is written once as a modifier on `.stage-control` and applied
in both places, not authored twice.

`.stage-control` currently sets `overflow: hidden` — which would clip the strip rather
than scroll it. It becomes `overflow-x: auto; overflow-y: hidden` under the query,
plus `scroll-snap-type: x proximity` and a hidden scrollbar
(`scrollbar-width: none` + `::-webkit-scrollbar { display: none }`).

The 1px dividers between tabs and the outer `.stage-control` frame **stay**. This is a
strip cut from a form, not a row of pills; losing the frame would be the "material"
drift the design prohibitions exist to prevent. `flex-shrink: 0` on `.stage-control`
is correct inside a scroll container and is left as it is.

The active tab is centred with `scrollIntoView({ inline: "center", block: "nearest" })`
in an effect keyed on the active tab. `block: "nearest"` is essential and not in the
brief: without it, centring a tab horizontally also scrolls the page vertically to
centre the topbar, which on a sticky topbar jumps the whole workspace.

Topbar is `position: sticky; top: 0`, never `fixed`. `fixed` elements detach and judder
in mobile Safari while the address bar collapses.

### D9 — The full-screen HR step is a wrapper, and sign-up's state is what makes it safe

Below 768px, `HRSearchPicker` moves out of the flow of the sign-up form and onto a
full-screen layer above it. The critical property is that **no route changes and the
form does not unmount** — the layer is rendered by the same component that owns
`email`, `password`, `name` and `language`, so every keystroke survives the round trip.
Routing to a `/signup/hr` screen would discard it; that is why the picker is overlaid
rather than navigated to.

`ProfilePage` uses the same wrapper (owner's brief: one component, not two
implementations). The two call sites pass different props and the wrapper must not
flatten that difference:

| | sign-up | Profile |
|---|---|---|
| `lockedQuery` | the form's `name` | *unset* — picker shows its own query input |
| `initialQuery` | — | `account.display_name` |
| `onCancel` | closes to the form | *unset* — no cancel button today |
| `requireNationality` | `true` | `false` |

The wrapper therefore takes children/props through and owns only the layer: full-bleed
panel, a title, and a back control. Because sign-up passes `lockedQuery`, the picker
hides its own query field — so the full-screen step **must display the name it is
searching for**, or the fencer meets a nationality dropdown and a Search button with
nothing saying what is being searched. That line is part of the step, not the picker.

### D10 — Paying on the device the QR is displayed on

The SPAYD QR assumes two devices. On one device it is inert, and today there is no
alternative: account number, IBAN, VS and amount are `<strong className="data-value">`
elements that cannot be selected conveniently on a phone.

**Save the QR image — Web Share first, download as fallback** (owner decision). The
brief specified `<a download>` with the data URL. On iOS that writes to the Files app,
not to Photos, and several Czech banking apps read a QR only from the photo library —
so download-only would produce a button that appears to work and leads nowhere.
`navigator.share({ files: [File] })` hands the PNG to the system sheet, from which the
fencer can add it to Photos or send it straight into the banking app; it is available
on iOS Safari and Android Chrome. Guarded by `navigator.canShare?.({ files })`, falling
back to an anchor download where sharing is unavailable (desktop Firefox, older
browsers). `qr_png_base64` is already in the payload — this is client-side only, with
no backend change.

**Copy actions on account number, IBAN, VS and amount**, via
`navigator.clipboard.writeText`. Offered at **every** width, not just mobile: copying a
VS with a mouse is tedious everywhere.

`navigator.clipboard` requires a secure context — fine on `hemasquire.eu` and on
`localhost`, **absent over a LAN IP**, which is exactly how a phone is usually pointed
at a dev server. The control is therefore rendered from a capability check rather than
assumed present, and the manual-testing task says to expect it missing over LAN IP so
that absence is not misread as a bug.

Confirmation of a copy is **static text next to the field** that appears and later
fades out. No toast, no entrance animation, no icon swap — the prohibitions allow a
fade-out departure and nothing more.

`PaymentPanel.tsx` renders two near-identical currency branches (local and EUR) at ~175
lines. Adding a save control and four copy affordances to both would push it past the
~300-line seam in `CLAUDE.md` and duplicate the new logic. The slip block is extracted
to its own file alongside a small copy-field component, and the two branches become
data passed to it. The branches differ — EUR has no `account_domestic` and carries
`message` instead of `vs` — so the extracted component takes a field list rather than
fixed slots.

### D11 — `.prose` needs wrapping, not image and table handling

The brief asks for `img { max-width: 100% }` and an `overflow-x` wrapper around tables
inside `.prose`, on the reasoning that organizers will paste anything. They can paste
anything, but it cannot arrive: `markdown.ts` sanitises with DOMPurify against
`ALLOWED_TAGS = [strong, em, del, code, a, p, br, ul, ol, li, h3, h4, blockquote, pre,
hr]`. `img` and the whole table family are stripped before render. Those two rules
would be dead CSS, and dead CSS in a file this size is worse than absent CSS — the next
reader infers images are supported.

What *can* overflow a 360px column is a long unbroken string: a bare URL in a
paragraph, or a URL used as its own link text. `.prose` gets `overflow-wrap: anywhere`
on its text-bearing children. `.prose pre` already carries `overflow-x: auto`
(`index.css:2159`) and needs nothing.

If organizers should be able to post images or tables, that is a change to the
sanitiser allowlist — a security-relevant decision with its own proposal, not a side
effect of a layout change.

### D12 — Where the mobile rules live

Every rule added by this change goes **in its component's own block** in `index.css`,
adjacent to the desktop rules it modifies. There is no trailing "mobile" section.

A section at the end of a 2900-line file collects rules for components whose desktop
rules are 2000 lines away; within a release the two drift, and a component deleted at
line 700 leaves orphans at line 2900 that nobody dares remove. Locality means a
component's responsive behaviour is read, edited and deleted with the component.

Where a media query can be avoided it is: `min()` for `.login-card`'s width,
`flex-wrap` on `.home-card-header`, the existing `1fr auto` grid on `.amount-line`
(which already holds at narrow widths and needs only `min-width: 0` on its first
column so a long Czech label cannot push the amount out). A media query binds to
window size rather than container size and quietly stops matching after the next
layout refactor, so it is the second choice, not the first.

### D13 — Verification is typecheck, build, unit tests, and a scripted manual pass

`npm run lint` (`tsc -b --noEmit`), `npm run build`, and `npm test` must pass.

The frontend **does** have a test runner: `package.json` defines `"test": "vitest run"`
and `src/` holds 23 test files. `add-payments-console-ui/proposal.md:35` states the
opposite; that line is corrected in this change so the next proposal does not inherit
it. `i18n/locale-parity.test.ts` will catch any new key added to one locale and not the
other.

Unit tests are added where behaviour is testable without a viewport: the 401 path in
`RequireAuth`, the submitting label, and the autofill attributes on both forms. Layout
itself is not unit-tested — jsdom has no layout engine, so a test asserting a
breakpoint's effect would assert only that a class name is present.

No Playwright. It is a new dependency, and a visual regression across three widths is
not what it reliably catches.

Manual pass in DevTools at **360 / 390 / 768 / 1024**, each width walking sign-in →
sign-up → home → detail → registration → payment slip → profile → sign-out.

Four things DevTools does not emulate faithfully and that must be checked on a real
iPhone: focus zoom (D2), the autofill offer and save prompt (D6), topbar behaviour as
the address bar collapses (D8), and loading the saved QR into a banking app (D10).

## Risks / Trade-offs

**Group 1 changes shared CSS the organizer console depends on** → `.form-field`,
`.param-field`, `.app`, `.topbar` and `.stage-control` are shared. Console fields grow
2px; the topbar and stage-control changes are scoped under `max-width: 768px`, which
the console is never viewed at. A desktop console pass — Setup field density and
sheet-table row height in particular — is an explicit task, and `.cell-input` is
deliberately excluded from the 16px change (D2).

**Moving `.match-results` from 640 to 768 is a real behaviour change** → HR result rows
stay stacked over a band they currently render as single lines. Accepted knowingly
(owner decision) to keep one breakpoint vocabulary; the cost is taller rows on small
tablets in one list.

**`navigator.clipboard` is absent over plain HTTP** → the copy controls would vanish
when a phone is pointed at a dev server by LAN IP. Rendered from a capability check, and
called out in the manual-test task so it reads as expected rather than as a defect.

**`navigator.share` with files is unevenly supported** → guarded by `canShare({ files })`
with an `<a download>` fallback, so the control always does something. On desktop
Firefox that means a file download, which is the correct behaviour there anyway.

**A full-screen HR step could silently discard the sign-up form** → mitigated by
construction: the layer is rendered by the component holding the form state and no
route changes (D9). Worth an explicit manual check — fill every field, open the HR
step, confirm a candidate, verify nothing was lost.

**`scrollIntoView` on the tab band can scroll the page vertically** → `block: "nearest"`
alongside `inline: "center"`; without it, centring a tab jumps the workspace under a
sticky topbar.

**16px controls could reflow console layouts that were tuned at 14px** → the risk is
real but bounded to fields inside Setup sections, all of which are in a vertical
single-column flow (`.param-fields` is `flex-direction: column`) where 2px of type
grows the column slightly rather than breaking a row.

**`dvh` is written without a `vh` fallback** → deliberate (D3). Browsers lacking `dvh`
predate the mobile toolbar behaviour that makes `vh` wrong, so the fallback would only
serve browsers that do not need it while implying maintenance we are not doing.

## Migration Plan

No data migration; the change is presentational plus one auth-handling correction.

Groups land in order, each verifiable on its own:

1. **Group 1** — tokens, `--field-size`, `dvh`, safe areas, touch targets, hover split.
   Verified by the desktop console pass before anything else proceeds.
2. **Group 2** — sign-in and sign-up. The priority; verified on a real iPhone for the
   zoom and autofill behaviours before groups 3–7 begin.
3. **Groups 3–7** — shell, home, detail, payment slip, profile. Independent of one
   another and can land in any order once 1 and 2 are done.

Rollback is per group: each is a self-contained set of CSS blocks and component edits
with no schema or API surface behind it. The single behavioural change with a blast
radius beyond layout is D7's 401 handling; it is one narrowed `catch` in `RequireAuth`
and reverts alone.

## Open Questions

- Should organizer-authored markdown support images and tables at all? D11 establishes
  that it cannot today. If the answer is yes, it is a sanitiser-allowlist change with
  its own security review, not part of this one.
- `.setup-split`'s 1300px threshold stays as a documented content threshold. If the
  console is later made responsive, that number and the canonical set need
  reconciling — out of scope here.
- The two `HRSearchPicker` call sites differ in whether a cancel control exists
  (Profile passes no `onCancel`). The full-screen step needs a way back on every
  surface; whether Profile's inline picker should also gain a cancel above 768px is
  left open rather than decided silently.
