import { IconArrowBackUp, IconTrash } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { SheetRow, TournamentDetail } from "./api";
import {
  CellDisplay,
  MARKER_COLUMNS,
  PHASE_COLUMNS,
  type Phase,
  absorbedInto,
  editableHere,
  rowAction,
  rowNumber,
} from "./Console";
import EditableCell from "./EditableCell";
import { usesHRIdentity } from "./identity";
import MatchCell from "./MatchCell";
import type { FieldError } from "./validation";

/** The fencer table and the document it sits in: the main area of every phase
 *  that shows one.
 *
 *  Lifted out of `Console` when Deduplication stopped showing a fencer table
 *  and started showing its candidate groups instead: the workspace now chooses
 *  between two main areas, and choosing between them inside a 130-line block of
 *  JSX is how a file gets to 700 lines (design D8). Behaviour is unchanged —
 *  every decision this makes is still `Console`'s, arriving as a prop.
 */
export default function SheetArea({
  phase,
  queues,
  rows,
  visibleRows,
  columns,
  activeRows,
  paidCount,
  revision,
  timezone,
  currency,
  error,
  refresh,
  onEdit,
  onValidate,
  onDelete,
  onRestore,
  onRatify,
  onSearch,
}: {
  phase: Phase;
  /** What this phase puts above the table — the payments phase's resolution
   *  queues. The work a phase exists to do belongs in the column the organizer
   *  is looking at; null for a phase whose work is the table itself. */
  queues?: React.ReactNode;
  /** The whole fencer list, which the index column reads to say where an
   *  absorbed row went; `visibleRows` is what this phase lists. */
  rows: SheetRow[];
  visibleRows: SheetRow[];
  columns: string[];
  activeRows: SheetRow[];
  paidCount: number;
  revision: number;
  timezone: string | null;
  /** Passed through to the money cells; null until the tournament detail has
   *  arrived beside the sheet. */
  currency: Pick<TournamentDetail, "local_currency" | "eur_payments_enabled"> | null;
  error: boolean;
  refresh: () => void;
  onEdit: (row: SheetRow, column: string, raw: string) => void;
  onValidate: (column: string, raw: string) => FieldError | null;
  onDelete: (row: SheetRow) => void;
  onRestore: (row: SheetRow) => void;
  onRatify: (row: SheetRow) => void;
  onSearch: (row: SheetRow) => void;
}) {
  const { t } = useTranslation();
  const hrIdentity = usesHRIdentity(phase);

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        {/* the Import view is a record of one uploaded file, not the
            tournament's list of fencers, and says so */}
        <h1>{t(phase === "import" ? "console.titleImport" : "console.title")}</h1>
        <button className="secondary" onClick={refresh}>
          {t("console.refresh")}
        </button>
      </div>

      {queues && <div className="sheet-queues">{queues}</div>}

      <div className="sheet-scroll">
        {error ? (
          <p className="sheet-empty">{t("console.error")}</p>
        ) : visibleRows.length === 0 ? (
          <p className="sheet-empty">{t("sheet.empty")}</p>
        ) : (
          <table className="sheet-table">
            <thead>
              <tr>
                <th className="col-index">#</th>
                {columns.map((column) => (
                  <th
                    key={column}
                    className={[
                      PHASE_COLUMNS[phase].includes(column) ? "col-phase" : "",
                      MARKER_COLUMNS.has(column) ? "col-marker" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {t(`column.${column}`)}
                  </th>
                ))}
                <th className="col-actions" />
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.id} className={row._deleted ? "row-deleted" : ""}>
                  <td className="col-index">
                    {rowNumber(row, phase)}
                    {absorbedInto(row, rows) !== null && (
                      <span className="row-absorbed" title={t("row.absorbed")}>
                        {" \u2192 #"}
                        {absorbedInto(row, rows)}
                      </span>
                    )}
                  </td>
                  {columns.map((column) => {
                    const phaseOwned = PHASE_COLUMNS[phase].includes(column);
                    const editable = editableHere(column, phase) && !row._deleted;
                    const isMatch = column === "match";
                    return (
                      <td
                        key={column}
                        className={`${phaseOwned ? "col-phase" : ""} ${
                          isMatch ? "col-verdict" : ""
                        } ${MARKER_COLUMNS.has(column) ? "col-marker" : ""}`}
                      >
                        {isMatch ? (
                          <MatchCell
                            row={row}
                            onRatify={() => onRatify(row)}
                            onSearch={() => onSearch(row)}
                          />
                        ) : editable ? (
                          <EditableCell
                            display={
                              <CellDisplay
                                row={row}
                                column={column}
                                timezone={timezone}
                                currency={currency}
                                hrIdentity={hrIdentity}
                              />
                            }
                            value={row[column]}
                            onSave={(raw) => onEdit(row, column, raw)}
                            validate={(raw) => onValidate(column, raw)}
                          />
                        ) : (
                          <CellDisplay
                            row={row}
                            column={column}
                            timezone={timezone}
                            currency={currency}
                            hrIdentity={hrIdentity}
                          />
                        )}
                      </td>
                    );
                  })}
                  <td className="col-actions">
                    {rowAction(row) === null ? null : rowAction(row) === "restore" ? (
                      <button
                        className="row-action"
                        title={t("actions.restore")}
                        onClick={() => onRestore(row)}
                      >
                        <IconArrowBackUp size={16} stroke={1.5} />
                      </button>
                    ) : (
                      <button
                        className="row-action"
                        title={t("actions.delete")}
                        onClick={() => onDelete(row)}
                      >
                        <IconTrash size={16} stroke={1.5} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {!error && visibleRows.length > 0 && (
        <div className="doc-footer">
          <span>
            {t("console.footerStats", { rows: activeRows.length, paid: paidCount })}
          </span>
          <span>
            {t("console.footerNote")}{" "}
            <span className="doc-footer-revision">
              {t("console.footerRevision", { n: revision })}
            </span>
          </span>
        </div>
      )}
    </main>
  );
}
