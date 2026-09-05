## Why

A tournament's mode can be changed at any point in its life, including after
publication. That was inherited from the four feature flags, which genuinely can
be — they govern which controls Setup offers, and turning one off hides settings
and changes nothing a fencer experiences. The mode is not like that. It decides
whether Squire owns the roster, and everything downstream of that decision is
built on the answer holding still.

Three consequences of letting it move, each of which has to be handled
separately today:

**Registrations that carry no variable symbol land on a tournament that assumes
they do.** `issue-imported-registrations` is being revised so that a manual
tournament allocates no symbol — a symbol is what Squire tells a fencer to
quote, and on a manual tournament it has told them nothing. Switch that
tournament to automatic afterwards and its roster is a set of registrations with
no symbols on a tournament whose matching resolves through them.

**A published tournament can be made incomplete by a switch.** Publishing a
manual tournament requires the address of its external registration, since a
published tournament nobody can enter and that names no other way in leaves a
fencer nowhere to go. Switching a published tournament to manual afterwards puts
it in exactly that state: complete when it was published, incomplete now, and
every later Setup save refused until the address is supplied. This is not
hypothetical — it happened on this repository's own database today.

**The confirmation exists to count something that cannot be there.** Changing
the mode is confirmed, and the confirmation counts the in-app registrations
Squire would stop managing. A draft accepts no registrations at all: the gate
requires publication. So on the only tournaments the switch would remain
available for, the count is always zero and the warning always says the same
thing.

Publication is already the moment this product freezes what must not move
afterwards. It is one-way — no action ever clears it. The variable-symbol series
stops being editable at the first registration. A discipline's identity freezes
once anything references it. The mode belongs in that company.

## What Changes

- **A tournament's mode SHALL be fixed at publication.** It is chosen when the
  tournament is created and may be changed while it is a draft; publishing
  settles it.
- **The attempt is refused with a stated reason**, not silently ignored, so an
  organizer who tries learns why rather than wondering whether it took.
- **The settings surface states the mode instead of offering it** on a published
  tournament, alongside the payments setting and the features, which stay
  changeable. A control that answers a refusal is worse than no control.
- **The confirmation for changing the mode goes.** It counted in-app
  registrations, and a draft can hold none; what remains to say about a change
  belongs in the surface's own copy, not in a dialog that always says zero.
- **BREAKING:** an organizer who publishes with the wrong mode cannot change it.
  Cancelling and recreating is the way back, as it is for a slug or a variable
  symbol series.

Not in scope: the payments setting, which stays changeable after publication. An
organizer may reasonably start collecting money partway, or stop; nothing
downstream assumes it holds still, and `payments` already fixes what turning it
off suspends and what it retains.

## Capabilities

### Modified Capabilities
- `tournament-mode`: the mode is fixed at publication; changing it is refused on
  a published tournament with a stated reason; the confirmation requirement is
  removed, its whole content having been a count that can only be zero.
- `setup-navigation`: the settings surface states the mode rather than offering
  it once the tournament is published, and offers the other two tiers as before.
- `tournament-admin`: setup completeness gains the guarantee this makes possible
  — a published tournament cannot be made incomplete by a change of mode.

## Impact

**Backend** (`backend/app/`): a refusal in the `registrations-kept-by` handler in
`routers/tournaments.py` when `published_at` is set. No model change, no
migration; the column keeps its meaning and every existing value is already
valid.

**Frontend** (`frontend/src/`): the mode tier in `TournamentSettingsDialog.tsx`
becomes a statement rather than a radio group on a published tournament, and the
confirmation branch for a mode change goes with the requirement. `SettingsSection`
already states the mode in words and needs no change.

**What this removes rather than adds.** The manual-to-automatic migration
question, raised and deferred twice, stops existing. The
`add-manual-paid-marking` risk about switching afterwards is untouched, because
that one is about payments.

**Risk**: an organizer publishes in the wrong mode and is stuck with it. The
mitigations are that the choice is made on the creation surface with each
answer's consequence stated beside it, that publication is a deliberate act
behind its own tab, and that a draft is freely switchable for as long as it is a
draft. The cost is real and it is the price of the three problems above.

**Verification**: `pytest` for the refusal and for a draft still switching
freely; `vitest` for the tier reading as a statement once published; and a check
that no existing test relied on switching a published tournament's mode.
