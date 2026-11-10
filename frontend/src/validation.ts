// Client-side field checks against the shared bound table (design
// `add-field-validation`), emitting the same closed code set the backend's
// `RequestValidationError` handler produces (`app/errors.py`), plus
// `apiErrors()` to map a caught `ApiError` back into the same shape so a
// backend rejection the client could not predict lands under the field it
// names, exactly like a client-caught one.

import { ApiError } from "./api";
import { FIELD_CONSTRAINTS, type FieldConstraint, MONEY_MAX, PERCENT_MAX } from "./constraints";
import { parseDecimal, parseInteger } from "./numeric";

export type FieldError = { field: string; code: string; params: Record<string, unknown> };

// The closed code set a validation.* message exists for on every layer
// (design D3) — checked for locale-parity in i18n/locale-parity.test.ts.
export const VALIDATION_CODES = [
  "code_taken",
  "code_in_use",
  "below_uses",
  "required",
  "too_short",
  "too_long",
  "out_of_range",
  "not_a_number",
  "must_be_whole",
  "bad_pattern",
  "bad_email",
  "bad_url",
  "bad_link_scheme",
  "bad_enum",
  "bad_date",
  "forbidden_characters",
] as const;

// biome-ignore lint/suspicious/noControlCharactersInRegex: the control characters are what this pattern is for
const ZERO_WIDTH_OR_CONTROL = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\u009f\u200b-\u200d\u2060\ufeff]/;

/** Trims and, for a single-line field, collapses internal whitespace runs —
 * the same normalization the backend's shared string type applies. */
export function normalizeString(
  raw: string,
  { multiline = false }: { multiline?: boolean } = {},
): string {
  const trimmed = raw.trim();
  return multiline ? trimmed : trimmed.replace(/\s+/g, " ");
}

function lengthAndPatternErrors(
  field: string,
  raw: string,
  bounds: FieldConstraint,
  { multiline = false }: { multiline?: boolean } = {},
): FieldError | null {
  if (ZERO_WIDTH_OR_CONTROL.test(raw)) {
    return { field, code: "forbidden_characters", params: {} };
  }
  const value = normalizeString(raw, { multiline });
  if (bounds.minLength !== undefined && value.length < bounds.minLength) {
    return { field, code: "too_short", params: { min: bounds.minLength } };
  }
  if (bounds.maxLength !== undefined && value.length > bounds.maxLength) {
    return { field, code: "too_long", params: { max: bounds.maxLength } };
  }
  if (bounds.pattern !== undefined && value !== "" && !new RegExp(bounds.pattern).test(value)) {
    return { field, code: "bad_pattern", params: { pattern: bounds.pattern } };
  }
  return null;
}

/**
 * Checks a single-line or multiline text field. `field` is the bare name
 * the control (and a backend rejection naming this field) uses — e.g.
 * `"display_name"`; `constraintKey` is the `"Model.field"` key its bound is
 * filed under in `FIELD_CONSTRAINTS` (design D1), e.g.
 * `"TournamentUpdate.display_name"`. The two differ because a mirror-table
 * key is only meaningful with its owning model, while the field name it
 * produces an error for must match whatever the backend calls that same
 * field in its own response (no model prefix there).
 */
export function checkString(
  field: string,
  constraintKey: string,
  raw: string,
  { multiline = false, required = false }: { multiline?: boolean; required?: boolean } = {},
): FieldError | null {
  const bounds = FIELD_CONSTRAINTS[constraintKey] ?? {};
  if (required && normalizeString(raw, { multiline }) === "") {
    return { field, code: "required", params: {} };
  }
  return lengthAndPatternErrors(field, raw, bounds, { multiline });
}

/** As `checkString`, for a numeric field: parses with the tolerant
 * decimal/integer parser, then checks `FIELD_CONSTRAINTS[constraintKey]`'s
 * minimum/maximum. */
export function checkNumeric(
  field: string,
  constraintKey: string,
  raw: string,
  { integer = true, required = false }: { integer?: boolean; required?: boolean } = {},
): FieldError | null {
  if (raw.trim() === "") {
    return required ? { field, code: "required", params: {} } : null;
  }
  const result = integer ? parseInteger(raw) : parseDecimal(raw);
  if (!result.ok) return { field, code: result.code, params: {} };
  const bounds = FIELD_CONSTRAINTS[constraintKey] ?? {};
  return numericBoundsError(field, result.value, bounds);
}

