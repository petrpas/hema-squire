## Why

On an automatic tournament a fencer can arrive by three roads, and only one of them makes
a registration. An imported row and a hand-entered row are source rows: they hold no
seat until a payment intake issues them, are then seated past capacity, and stay dormant
for good — a second class of entrant inside a tournament whose whole point is that Squire
keeps the list. The Queue phase would have to explain rows that stand above the line
without holding a seat, and settlement would leave them alone whatever they owe.

Import exists for organizers who keep their list elsewhere; that is what manual mode is.
An organizer who began on a Google Form belongs in manual mode, and an automatic
tournament's only other road — the fencer at the door, the paper form — should produce a
registration like any other.

## What Changes

- **Import is a manual-mode road only.** The Import phase is offered on manual
  tournaments alone, and an upload to an automatic tournament is refused with a reason
  naming the mode. Existing automatic tournaments holding imported rows are left as they
  are.
- **A hand entry on an automatic tournament creates a registration at once**, instead of
  a source row waiting to be issued:
  - it is placed against capacity per discipline exactly as an in-app submission is —
    a full discipline queues it, and once seating has settled every discipline does;
  - it carries a variable symbol from the tournament's sequence;
  - it creates no account: the fencer record carries the address if one was typed and
    the address belongs to nobody, and no password;
  - its lifecycle clocks are dormant by origin, a new dormancy cause *entered by hand*:
    no window, no reminder, no expiry, no demotion at settlement;
  - **Squire sends it no mail at all** — not a confirmation, not a promotion, not a
    payment receipt, not a demotion notice. The organizer who entered the fencer is the
    one in contact with them.
  - an address already belonging to a fencer registered on this tournament is refused,
    naming that registration; any other likeness is left to deduplication, as today.
- **A hand entry on a manual tournament is unchanged**: a source row, issued at payment
  intake.
- The hand-entry action stays on the Fencers phase, available whenever the tournament is
  published, including after registration closes and after seating settles — the door
  on the tournament's day is the case it exists for.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `etl-console`: the Import phase is offered only on a manual tournament; manual entry
  branches by mode — a registration on an automatic tournament, a source row on a manual
  one.
- `table-import`: an external table is imported into a manual tournament only.
- `tournament-mode`: an automatic tournament refuses an import; the "not derived from
  contents" example is restated on a manual tournament.
- `registration`: a new requirement for a registration entered by hand; the dormancy
  predicate gains the cause *entered by hand*.

## Impact

- Backend: `routers.manual_api.create_manual_row` branches on the mode — on automatic it
  creates `Fencer` + `Registration` + entries through the same placement code in-app
  submission uses, with `clocks_dormant=True`; `setup.dormancy_cause` distinguishes
  *entered by hand* (dormant, no `source_row_id`) from *issued from import*; every
  fencer mail's guard (`emails._payment_mail_suppressed`, `send_promoted`,
  confirmation) silences a hand-entered registration; the import upload endpoint
  refuses an automatic tournament.
- Frontend: `offeredPhases` drops Import on an automatic tournament; the manual entry
  dialog states on an automatic tournament that it creates a registration, owes the
  tournament's price, and mails nothing; refusal texts.
- i18n: dialog hint, refusal reasons (cs, en).
- Sequencing: its `etl-console` delta is written over `queue-rosters`' phase-order text
  and lands after it.
