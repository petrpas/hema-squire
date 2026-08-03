import { useEffect, useRef, useState } from "react";

import FieldError, { invalidProps } from "./FieldError";
import type { FieldError as FieldErrorValue } from "./validation";

export default function EditableCell({
  display,
  value,
  onSave,
  validate,
}: {
  display: React.ReactNode;
  value: unknown;
  onSave: (value: string) => void;
  /** Checked on blur/Enter; a returned error keeps the cell in edit mode
   * and shows the message below it rather than committing (design
   * `add-field-validation`). */
  validate?: (raw: string) => FieldErrorValue | null;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<FieldErrorValue | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  if (!editing) {
    return (
      <div
        className="cell-editable"
        onDoubleClick={() => {
          setDraft(value === null || value === undefined ? "" : String(value));
          setError(null);
          setEditing(true);
        }}
      >
        {display}
      </div>
    );
  }

  function commit() {
    const problem = validate?.(draft) ?? null;
    if (problem) {
      setError(problem);
      return;
    }
    setEditing(false);
    const original = value === null || value === undefined ? "" : String(value);
    if (draft !== original) onSave(draft);
  }

  return (
    <>
      <input
        ref={inputRef}
        className="cell-input"
        value={draft}
        onChange={(event) => {
          setDraft(event.target.value);
          if (error && !validate?.(event.target.value)) setError(null);
        }}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") commit();
          if (event.key === "Escape") setEditing(false);
        }}
        {...invalidProps("cell", error ?? undefined)}
      />
      <FieldError field="cell" error={error ?? undefined} />
    </>
  );
}