function numericBoundsError(
  field: string,
  value: number,
  bounds: FieldConstraint,
): FieldError | null {
  const min =
    bounds.minimum ?? (bounds.exclusiveMinimum !== undefined ? bounds.exclusiveMinimum : undefined);
  const max =
    bounds.maximum ?? (bounds.exclusiveMaximum !== undefined ? bounds.exclusiveMaximum : undefined);
  if (bounds.exclusiveMinimum !== undefined && value <= bounds.exclusiveMinimum) {
    return { field, code: "out_of_range", params: { min, max } };
  }
  if (bounds.minimum !== undefined && value < bounds.minimum) {
    return { field, code: "out_of_range", params: { min, max } };
  }
  if (bounds.exclusiveMaximum !== undefined && value >= bounds.exclusiveMaximum) {
    return { field, code: "out_of_range", params: { min, max } };
  }
  if (bounds.maximum !== undefined && value > bounds.maximum) {
    return { field, code: "out_of_range", params: { min, max } };
  }
  return null;
}

/** A money field: non-negative, ceiling resolved from the currency it
 * actually carries (design 2.4a) — never a static bound, since a
 * local-currency field's ceiling depends on the tournament it belongs to. */
export function checkMoney(
  field: string,
  raw: string,
  currency: keyof typeof MONEY_MAX,
  { required = false }: { required?: boolean } = {},
): FieldError | null {
  if (raw.trim() === "") {
    return required ? { field, code: "required", params: {} } : null;
  }
  const result = parseInteger(raw);
  if (!result.ok) return { field, code: result.code, params: {} };
  if (result.value < 0) {
    return { field, code: "out_of_range", params: { min: 0, max: MONEY_MAX[currency] } };
  }
  const max = MONEY_MAX[currency];
  if (result.value > max) {
    return { field, code: "out_of_range", params: { min: 0, max } };
  }
  return null;
}

/** A password field: length-checked only, never trimmed or collapsed like
 * other string fields — the backend's password field carries no shared
 * string type either, so a meaningful leading/trailing space is preserved
 * on both layers. */
export function checkPassword(
  field: string,
  constraintKey: string,
  raw: string,
): FieldError | null {
  const bounds = FIELD_CONSTRAINTS[constraintKey] ?? {};
  if (bounds.minLength !== undefined && raw.length < bounds.minLength) {
    return { field, code: "too_short", params: { min: bounds.minLength } };
  }
  return null;
}

/** A percentage field, bounded 0-100. */
export function checkPercent(field: string, raw: string): FieldError | null {
  if (raw.trim() === "") return null;
  const result = parseInteger(raw);
  if (!result.ok) return { field, code: result.code, params: {} };
  if (result.value < 0 || result.value > PERCENT_MAX) {
    return { field, code: "out_of_range", params: { min: 0, max: PERCENT_MAX } };
  }
  return null;
}

const ALLOWED_URL_SCHEMES = new Set(["http:", "https:"]);

/** A link field: must parse as a URL and carry only an http(s) scheme
 * (design: URL fields are parsed and scheme-restricted). */
export function checkUrl(
  field: string,
  constraintKey: string,
  raw: string,
  { required = false }: { required?: boolean } = {},
): FieldError | null {
  const value = normalizeString(raw);
  if (value === "") {
    return required ? { field, code: "required", params: {} } : null;
  }
  const bounds = FIELD_CONSTRAINTS[constraintKey] ?? {};
  if (bounds.maxLength !== undefined && value.length > bounds.maxLength) {
    return { field, code: "too_long", params: { max: bounds.maxLength } };
  }
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return { field, code: "bad_url", params: {} };
  }
  if (!ALLOWED_URL_SCHEMES.has(parsed.protocol)) {
    return { field, code: "bad_link_scheme", params: {} };
  }
  return null;
}

/** Maps a caught `ApiError`'s body to the same `{field, code, params}[]`
 * shape client-side checks emit, so a rejection the client could not
 * predict (an already-taken slug) renders exactly like one caught before
 * the request (design: "A rejection the client could not predict"). */
export function apiErrors(err: unknown): FieldError[] {
  if (!(err instanceof ApiError)) return [];
  const detail = err.detail;
  if (
    detail &&
    typeof detail === "object" &&
    "errors" in detail &&
    Array.isArray((detail as { errors: unknown }).errors)
  ) {
    return (detail as { errors: FieldError[] }).errors;
  }
  return [];
}

/** The checklist items a published tournament is still missing, when that is
 * why a write was refused — `app/setup.py:guard_published_completeness` runs
 * after every mutation of a published tournament, so a save of one section
 * can be refused over an item belonging to another (envelope
 * `{reason: "setup_incomplete", missing: [...]}`). `null` for every other
 * failure, which keeps a caller's existing fallback reachable. */
export function setupIncompleteItems(err: unknown): string[] | null {
  if (!(err instanceof ApiError)) return null;
  const detail = err.detail;
  if (!detail || typeof detail !== "object") return null;
  const envelope = detail as { reason?: unknown; missing?: unknown };
  if (envelope.reason !== "setup_incomplete") return null;
  return Array.isArray(envelope.missing)
    ? envelope.missing.filter((key): key is string => typeof key === "string")
    : [];
}
