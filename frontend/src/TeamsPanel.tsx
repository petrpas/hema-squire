import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import PaidStamp from "./PaidStamp";
import { type ConsoleTeamDiscipline, api } from "./api";

/** Read-only, per team discipline (spec: "Organizer's read-only teams
 *  view"). Offers no action — no admission, no roster editing on the
 *  entrant's behalf, no cancellation: those controls simply do not exist
 *  here, rather than existing disabled. */
export default function TeamsPanel({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [disciplines, setDisciplines] = useState<ConsoleTeamDiscipline[] | null>(null);

  useEffect(() => {
    api.consoleTeams(slug).then(setDisciplines, () => setDisciplines([]));
  }, [slug]);

  if (disciplines === null) return <p>{t("common.loading")}</p>;

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        <h1>{t("teams.title")}</h1>
      </div>
      <div className="sheet-scroll">
        {disciplines.length === 0 ? (
          <p className="sheet-empty">{t("teams.empty")}</p>
        ) : (
          disciplines.map((discipline) => (
            <section key={discipline.slug} className="rail-card">
              <h2>
                {discipline.slug} — {discipline.name}
              </h2>
              <p className="rail-hint">
                {t("teams.bounds", { min: discipline.team_min, max: discipline.team_max })}
              </p>
              {discipline.teams.length === 0 ? (
                <p className="muted">{t("teams.noneEntered")}</p>
              ) : (
                <ul className="detail-list">
                  {discipline.teams.map((team) => (
                    <li key={team.id}>
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
                          {team.below_minimum && (
                            <PaidStamp id={team.id} label={t("teams.belowMinimum")} />
                          )}
                        </span>
                      </div>
                      <div className="detail-extra">{t("teams.enteredBy", { name: team.entering_fencer })}</div>
                      {team.members.length > 0 && (
                        <ul className="detail-list">
                          {team.members.map((member, index) => (
                            <li key={index} className="muted">
                              {member.name}
                              {member.club && ` · ${member.club}`}
                              {member.nationality && ` · ${member.nationality}`}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))
        )}
      </div>
    </main>
  );
}
