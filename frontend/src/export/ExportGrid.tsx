import { Fragment } from "react";
import { useTranslation } from "react-i18next";

import type { SheetRow } from "../api";
import { type ExportColumn, POSITION } from "./columns";
import type { CapacityLine } from "./ordering";

/** The table body every export tab draws: its columns, its rows in the order
 *  they arrive, and — on a discipline tab — the one line marking capacity.
 *
 *  Every row is numbered from 1 in the order it is drawn, straight across the
 *  line, which carries no number of its own.
 *
 *  The line is a row of this table with a rule above it, not a break splitting
 *  the table in two: what leaves the tab, copied or written to a spreadsheet,
 *  is every fencer in one block. It carries its own label, so a reader is never
 *  left inferring from a setting whether the fencers below it are queued or
 *  merely past the cut.
 */
export default function ExportGrid({
  columns,
  rows,
  line,
  cell,
}: {
  columns: ExportColumn[];
  rows: SheetRow[];
  line?: CapacityLine;
  /** A cell rendered as something other than its text — the rating, which the
   *  organizer corrects in place. Falls back to the column's own value. */
  cell?: (row: SheetRow, column: ExportColumn, index: number) => React.ReactNode | null;
}) {
  const { t } = useTranslation();
  if (rows.length === 0) return <p className="sheet-empty">{t("sheet.empty")}</p>;
  return (
    <div className="sheet-scroll">
      <table className="sheet-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.id} className={column.id === POSITION.id ? "col-index" : undefined}>
                {t(`export.column.${column.id}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <Fragment key={row.id}>
              {line?.after === index && (
                <tr className="export-line">
                  <td colSpan={columns.length}>{t(`export.line.${line.kind}`)}</td>
                </tr>
              )}
              <tr>
                {columns.map((column) => (
                  <td
                    key={column.id}
                    className={column.id === POSITION.id ? "col-index" : undefined}
                  >
                    {cell?.(row, column, index) ?? column.value(row, index)}
                  </td>
                ))}
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
