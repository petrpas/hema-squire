import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ConsoleTeam, type ConsoleTeamDiscipline } from "./api";
import PhaseSummary from "./PhaseSummary";
import TeamRow from "./teams/TeamRow";

/** Per team discipline, the teams entered into it, each with its roster, the
 *  editor for that roster and its log (spec: "Organizer's teams view").
 *
 *  Editing is here because a team arrives at the venue and the fencer who
 *  entered it cannot always reach their own editor. No other action is: no
 *  cancellation, and no admission — that is the Queue phase's, which a
 *  waitlisted team's row says. Those controls do not exist here rather than
 *  existing disabled. */
export default function TeamsPanel({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [disciplines, setDisciplines] = useState<ConsoleTeamDiscipline[] | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    api.consoleTeams(slug).then(setDisciplines, () => setDisciplines([]));
  }, [slug, reload]);

  /** A saved roster lands back in the discipline it belongs to, so the member
   *  count, the below-minimum mark and the log the response carries all move
   *  together without a reload. */
  function replaceTeam(disciplineSlug: string, saved: ConsoleTeam) {
    setDisciplines(
      (prev) =>
        prev?.map((discipline) =>
          discipline.slug === disciplineSlug
            ? {
                ...discipline,
                teams: discipline.teams.map((team) => (team.id === saved.id ? saved : team)),
              }
            : discipline,
        ) ?? prev,
    );
  }

  if (disciplines === null) return <p>{t("common.loading")}</p>;

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        <h1>{t("teams.title")}</h1>
        {/* a team short of its own minimum is the view's outstanding work: it
            is entered, and it cannot compete as it stands */}
        <PhaseSummary
          text={t("console.summary.belowMinimum", {
            count: disciplines.reduce(
              (total, discipline) =>
                total + discipline.teams.filter((team) => team.below_minimum).length,
              0,
            ),
          })}
          onRefresh={() => setReload((n) => n + 1)}
        />
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
                    <TeamRow
                      key={team.id}
                      slug={slug}
                      team={team}
                      discipline={discipline}
                      onSaved={(saved) => replaceTeam(discipline.slug, saved)}
                    />
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
