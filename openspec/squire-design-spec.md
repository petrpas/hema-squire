# HEMA Squire — design spec "Bureau 1952"

Binding design convention for all Squire UI. This document is the single source
of truth for visual decisions. Implementation must not deviate from it; anything
the spec does not cover gets resolved by amending the spec, not by improvising
in code.

---

## 1. Thesis

Squire is a **bureaucratic app for managing one table**, and its design owns
that. Visual metaphor: **a Czechoslovak government office, ~1948–1955** — the
accounting ledger, the official form (tiskopis), the index card, the rubber
stamp. The mood is sober, papery, precise.

Layered on top: **a quarter dose of Wes Anderson** — pastel accents desaturated
by 50–60 %, symmetry in forms, dry humor in microcopy. Target impression:
*a boring app that occasionally winks.*

Balance of power: **90 % strictly neutral bureau, 10 % personality** — and that
10 % is confined to an explicit budget (section 7). Personality never leaks into
layout, button colors, or component behavior.

Every UI element has a physical antecedent:

| UI element | Antecedent | Consequence |
|---|---|---|
| Table | accounting ledger | hairline rules, tabular numerals, no zebra stripes |
| Form | official form (tiskopis) | numbered sections (I., II., III.), underlined fields |
| Badge / tag | index-card label | rectangle, 2px radius, muted pastel fill |
| Status confirmation | rubber stamp | outline, uppercase, slight rotation |
| Modal | official document frame | double rule instead of a shadow |
| Payment (SPAYD QR) | payment slip | framed block titled "Payment slip" |

## 2. Tokens

The single source of colors and dimensions is `tokens.css`. Components never use
literal hex — variables only.

```css
:root {
  /* Paper */
  --paper:        #F4F0E6;  /* page background — never pure white */
  --paper-raised: #FAF7EF;  /* cards, modals, inputs */
  --paper-shade:  #EFEADC;  /* row hover, highlighted section */

  /* Ink */
  --ink:          #2B2A26;  /* text, strong rules — never #000 */
  --ink-soft:     #55503F;  /* secondary text */
  --ink-faded:    #7A7263;  /* labels, metadata, row numbers */

  /* Rules */
  --hairline:     #D8D1BF;  /* row separators, field frames */
  --rule-strong:  var(--ink); /* 2px rule under table/document headers */

  /* Stamp red — the only saturated color in the app */
  --stamp:        #A34434;  /* primary actions, "Paid" stamp, errors */
  --stamp-hover:  #8C3A2C;
  --stamp-tint:   #EAD6D0;  /* error message background */

  /* Pastel accents (the ¼ of Anderson) — tag and status backgrounds only */
  --seal-green:      #DCE6DA;  /* text always --seal-green-ink */
  --seal-green-ink:  #3D5240;
  --file-blue:       #D9E0E6;
  --file-blue-ink:   #3C4C58;
  --form-yellow:     #EAE0C8;  /* "pending" state */
  --form-yellow-ink: #6B5A2E;

  /* Typography */
  --font-ui:   'IBM Plex Sans', system-ui, sans-serif;
  --font-data: 'IBM Plex Mono', monospace;
  --font-doc:  'IBM Plex Serif', serif;   /* document H1s ONLY */

  /* Geometry */
  --radius: 2px;         /* app-wide maximum; table cells get 0 */
  --border-w: 1px;
  --focus: 2px solid var(--stamp);
}
```

Notes:
- One family (IBM Plex) in three cuts — the superfamily keeps things coherent
  and has full Czech diacritics. Load from Google Fonts, subsets
  `latin,latin-ext`.
- Status semantics: success/active = `--seal-green`, info/category =
  `--file-blue`, pending = `--form-yellow`, error/emphasis = `--stamp`.
- Dark mode is out of scope for v1. The bureau does not glow at night.

## 3. Typography

- Base: `--font-ui`, 14px / 1.5, color `--ink`. Weights 400 and 500 only —
  never 600+; bold text on paper reads as shouting.
- **Labels and table headers:** 10.5–11px, uppercase, `letter-spacing: 0.12em`,
  weight 500, color `--ink-faded`. This is a load-bearing stylistic device —
  apply consistently to every label.
- **Data:** `--font-data` for variable symbols, IDs, amounts, row numbers, and
  revision numbers. 12px.
- **Numerals in tables and amounts:** mandatory
  `font-variant-numeric: tabular-nums`. Amounts right-aligned, currency after
  the number ("1 200 Kč").
- **Document H1** (tournament name, form title): `--font-doc`, 19–22px,
  weight 500. The only place serif appears; nowhere else.
- Date format per locale; Czech style is `21. 7. 1952`, i.e. `D. M. YYYY`.

## 4. Components

### Table (ledger) — the center of the app
- Header: labels per section 3, underlined by `2px solid var(--rule-strong)`.
- Rows: separated by `1px solid var(--hairline)`. **No zebra stripes.**
- Row hover: `background: var(--paper-shade)`. No other hover effects.
- First column: ordinal `001, 002…` in `--font-data`, color `--ink-faded`.
- Cells: `border-radius: 0`, padding 9px vertical, 12px horizontal.
- Table footer: summary on the left ("Registered: N · paid: M"), metadata on
  the right in `--font-data`.

