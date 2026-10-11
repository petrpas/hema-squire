import { useTranslation } from "react-i18next";

import type { EntrantRow, Roster } from "../api";
import { CapacityLine, HrIdCell, PaidCell } from "./rosterCells";

type IndividualRosterData = Extract<Roster, { kind: "individual" | "event" }>;

/** A roster of fencers — an individual discipline's or a side event's: the
 *  seated above the capacity line and the queue below it, each queued row
 *  numbered by its position in the queue. A side event has no capacity, so
 *  it draws neither (spec public-entrants). */
export default function IndividualRoster({ roster }: { roster: IndividualRosterData }) {
  const { t } = useTranslation();
  if (roster.seated.length === 0 && roster.queued.length === 0) {
    return <p className="sheet-empty">{t("entrants.empty")}</p>;
  }
  return (
    <div className="sheet-scroll entrants-scroll">
      <table className="sheet-table entrants-table">
        <thead>
          <tr>
            <th className="col-index">{t("export.column.position")}</th>
            <th>{t("export.column.name")}</th>
            <th>{t("export.column.nat")}</th>
            <th>{t("export.column.club")}</th>
            <th className="col-number">{t("export.column.hr_id")}</th>
            <th>{t("export.column.paid")}</th>
          </tr>
        </thead>
        <tbody>
          {roster.seated.map((row) => (
            <EntrantLine key={`seated-${row.number}`} row={row} />
          ))}
          {roster.line && <CapacityLine columns={6} queued={roster.queued.length > 0} />}
          {roster.queued.map((row) => (
            <EntrantLine key={`queued-${row.number}`} row={row} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EntrantLine({ row }: { row: EntrantRow }) {
  const { t } = useTranslation();
  return (
    <tr className={row.faded ? "muted" : undefined}>
      <td className="col-index">{row.number}</td>
      <td>
        {row.name}
        {/* a placement waiting for all of its conditional disciplines can stand
            in the queue while places are free; said in words, not a glyph */}
        {row.conditional && (
          <span className="entrant-mark" title={t("entrants.conditionalHint")}>
            {t("entrants.conditional")}
          </span>
        )}
      </td>
      <td>{row.nationality}</td>
      <td>{row.club}</td>
      <HrIdCell hrId={row.hr_id} />
      <PaidCell paid={row.paid} />
    </tr>
  );
}
