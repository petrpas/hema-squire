## Why

Squire has two front doors. A fencer lands on a list of tournaments; an organizer
is sent through a second screen, the picker, which lists the same tournaments in a
different shape. Neither door is open to anyone who has not signed in, so the one
thing a public tournament calendar exists to do — be read by somebody deciding
whether to come — requires an account first.

One list, readable by everyone, is both the simpler product and the simpler code.
The organizer's extra power becomes one control on a card rather than a screen of
its own, and the four filter tabs move out of the top bar, which is what made the
bar too crowded to carry the application's actual name.

## What Changes

- **BREAKING** The fencer-facing tournament list and tournament detail become
  readable without authentication. `GET /tournaments/open`, `/held` and the
  fencer-facing detail accept an absent credential and answer with the
  account-bound fields (`my_registration_state`, `organized`) omitted rather than
  refusing with 401. `/tournaments/mine` stays authenticated.
- **BREAKING** The organizer's index, `GET /tournaments`, requires a credential.
  It is the same hole as the detail below — unauthenticated, every draft, every
  bank account — in the listing that feeds the picker, and a public detail that
  withheld those fields while this handed them out would state a rule the
  deployment does not keep.
- **BREAKING** The fencer-facing detail gains a projection of its own. `GET
  /tournaments/{slug}` is already unauthenticated today and already answers with
  the organizer's bank account, feed-token state, accounting sheet, setup report
  and drafts — a hole that has been survivable only because nothing pointed a
  logged-out visitor at it. Declaring the detail public is the moment to close
  it: the fencer-facing answer carries fencer-facing fields and published
  tournaments only, and the console keeps the full payload behind its own path.
- **BREAKING** `/` and `/t/:slug` leave the auth gate. An unauthenticated visit
  renders the list or the detail; it no longer renders Login in place. Every other
  route keeps the gate exactly as it is.
- One list for everyone. The list an organizer sees is the list a fencer sees; no
  role changes its content. What an organizer gets in addition is a **Spravovat**
  control on the card of a tournament they own or sit on the console team of,
  opening that tournament's console.
- The four filter tabs (Announced, Open, Past, Mine) move out of the top bar into
  the top of the main field, centred, above the list.
- The top bar reads three across: "Hema Squire" at the left, the page's title
  centred — "Šermířské turnaje a akce" in Czech, "HEMA Tournaments and Events"
  in English, one line, following the UI language — and the visitor at the
  right.
- Creating a tournament moves into the account menu, where the organizer reaches
  it from anywhere rather than only from the picker.
- The picker stays at `/organizer`, reached from the account menu as it is today.
  It remains the only place drafts and cancelled tournaments are listed, which is
  why it is not replaced by the Spravovat control.
- The default filter tab is resolved from what there is to show, not fixed to Open:
  an account with entries under Mine opens on Mine; otherwise Open when it holds
  anything, and Announced when it does not. `/?tab=…` still names a tab exactly.
- An anonymous visitor sees three tabs, not four — Mine is an account's list and
  is not offered without one — an identity block that offers sign-in in place of a
  name, and a Register action on the detail page that leads to sign-in.

## Capabilities

### New Capabilities
- `public-browsing`: what an unauthenticated visitor may read — which
  fencer-facing endpoints answer without a credential, which fields drop out of
  the payload when there is no account behind the request, which routes render
  without the auth gate, what the shell shows in place of an identity, and how an
  action that needs an account leads to sign-in.

### Modified Capabilities
- `fencer-home`: one list for every role in place of the fencer/organizer split;
  the filter tabs move from the top bar to the main field; the top bar carries the
  application title; the default tab is resolved from the lists rather than fixed
  to Open; the Spravovat control appears on a card an organizer may manage; the
  anonymous variant of the list, the cards and the heading.
- `routing`: `/` and `/t/:slug` are public; the "unauthenticated visits keep their
  destination" rule narrows to the routes that still hold a gate; the landing URL
  `/` no longer names a fixed tab.
- `tournament-admin`: creating a tournament is offered from the account menu, not
  only from the picker.
- `localization`: the UI language of a visitor with no account.

## Impact

- Backend: `app/auth.py` gains an optional-credential dependency;
  `app/routers/tournaments.py` — `open_tournaments`, `held_tournaments`, and the
  fencer-facing detail — take it in place of `FencerDep`, and
  `_fencer_tournament_out` learns to build a payload with no fencer.
  `OpenTournamentOut` fields that describe a bond become optional.
- Frontend: `App.tsx` route table (the public routes leave `RequireAuth`),
  `RequireAuth.tsx` (it must tolerate being absent for a route),
  `FencerShell.tsx` (title in, tabs out), `FencerLayout.tsx` (tab resolution),
  `FencerHome.tsx` (tab band, Spravovat), `AccountMenu.tsx` (create entry,
  anonymous form), `FencerIdentity.tsx` (anonymous form), `TournamentDetail.tsx`
  (anonymous register path), `TournamentPicker.tsx` (create dialog is shared, not
  owned), `routes.ts`, `tokens.css`/`index.css` for the moved band, and the cs/en
  locale bundles.
- No migration: no schema change. Nothing in the data model distinguishes a
  public tournament from a published one; publication already is that line.
