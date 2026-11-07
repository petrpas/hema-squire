import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ConsoleTeam, ConsoleTeamDiscipline } from "../api";
import PaidStamp from "../PaidStamp";
import ConsoleRosterEditor from "./ConsoleRosterEditor";
import RosterLog from "./RosterLog";

/** One team as the organizer reads it: its name, who entered it, the roster
 *  in order with each member's HEMA Ratings identifier where they are bound,
 *  the member count against the bounds, and its waitlist position where it
 *  waits.
 *
 *  The roster is editable from here and every edit is logged. No other action
 *  is offered — admission from the waitlist is the Queue phase's, which the
 *  row says, and cancellation is offered nowhere (spec team-disciplines,
 *  Organizer's teams view). */
export default function TeamRow({
  slug,
  team,
  discipline,
  onSaved,
}: {
  slug: string;
  team: ConsoleTeam;
  discipline: ConsoleTeamDiscipline;
  onSaved: (team: ConsoleTeam) => void;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [showLog, setShowLog] = useState(false);

  return (
    <li>
      <div className="detail-row">
        <strong>{team.name}</strong>
        <span>
          {t("teams.memberCount", {
            count: team.members.length,
            min: discipline.team_min,
            max: discipline.team_max,
          })}
          {team.waitlisted && (
            <span className="tag tag-file-blue">
              {" "}
              {t("teams.waitlistPosition", { position: team.waitlist_position })}
            </span>
          )}
          {team.below_minimum && <PaidStamp id={team.id} label={t("teams.belowMinimum")} />}
        </span>
      </div>
      <div className="detail-extra">
        {t("teams.enteredBy", { name: team.entering_fencer })}
        {team.waitlisted && ` · ${t("teams.admittedOnQueue")}`}
      </div>

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
          {team.members.length > 0 && (
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
            <button type="button" className="link-button" onClick={() => setShowLog(!showLog)}>
              {showLog ? t("teams.log.hide") : t("teams.log.show")}
            </button>
          </div>
        </>
      )}

      {showLog && <RosterLog entries={team.log} />}
    </li>
  );
}