### Form (tiskopis)
- Sections numbered with Roman numerals: "I. Personal details", "II. Category".
- Labels above fields, styled per section 3.
- Inputs: transparent background, bottom rule only `1px solid var(--ink)`;
  focus = bottom rule `2px solid var(--stamp)`. No full-perimeter frames.
- Select and checkbox: frame `1px solid var(--hairline)` on `--paper-raised`,
  2px radius.
- Error message: text `--stamp`, 12px, below the field. Matter-of-fact — what
  happened and what to do: "The variable symbol must be 4–10 digits." No
  exclamation marks.
- The form header carries the form designation (see budget, section 7).

### Buttons
- Primary: fill `--stamp`, text `--paper`, uppercase 12px,
  `letter-spacing: 0.08em`, 2px radius. **Max one per screen.**
- Secondary: outline `1px solid var(--ink)`, text `--ink`, otherwise identical.
- Tertiary: underlined text in `--ink`, no frame.
- In-text links: `--ink` with underline. Never blue.
- Button text = a verb: "Register fencer", "Confirm payment". Not "OK", not
  "Submit".

### Tags and statuses
- Category: pastel background + its matching `-ink` color, 11px, 2px radius,
  padding 2×8px.
- **"Paid" stamp:** outline `1.5px solid var(--stamp)`, text `--stamp`,
  uppercase 10px, `letter-spacing: 0.1em`, rotation −2° to +2° — derived
  deterministically from a hash of the registration ID (same record = same tilt
  on every render).
- Pending payment: plain text in `--ink-faded` + VS in `--font-data`:
  "pending — VS 2604". No badge; waiting is not a status that earns a label.

### Modal and payment slip
- Modal: `--paper-raised`, double frame (`border: 1px solid var(--ink)` +
  `outline: 1px solid var(--ink); outline-offset: 3px`). **No shadow.**
  Backdrop: `--ink` at 0.35 opacity.
- SPAYD QR payment block: framed as a "Payment slip" — heading in label style,
  QR on `--paper-raised`, amount and VS in `--font-data`.

### Empty and loading states
- Empty state: one sentence + an action. See the wink budget.
- Loading: text only ("Leafing through the file…"), no skeleton shimmer, no
  gradient spinners. Plain text or three dots.

## 5. Icons

Sparingly. A bureau writes, it does not draw — where a text label suffices, no
icon is used. When one is needed: a single outline set (Tabler), 1.5px stroke,
16–18px, color inherited from text. Never filled variants, never emoji.

## 6. Interaction and accessibility

- Focus visible everywhere: `outline: var(--focus); outline-offset: 2px`.
- Transitions max 120ms, `background-color` and `border-color` only. No bouncy
  easing, no hover transforms.
- Contrast: all text on paper must pass WCAG AA (`--ink-faded` on `--paper` is
  borderline — use only for 11px+ metadata, never for primary content).
- `prefers-reduced-motion`: disable even the 120ms.

## 7. The wink budget

Personality is permitted **exclusively** in the following places, **max one wink
per screen**:

1. The "Paid" stamp with deterministic rotation (section 4).
2. Empty-state microcopy — e.g. "The file is empty. For now."
   (cs: "Spis je prázdný. Zatím.")
3. Numbering forms as official tiskopisy: "Registration — form no. 3". Form
   numbers are stable and registered in this spec (registration = no. 3,
   account creation = no. 1, tournament creation = no. 2).
4. Document/table footer: "File maintained in good order." (cs: "Spis veden
   řádně.") + revision number in `--font-data`.

Budget rules:
- Winks **never** appear on error paths, failed payments, or in emails about
  money. There the tone is strictly matter-of-fact.
- Microcopy jokes are written per-locale by a native eye, not machine
  translated. If no good variant exists for a locale, neutral text is used.
- A new wink = an amendment to this spec, not an ad-hoc idea in a PR.

## 8. Prohibitions (negative constraints)

This list takes precedence over everything else. The implementation NEVER uses:

- gradients, shadows (`box-shadow`, `text-shadow`), blur, glow
- zebra stripes in tables
- `border-radius` > 2px (no pills, no rounded cards)
- pure white `#FFF` or pure black `#000`
- default blue links or the browser's default blue focus outline
- emoji or filled icons
- skeleton shimmer, spinners, animated progress bars
- toasts with entrance animations; confirmations are static and leave via
  fade-out
- weight 600+, Title Case, exclamation marks in system copy
- more than one saturated color (`--stamp` is the only one)
- any hex value outside `tokens.css`

## 9. Implementation procedure

1. Generate `tokens.css` exactly per section 2 + font loading.
2. Build **one reference screen**: the tournament registration table (document
   header, ledger, footer, stamps). Iterate on it with a screenshot after each
   change until it matches this spec.
3. Declare the reference screen canonical and derive everything else from it
   (forms, tournament list, payment slip).
4. Copy section 8 into the repo's `CLAUDE.md` so it applies to every future
   session regardless of context.
