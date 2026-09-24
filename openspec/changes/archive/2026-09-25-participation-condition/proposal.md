## Why

Squire places each discipline of a registration on its own: a fencer entering Longsword
and Sabre, with Sabre full, is seated in Longsword and queued in Sabre. For one kind of
fencer that is right — one discipline is reason enough to come. For another it is a seat
they will not use and a bill for it: they travel only if they fence both. Squire cannot
tell them apart, so it treats everyone as the first kind. Every rule that meets a
registration seated in part and queued in part — what it owes, what a payment for it
means, whether promoting one placement is a favour — keeps running into that guess. The
next change, letting a paying substitute take a free place, cannot be stated without an
answer to it.

## What Changes

- **A registration may carry a participation condition**: a set of its individual
  disciplines it attends only together. The system holds a general set; the registration
  form offers it as one tick — *"Pojedu jen, pokud dostanu místo ve všech vybraných
  disciplínách"* — which sets the condition to every individual discipline selected, or
  to none. The tick is offered only where at least two individual disciplines are
  selected. Unticked is today's behaviour, and every existing registration has no
  condition.
- **A registration whose condition is not met waits whole.** If any discipline of the
  condition has no free place, every placement of the registration is queued — including
  ones with free places, and including disciplines outside the condition — and it owes
  nothing. It holds no seat anywhere while it waits.
- **A met condition seats together.** Where every discipline of the condition has a free
  place, they are seated together; disciplines outside the condition are then placed on
  their own, as today.
- **Promotion and return treat the condition as one.** Promoting a waiting conditional
  registration seats every discipline of the condition at once and is offered only while
  all of them have a free place. Returning any placement of a met condition returns the
  whole registration to the queue.
- **The Queue rosters say it.** A queued row of a conditional registration states which
  other disciplines it waits for, and carries the promote arrow only when all of them
  are free — so the rows the organizer can seat now are the ones with an arrow.
- **Amendment re-places.** Ticking the condition, or adding a full discipline to it,
  queues the whole registration; the form states this before submitting. An amendment
  that would queue a registration holding credit is refused, directing the fencer to the
  organizer — money is not put in the queue by a fencer's own edit.
- **Hand entry** carries the same tick.
- Teams are outside the condition.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `registration`: a new requirement for the participation condition (form tick,
  placement, amendment); per-discipline independence in **Capacity and substitutes**
  becomes the rule for a registration without a condition.
- `seating-queue`: a new requirement that a conditional registration is promoted and
  returned as one, and how the queue view states and gates it.
- `etl-console`: the manual entry dialog offers the tick.

## Impact

- Backend: `RegistrationDiscipline.conditional` (bool, default false; migration);
  one placement function shared by submission, amendment and hand entry replacing the two
  `is_substitute = slug in full` sites; `admit_substitute` and `return_to_queue` act on
  the condition set; `sheet.base_rows` carries the condition; schemas for registration
  submission, amendment, hand entry and outputs; `export_json` next schema version.
- Frontend: the tick in the registration and amendment forms and the manual entry
  dialog with its consequence text; the fencer's registration detail states the
  condition and what it waits for; Queue roster marker and arrow gating.
- i18n: tick label, explanations, marker, refusal (cs, en; backend mail catalogs where
  the confirmation states the condition).
- Sequencing: after `demotion-hardening`, `queue-rosters` and `manual-entry-registers`
  (its deltas extend their text); before `paying-substitutes`, which relies on it.
