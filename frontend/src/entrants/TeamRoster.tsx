import { IconChevronDown, IconChevronRight } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { EntrantTeam, Roster } from "../api";
import { CapacityLine, HrIdCell, PaidCell } from "./rosterCells";

type TeamRosterData = Extract<Roster, { kind: "team" }>;

const COLUMNS = 6;

/** A team discipline's roster: each team by name, folded, opening onto its
 *  members beneath it, and the waitlist below the capacity line (spec
 *  public-entrants). */
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
            <th className="col-gutter" aria-label={t("export.column.position")} />
            <th>{t("entrants.team")}</th>
            <th>{t("export.column.nat")}</th>
            <th>{t("export.column.club")}</th>
            <th className="col-number">{t("export.column.hr_id")}</th>
            <th>{t("export.column.paid")}</th>
          </tr>
        </thead>
        {roster.seated.map((team) => (
          <TeamLines key={`seated-${team.number}`} team={team} />
        ))}
        {roster.line && (
          <tbody>
            <CapacityLine columns={COLUMNS} queued={roster.queued.length > 0} />
          </tbody>
        )}
        {roster.queued.map((team) => (
          <TeamLines key={`queued-${team.number}`} team={team} />
        ))}
      </table>
    </div>
  );
}

/** The value every member shares, or nothing: a team row states a
 *  nationality or club only where it speaks for the whole team. A member
 *  with none recorded breaks the agreement. */
function shared(values: (string | null)[]): string | null {
  const first = values[0];
  if (!first) return null;
  return values.every((value) => value === first) ? first : null;
}

function TeamLines({ team }: { team: EntrantTeam }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const faded = team.faded ? "muted" : undefined;
  const composed = team.members.length > 0;
  const Chevron = open ? IconChevronDown : IconChevronRight;
  return (
    // one team is one row group: the hairline falls between teams, not
    // between a team and its own members
    <tbody className="entrant-team-block">
      <tr className={faded}>
        <td className="col-gutter">{team.number}</td>
        <td>
          {composed ? (
            <button
              type="button"
              className="entrant-team-toggle"
              aria-expanded={open}
              onClick={() => setOpen((was) => !was)}
            >
              <Chevron size={12} stroke={1.5} aria-hidden />
              <strong className="entrant-team">{team.name}</strong>
            </button>
          ) : (
            <strong className="entrant-team">{team.name}</strong>
          )}
        </td>
        <td>{shared(team.members.map((member) => member.nationality))}</td>
        <td>{shared(team.members.map((member) => member.club))}</td>
        <td />
        <PaidCell paid={team.paid} />
      </tr>
      {!composed ? (
        <tr className="muted">
          <td />
          <td className="entrant-member" colSpan={COLUMNS - 1}>
            {t("entrants.membersPending")}
          </td>
        </tr>
      ) : (
        open &&
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
    </tbody>
  );
}
