import { useTranslation } from "react-i18next";

import type { ExportSummaryLine } from "../api";
import { SUMMARY_COLUMNS, summaryLabel } from "./summary";

/** The Summary tab: how many of each discipline and item the tournament
 *  offers, paid and unpaid (spec export-summary). Its lines are the offer's,
 *  so an item nobody chose still stands here at 0 and 0. */
export default function SummaryTable({ lines }: { lines: ExportSummaryLine[] }) {
  const { t } = useTranslation();
  if (lines.length === 0) return <p className="sheet-empty">{t("sheet.empty")}</p>;
  return (
    <div className="sheet-scroll summary-scroll">
      <table className="sheet-table">
        <thead>
          <tr>
            {SUMMARY_COLUMNS.map((id) => (
              <th key={id} className={id === "item" ? undefined : "col-number"}>
                {t(`export.column.${id}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr key={`${line.kind}:${line.item_id ?? line.name}:${line.option}:${line.missing}`}>
              <td>{summaryLabel(t, line)}</td>
              <td className="col-number">{line.paid}</td>
              <td className="col-number">{line.unpaid}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
