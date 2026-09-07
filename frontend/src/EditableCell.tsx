import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import FieldError, { invalidProps } from "./FieldError";
import type { FieldError as FieldErrorValue } from "./validation";

export default function EditableCell({
  display,
  label,
  value,
  onSave,
  validate,
}: {
  display: React.ReactNode;
  /** The column's own heading. The cell is a button, and a button whose only
   *  content is an empty column announces itself as "button" and nothing
   *  else — so the name is given here rather than left to the text. */
  label: string;
  value: unknown;
  onSave: (value: string) => void;
  /** Checked on blur/Enter; a returned error keeps the cell in edit mode
   * and shows the message below it rather than committing (design
   * `add-field-validation`). */
  validate?: (raw: string) => FieldErrorValue | null;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<FieldErrorValue | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  const shown = value === null || value === undefined ? "" : String(value);

  function open() {
    setDraft(shown);
    setError(null);
    setEditing(true);
  }

  if (!editing) {
    // A cell that only opens on a double click cannot be edited from a
    // keyboard at all. Enter and F2 open it as well — F2 because that is what
    // a cell in a table opens with everywhere else — and the cell is a tab
    // stop so that those keys can reach it.
    return (
      <button
        type="button"
        className="cell-editable"
        aria-label={
          shown === ""
            ? t("console.cell.editEmpty", { column: label })
            : t("console.cell.edit", { column: label, value: shown })
        }
        onDoubleClick={open}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === "F2") {
            event.preventDefault();
            open();
          }
        }}
      >
        {display}
      </button>
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
