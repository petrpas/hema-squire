/** How a stored registration moment reads on an organizer's screen.
 *
 *  Pure, like `openingMoment.ts`, and for the same reason: the rules about
 *  which zone a moment is read in are worth testing away from a component.
 *
 *  A moment reaches here in one of two shapes, and the difference matters.
 *  A registration carries an offset — the backend stores an aware UTC instant
 *  and sends it in full — so it can be resolved and re-read in the
 *  tournament's zone. An imported row carries whatever the extractor lifted
 *  out of the spreadsheet, which states no zone at all; that one is spelled
 *  back out as written, because assuming a zone would invent a fact the file
 *  never stated (design show-register-times D3).
 */

/** What the console shows where nothing was recorded. */
const ABSENT = "—";

/** A trailing `Z` or `±HH:MM` — the whole difference between an instant and a
 *  bare wall clock. */
const OFFSET = /(?:Z|[+-]\d{2}:?\d{2})$/i;

/** The head of an ISO-shaped stamp: the parts that can be spelled back out. */
const STATED = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/;

/** The day and the clock together, on the 24-hour scale to the minute, read
 *  in `timezone` when the moment carries one and `timezone` is a zone `Intl`
 *  knows. Null gives the em dash the table uses for an absent value; anything
 *  unreadable gives itself back, since a garbled import stamp is something
 *  recorded and the organizer needs to see it (design D6). */
export function registeredMoment(value: string | null, timezone: string | null): string {
  if (value === null) return ABSENT;
  if (!OFFSET.test(value)) return stated(value);
  const at = Date.parse(value);
  if (Number.isNaN(at)) return value;
  return `${day(at, timezone)} ${clock(at, timezone)}`;
}

/** A zone-less stamp, re-spelled: its day in the display shape, its clock
 *  exactly as written. The `Date` here is built from the calendar parts and
 *  read back in the same zone it was built in, so it never resolves the
 *  stamp to an instant — it only spells a date the way `cs` spells dates. */
function stated(value: string): string {
  const parts = STATED.exec(value);
  if (!parts) return value;
  const [, year, month, date, hour, minute] = parts;
  const calendar = new Date(Number(year), Number(month) - 1, Number(date));
  return `${calendar.toLocaleDateString("cs")} ${hour}:${minute}`;
}

function day(at: number, timezone: string | null): string {
  return zoned(timezone, (options) => new Date(at).toLocaleDateString("cs", options));
}

/** `sv-SE` is used only for its plain 24-hour `HH:MM` shape, as
 *  `openingHourIn` already does. */
function clock(at: number, timezone: string | null): string {
  return zoned(timezone, (options) =>
    new Date(at).toLocaleTimeString("sv-SE", { ...options, hour: "2-digit", minute: "2-digit" }),
  );
}

/** Formats in the tournament's zone, falling back to the reader's own when
 *  there is no zone yet or `Intl` does not know the one it was given. A cell
 *  framed in the wrong zone beats a cell that throws. */
function zoned(
  timezone: string | null,
  format: (options: Intl.DateTimeFormatOptions) => string,
): string {
  if (timezone) {
    try {
      return format({ timeZone: timezone });
    } catch {
      // an unknown zone must not break the table
    }
  }
  return format({});
}
