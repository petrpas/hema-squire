## Why

The status block's "registrace / jinde" for a tournament whose organizer keeps
its registrations read as unclear; the owner asked for it to go (2026-10-11).

## What Changes

- A tournament in manual mode carries no status block, on its card or on its
  detail's cover. The card says nothing about its registration; the detail
  keeps the way out where the form would be.
- The `home.block.elsewhere` locale key is removed.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `fencer-home`: the landing's card and the detail's cover state nothing for
  an organizer-kept tournament.

## Impact

`StatusBlock.tsx`, `i18n/cs.json`, `i18n/en.json`, `homeCard.test.tsx`; CSS for
the `elsewhere` tone removed.
