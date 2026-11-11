import { useTranslation } from "react-i18next";

import type { EntrantRow, Roster } from "../api";
import NationalityCell from "./NationalityCell";
import { CapacityLine, HrIdCell, PaidCell, TwoLengthHeader } from "./rosterCells";

type IndividualRosterData = Extract<Roster, { kind: "individual" | "event" }>;

/** A roster of fencers — an individual discipline's or a side event's: the
 *  seated above the capacity line and the queue below it, each queued row
 *  numbered by its position in the queue. A side event keeps no queue, and
 *  draws its line, stating its capacity, only where it has one (spec
 *  public-entrants). */
export default function IndividualRoster({ roster }: { roster: IndividualRosterData }) {
  const { t } = useTranslation();
  if (roster.seated.length === 0 && roster.queued.length === 0) {
    return <p className="sheet-empty">{t("entrants.empty")}</p>;
  }
  return (
    <div className="sheet-scroll entrants-scroll">
      {/* Declared widths, the name taking what is left: measured columns let
          a long club win the width a name needs (spec public-entrants, A
          roster fits a phone). */}
      <table className="sheet-table entrants-table">
        <colgroup>
          <col className="col-w-gutter" />
          <col />
          <col className="col-w-nat" />
          <col className="col-w-club" />
          <col className="col-w-hr" />
          <col className="col-w-paid" />
        </colgroup>
        <thead>
          <tr>
            <th className="col-gutter" aria-label={t("export.column.position")} />
            <th>{t("export.column.name")}</th>
            <th className="col-nat">{t("export.column.nat")}</th>
            <th>{t("export.column.club")}</th>
            <TwoLengthHeader
              className="col-number col-hr"
              wide={t("entrants.column.hr")}
              narrow={t("entrants.column.hrShort")}
            />
            <TwoLengthHeader
              className="col-paid"
              wide={t("entrants.column.paid")}
              narrow={t("entrants.column.paidShort")}
            />
          </tr>
        </thead>
        <tbody>
          {roster.seated.map((row) => (
            <EntrantLine key={`seated-${row.number}`} row={row} />
          ))}
          {roster.line && (
            <CapacityLine
              columns={6}
              queued={roster.queued.length > 0}
              capacity={roster.kind === "event" ? roster.capacity : null}
            />
          )}
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
      <td className="col-gutter">{row.number}</td>
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
      <NationalityCell nationality={row.nationality} country={row.country} />
      <td className="col-club">{row.club}</td>
      <HrIdCell hrId={row.hr_id} />
      <PaidCell paid={row.paid} />
    </tr>
  );
}
