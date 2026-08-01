## Context

The console Setup phase renders `SetupPanel` as the sole child of `.workspace`
(`Console.tsx:203`), a single scrolling column capped at `max-width: 60rem`. Each
Setup section saves independently and calls `onSaved`, which makes `Console` refetch
the tournament detail and pass a fresh `detail` object down.

The tournament's two fencer-facing faces both live in `TournamentDetail.tsx` (993
lines). Its default export is a page shell — account menu, back button, loading
guard — that switches between an `information` screen (`InfoHeader`,
`DisciplinesInfo`, `OtherActionsInfo`, plus the fencer's own registration panel) and
a `register`/`amend` screen (`RegistrationForm`). All of those are module-private
functions today; nothing outside the file can render them.

The backend needs nothing. `POST /api/tournaments/{slug}/price-preview`
(`registrations.py:253`) resolves the selection and computes totals without touching
the session, without an authenticated fencer, and without checking the registration
window — it is already safe to drive from the console.

Constraint of record: `CLAUDE.md` / `openspec/squire-design-spec.md` §8 prohibitions
are binding — no shadows, no radius above 2px, no second saturated colour, no
emoji or filled icons, no weight 600+.

## Goals / Non-Goals

**Goals:**

- The organizer sees, beside the settings they are editing, exactly what a fencer
  sees — both faces of the tournament.
- One implementation of each face, shared by fencer view and preview, so the preview
  cannot drift.
- The previewed form is explorable (selections, quantities, options, running total)
  and provably incapable of creating a registration.

**Non-Goals:**

- Reflecting unsaved settings edits. The preview shows the saved, published state.
- Any change to what fencers see or to their information → register/amend flow.
- Any backend, schema, or endpoint change.
- Editing the tournament from inside the preview.

## Decisions

### D1 — Extract the two faces into `TournamentFace.tsx`; import them back

Move `LEGACY_WEAPONS`, `ACTION_CATEGORIES`, `registrationStatus`, `amendmentOpen`,
`InfoHeader`, `ScheduleLines`, `DisciplinesInfo`, `OtherActionsInfo`, `ChecklistRow`,
`ItemControls` and `RegistrationForm` from `TournamentDetail.tsx` into a new
`frontend/src/TournamentFace.tsx`, exported. `TournamentDetail.tsx` imports them back
and keeps only the page shell and the fencer-only pieces (`PaymentPanel`,
`RegistrationStateTag`, `RegistrationLines`, `RegistrationSummary`,
`RegistrationPanel`). The preview imports from `TournamentFace.tsx`.

*Alternative rejected:* simply adding `export` to the existing functions and letting
the preview import from `./TournamentDetail`. It is a smaller diff and creates no
import cycle, but it makes a routed page component the public home of shared UI,
which is exactly the arrangement that later tempts someone to copy markup rather than
import a page. Extraction also leaves `TournamentDetail.tsx` at a reviewable size.

`RegistrationPanel` and friends stay behind deliberately: they render *a fencer's own
registration*, which the preview has no counterpart for.

### D2 — Non-submittability is enforced by the prop type, not a flag

`RegistrationForm` takes a discriminated `mode` prop in place of today's
`initial` + `onRegistered` pair:

```ts
type FormMode =
  | { kind: "register"; onRegistered: (r: RegistrationDetail) => void }
  | { kind: "amend"; initial: RegistrationDetail; onRegistered: (r: RegistrationDetail) => void }
  | { kind: "preview" };
```

In `preview` mode there is no `onRegistered` to call and the submit branch is not
rendered at all; the spec's "no interaction creates a registration" becomes a
type-level fact rather than a runtime promise a later edit could break. The two
existing call sites in `TournamentDetail` map onto `register` and `amend`.

*Alternative rejected:* a `preview?: boolean` prop that disables the button. Smaller,
but leaves `submit()` reachable and one `disabled` removal away from firing.

### D3 — The preview pane owns its own data fetch

`SetupPreview` receives `detail` and `slug` as props from `SetupPanel` (which already
has both) and fetches `api.availability(slug)` itself, re-fetching whenever `detail`
changes identity. `Console` and `SetupPanel`'s existing sections are untouched.

Refresh therefore needs no new mechanism: a section save → `onSaved` → `Console`
refetch → new `detail` object → preview re-renders and re-fetches availability. Tab
selection and the organizer's trial selections live in component state that is not
remounted, so they survive the save (`SetupPanel` carries no `key`).

### D4 — Trial selections are pruned against the current detail

`RegistrationForm` keeps selections in `extraQty` / `extraOption` keyed by extra-item
id and in a `Set` of discipline codes, initialised once. When the organizer deletes an
item or discipline and saves, a stale key would be sent to `price-preview`, which
answers 422 for an unknown id (`_resolve_selection`) and would blank the total. On
`detail` change the form drops selection keys that no longer exist in
`detail.extra_items` / `detail.disciplines`. This is correct for the fencer view too
— it just cannot happen there, because a fencer's `detail` does not change mid-form.

### D5 — Layout: a two-pane split inside `.workspace`, stacking when narrow

Setup renders `<div class="setup-split">` containing the existing `.setup-panel` and
the new `.setup-preview`, each scrolling independently (`overflow-y: auto`,
`min-height: 0`). `.setup-panel` keeps its `max-width: 60rem`; the preview takes the
remaining width with its own sensible cap, separated by a single hairline
`border-left` — no shadow, no card, per the prohibitions. Below a breakpoint the
split becomes `flex-direction: column` and the preview follows the settings at full
width.

Only the Setup phase is wrapped; other phases keep `.workspace` exactly as it is.

### D6 — Tabs reuse the existing `.stage-control` vocabulary

`FencerHome` already renders a tab row as `<nav class="stage-control">` with an
`active` class on the selected button (`FencerHome.tsx:186`). The preview uses the
same markup and class, so the change introduces no new visual pattern. Labels come
from new i18n keys (`preview.tabs.face`, `preview.tabs.form`) in both `cs.json` and
`en.json`.

### D7 — The preview is marked as such in words, not decoration

A small-caps heading names the pane as a preview, and the submit control is replaced
by a static line of copy (`preview.cannotSubmit`). No badge colour, no icon, no
emoji — the design spec allows exactly one saturated colour and it is spent
elsewhere. Copy stays sentence case, no exclamation marks.

## Risks / Trade-offs

- **The preview lags one Save click behind the organizer's typing** → Accepted, and
  in fact the point: the preview's guarantee is that it shows what fencers can see
  right now. D4's pruning keeps it coherent immediately after each save.
- **Extraction touches a 993-line file that has no test coverage of its own** →
  The move is mechanical (cut, paste, add `export`, add imports); correctness is
  checked by `tsc` plus a manual pass over the fencer view's three states
  (information, register, amend) before and after.
- **`RegistrationForm` gains a third mode, raising its branch count** → The union
  keeps the branches explicit and exhaustive; `amending` becomes
  `mode.kind === "amend"` rather than an inferred `initial !== undefined`.
- **Two independently scrolling panes on a laptop screen can leave each pane short**
  → The stacking breakpoint is chosen against the settings pane's existing 60rem
  cap, so a viewport that cannot give the preview a usable column stacks instead of
  squeezing.
- **Price-preview traffic from the console** → One debounced call per selection
  change (the existing 300 ms debounce), read-only, unauthenticated-path-equivalent.
  Negligible.

## Migration Plan

Not applicable — frontend-only, no data, no persisted state, no API contract change.
Reverting the commit restores the previous Setup layout exactly.

## Open Questions

None. The three decisions that shaped this change — refresh-on-save rather than live
drafts, an interactive but non-submitting form, and tabs confined to the preview pane
— were settled with the project owner before drafting.
