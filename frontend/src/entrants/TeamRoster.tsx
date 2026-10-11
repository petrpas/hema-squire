import { useTranslation } from "react-i18next";

import type { EntrantTeam, Roster } from "../api";
import { CapacityLine, HrIdCell, PaidCell } from "./rosterCells";

type TeamRosterData = Extract<Roster, { kind: "team" }>;

const COLUMNS = 6;

/** A team discipline's roster: each team by name with its members beneath
 *  it, and the waitlist below the capacity line (spec public-entrants). */
export default function TeamRoster({ roster }: { roster: TeamRosterData }) {
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
            <th>{t("entrants.team")}</th>
            <th>{t("export.column.nat")}</th>
            <th>{t("export.column.club")}</th>
            <th className="col-number">{t("export.column.hr_id")}</th>
            <th>{t("export.column.paid")}</th>
          </tr>
        </thead>
        <tbody>
          {roster.seated.map((team) => (
            <TeamLines key={`seated-${team.number}`} team={team} />
          ))}
          {roster.line && <CapacityLine columns={COLUMNS} queued={roster.queued.length > 0} />}
          {roster.queued.map((team) => (
            <TeamLines key={`queued-${team.number}`} team={team} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TeamLines({ team }: { team: EntrantTeam }) {
  const { t } = useTranslation();
  const faded = team.faded ? "muted" : undefined;
  return (
    <>
      <tr className={faded}>
        <td className="col-index">{team.number}</td>
        <td>
          <strong className="entrant-team">{team.name}</strong>
        </td>
        <td />
        <td />
        <td />
        <PaidCell paid={team.paid} />
      </tr>
      {team.members.length === 0 ? (
        <tr className="muted">
          <td />
          <td className="entrant-member" colSpan={COLUMNS - 1}>
            {t("entrants.membersPending")}
          </td>
        </tr>
      ) : (
        team.members.map((member, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: a read-only roster rebuilt from props; position is the only identity a member has
          <tr key={index} className={faded}>
            <td />
            <td className="entrant-member">{member.name}</td>
            <td>{member.nationality}</td>
            <td>{member.club}</td>
            <HrIdCell hrId={member.hr_id} />
            <td />
          </tr>
        ))
      )}
    </>
  );
}
