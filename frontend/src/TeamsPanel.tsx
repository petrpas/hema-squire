import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ConsoleTeam, type ConsoleTeamDiscipline } from "./api";
import PhaseSummary from "./PhaseSummary";
import CancelTeamDialog from "./teams/CancelTeamDialog";
import TeamsTable, { type TeamEntry } from "./teams/TeamsTable";

/** The Teams phase: the tournament's team entries as one table, carrying the
 *  team agenda (spec: "Organizer's teams view").
 *
 *  It stands immediately after Fencers because the two are read together —
 *  Fencers lists who will fight, this lists the entries they fight under. A
 *  fencer who entered a team and fights nothing is not on the fencer list at
 *  all, so this is the one place that registration's team agenda is offered:
 *  the roster and its log, and cancelling one team of a registration that may
 *  hold several.
 *
 *  Admission from the waitlist is not here. It moves money and opens a payment
 *  window, and the phase that does that is the Queue, which a waitlisted row
 *  says. */
export default function TeamsPanel({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [disciplines, setDisciplines] = useState<ConsoleTeamDiscipline[] | null>(null);
  const [reload, setReload] = useState(0);
  // the dialog lives here rather than on the row: a `dialog` element cannot
  // stand inside a table body
  const [cancelling, setCancelling] = useState<TeamEntry | null>(null);

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

  /** A cancelled team leaves the table at once. Reloaded as well, because the
   *  cancellation repriced its registration and freed a place: what else it
   *  moved is the server's to state. */
  function dropTeam(disciplineSlug: string, teamId: number) {
    setDisciplines(
      (prev) =>
        prev?.map((discipline) =>
          discipline.slug === disciplineSlug
            ? { ...discipline, teams: discipline.teams.filter((team) => team.id !== teamId) }
            : discipline,
        ) ?? prev,
    );
    setReload((n) => n + 1);
  }

  if (disciplines === null) return <p>{t("common.loading")}</p>;

  // one table over the tournament's teams, in the tournament's discipline
  // order and each discipline's own team order
  const entries: TeamEntry[] = disciplines.flatMap((discipline) =>
    discipline.teams.map((team) => ({ discipline, team })),
  );

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        <h1>{t("teams.title")}</h1>
        {/* a team short of its own minimum is the view's outstanding work: it
            is entered, and it cannot compete as it stands */}
        <PhaseSummary
          text={t("console.summary.belowMinimum", {
            count: entries.filter(({ team }) => team.below_minimum).length,
          })}
          onRefresh={() => setReload((n) => n + 1)}
        />
      </div>
      <div className="sheet-scroll">
        {disciplines.length === 0 ? (
          <p className="sheet-empty">{t("teams.empty")}</p>
        ) : entries.length === 0 ? (
          <p className="sheet-empty">{t("teams.noneEntered")}</p>
        ) : (
          <TeamsTable
            slug={slug}
            entries={entries}
            onSaved={replaceTeam}
            onCancel={setCancelling}
          />
        )}
      </div>

      {cancelling !== null && (
        <CancelTeamDialog
          team={cancelling.team}
          discipline={cancelling.discipline}
          onConfirm={async () => {
            await api.cancelTeam(slug, cancelling.team.id);
            setCancelling(null);
            dropTeam(cancelling.discipline.slug, cancelling.team.id);
          }}
          onClose={() => setCancelling(null)}
        />
      )}
    </main>
  );
}
