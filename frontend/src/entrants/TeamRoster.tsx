import { IconChevronDown, IconChevronRight } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { EntrantTeam, Roster } from "../api";
import NationalityCell from "./NationalityCell";
import { CapacityLine, PaidCell, TwoLengthHeader } from "./rosterCells";

type TeamRosterData = Extract<Roster, { kind: "team" }>;

const COLUMNS = 5;

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
      {/* Fixed layout over declared widths: opening a team adds rows whose
          names and clubs would otherwise reshare the columns, and the table
          would jump under the pointer that opened it. */}
      <table className="sheet-table entrants-table entrants-team-table">
        <colgroup>
          <col className="col-w-gutter" />
          <col />
          <col className="col-w-nat" />
          <col className="col-w-club" />
          <col className="col-w-paid" />
        </colgroup>
        <thead>
          <tr>
            <th className="col-gutter" aria-label={t("export.column.position")} />
            <th className="col-team">{t("entrants.team")}</th>
            <th className="col-nat">{t("export.column.nat")}</th>
            <th>{t("export.column.club")}</th>
            <TwoLengthHeader
              className="col-paid"
              wide={t("entrants.column.paid")}
              narrow={t("entrants.column.paidShort")}
            />
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

/** The team row's Nat. cell: the nationality every member shares, drawn as
 *  its flag where a country is read from it. Members agreeing on the
 *  nationality agree on its country, so the first member's speaks for all. */
function SharedNationality({ members }: { members: EntrantTeam["members"] }) {
  const nationality = shared(members.map((member) => member.nationality));
  const country = nationality === null ? null : (members[0]?.country ?? null);
  return <NationalityCell nationality={nationality} country={country} />;
}

function TeamLines({ team }: { team: EntrantTeam }) {
  const [open, setOpen] = useState(false);
  const faded = team.faded ? "muted" : undefined;
  const composed = team.members.length > 0;
  const Chevron = open ? IconChevronDown : IconChevronRight;
  // a club the team's row states is every member's; a member's row states
  // one only where the team's row cannot (spec public-entrants)
  const teamClub = shared(team.members.map((member) => member.club));
  return (
    // one team is one row group: the hairline falls between teams, not
    // between a team and its own members
    <tbody className="entrant-team-block">
      <tr className={faded}>
        <td className="col-gutter">{team.number}</td>
        <td className="col-team">
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
        <SharedNationality members={team.members} />
        <td className="col-club">{teamClub}</td>
        <PaidCell paid={team.paid} />
      </tr>
      {open &&
        team.members.map((member, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: a read-only roster rebuilt from props; position is the only identity a member has
          <tr key={index} className={faded}>
            <td className="col-gutter" />
            <td className="entrant-member">{member.name}</td>
            <NationalityCell nationality={member.nationality} country={member.country} />
            <td className="col-club">{teamClub === null ? member.club : null}</td>
            <td className="col-paid" />
          </tr>
        ))}
    </tbody>
  );
}
