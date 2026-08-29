import { IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { NetChange, SheetRow } from "./api";
import { registeredMoment } from "./momentText";

/** The manual-edits log: what the phase's rules made the table differ from the
 *  source data, one entry per changed cell (spec `edit-rules`, Audit of applied
 *  changes). Entries read in the organizer's words, naming rows by the fixed
 *  number the table gives them (spec `etl-console`, Readable manual-edits
 *  log). */

type Translate = (key: string, options?: Record<string, unknown>) => string;

const VERDICT_KEYS: Record<string, string> = {
  confirmed: "match.verdict.confirmed",
  found: "match.verdict.found",
  none_found: "match.verdict.noneFound",
  proposed: "match.verdict.proposed",
  unknown: "match.verdict.unknown",
};

/** A row as the table names it: its fixed number and the fencer on it. The
 *  number comes off the row, never off its position in the list, so an entry
 *  keeps naming the same fencer after a deletion or a merge moves rows about
 *  (spec `etl-console`, Readable manual-edits log). A row the table no longer
 *  holds is said to be gone rather than shown by its id. */
export function rowText(target: unknown, rows: SheetRow[], t: Translate): string {
  const row = rows.find((candidate) => candidate.id === target);
  if (row === undefined) return t("rail.edit.unknownRow");
  return t("rail.edit.row", { number: row.number ?? "—", name: row.name });
}

/** One side of an assignment, formatted as the table's cell formats it. */
export function valueText(
  field: string,
  value: unknown,
  timezone: string | null,
  t: Translate,
): string {
  if (value === null || value === undefined || value === "") return t("rail.edit.empty");
  if (field === "match_verdict" && typeof value === "string" && value in VERDICT_KEYS)
    return t(VERDICT_KEYS[value]);
  if (field === "registered_at") return registeredMoment(value as string, timezone);
  if (field === "expires_at" || field === "paid_at")
    return new Date(value as string).toLocaleDateString("cs");
  if (Array.isArray(value))
    return value.length > 0 ? value.join(", ") : t("rail.edit.empty");
  if (typeof value === "boolean") return value ? "✓" : t("rail.edit.empty");
  return String(value);
}

/** What an entry says happened. Changes with no column of their own are
 *  sentences, not assignments: a deletion reads as a deletion, a merge as a
 *  merge into the surviving row. */
export function changeText(
  entry: NetChange,
  rows: SheetRow[],
  timezone: string | null,
  t: Translate,
): string {
  if (entry.field === "_deleted")
    return entry.after === true ? t("rail.edit.deleted") : t("rail.edit.restored");
  if (entry.field === "_merged_into")
    return t("rail.edit.mergedInto", { row: rowText(entry.after, rows, t) });
  return t("rail.edit.assignment", {
    field: t(`column.${entry.field}`, { defaultValue: entry.field }),
    before: valueText(entry.field, entry.before, timezone, t),
    after: valueText(entry.field, entry.after, timezone, t),
  });
}

export function entryText(
  entry: NetChange,
  rows: SheetRow[],
  timezone: string | null,
  t: Translate,
): string {
  return t("rail.edit.entry", {
    row: rowText(entry.target, rows, t),
    change: changeText(entry, rows, timezone, t),
  });
}

export default function ManualEditsRail({
  entries,
  rows,
  timezone,
  onUndo,
}: {
  entries: NetChange[];
  rows: SheetRow[];
  timezone: string | null;
  /** Undoes the whole entry — every rule that put the cell where it is. */
  onUndo: (ruleIds: number[]) => void;
}) {
  const { t } = useTranslation();
  return (
    <section className="rail-card plain">
      <h2>
        {t("rail.manualEdits")} <span className="rail-count">({entries.length})</span>
      </h2>
      {entries.length === 0 ? (
        <p className="rail-hint">{t("rail.noEdits")}</p>
      ) : (
        <ul className="edits-list">
          {entries.map((entry) => (
            <li key={`${entry.target}:${entry.field}`} className="edit-entry">
              <div className="edit-body">
                <div>{entryText(entry, rows, timezone, t)}</div>
                <div className="edit-meta">
                  {t("rail.edit.meta", {
                    actor: entry.actor,
                    time: new Date(entry.at).toLocaleTimeString("cs", {
                      hour: "2-digit",
                      minute: "2-digit",
                    }),
                  })}
                </div>
              </div>
              <button
                className="row-action"
                title={t("actions.removeRule")}
                onClick={() => onUndo(entry.rule_ids)}
              >
                <IconX size={16} stroke={1.5} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
