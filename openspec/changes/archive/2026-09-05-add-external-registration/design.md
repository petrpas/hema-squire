## Context

`add-registrations-kept-by` gives a tournament the ability to say the organizer
keeps its registrations, and makes Squire stop acting on it. What it deliberately
did not do is give the fencer anywhere to go, or tell the organizer what such a
tournament needs before it can be published. That is this change.

Three defects sit together here, and only one of them is about the new axis:

1. No field holds the address of an external registration form. Confirmed by
   grep across `backend/app`, `frontend/src` and `openspec/specs` — the phrase
   appears only in `table-import`'s prose.
2. The public participant list computes `confirmed = registration.state == PAID`
   (`routers/registrations.py:251`). On any tournament Squire does not collect
   for, no registration ever reaches `PAID`, so the list is empty or entirely
   unconfirmed. This is live today on payments-off tournaments, and it
   contradicts `registration`'s own lifecycle requirement, which says such a
   registration is "presented to the fencer as confirmed rather than as awaiting
   payment".
3. `setup_missing` conditions the bank account on `feature_payments` and has no
   branch for who keeps the registrations, so an organizer-kept tournament can be
   published with no way for anyone to reach its registration.

And one payment constraint that is the same shape as (3): the deposit payment
mode assumes a feed that arrives by itself, and nothing checks that one is
configured.

## Goals / Non-Goals

**Goals:**

- A published organizer-kept tournament always tells the fencer where to go.
- A participant list means "who is entered", and says nothing about payment where
  no payment state is guaranteed — on organizer-kept and payments-off tournaments
  alike.
- Mandatory setup asks for what each kind of tournament actually needs.
- The deposit mode is not offered where the intake cannot support it.

**Non-Goals:**

- Rendering the external registration form, proxying it, or knowing anything
  about it beyond its address. Squire links out; it does not integrate.
- Importing from the external form automatically. The roster arrives by
  `table-import` as it does today.
- Migration from organizer-kept back to Squire-kept with a roster intact.
- Any change to what the console does with an imported roster.

## Decisions

### Decision 1: One address field, validated as a URL and nothing more

A single optional URL on the tournament. Not a label-and-link pair, not a list.

The organizer's own registration lives in one place; where it does not, the
description field already exists for prose and carries `organizer-prose`'s
markdown, links included. Adding structure here would be inventing a need.

Validation is that it parses as an absolute `http`/`https` URL. Squire does not
fetch it, does not check that it resolves, and does not warn that it might be
dead — a fetch at save time proves nothing about the moment a fencer clicks, and
a background check is a monitoring feature nobody asked for.

### Decision 2: The list states who is entered, and states how current it is

Where Squire guarantees a payment state — payments on and Squire-kept — the list
behaves exactly as it does today: paid registrations shown confirmed, unpaid
hidden or greyed per the tournament's setting.

Where it does not, the list SHALL show entrants plainly, with no confirmed or
unconfirmed distinction drawn at all, and the unpaid-list setting SHALL NOT
apply — it is a setting about unpaid reservations, and there are none in the
sense it means.

The addition that is not merely a removal: such a list SHALL state **how current
it is**. On a Squire-kept tournament the list is live by construction, and saying
so would be noise. On an imported roster it is as current as the last import,
which may be a week ago, and a visitor reading it as live will conclude the wrong
thing about whether their club-mate is entered. The freshness is derivable —
the tournament knows when it was last imported into.

Alternative considered: keeping the greyed/hidden setting and treating every
entrant as unconfirmed. Rejected: it publishes a claim about payment that Squire
has no basis for, on a tournament whose payments it was never asked to handle.

Alternative considered: showing nothing, on the grounds that Squire cannot vouch
for the list. Rejected: the roster is the most useful thing the public page has,
and the organizer imported it precisely so it could be shown.

### Decision 3: Completeness branches, and the registration window stops being a gate

On an organizer-kept tournament, mandatory setup:

- **requires** the external registration address, because publishing a tournament
  nobody can enter is the failure this change exists to prevent;
- **does not require** a bank account, on the same reasoning the payments feature
  already carries — Squire collects nothing;
- **does not enforce** the registration window. The dates stay, and stay
  editable, because the organizer may well want to state when their own
  registration opens and closes; they simply stop being a gate, since the gate
  they would guard refuses everything already.

Everything else in completeness is untouched. Location, organizers, disciplines
and prices describe what the tournament *is*, and an organizer-kept tournament is
no less a tournament.

