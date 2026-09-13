import { IconArrowBackUp, IconCoins, IconTrash, IconUserShare } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { SheetRow, TournamentDetail } from "./api";
import {
  absorbedInto,
  CellDisplay,
  canSubstitute,
  editableHere,
  MARKER_COLUMNS,
  PHASE_COLUMNS,
  type Phase,
  phaseRemovesRows,
  phaseSummary,
  rowAction,
  rowNumber,
} from "./Console";
import EditableCell from "./EditableCell";
import { usesHRIdentity } from "./identity";
import MatchCell from "./MatchCell";
import PhaseSummary from "./PhaseSummary";
import { useSheetVisible } from "./payments/PaymentTabs";
import SettledCell from "./SettledCell";
import StateCell from "./StateCell";
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
/** What the phase's own heading calls its main area.
 *
 *  Most phases show the tournament's list of fencers and say so. Two do not:
 *  Import is a record of one uploaded file, and Payments is the management of
 *  money, whose fencer table is one tab of three. A phase-keyed lookup rather
 *  than a chain of conditions, so a third exception is a line rather than
 *  another branch. */
function headingKey(phase: Phase): string {
  if (phase === "import") return "console.titleImport";
  if (phase === "payments") return "console.titlePayments";
  return "console.title";
}

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
  onSubstitute,
  onRestore,
  onRatify,
  onSearch,
  onToggleSettled,
  collects,
  onRecordPayment,
  settling,
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
  /** Hands the row's seat to somebody else. Absent on every phase but the
   *  fencer list, where the roster is settled. */
  onSubstitute?: (row: SheetRow) => void;
  /** Marks a registration settled, or unmarks it. Offered on the Payments
   *  phase of every tournament: on the boned-out one it is the phase's whole
   *  content, and on a collecting one it is the waiver.
   *
   *  Rejects when the mark is refused, so the waiver's dialog can stay open
   *  and say why rather than closing on a row that did not change. */
  onToggleSettled?: (row: SheetRow, reason?: string | null) => Promise<void>;
  /** Whether Squire handles this tournament's payments. Where it does, the
   *  waiver is offered on the state cell rather than in a column of its own,
   *  and a paid row is not evidence of a mark — money reaches such a
   *  tournament by other routes. */
  collects?: boolean;
  /** Opens the record-payment dialog for a row. Offered only where Squire
   *  handles the payments: where it tracks no amounts, an amount means nothing
   *  it could keep. */
  onRecordPayment?: (row: SheetRow) => void;
  settling?: boolean;
  onRestore: (row: SheetRow) => void;
  onRatify: (row: SheetRow) => void;
  onSearch: (row: SheetRow) => void;
}) {
  const { t } = useTranslation();
  const hrIdentity = usesHRIdentity(phase);
  const sheetVisible = useSheetVisible();
  // asked of the phase, not of the rows: a phase that removes rows keeps the
  // column even where every row it lists happens to offer nothing, so the
  // table does not change width as rows come and go
  const actionable = phaseRemovesRows(phase);
  // The end-of-row column, which Import and Fencers use for delete and restore
  // and Payments now uses for recording a payment. Asked of the phase rather
  // than of the rows, as `actionable` is, so the table keeps its width.
  const rowActions = actionable || onRecordPayment !== undefined || onSubstitute !== undefined;
  // How many actions the phase offers, asked of the phase and not of the rows
  // it happens to list, so the column keeps its width as rows are deleted and
  // restored — the same reason `phaseRemovesRows` is a phase question.
  const actionsClass =
    (actionable ? 1 : 0) + (onRecordPayment ? 1 : 0) + (onSubstitute ? 1 : 0) > 1
      ? "col-actions col-actions-pair"
      : "col-actions";
  // read from the rows this phase lists, so a count and the table beneath it
  // are two statements about the same thing
  const summary = phaseSummary(phase, visibleRows);

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        {/* the Import view is a record of one uploaded file and Payments is
            the management of money — neither is the tournament's list of
            fencers, and each says so */}
        <h1>{t(headingKey(phase))}</h1>
        <PhaseSummary
          text={summary === null ? null : t(summary.key, { count: summary.count })}
          onRefresh={refresh}
        />
      </div>

      {queues && <div className="sheet-queues">{queues}</div>}

      {/* on the payments phase the table is itself a tab, and gives way to
          whichever queue is being read. Everywhere else there are no tabs and
          it is always what the phase shows */}
      {sheetVisible && (
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
                        PHASE_COLUMNS[phase].includes(column) || column === "settled"
                          ? "col-phase"
                          : "",
                        MARKER_COLUMNS.has(column) ? "col-marker" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {t(`column.${column}`)}
                    </th>
                  ))}
                  {/* the column exists only where the phase offers something to
                    do to a row; drawn empty it is a gap at the end of every
                    row with nothing to explain it */}
                  {rowActions && <th className={actionsClass} />}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => (
                  <tr key={row.id} className={row._deleted ? "row-deleted" : ""}>
                    <td className="col-index">
                      {rowNumber(row)}
                      {absorbedInto(row, rows) !== null && (
                        <span className="row-absorbed" title={t("row.absorbed")}>
                          {" \u2192 #"}
                          {absorbedInto(row, rows)}
                        </span>
                      )}
                    </td>
                    {columns.map((column) => {
                      const phaseOwned =
                        PHASE_COLUMNS[phase].includes(column) || column === "settled";
                      const editable = editableHere(column, phase) && !row._deleted;
                      const isMatch = column === "match";
                      return (
                        <td
                          key={column}
                          className={`${phaseOwned ? "col-phase" : ""} ${
                            isMatch ? "col-verdict" : ""
                          } ${MARKER_COLUMNS.has(column) ? "col-marker" : ""}`}
                        >
                          {column === "settled" && onToggleSettled ? (
                            <SettledCell
                              row={row}
                              onToggle={onToggleSettled}
                              busy={settling ?? false}
                            />
                          ) : column === "state" && collects && onToggleSettled ? (
                            <StateCell
                              row={row}
                              onToggle={onToggleSettled}
                              busy={settling ?? false}
                            />
                          ) : isMatch ? (
                            <MatchCell
                              row={row}
                              onRatify={() => onRatify(row)}
                              onSearch={() => onSearch(row)}
                            />
                          ) : editable ? (
                            <EditableCell
                              label={t(`column.${column}`)}
                              display={
                                <CellDisplay
                                  row={row}
                                  column={column}
                                  timezone={timezone}
                                  currency={currency}
                                  hrIdentity={hrIdentity}
                                />
                              }
                              // a list is edited as the text it is shown as, so
                              // the draft round-trips to itself when untouched
                              value={
                                column === "disciplines"
                                  ? row.disciplines.join(", ")
                                  : column === "weapon_rentals"
                                    ? row.weapon_rentals.join(", ")
                                    : row[column]
                              }
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
                    {rowActions && (
                      <td className={actionsClass}>
                        {/* Side by side and on one line: two actions at the end
                          of a row are two decisions offered together, and
                          stacked they read as one above the other. */}
                        <div className="row-actions">
                          {/* money that arrived where the feed does not reach.
                          Sits with the row actions rather than in a column,
                          because it is an action and not a value */}
                          {onRecordPayment && typeof row.registration_id === "number" && (
                            <button
                              type="button"
                              className="row-action"
                              title={t("payments.record.action")}
                              onClick={() => onRecordPayment(row)}
                            >
                              <IconCoins size={16} stroke={1.5} />
                              <span className="visually-hidden">{t("payments.record.action")}</span>
                            </button>
                          )}
                          {/* a seat handed on, beside the seat given up: two
                          different decisions, both of them the roster's */}
                          {onSubstitute && canSubstitute(row, phase) && (
                            <button
                              type="button"
                              className="row-action"
                              title={t("actions.substitute")}
                              onClick={() => onSubstitute(row)}
                            >
                              <IconUserShare size={16} stroke={1.5} />
                              <span className="visually-hidden">{t("actions.substitute")}</span>
                            </button>
                          )}
                          {rowAction(row, phase) === null ? null : rowAction(row, phase) ===
                            "restore" ? (
                            <button
                              type="button"
                              className="row-action"
                              title={t("actions.restore")}
                              onClick={() => onRestore(row)}
                            >
                              <IconArrowBackUp size={16} stroke={1.5} />
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="row-action"
                              title={t("actions.delete")}
                              onClick={() => onDelete(row)}
                            >
                              <IconTrash size={16} stroke={1.5} />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {sheetVisible && !error && visibleRows.length > 0 && (
        <div className="doc-footer">
          <span>{t("console.footerStats", { rows: activeRows.length, paid: paidCount })}</span>
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
