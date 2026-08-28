## 1. The formatter

- [x] 1.1 Add `frontend/src/momentText.ts` with a pure `registeredMoment(value: string | null, timezone: string | null): string` returning the em dash for `null`, the day plus 24-hour clock otherwise (design D1, D4)
- [x] 1.2 Handle the offset-bearing case: parse with `Date`, format the day with `toLocaleDateString("cs", { timeZone })` and the clock with `toLocaleTimeString("sv-SE", { timeZone, hour: "2-digit", minute: "2-digit" })`, falling back to the browser zone when `timezone` is null or `Intl` throws (design D2)
- [x] 1.3 Handle the zone-less case: detect the absence of `Z` or `±HH:MM`, re-spell the stated date and time without passing through `Date`, and return the raw string when it cannot be split (design D3, D6)
- [x] 1.4 Add `frontend/src/momentText.test.ts` covering the spec scenarios — an offset-bearing moment read the same from two browser zones, two moments on one day, a bare local timestamp shown unshifted, and `null` giving the em dash — plus the unknown-zone and unparseable-string fallbacks; verify with `npm test`

## 2. The fencer table

- [x] 2.1 Thread `timezone` from `Console`'s `detail` into `CellDisplay` as a prop, defaulting to `null` while `detail` has not arrived (design D5); verify the console still renders on first paint with `npm run build` clean and the app loading
- [x] 2.2 Replace the `registered_at` branch of `CellDisplay` with a call to `registeredMoment`, leaving the `expires_at` / `paid_at` branches as they are; verify a Load-phase row shows day and clock and an unparsed import row still shows the em dash

## 3. The queue view

- [x] 3.1 Rename the `queue.registeredAt` placeholder from `{{date}}` to `{{moment}}` in `frontend/src/i18n/cs.json` and `en.json`, leaving the visible wording alone (design D7); verify `npm test` passes, locale parity included
- [x] 3.2 Give `QueuePanel` a `timezone: string | null` prop and pass `detail?.timezone ?? null` from `Console`'s `QueuePanel` call site (design D5); verify with `npx tsc --noEmit`
- [x] 3.3 Render each entry's `registered_at` through `registeredMoment` in `entryLine`, leaving the panel's local `date()` helper serving `seating_deadline` and `settledOn`; verify an entry line reads day plus clock and the deadline line still reads a day alone
- [x] 3.4 Add a `QueuePanel` test asserting two entries registered minutes apart on one day show different clock times; verify with `npm test`

## 4. Checks

- [x] 4.1 Run `npm run lint`, `npx tsc --noEmit` and `npm test` in `frontend/` and verify all pass
- [x] 4.2 Open the console's Load phase and Queue phase against a tournament with registrations recorded at different hours and verify both state the moments in the tournament's zone, and that the fencer table's times align in the column (spec: `etl-console`, `seating-queue`) — confirmed by the organizer; the local dev database holds no registrations, so the automated cover is `consoleCells.test.tsx` and `QueueEntryLine.test.tsx`
