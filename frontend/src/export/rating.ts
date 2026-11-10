import type { FieldError } from "../validation";

/** A rating is a number, or nothing — which states that the register has
 *  nobody by that name, and is not the same as removing the correction.
 *
 *  Shared by the two tables that offer the cell: an individual discipline's
 *  roster and a team discipline's fighters. */
export function validateRating(raw: string): FieldError | null {
  if (raw.trim() === "") return null;
  const value = Number(raw.replace(",", "."));
  return Number.isFinite(value) ? null : { field: "rating", code: "not_a_number", params: {} };
}
