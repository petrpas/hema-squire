## Why

The fencer-facing half of Squire has never been laid out for a phone, and a fencer's
first contact with the app — signing in, creating an account, paying — happens almost
entirely on one. Three faults make that contact worse than merely cramped:

- **Every form control is 14px.** Safari on iOS zooms the viewport on focus for any
  control under 16px and never zooms back, so tapping the e-mail field on the sign-in
  card pushes the rest of the form off-screen.
- **No field in `frontend/src/` carries `autoComplete` or `name`.** iCloud Keychain,
  Google Password Manager and Bitwarden therefore neither fill the sign-in form nor
  offer to save the pair after sign-up. Every visit is typed by hand.
- **`RequireAuth` trusts a token's mere presence and swallows `api.account()` failures
  in an empty handler.** A phone's token is typically weeks old, so reopening a tab
  yields a signed-in shell with a blank name and an empty tournament list rather than
  the sign-in form — indistinguishable from a broken app.

Alongside those, fixed widths (`.login-card` at `22rem`, `.payment-qr` at `10rem`),
`100vh` heights, and a four-tab topbar carrying ~600px of content in one flex row all
overflow a 360–390px screen. And the SPAYD QR flow assumes "payment on the monitor,
phone in hand": on a phone the QR is on the same screen the fencer would scan it
with, and the account number and VS are plain `<strong>` elements that cannot be
copied.

## What Changes

Work is grouped; groups 1 and 2 are a binding order and must land before the rest.

**Group 1 — cross-cutting foundations.** The one group permitted to touch the
organizer console.

- Adopt a single canonical breakpoint set — **480 / 768 / 1024** — recorded as a
  comment in `tokens.css`. Breakpoints are *not* stored in custom properties:
  `@media (max-width: var(--bp-sm))` is silently ignored, so media queries take
  literals.
- Introduce `--field-size: 16px` and apply it to every form control, at every width.
  Body text stays 14px.
- `100vh` → `100dvh` on `.app` and `.login-page`; `70vh`/`88vh` → `dvh` on `.modal`
  and `.wide-card`.
- Add `env(safe-area-inset-*)` padding to edge-pinned chrome.
- Below 768px, grow vertical padding on buttons, tabs and row actions to a 44×44px
  target while holding font-size and letter-spacing fixed.
- Audit the 18 `:hover` rules: wrap the decorative ones in `@media (hover: hover)`;
  give a persistent affordance to any that are the sole signal an action exists.
- Mobile rules live **in each component's own block** in `index.css`, never in a
  trailing "mobile" section. Prefer `min()`, `clamp()`, `flex-wrap` and
  `auto-fit`/`minmax` over media queries.

**Group 2 — sign-in and account creation.** The priority of the whole change.

- `.login-card` `width: 22rem` → `min(22rem, 100%)`; tighter padding below 480px.
- Add the full `autoComplete`/`name`/`inputMode`/`autoCapitalize` attribute set to
  both forms so credential managers fill and save.
- Give each mode's `<form>` a stable `id` (`login-form` / `signup-form`).
- `autoFocus` only above 768px, resolved once at mount via `matchMedia`.
- On `api.account()` returning **401**, clear the token and show `Login` at the same
  URL. Network errors do not sign anyone out.
- Replace the silent `disabled` submit state with a changed button label
  (`login.submitting` / `signup.submitting`, cs + en). Static text, no spinner.
- Reserve vertical space for `.login-error` so the submit button does not jump.
- Below 768px, `HRSearchPicker` inside sign-up becomes a full-screen step overlaying
  the form; form state survives because no route changes.

**Groups 3–7 — fencer shell, home, detail, payment slip, profile.**

- Topbar below 768px: logo + account menu on row one (identity block folds into the
  menu), tab strip on row two as a horizontally scrollable, scroll-snapped band with
  the active tab centred via `scrollIntoView`. `position: sticky`, never `fixed`.
- Workspace padding `1.5rem` → `1rem 0.75rem` below 480px.
- Home cards: `flex-wrap` on the header, smaller/omitted logo below 480px, verified
  chip and long-name wrapping.
- Detail header below 768px: title on its own row, tabs beneath as the same scroll
  band, close action staying level with the title.
- Modals below 768px go full-bleed; `.modal-actions` stack below 480px with the
  destructive action last.
- **Payment slip:** add a "save QR" action and copy actions for account number,
  IBAN, VS and amount — on every width, not just mobile. Below 480px the block
  stacks: QR, then actions, then fields.
- Profile reuses the *same* full-screen HR step component as sign-up.

**Corrections to the brief this proposal supersedes** (each verified against the
tree at `14d9f6e`):

- `add-payments-console-ui/proposal.md:35` claims the frontend has no test runner.
  `package.json` defines `"test": "vitest run"` and `src/` holds 23 test files. That
  line is corrected as part of this change.
- The brief asks for `.prose img { max-width: 100% }` and an `overflow-x` wrapper
  around `.prose table`. **Neither can occur:** `markdown.ts` sanitises with an
  allowlist of `strong, em, del, code, a, p, br, ul, ol, li, h3, h4, blockquote,
  pre, hr` — `img`, `table` and its children are stripped before reaching the DOM.
  Those rules would be dead code. The real narrow-screen risk in `.prose` is long
  unbroken strings (URLs), addressed with `overflow-wrap` instead; `.prose pre`
  already carries `overflow-x: auto`.
