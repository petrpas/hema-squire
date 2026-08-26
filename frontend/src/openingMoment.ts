/** The moment registration opens, as the fencer-facing pages measure it.
 *
 *  Every function here is pure and takes its "now" from the caller, because
 *  the device clock is not trusted: the server states its own instant on every
 *  response carrying an opening moment, and the pages count down against that
 *  clock rather than the browser's (design add-registration-open-time D6).
 */

import type { TournamentDetail } from "./api";

/** How far the device clock is *behind* the server's, in milliseconds.
 *  Add it to a device reading to get the server's. Measured once per load;
 *  the network delay it also absorbs is a fraction of a second, far inside
 *  the resolution anything here is presented at. */
export function serverSkewMs(serverTime: string, deviceNow: number = Date.now()): number {
  const stated = Date.parse(serverTime);
  return Number.isNaN(stated) ? 0 : stated - deviceNow;
}

/** The server's clock, as best this device can tell. */
export function correctedNow(skewMs: number, deviceNow: number = Date.now()): number {
  return deviceNow + skewMs;
}

/** The opening instant, or null when the tournament opens on publication.
 *  Parsed from the resolved, offset-bearing instant the server sends — never
 *  folded here from a date, a time and a zone. */
export function openingMomentMs(opensAt: string | null): number | null {
  if (!opensAt) return null;
  const parsed = Date.parse(opensAt);
  return Number.isNaN(parsed) ? null : parsed;
}

/** The last day before the opening, the only span a countdown is shown in
 *  (design D7). A ticking seconds counter beside a date six weeks out is
 *  noise, and a page left open that long should not hold a running timer. */
export const COUNTDOWN_WINDOW_MS = 24 * 60 * 60 * 1000;

export function withinCountdownWindow(remainingMs: number): boolean {
  return remainingMs > 0 && remainingMs <= COUNTDOWN_WINDOW_MS;
}

/** The remaining time as a figure: `MM:SS` under an hour, `H:MM:SS` above.
 *  Never negative — it stops at zero, where the opened state replaces it. */
export function formatCountdown(remainingMs: number): string {
  const total = Math.max(0, Math.ceil(remainingMs / 1000));
  const seconds = total % 60;
  const minutes = Math.floor(total / 60) % 60;
  const hours = Math.floor(total / 3600);
  const pad = (value: number) => String(value).padStart(2, "0");
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`;
}

/** The opening hour as it reads in the tournament's own zone, or null when the
 *  tournament opens at the start of its day and there is no hour worth
 *  stating. `sv-SE` is used only for its 24-hour `HH:MM` shape. */
export function openingHourIn(opensAt: string | null, timezone: string): string | null {
  const at = openingMomentMs(opensAt);
  if (at === null) return null;
  let clock: string;
  try {
    clock = new Date(at).toLocaleTimeString("sv-SE", {
      timeZone: timezone,
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return null;
  }
  return clock === "00:00" ? null : clock;
}

/* ---- the gate mirror ---- */

type RegistrationStatus = "open" | "opens_on" | "closed";

/** Mirrors `setup.registration_availability` on the backend, which stays the
 *  authority: this only decides what the page offers.
 *
 *  The two edges are measured differently, as they are there. Opening is an
 *  *instant* — compared against the server's resolved moment, never re-folded
 *  here from a date, a time and a zone. Closing is a whole *day*, read in the
 *  tournament's own zone (design add-registration-open-time D3, D6).
 *
 *  `now` is the server's clock as `useOpeningMoment` measures it; it defaults
 *  to the device's only for a caller that has no payload to correct against. */
export function registrationStatus(
  detail: TournamentDetail,
  now: number = Date.now(),
): RegistrationStatus {
  const opensAt = openingMomentMs(detail.registration_opens_at);
  if (opensAt !== null && now < opensAt) return "opens_on";
  const closes = detail.registration_closes ?? detail.date;
  if (localDay(now, detail.timezone) > closes) return "closed";
  return "open";
}

/** `now` as a calendar day in the tournament's own zone — the same day the
 *  backend measures a whole-day boundary against. `sv-SE` is used only
 *  because its date format is ISO, which is the shape the stored dates are
 *  compared in. */
function localDay(now: number, timezone: string): string {
  try {
    return new Date(now).toLocaleDateString("sv-SE", { timeZone: timezone });
  } catch {
    // an unknown zone must not break the page; the backend is the authority
    return new Date(now).toISOString().slice(0, 10);
  }
}

/** Amendment is closed by every reason registration is, plus its own,
 * earlier `amendments_close` boundary when set (mirrors
 * setup.amendment_availability on the backend). */
export function amendmentOpen(detail: TournamentDetail, now: number = Date.now()): boolean {
  if (registrationStatus(detail, now) !== "open") return false;
  if (!detail.amendments_close) return true;
  return localDay(now, detail.timezone) <= detail.amendments_close;
}
