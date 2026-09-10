import { useTranslation } from "react-i18next";

import type { SheetRow } from "../api";
import EditableCell from "../EditableCell";
import type { FieldError } from "../validation";
import { type ExportColumn, ROSTER_COLUMNS, ratingOf } from "./columns";
import ExportGrid from "./ExportGrid";
import { rosterOrder } from "./ordering";

/** One discipline's seeding roster: the fencers entered in it, the line where
 *  its capacity falls, and the rating each is seeded by.
 *
 *  The rating cell is the organizer's to correct — HEMA Ratings is not always
 *  right, and the corrected figure is what the order, the line and the
 *  spreadsheet all read.
 */
export default function RosterTable({
  rows,
  slug,
  capacity,
  lineKind,
  seeded,
  edited,
  onRate,
}: {
  rows: SheetRow[];
  slug: string;
  capacity: number | null;
  lineKind: "queue" | "capacity";
  /** Whether the tab is switched to active only, which is when the roster is
   *  read as a seeding order rather than as a list of who is entered. */
  seeded: boolean;
  /** Whether this row's rating carries an organizer's correction, marked the
   *  way every other manual edit is. */
  edited: (row: SheetRow) => boolean;
  onRate: (row: SheetRow, raw: string) => void;
}) {
  const { t } = useTranslation();
  const columns = ROSTER_COLUMNS(t, slug);
  const { rows: ordered, line } = rosterOrder(rows, slug, capacity, lineKind, seeded);

  function cell(row: SheetRow, column: ExportColumn) {
    if (!column.editable) return null;
    const display = column.value(row);
    return (
      <EditableCell
        label={t("export.column.rating")}
        display={edited(row) ? <span className="cell-edited">{display}</span> : display || "—"}
        value={ratingOf(row, slug)}
        onSave={(raw) => onRate(row, raw)}
        validate={validateRating}
      />
    );
  }

  return <ExportGrid columns={columns} rows={ordered} line={line} cell={cell} />;
}

/** A rating is a number, or nothing — which states that the register has
 *  nobody by that name, and is not the same as removing the correction. */
function validateRating(raw: string): FieldError | null {
  if (raw.trim() === "") return null;
  const value = Number(raw.replace(",", "."));
  return Number.isFinite(value) ? null : { field: "rating", code: "not_a_number", params: {} };
}
