// Tolerant numeric parsing (design `add-field-validation` D2): accepts `,`
// or `.` as the decimal separator interchangeably, tolerates space/NBSP/
// narrow-NBSP thousands grouping, and rejects anything else as malformed
// rather than silently truncating. Mirrors backend/app/fieldtypes.py's
// `_coerce_decimal`/`_coerce_int` exactly, so a value parses the same way on
// both layers — proven in numeric.test.ts (task 4.5).

export type ParseResult =
  | { ok: true; value: number }
  | { ok: false; code: "not_a_number" | "must_be_whole" };

const GROUPING_CHARS = [" ", " ", " "];
const NUMBER_RE = /^-?\d+(?:[.,]\d+)?$/;

function normalizeNumericText(raw: string): string | null {
  let text = raw;
  for (const ch of GROUPING_CHARS) text = text.split(ch).join("");
  text = text.trim();
  if (!text) return null;
  const commaCount = (text.match(/,/g) ?? []).length;
  const dotCount = (text.match(/\./g) ?? []).length;
  if (commaCount + dotCount > 1) return null;
  if (commaCount === 1) text = text.replace(",", ".");
  if (!NUMBER_RE.test(text)) return null;
  if (text.startsWith(".") || text.startsWith("-.") || text.endsWith(".")) return null;
  return text;
}

/** Accepts a decimal comma or point, tolerates thousands grouping, rejects
 * anything malformed as `not_a_number` — never returns `NaN`. */
export function parseDecimal(raw: string): ParseResult {
  const text = normalizeNumericText(raw);
  if (text === null) return { ok: false, code: "not_a_number" };
  const value = Number(text);
  if (!Number.isFinite(value)) return { ok: false, code: "not_a_number" };
  return { ok: true, value };
}

/** As `parseDecimal`, but rejects a non-zero fractional part as
 * `must_be_whole` rather than rounding it away. */
export function parseInteger(raw: string): ParseResult {
  const result = parseDecimal(raw);
  if (!result.ok) return result;
  if (!Number.isInteger(result.value)) return { ok: false, code: "must_be_whole" };
  return result;
}

/** Writes a stored numeric value back into a control using the active
 * locale's decimal separator, so a value round-trips through the form
 * unchanged (a Czech UI reads back "25,5", not "25.5"). */
export function formatForLocale(value: number, locale: string): string {
  return value.toLocaleString(locale, { maximumFractionDigits: 20, useGrouping: false });
}
