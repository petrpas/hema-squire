import { useCallback, useState } from "react";

import type { FieldError } from "./validation";

/** Blur-and-save validation timing shared by every form surface (design
 * `add-field-validation` D5): a field is checked when it loses focus and
 * again on save; nothing is checked on every keystroke, but an error
 * already showing clears the moment its value becomes valid. */
export function useFieldValidation() {
  const [errors, setErrors] = useState<Record<string, FieldError>>({});

  /** Call on blur: runs the check and shows or clears that field's error. */
  const touch = useCallback((field: string, check: () => FieldError | null) => {
    const error = check();
    setErrors((prev) => {
      const next = { ...prev };
      if (error) next[field] = error;
      else delete next[field];
      return next;
    });
  }, []);

  /** Call on change, while the field is still focused: never adds an error,
   * only clears one already showing once the value becomes acceptable. */
  const clearIfValid = useCallback((field: string, check: () => FieldError | null) => {
    setErrors((prev) => {
      if (!(field in prev)) return prev;
      if (check()) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  /** Call on save: runs every check, replaces the whole error set, and
   * returns how many fields are invalid (0 means the section may flush). */
  const validateAll = useCallback((checks: Array<() => FieldError | null>): number => {
    const next: Record<string, FieldError> = {};
    for (const check of checks) {
      const error = check();
      if (error) next[error.field] = error;
    }
    setErrors(next);
    return Object.keys(next).length;
  }, []);

  /** Merges a backend rejection the client could not predict (an
   * already-taken slug) in under the field the response names, exactly like
   * a client-caught error. */
  const applyApiErrors = useCallback((apiFieldErrors: FieldError[]) => {
    if (apiFieldErrors.length === 0) return;
    setErrors((prev) => {
      const next = { ...prev };
      for (const error of apiFieldErrors) next[error.field] = error;
      return next;
    });
  }, []);

  const clearAll = useCallback(() => setErrors({}), []);

  const firstInvalidField = Object.keys(errors)[0] ?? null;

  return { errors, touch, clearIfValid, validateAll, applyApiErrors, clearAll, firstInvalidField };
}
