import { useTranslation } from "react-i18next";

import type { DedupMember } from "../api";
import { IDENTITY_COLUMNS, identityValue } from "../identity";
import { registeredMoment } from "../momentText";
import ConclusionCell from "./ConclusionCell";
import { GROUP_COLUMNS, asList, editableInConclusion, isBound } from "./mergeFields";

/** The record a merge would produce, in the same columns as the records it
 *  would merge — the verdict register of a candidate group (spec `etl-console`,
 *  The ledger idiom).
 *
 *  Its identity cells follow the phase's identity rule: the profile's values
 *  where one stands behind the group, read-only, and the registered words where
 *  none does, which is the one place choosing between them can be done at all
 *  (design D7).
 */
export default function ConclusionRow({
  fields,
  note,
  members,
  editable,
  timezone,
  onField,
  onNote,
}: {
  fields: Record<string, unknown>;
  note: string;
  members: DedupMember[];
  /** False once the group is settled and until its conclusion is reopened. */
  editable: boolean;
  timezone: string | null;
  onField: (column: string, value: unknown) => void;
  onNote: (note: string) => void;
}) {
  const { t } = useTranslation();
  const bound = isBound(members);
  const survivor = members[0];

  function display(column: string) {
    if (IDENTITY_COLUMNS.includes(column)) {
      // where a profile stands behind the group it states the identity, read
      // off the survivor's evidence register; where none does, the merged
      // registered value stands in italic, as it does everywhere after Matching
      if (bound && survivor) {
        const { text } = identityValue(survivor, column, true);
        return <>{text}</>;
      }
      const value = fields[column];
      const text = value === null || value === undefined || value === "" ? "—" : String(value);
      return text === "—" ? <>{text}</> : <span className="identity-declared">{text}</span>;
    }
    if (column === "registered_at") return <>{registeredMoment(survivor?.registered_at ?? null, timezone)}</>;
    if (column === "disciplines" || column === "weapon_rentals") {
      const values = asList(fields[column]);
      return <>{values.length > 0 ? values.join(", ") : "—"}</>;
    }
    if (column === "afterparty") return <>{fields[column] === true ? "✓" : "—"}</>;
    const value = fields[column];
    return <>{value === null || value === undefined || value === "" ? "—" : String(value)}</>;
  }

  return (
    <>
      <tr className="conclusion-row">
        <th scope="row" className="col-index">
          {t("dedup.conclusion")}
        </th>
        {GROUP_COLUMNS.map((column) => {
          const open = editable && editableInConclusion(column, members);
          return (
            <td key={column} className="conclusion-td">
              {open ? (
                <ConclusionCell
                  column={column}
                  value={fields[column]}
                  members={members}
                  onChange={(value) => onField(column, value)}
                />
              ) : (
                display(column)
              )}
            </td>
          );
        })}
      </tr>
      <tr className="conclusion-note-row">
        <th scope="row" className="col-index">
          {t("column.merge_note")}
        </th>
        <td colSpan={GROUP_COLUMNS.length}>
          {editable ? (
            <textarea
              className="conclusion-note"
              rows={2}
              value={note}
              aria-label={t("column.merge_note")}
              onChange={(event) => onNote(event.target.value)}
            />
          ) : (
            <span className="conclusion-note-text">{note || "—"}</span>
          )}
        </td>
      </tr>
    </>
  );
}