- The brief asks to collapse `.param-fields` grids to one column on Profile.
  `.param-fields` is already `flex-direction: column`; only `.detail-subrow
  .param-fields` overrides its gap. No work required.
- The brief states sign-in and sign-up share one `<form>` element. They do not:
  `SignupForm` is a separate component, so React reconciles a component against a
  host element and remounts the DOM node. The autofill confusion comes from the
  total absence of `name` and `autocomplete`, not from a shared form. Distinct form
  `id`s remain worth adding as reinforcement.
- The brief lists four 14px input blocks. There are six, and one is fencer-facing
  and smaller: `.checklist-control input/select` is **13px** and renders in
  `TournamentFace.tsx` — the registration checklist. `.inline-form input` (14px,
  console-only) completes the set.
- Two width media queries already exist and neither is in the canonical set:
  `@media (min-width: 640px)` governs `.match-results` (fencer-facing, reached from
  both sign-up and Profile) and `@media (max-width: 1300px)` governs `.setup-split`
  (console). Both must be reconciled or documented as deliberate exceptions.
- `.stage-control` sets `overflow: hidden`, which blocks the scroll strip in 3.1;
  it becomes `overflow-x: auto; overflow-y: hidden`.
- `index.html` already carries a correct `width=device-width, initial-scale=1.0`
  viewport with no `user-scalable=no`. Nothing to change; the brief's warning is
  preventive only.

## Capabilities

### New Capabilities

- `responsive-layout`: the cross-cutting rules that make every Squire screen usable
  at phone widths — the canonical breakpoint set and its literal-only usage,
  dynamic viewport units, safe-area insets, minimum touch-target sizing, the
  pointer-capability policy for hover affordances, and the narrow-screen scrolling
  tab band.

### Modified Capabilities

- `design-system`: *Typography conventions* — form controls (`input`, `select`,
  `textarea`) move from 14px to 16px at every width while body text stays 14px, with
  the iOS focus-zoom rationale recorded so a later audit does not revert it.
- `fencer-accounts`: sign-in and sign-up become fillable and savable by credential
  managers, report their in-flight state in the submit label, and hold layout steady
  when an error appears.
- `fencer-home`: the identity header's narrow-viewport form (identity folded into the
  account menu, tabs as a scrolling band); the tournament detail shell's narrow form;
  and *In-app payment instructions* gains copyable transfer details and a savable QR
  image, so a fencer on the same device as the QR can still pay.
- `profile-page`: *HEMA Ratings section — find and match* is presented as a
  full-screen step on narrow viewports, sharing one component with sign-up.
- `routing`: *Unauthenticated visits keep their destination* extends to a session
  that expires — a rejected credential returns the visitor to Login at the URL they
  were on, while a network failure does not.

## Impact

**Frontend, styles.** `frontend/src/tokens.css` (breakpoint comment, `--field-size`),
`frontend/src/index.css` (2917 lines; edits distributed across the `.login-*`,
`.app`/`.topbar`/`.stage-control`, `.home-*`, `.detail-*`, `.modal`/`.wide-card`,
`.payment-*`, `.param-field`/`.form-field`, `.checklist-control`, `.match-results`,
`.prose`, `.chips` and `.row-action` blocks).

**Frontend, components.** `Login.tsx` (attributes, split forms, conditional
`autoFocus`, submitting label, error slot, full-screen HR step), `RequireAuth.tsx`
(401 handling), `FencerShell.tsx` (two-row topbar, identity into menu),
`AccountMenu.tsx` (receives identity), `PaymentPanel.tsx` (copy + save-QR actions;
at ~175 lines and two near-duplicate currency branches it needs its slip block
extracted to its own file per the ~300-line rule), `HRSearch.tsx` (hosted by a new
full-screen step wrapper used by both sign-up and Profile), `ProfilePage.tsx`,
`TournamentDetail.tsx`, `FencerHome.tsx`.

**Localization.** New keys in `i18n/cs.json` and `i18n/en.json` for the submitting
labels, the HR step title, and the copy/save-QR actions. `locale-parity.test.ts`
enforces both files stay in step.

**Cross-cutting risk.** Group 1 reaches the organizer console through the shared
`.form-field`/`.param-field` and `.app`/`.topbar`/`.stage-control` blocks. Console
density — particularly `EditableCell`'s `.cell-input` (which inherits its font from
the table, so 16px reaches it only if the table's own size changes) and sheet-table
row height — is verified on desktop before the change is considered done.

**No new dependencies.** No Tailwind, no CSS framework, no bottom-sheet library, no
Playwright. Vanilla CSS in `index.css`, as today.

**No backend changes.** `qr_png_base64` is already delivered by the payment
instructions endpoint; the save action is client-side only.

**Out of scope.** PWA, service worker, offline mode, a mobile console, bottom
navigation, colour or type-scale changes beyond the 16px control size, and any
backend edit.
