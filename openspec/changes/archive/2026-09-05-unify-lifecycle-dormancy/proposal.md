## Why

A tournament with the payments feature off moves every one of its registrations
into the substitute queue on the day after registration closes. Nobody owed
anything; there was nothing to penalise them for.

The cause is that "this registration is not under Squire's clocks" is expressed
twice, with two different reaches, and nothing holds the two together.

`feature_payments` being off suppresses two of the four lifecycle passes —
reminders and expiry — in a branch inside `run_tournament_tick`
(`scheduler.py:345`). Seating settlement deliberately runs anyway, on the stated
grounds that seats and rosters are what every tournament has. That reasoning is
sound; the predicate underneath it is not. `settle_seating` demotes every
registration still in `RESERVED`, on the premise that `RESERVED` means "still
owes money". On a payments-off tournament nothing ever reaches `PAID` — money is
never requested, reconciliation is refused (`bank.py:33`) — so every registration
is `RESERVED` forever, and the premise inverts: the state that was supposed to
select the debtors selects everyone.

`clocks_dormant` (`models.py:590`), added by `issue-imported-registrations` for
registrations issued from an imported row, has the reach the other one lacks. It
is honoured in four places — the reminder pass, the expiry pass, `settle_seating`
and `pending_demotions` — and its own tasks note that the fourth was nearly
missed, because the console's stated count and the settlement's actual selection
are two predicates that must not drift apart.

Proven rather than read. A payments-off tournament with two registrations and
`registration_closes` set to yesterday, given one scheduler tick:

```
seating deadline: 2026-09-04   today: 2026-09-05
TICK RESULT: {'seating_demoted': 2, 'expired': 0, 'reminders': 0, ...}
VS 2601001  state reserved  substitute entries [True]
VS 2601002  state reserved  substitute entries [True]
```

No test covers it. `test_payments_off.py:159` runs the lifecycle over a
payments-off tournament aged sixty days, but asserts only that the registration
is still `RESERVED` — which it is, demoted — and its seating deadline has not
passed.

Now, because a third cause is coming. The automatic/manual registration cut adds
"the organizer keeps this tournament's list, Squire does not" as a further reason
to leave a registration alone. Three independent conditions across four passes is
an eight-way matrix guarding against sending mail to people who registered a
season ago. Unifying two is cheap; unifying three after the fact is a retrofit
into a freshly built path.

## What Changes

- **One predicate on the registration** answers whether Squire runs its
  lifecycle clocks against it, and every lifecycle pass consults that predicate
  and nothing else. The two causes that exist today feed it; the third has one
  place to land.
- **The predicate carries its reason.** Which cause made a registration dormant
  is readable rather than inferred, because "why is this one not expiring?" is
  a question the organizer and the maintainer both ask, and three causes that
  produce one boolean cannot answer it.
- **BREAKING (deliberately): seating settlement no longer demotes a registration
  on a payments-off tournament.** A seat given away for free is not lost for
  non-payment. This changes the behaviour of tournaments that exist today, and
  it is the fix this change is for.
- **`pending_demotions` and `settle_seating` are made to share their selection
  by construction**, not by two comments asking future editors to keep them
  aligned. The console must not promise a count that settlement will not deliver.
- Regression coverage for the demotion itself — the scenario above, asserting
  the substitute flags rather than the registration state, since the state is
  what made the bug invisible.

Not in scope: the automatic/manual axis itself, and any change to what happens
on a tournament that *does* collect. A payments-on tournament's reminders,
expiries and settlement behave exactly as they do today.

## Capabilities

### Modified Capabilities
- `registration`: the reservation lifecycle states one dormancy predicate with a
  recorded cause, replacing the payments-off clause that today reaches only two
  of the four passes; seating settlement is named among what dormancy suspends.
- `tournament-modes`: the payments feature's suspension list gains seating
  settlement — a payments-off tournament expires nothing *and* demotes nothing,
  where today the requirement's "expire no reservation for non-payment" was read
  as leaving settlement alone.
- `seating-queue`: settlement demotes registrations that owe money, so a
  tournament that asks for none demotes nobody; the deadline still settles, it
  just finds nothing to move.

## Impact

**Backend** (`backend/app/`): a derived predicate and its recorded cause on
`Registration` in `models.py`; `scheduler.py`'s four selections and the
`feature_payments` branch in `run_tournament_tick` rewritten to consult it. The
existing `clocks_dormant` column is the storage for the by-origin cause and
keeps its meaning; whether the recorded cause needs a column of its own or is
derivable from the tournament plus that flag is a design question, not a
foregone migration.

**Frontend**: none expected. The console reads `pending_demotions` through its
existing endpoint and the number it states will simply be right.

**Interaction with `issue-imported-registrations`**: that change is implemented
and its dormancy tests pass today. They must keep passing unchanged — an issued
registration is dormant for its own reason, and this change must not alter what
it does, only where the decision is made.

**Risk**: the load-bearing property is that no payments-on tournament changes
behaviour. The test to write is not "the predicate returns True" but a
payments-on tournament running the full lifecycle and producing exactly the
demotions, expiries and mail it produces today.

**Verification**: `pytest` in `backend/`, with attention to
`test_payments_off.py`, `test_issuing.py`, `test_scheduler.py` and the seating
tests; the new regression is the reproduction above turned into a test that
asserts on substitute placements.
