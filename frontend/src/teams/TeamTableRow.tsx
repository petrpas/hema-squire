import { IconChevronDown, IconChevronRight, IconUserX } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ConsoleTeam, ConsoleTeamDiscipline } from "../api";
import PaidStamp from "../PaidStamp";
import ConsoleRosterEditor from "./ConsoleRosterEditor";
import RosterLog from "./RosterLog";

/** The teams table's width, which an unfolded roster spans. */
export const COLUMNS = 6;

/** One team's row, and the panel it opens.
 *
 *  The row states what a reader comparing teams needs — the name, who entered
 *  it and where to write to them, the count against the bounds, and whether the registration it was entered on is paid. The
 *  roster, its editor and its log unfold from the count rather than printed
 *  under every row (spec team-disciplines, Organizer's teams view).
 *
 *  Two actions: the roster, and cancelling this one team. No admission — that
 *  is the Queue phase's, which the capacity line above the waitlisted rows
 *  says, because admission moves money and opens a payment window. */
export default function TeamTableRow({
  slug,
  team,
  discipline,
  onSaved,
  onCancel,
}: {
  slug: string;
  team: ConsoleTeam;
  discipline: ConsoleTeamDiscipline;
  onSaved: (team: ConsoleTeam) => void;
  /** Asks for this team's cancellation dialog, which the panel owns: a
   *  `dialog` element cannot stand inside a table body. */
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showLog, setShowLog] = useState(false);
  const withinBounds =
    team.members.length >= discipline.team_min && team.members.length <= discipline.team_max;

  return (
    <>
      <tr>
        <td>
          <strong>{team.name}</strong>
          {team.below_minimum && <PaidStamp id={team.id} label={t("teams.belowMinimum")} />}
        </td>
        <td>{team.entering_fencer}</td>
        <td>{team.entering_email ?? ""}</td>
        {/* The count alone: the organizer knows the size the discipline asks
            for, and a bound repeated on eighteen rows is eighteen readings of
            one fact. A count outside the bounds is marked instead, which is
            the comparison the reader wanted (spec team-disciplines,
            Organizer's teams view). */}
        <td className="col-center">
          <span className={withinBounds ? undefined : "member-count-off"}>
            {team.members.length}
          </span>
          <button
            type="button"
            className="roster-toggle"
            aria-expanded={open}
            title={open ? t("teams.roster.hide") : t("teams.roster.show")}
            onClick={() => setOpen(!open)}
          >
            {open ? (
              <IconChevronDown size={14} stroke={1.5} aria-hidden />
            ) : (
              <IconChevronRight size={14} stroke={1.5} aria-hidden />
            )}
            <span className="visually-hidden">
              {open ? t("teams.roster.hide") : t("teams.roster.show")}
            </span>
          </button>
        </td>
        <td className="col-center">{t(team.paid ? "export.yes" : "export.no")}</td>
        <td className="col-actions">
          <div className="row-actions">
            <button
              type="button"
              className="row-action"
              title={t("teams.cancel.action")}
              onClick={onCancel}
            >
              <IconUserX size={16} stroke={1.5} />
              <span className="visually-hidden">{t("teams.cancel.action")}</span>
            </button>
          </div>
        </td>
      </tr>

      {open && (
        <tr>
          <td colSpan={COLUMNS}>
            {editing ? (
              <ConsoleRosterEditor
                slug={slug}
                team={team}
                discipline={discipline}
                onSaved={(saved) => {
                  onSaved(saved);
                  setEditing(false);
                }}
                onClose={() => setEditing(false)}
              />
            ) : (
              <>
                {team.members.length === 0 ? (
                  <p className="muted">{t("teams.rosterEmpty")}</p>
                ) : (
                  <ul className="detail-list">
                    {team.members.map((member) => (
                      <li key={member.id} className="muted">
                        {member.name}
                        {/* the identifier the requirement asks for here, as the
                            public entrants roster already states it */}
                        {member.hr_id !== null && ` · #${member.hr_id}`}
                        {member.club && ` · ${member.club}`}
                        {member.nationality && ` · ${member.nationality}`}
                      </li>
                    ))}
                  </ul>
                )}
                <div className="detail-row">
                  <button type="button" className="link-button" onClick={() => setEditing(true)}>
                    {t("teams.editRoster")}
                  </button>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => setShowLog(!showLog)}
                  >
                    {showLog ? t("teams.log.hide") : t("teams.log.show")}
                  </button>
                </div>
              </>
            )}
            {showLog && <RosterLog entries={team.log} />}
          </td>
        </tr>
      )}
    </>
  );
}
