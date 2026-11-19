import { IconChevronDown, IconChevronRight } from "@tabler/icons-react";
import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { LapsedTeam } from "../api";
import { dayIn } from "../momentText";
import { formatMoney } from "../money";

/** Why a team is gone and since when, with what its registration still holds:
 *  the cell standing where a live row states its money. */
export function lapsedText(t: TFunction, team: LapsedTeam, timezone: string | null): string {
  const why =
    team.lapsed_at === null
      ? t(`teams.lapsed.${team.reason}Undated`)
      : t(`teams.lapsed.${team.reason}`, { day: dayIn(team.lapsed_at, timezone) });
  if (team.held_amount === null || team.held_currency === null) return why;
  return `${why} · ${t("teams.lapsed.held", {
    amount: formatMoney(team.held_amount, team.held_currency),
  })}`;
}

/** The teams gone with their registrations, below a table's live teams
 *  beneath a line of their own (spec team-disciplines, Organizer's teams
 *  view; seating-queue, The team waitlist in the Queue phase).
 *
 *  Read-only and holding no place: faded as a queued row is, no count in the
 *  gutter — a number there would read as a place, and these hold none — and
 *  no action. An expiry happens on its own, by the payment clock, and this is
 *  where the organizer learns that a team they expect is gone.
 *
 *  `layout` is the table it stands in: the Teams view, whose row unfolds the
 *  roster and whose columns state the address and the items, or the Queue's
 *  roster, which states neither. Draws nothing where nothing lapsed. */
export default function LapsedTeamRows({
  teams,
  timezone,
  layout,
}: {
  teams: LapsedTeam[];
  timezone: string | null;
  layout: "teams" | "queue";
}) {
  const { t } = useTranslation();
  if (teams.length === 0) return null;
  const columns = layout === "teams" ? 8 : 6;
  return (
    <>
      <tbody>
        <tr className="export-line">
          <td colSpan={columns}>{t("teams.lapsed.line")}</td>
        </tr>
      </tbody>
      {teams.map((team) => (
        <LapsedTeamRow
          key={team.id}
          team={team}
          timezone={timezone}
          layout={layout}
          columns={columns}
        />
      ))}
    </>
  );
}

function LapsedTeamRow({
  team,
  timezone,
  layout,
  columns,
}: {
  team: LapsedTeam;
  timezone: string | null;
  layout: "teams" | "queue";
  columns: number;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const standing = lapsedText(t, team, timezone);
  const label = open ? t("teams.roster.hide") : t("teams.roster.show");

  return (
    <tbody className="entrant-team-block">
      <tr className="muted">
        <td className="col-gutter" />
        <td>{team.name}</td>
        <td>{team.entering_fencer}</td>
        {layout === "teams" && <td>{team.entering_email ?? ""}</td>}
        {layout === "teams" && <td />}
        <td className={layout === "teams" ? "col-center" : "col-number"}>
          {team.members.length}
          {layout === "teams" && (
            <button
              type="button"
              className="roster-toggle"
              aria-expanded={open}
              title={label}
              onClick={() => setOpen(!open)}
            >
              {open ? (
                <IconChevronDown size={14} stroke={1.5} aria-hidden />
              ) : (
                <IconChevronRight size={14} stroke={1.5} aria-hidden />
              )}
              <span className="visually-hidden">{label}</span>
            </button>
          )}
        </td>
        <td className={layout === "teams" ? "col-center" : undefined}>{standing}</td>
        <td className={layout === "teams" ? "col-actions" : undefined} />
      </tr>
      {open && (
        <tr>
          <td className="col-gutter" />
          <td colSpan={columns - 1}>
            <div className="roster-panel">
              {team.members.length === 0 ? (
                <p className="muted">{t("teams.rosterEmpty")}</p>
              ) : (
                <ul className="detail-list">
                  {team.members.map((member) => (
                    <li key={member.id} className="muted">
                      {member.name}
                      {member.hr_id !== null && ` · HR ${member.hr_id}`}
                      {member.club && ` · ${member.club}`}
                      {member.nationality && ` · ${member.nationality}`}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </td>
        </tr>
      )}
    </tbody>
  );
}
