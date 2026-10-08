import { useTranslation } from "react-i18next";

import type { ExportSummaryLine } from "../api";
import { SUMMARY_COUNTS, summaryGroups, summaryGroupTitle, summaryLabel } from "./summary";

/** The Summary tab: how many of each discipline and item the tournament
 *  offers, paid and unpaid (spec export-summary). Its lines are the offer's,
 *  so an item nobody chose still stands here at 0 and 0.
 *
 *  One table per group — the disciplines, then each category — each headed
 *  by what it counts. The tables share fixed column widths, so the counts of
 *  every one stand in the same place rather than wherever its names end. */
export default function SummaryTable({ lines }: { lines: ExportSummaryLine[] }) {
  const { t } = useTranslation();
  if (lines.length === 0) return <p className="sheet-empty">{t("sheet.empty")}</p>;
  return (
    <div className="sheet-scroll summary-scroll">
      {summaryGroups(lines).map((group) => (
        <table key={group.category} className="sheet-table summary-table">
          <colgroup>
            <col className="summary-col-name" />
            <col className="summary-col-count" />
            <col className="summary-col-count" />
          </colgroup>
          <thead>
            <tr>
              <th>{summaryGroupTitle(t, group.category)}</th>
              {SUMMARY_COUNTS.map((id) => (
                <th key={id} className="col-number">
                  {t(`export.column.${id}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {group.lines.map((line) => (
              <tr key={`${line.kind}:${line.item_id ?? line.name}:${line.option}:${line.missing}`}>
                <td>{summaryLabel(t, line)}</td>
                <td className="col-number">{line.paid}</td>
                <td className="col-number">{line.unpaid}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ))}
    </div>
  );
}
