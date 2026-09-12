## Context

See proposal.md — Why. What shapes the approach is the existing code's shape:

- Every route sits inside one `RequireAuth` element in `App.tsx`, and
  `RequireAuth` renders `Login` in place when there is no token. There is no
  notion of a route that renders without one.
- `FencerLayout` is the layout route that owns the tab, fetches the account, and
  fetches the upcoming lists once for both `/` and `/t/:slug`. `FencerShell` is
  the top bar it renders them inside, and it is the bar that currently carries the
  four tabs.
- `resolveTab` in `FencerLayout` is a pure function of the query string, with
  `"open"` as its constant fallback. The default becoming data-dependent is the
  one change that turns a pure resolution into a timed one.
- The backend's fencer-facing list endpoints take `FencerDep`, which raises 401
  on an absent credential, and build each entry through `_fencer_tournament_out`,
  which takes a `Fencer` and cannot be called without one.
- `GET /tournaments/{slug}` already takes no credential at all and already
  returns `TournamentOut` — the console's full payload, drafts included.
- `TournamentPicker` owns `TournamentCreateDialog` in its own file and reaches
  the console through `consolePath`.

## Goals / Non-Goals

**Goals:**
- One list component, one payload shape, for every visitor; role affects one
  control on a card and nothing else.
- An absent credential is a first-class case in the API and in the route table,
  not an error path.
- The default tab is resolved once, from data, without the URL moving and without
  a history entry.
- The fencer-facing detail stops carrying the organizer's configuration.

**Non-Goals:**
- Anonymous *writing* of any kind. Registration, payment, amendment and
  cancellation all stay behind an account.
- Server-side rendering, crawler-facing metadata, sitemaps, per-tournament
  OpenGraph. The list becoming public makes those worth wanting; none is needed
  to make it public, and each is a change of its own.
- Any change to what "published" means, or to the picker's own contents.
- A public *console*. Nothing under `/organizer` loosens.

## Decisions

### 1. Optional credential as a separate dependency, not a nullable `current_fencer`

`current_fencer` keeps raising 401; a sibling `optional_fencer` returns
`Fencer | None`, returning `None` only when no credential was presented and
raising exactly as `current_fencer` does when one was presented and rejected.

Alternatives considered: making `current_fencer` return `Fencer | None` (every
one of its ~70 call sites would have to re-check, and the first one forgotten is
an authorization hole that type-checks); a `?public=1` query flag (the client
would be asserting its own privilege level); swallowing a bad credential into
`None` (a visitor with an expired session would silently read a stripped page and
never be told to sign in — `public-browsing` forbids it for that reason).

Two dependencies, one of which refuses and one of which does not, keeps the
distinction in the type: a handler holding a `Fencer | None` cannot forget that
the `None` exists.

### 2. Bond fields become optional in the payload, not defaulted

`OpenTournamentOut.my_registration_state` and `.organized` become optional and
are omitted when there is no fencer. `_fencer_tournament_out` takes
`Fencer | None` and skips the two per-caller queries when it is `None` — which
also makes the anonymous list cheaper than the authenticated one, not just
equivalent.

The alternative — sending `"none"` and `false` — reads as a claim about an
account that does not exist, and makes an anonymous response indistinguishable
from a signed-in fencer with no bonds. The client needs that distinction: it is
what decides between showing a Register action and showing a sign-in prompt.

On the TypeScript side `my_registration_state?: MyRegistrationState` with
`noUncheckedIndexedAccess`-grade strictness means each read has to narrow, which
is the point: the places that assume a bond are exactly the places that need a
signed-in branch.

### 3. A separate fencer-facing detail schema, not a filtered `TournamentOut`

Add `FencerTournamentOut` holding the fencer-facing subset, and a
`GET /tournaments/{slug}/public` — or the same path answered by a new router
prefix — leaving `GET /tournaments/{slug}` to the console with `FencerDep` plus
`require_console_access` added to it.

Alternatives considered: `response_model_exclude` on the existing route (the
exclusion list lives apart from the schema, so a field added to `TournamentOut`
later is public by default — the failure mode is silent and the wrong way
round); one schema with organizer fields set to `None` for fencers (a client
cannot tell "withheld" from "not configured", and the spec requires absence).

A second schema costs a definition and makes the boundary a thing the type
checker holds. Which of the two routes moves and which is added is a naming
question settled during implementation; what matters is that the fencer's answer
is built by a schema that has no organizer field to leak.

**This is the one part of the change with a security consequence**, so it carries
its own tests: a published tournament's fencer-facing answer asserted field by
field against the allowed set, and a draft's asserted to be not-found.

### 4. Auth becomes a per-route wrapper, and the shell tolerates no account

`App.tsx` grows two groups: the public routes (`/`, `/t/:slug`) outside
`RequireAuth`, and everything else inside it, unchanged. `FencerLayout` moves
outside the gate and must therefore stop assuming a token: it fetches the account
only when one is present, and passes `account: null` down otherwise.

`useAuth()` is an outlet context supplied by `RequireAuth`, so a public route has
none. Rather than let `useOutletContext` return undefined and be narrowed at each
call site, sign-out moves to a small module-level helper (clear the token,
navigate to `/`) that both the gated and the public shell call, and `RequireAuth`
keeps its context for the screens that already read it.

