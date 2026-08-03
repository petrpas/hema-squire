import { useTranslation } from "react-i18next";

import type { FieldError as FieldErrorValue } from "./validation";

/** The id a field's control wires into `aria-describedby` — shared so the
 * control and its message always agree on the same id. */
export function fieldErrorId(field: string): string {
  return `field-error-${field.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

/** The `aria-invalid`/`aria-describedby` pair a control spreads onto itself
 * when it holds an error (design: "Marking the invalid field itself"). */
export function invalidProps(field: string, error: FieldErrorValue | undefined) {
  if (!error) return {};
  return { "aria-invalid": true as const, "aria-describedby": fieldErrorId(field) };
}

/** A field's error message: 12px `--stamp` text below the control, stating
 * what happened and, via its interpolated params, the limit that applies —
 * no exclamation mark (design `add-field-validation`). */
export default function FieldError({ field, error }: { field: string; error: FieldErrorValue | undefined }) {
  const { t } = useTranslation();
  if (!error) return null;
  return (
    <p className="field-error" id={fieldErrorId(field)}>
      {t(`validation.${error.code}`, error.params)}
    </p>
  );
}
