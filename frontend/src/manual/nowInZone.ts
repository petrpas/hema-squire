/** The present moment as the wall clock of a given zone, in the shape a
 *  `datetime-local` control takes.
 *
 *  The manual entry dialog opens on now as the tournament reads it, not as the
 *  organizer's laptop does — an organizer entering fencers at a tournament
 *  abroad states its clock, not their own (spec etl-console, Manual entry
 *  fields follow the tournament's structure).
 *
 *  `sv-SE` is used only for its ISO-shaped date and 24-hour clock, as
 *  `openingMoment.ts` already uses it.
 */
export function nowInZone(timezone: string | null, now: number = Date.now()): string {
  const at = new Date(now);
  try {
    const day = at.toLocaleDateString("sv-SE", timezone ? { timeZone: timezone } : {});
    const clock = at.toLocaleTimeString("sv-SE", {
      ...(timezone ? { timeZone: timezone } : {}),
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${day}T${clock}`;
  } catch {
    // an unknown zone must not keep the dialog from opening; the organizer can
    // still state the moment, and the backend is the authority on the default
    return `${at.toISOString().slice(0, 10)}T${at.toISOString().slice(11, 16)}`;
  }
}