`/?tab=mine` is the one URL whose gate depends on a query parameter rather than a
path. It is handled in the layout — resolving to `mine` without an account
renders `Login` in place, exactly as the gate does — rather than by splitting `/`
into two routes, because both halves are otherwise the same screen.

### 5. The default tab is resolved by the layout, once, and the URL does not move

`resolveTab` keeps its job for an explicit `?tab=`. When there is none, the
layout holds a `defaultTab: HomeTab | null` that is `null` until the lists it
needs have arrived, and the page shows the loading treatment while it is. Once
set, it is never recomputed: the resolution is latched, so a list that empties
under the visitor does not move them.

For a signed-in account the resolution needs the Mine list, which today is
fetched lazily by `FencerHome` only when that tab is selected. The Mine fetch
therefore moves up into `FencerLayout` alongside the upcoming lists — for an
account only, and unconditionally, since its emptiness is what the default turns
on. That is one extra request per visit for a signed-in fencer and none for an
anonymous one. The Past list stays lazy: it takes no part in the default.

Alternatives considered: redirecting `/` to `/?tab=…` once resolved (the URL
would stop meaning "the default", a bookmark would freeze one visit's answer, and
the redirect is a history entry or a replace that fights Back); resolving from
counts on a new summary endpoint (a second source of truth for "is Mine empty",
and the lists are being fetched anyway); resolving server-side (the default is a
UI decision, and the server would need to answer it for a client that has not
asked for a tab yet).

### 6. `Spravovat` is a link inside the card link, so the card stops being one link

A card is a `<Link>` today. A nested interactive element inside an anchor is
invalid HTML and behaves unpredictably, so the card becomes a container: the
heading area is the link to `/t/:slug`, and `Spravovat` is a sibling link to
`consolePath(slug)`. The card keeps its current appearance and its whole-surface
hover.

Alternatives considered: keeping the outer link and calling
`preventDefault`/`stopPropagation` on an inner button (middle-click and
modifier-click stop working, which `routing`'s "navigation targets are links"
forbids); putting the control on the detail page only (the point is to reach the
console without opening the fencer's page first).

Note that the same restructuring is what the manual-mode "registration is held
elsewhere" note already worked around by living on the detail page. That note is
left where it is — this change does not revisit it — but the seam it needed is
now open.

### 7. The create dialog moves to its own file; `AccountMenu` and the picker both open it

`TournamentCreateDialog` moves out of `TournamentPicker.tsx` into
`TournamentCreateDialog.tsx` unchanged, and both the picker and the account menu
render it. The menu shows the entry on the same predicate the picker uses today
(`role !== "fencer" || is_deployment_owner`), which means `AccountMenu` needs the
account it is already given — no new fetch.

`TournamentPicker.tsx` is over 300 lines today and the dialog is most of it, so
this is the split the frontend conventions ask for regardless.

### 8. The tab band moves markup, not behaviour

The band keeps `useTabBand` and the scrolling-band CSS that
`responsive-layout` fixes; only its parent changes, from the bar in
`FencerShell` to the top of the main field in `FencerHome`. Because it leaves the
bar, `FencerShell` no longer needs `tab` or `counts` at all — they become props of
the list, which is where the lists already are.

`TournamentDetail` renders inside `FencerLayout` too, and the band does not
follow it: the detail's own header row stays as it is. This is why the band moves
into `FencerHome` rather than into the layout.

## Risks / Trade-offs

- **A fencer-facing field is forgotten when the detail schema is split, and the
  detail page loses something it shows today.** → The split is driven from
  `TournamentDetail.tsx`'s reads rather than from the schema: every field the
  page touches is in the new schema, and the frontend type checker names any that
  is not. The existing detail tests cover the page's information screen.
- **An organizer field is *kept* in the fencer-facing schema out of caution and
  stays public.** → The spec lists the withheld fields by name, and the test
  asserts the answer's key set against the allowed one, so an extra field fails
  rather than passes.
- **The default-tab resolution shows the loading treatment slightly longer for a
  signed-in fencer**, since it now waits for the Mine list as well as the
  upcoming one. → The two requests are issued together, so the wait is the slower
  of the two rather than their sum. An explicit `?tab=` skips the wait entirely,
  which is what every in-app navigation produces.
- **`/?tab=mine` gating inside the layout is a gate in an unusual place**, and a
  later route change could miss it. → The routing spec's URL table marks the row
  `required`, and the behaviour has its own scenario.
- **Anonymous traffic is now unauthenticated load on the list endpoints**, with no
  rate limit in front of them. → The queries are the ones already served, minus
  the two per-caller ones; the payload is already cached-free and small. Rate
  limiting is deployment-level work and out of scope here, noted rather than
  solved.
- **The list becoming public invites search engines to a client-rendered page
  they will index poorly.** → Accepted. Named as a non-goal above so it is a
  decision rather than an oversight.

## Migration Plan

No schema change and no data migration. Squire is pre-launch, so the API's
breaking parts need no deprecation window:

1. Backend first: `optional_fencer`, the optional bond fields, the fencer-facing
   detail schema and its route. The existing frontend keeps working throughout —
   it sends a credential and reads fields that are still present.
2. Frontend second: route table, shell, tab resolution, card control, menu entry,
   locale strings.

Rollback is a revert of either half independently, in that order.
