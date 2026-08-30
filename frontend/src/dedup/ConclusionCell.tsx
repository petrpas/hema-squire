import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { DedupMember } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import { checkString, type FieldError as FieldErrorValue } from "../validation";
import { asList, choicesFor, fieldKind, unionFor } from "./mergeFields";

/** One cell of a candidate group's conclusion.
 *
 *  A merge is nearly always a choice among what the records already say, so the
 *  cell offers the members' own values one click each, and accepts a typed one
 *  for the case they do not cover (spec `etl-console`, Deduplication candidate
 *  review). A list field is edited by inclusion instead: dropping a discipline
 *  one record claimed is a real decision, and inventing one the tournament does
 *  not offer is not.
 *
 *  Nothing here reaches the API. The whole conclusion is a draft until the
 *  organizer confirms it, so that correcting three cells and accepting is one
 *  entry in the manual-edits log rather than four (design D5).
 */

function check(column: string, raw: string): FieldErrorValue | null {
  switch (column) {
    case "name":
      return checkString(column, "RosterMemberIn.name", raw, { required: true });
    case "club":
      return checkString(column, "RosterMemberIn.club", raw);
    case "nationality":
      return checkString(column, "RosterMemberIn.nationality", raw);
    default:
      return null;
  }
}

export default function ConclusionCell({
  column,
  value,
  members,
  onChange,
}: {
  column: string;
  value: unknown;
  members: DedupMember[];
  onChange: (value: unknown) => void;
}) {
  const { t } = useTranslation();
  const kind = fieldKind(column);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<FieldErrorValue | null>(null);
  const wrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    function outside(event: MouseEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("keydown", dismiss);
    document.addEventListener("mousedown", outside);
    return () => {
      document.removeEventListener("keydown", dismiss);
      document.removeEventListener("mousedown", outside);
    };
  }, [open]);

  if (kind === "boolean") {
    // the table's own two marks, so a merged row reads the same here as it will
    // read on the fencer list once the merge stands
    const on = value === true;
    return (
      <button
        type="button"
        className={on ? "conclusion-chip is-in" : "conclusion-chip"}
        aria-pressed={on}
        title={t("dedup.editValue")}
        onClick={() => onChange(!on)}
      >
        {on ? "✓" : "—"}
      </button>
    );
  }

  if (kind === "list") {
    const included = asList(value);
    const union = unionFor(column, members);
    return (
      <div className="conclusion-list">
        {union.length === 0 && <span className="conclusion-empty">—</span>}
        {union.map((item) => {
          const on = included.includes(item);
          return (
            <button
              key={item}
              type="button"
              className={on ? "conclusion-chip is-in" : "conclusion-chip"}
              aria-pressed={on}
              onClick={() =>
                onChange(
                  on
                    ? included.filter((kept) => kept !== item)
                    : union.filter((entry) => included.includes(entry) || entry === item),
                )
              }
            >
              {item}
            </button>
          );
        })}
      </div>
    );
  }

  const text = value === null || value === undefined || value === "" ? "—" : String(value);
  const choices = choicesFor(column, members).filter((choice) => choice !== text);

  function commit(raw: string) {
    const problem = check(column, raw);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setOpen(false);
    onChange(raw === "" ? null : raw);
  }

  return (
    <div className="conclusion-cell" ref={wrapper}>
      <button
        type="button"
        className="conclusion-value"
        aria-expanded={open}
        title={t("dedup.editValue")}
        onClick={() => {
          setDraft(text === "—" ? "" : text);
          setError(null);
          setOpen((was) => !was);
        }}
      >
        {text}
      </button>
      {open && (
        <div className="conclusion-choices">
          {choices.map((choice) => (
            <button
              key={choice}
              type="button"
              className="conclusion-choice"
              onClick={() => commit(choice)}
            >
              {choice}
            </button>
          ))}
          <input
            className="conclusion-input"
            value={draft}
            autoFocus
            aria-label={t("dedup.ownValue")}
            onChange={(event) => {
              setDraft(event.target.value);
              if (error && !check(column, event.target.value)) setError(null);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") commit(draft);
            }}
            {...invalidProps(column, error ?? undefined)}
          />
          <FieldError field={column} error={error ?? undefined} />
        </div>
      )}
    </div>
  );
}