### Decision 4: The way out replaces the Register action, and does not sit beside it

Wherever the fencer is offered a Register action today — the Fencer Home card,
the detail page's second tab — an organizer-kept tournament offers a link out
instead, in the same place. Not both, and not a Register button that explains
itself when pressed.

The copy states where registration is kept rather than that Squire's is closed.
"Closed" is a false statement about a window that never existed, and it is the
same reason the availability reason got a member of its own rather than reusing
`closed`.

The link is to somewhere that is not Squire, on a page that is otherwise entirely
Squire's, so it has to read as a destination — and under the design
prohibitions it cannot do that with a default blue anchor.

### Decision 5: The deposit mode requires a configured payment feed

`reservation with deposit` opens a per-registration payment window for the
deposit and expires the reservation when it is not credited in time. A sliding
window per registration can only be answered by a feed that arrives on its own;
a statement uploaded by hand in batches answers a single question after a single
date, not a hundred rolling ones.

So the deposit mode SHALL be offered only where a Fio token is configured. Where
none is, the two remaining modes both fall due at one seating deadline, which
batch intake answers correctly: the check is one pass after a date, not a
continuous watch.

The tournament loses nothing else. Reminders, confirmations and the seating
deadline all still work; what it loses is the sliding per-registration window.

This is a constraint on a *setting*, so it belongs where settings are validated,
and it must be stated in the Setup section rather than only refused on save —
an organizer choosing between three modes should see why one is unavailable, not
discover it when the save fails.

Alternative considered: allowing the deposit mode and converting its windows to
the seating deadline. Rejected: that is silently giving the organizer a different
mode from the one they chose.

### Decision 6: Setup hides what nobody operates, and hides nothing else

On an organizer-kept tournament, the sections governing a registration Squire
does not run — the reminder day, and the window's role as a gate — have no
operator. They follow `setup-navigation`'s existing rule for sections a mode does
not offer.

The line is drawn at *who acts on it*, not at *who might read it*. Prices stay:
they price the export, the totals and what the organizer charges. The seating
deadline stays where the payments feature keeps it, since it is about seats.

## Risks / Trade-offs

**[The participant list changes in public on tournaments that exist today] →
Real, and the owner should see it before it ships.** A payments-off tournament's
public list goes from empty-or-all-grey to a plain list of entrants. That is the
fix, and it is also a visible change to a page the organizer has already shared.
Worth a look at the pilot's own page before deploy.

**[Stating list freshness invites a wrong reading] → State the import moment, not
a judgement.** "As of" a date is a fact. "Up to date" or "may be out of date" is
an assessment Squire cannot make, and would be wrong the moment the organizer
imports again.

**[The external address goes dead and Squire keeps pointing at it] → Accepted,
and out of scope by Decision 1.** Squire does not monitor a URL it does not own.
The organizer who changes their form changes the field.

**[The deposit constraint blocks an organizer who was mid-configuration] → It
binds the mode to the token, so the escape is to configure the token, and the
Setup section says so.** Where a tournament already carries the deposit mode
without a token, it must be reported as an incompleteness naming the token,
rather than silently switched to another mode.

**[Two unrelated fixes ride in one change] → Judged worth it.** The participant
list and the deposit constraint are both "what does this mean where Squire does
not guarantee payment", which is the question this change is answering anyway.
Splitting them would mean touching the same completeness rule and the same list
twice.

## Migration Plan

One Alembic migration adding the nullable URL column. No backfill: every existing
tournament is Squire-kept and needs no address.

A tournament already carrying the deposit mode with no Fio token becomes
incomplete on deploy. That is the intended report, but it must not un-publish
anything — `tournament-admin` already fixes that completeness attaching later
does not retroactively un-publish, and the same treatment applies. Such
tournaments should be identified before deploy and the owner told.

Deploy order: after `add-registrations-kept-by`.

## Open Questions

- Where the address field sits in Setup — with the identity fields, which is
  where a fencer-facing fact belongs, or on the timeline beside the registration
  dates, which is where registration is otherwise discussed. Decided against the
  screen.
- Whether a Squire-kept tournament may also carry an external address — an
  organizer running both paths at once, taking in-app registrations and also
  accepting a club's spreadsheet. Nothing here forbids it, and the field is
  optional, so the question is only whether the public surfaces should offer both
  the form and the link. Deferred until someone asks for it; offering both is not
  hard to add later, and guessing at it now means designing a screen for a
  workflow nobody has described.
