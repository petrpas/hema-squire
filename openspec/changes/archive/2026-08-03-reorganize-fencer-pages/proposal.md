## Why

The fencer-facing pages have accumulated their layout one requirement at a time and now read as three unrelated screens. The home tabs cut the world into Open, Announced and a private Past, so a fencer has no one place holding the tournaments they are in; the cards bury date and place in a run of meta cells; the detail page announces itself with a different header than the list it was opened from; and the registration screen presents a team roster through an inline editor that asks for the same fencer's name twice and prices its lines in running text.

This change settles the fencer's three screens — home list, tournament detail, registration — into one layout with one heading.

## What Changes

**Home heading and tabs**

- The tab set becomes `Announced | Open | Past | Mine`. Announced and Open keep their present meaning (upcoming, published, registration not open / open now). Past becomes a public list of published tournaments already held, rather than the fencer's own history it holds today. Mine lists every tournament the account holds or held a registration for, and every tournament it organizes or organized, upcoming and past alike.
- The request wrote the third tab as `Closed`; per the owner's correction on 2026-08-02 it holds already-held tournaments and is labelled Past. Upcoming tournaments whose registration has closed stay in Announced, as they are today.
- The heading keeps its present shape otherwise: title at the left, tabs beside it, identity and account menu at the right.

**Tournament cards**

- The logo is shown at twice its present size.
- Each card reads as four lines: name, subtitle, date and place in bold, organizers.

**Tournament detail**

- The page adopts the home page's heading verbatim — same title, same four list tabs, same identity block and menu — so it reads as the same page rather than a different one. Its own `Tournament` / `Register` tabs and its close control move to a second row beneath, alongside the tournament name.
- The information block reads as an ordered set of lines: title, subtitle, date · place · qualification, registration opens · registration closes, description.
- The `team event` marker on a discipline gains a left margin so it no longer sits flush against the discipline's name.

**Registration**

- Amounts on a registration's lines — disciplines, teams, and extra services alike — are aligned on one right-hand column instead of running inline. A team's line states its discipline and its name together: `Team Sabre Open: Draci` … `3 000 Kč (120 €)`.
- The roster editor's inline add-and-search block is replaced by an `Add member` control that opens a dialog: one name field, the HEMA Ratings search beside it, one confirmation. A member SHALL occupy exactly one line, both in the dialog's results and on the roster.
- `Amend registration` and `Cancel registration` become a spaced, centered pair of destructive controls in `--stamp`, each asking for confirmation before it acts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fencer-home`: the tab set and what each tab holds; the card's four-line layout and logo size; the detail page's shared heading, its second row, and the order of its information lines; the registration's aligned amounts, its roster dialog, and its destructive controls.
- `registration`: the fencer-facing tournament lists — one for upcoming tournaments, one for tournaments already held, one for the account's own — and what each carries.
- `design-system`: how a destructive action is presented and confirmed.

## Impact

Backend:

- `backend/app/routers/tournaments.py` — the public Past list is new (today's `/mine/past` is scoped to the caller's involvement), and `Mine` needs registrations and organized tournaments across both directions of today.
- `backend/app/schemas.py` — the per-entry marker distinguishing a registration from an organizer relationship.
- No schema change, no migration: every fact these lists need is already stored.

Frontend:

- `frontend/src/FencerHome.tsx` — tabs, lists, card layout.
- `frontend/src/TournamentDetail.tsx` — shared heading, second row, destructive controls, roster dialog host.
- `frontend/src/TournamentFace.tsx` — information line order, team-event marker, aligned amounts.
- `frontend/src/HRSearch.tsx` — reused inside the new member dialog, unchanged in behaviour.
- `frontend/src/index.css`, `frontend/src/i18n/{cs,en}.json`.

Deliberate deviation from the request, flagged for the owner: the detail page keeps a line for the titular organizers, placed after the registration-window line. The request's line list omits them; dropping them would leave the organizers' public credit visible only on the list card.
