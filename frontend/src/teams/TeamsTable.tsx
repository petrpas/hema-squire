import { useTranslation } from "react-i18next";

import type { ConsoleTeam, ConsoleTeamDiscipline } from "../api";
import TeamTableRow, { COLUMNS } from "./TeamTableRow";

/** One team per discipline, flattened: the row and the discipline it belongs
 *  to, since the table states both and the API nests one inside the other. */
export interface TeamEntry {
  discipline: ConsoleTeamDiscipline;
  team: ConsoleTeam;
}

/** One team discipline's teams as a table, read the way the fencer list is
 *  read: a row per team stating the fencer who entered it and their address,
 *  its member count, and the payment standing of the registration it was
 *  entered on (spec team-disciplines, Organizer's teams view). The discipline
 *  is the tab above, not a column.
 *
 *  The waitlisted teams stand below a capacity line, in waitlist order, as
 *  the public roster draws them: the line says which teams wait, and the
 *  rows' order says in what order. The line also says where admission is,
 *  since the control is not here — admission moves money and opens a payment
 *  window, and the phase that does that is the one showing the queue.
 *
 *  The roster unfolds beside its count rather than printed under every row: a
 *  tournament of eighteen teams is a list to be read, and a roster under each
 *  would make it four pages. */
export default function TeamsTable({
  slug,
  entries,
  onSaved,
  onCancel,
}: {
  slug: string;
  entries: TeamEntry[];
  onSaved: (disciplineSlug: string, team: ConsoleTeam) => void;
  /** Asks for a team's cancellation dialog, which the panel owns: a `dialog`
   *  element cannot stand inside a table body. */
  onCancel: (entry: TeamEntry) => void;
}) {
  const { t } = useTranslation();
  // the server lists them in waitlist order; split rather than trusted to
  // fall seated-first, so the line can never stand between two seated teams
  const seated = entries.filter(({ team }) => !team.waitlisted);
  const waiting = entries.filter(({ team }) => team.waitlisted);
  // counted as the public roster counts: the seated from one, and below the
  // line the waitlist from one again, which is each team's waitlist place
  const row = ({ discipline, team }: TeamEntry, index: number) => (
    <TeamTableRow
      key={team.id}
      slug={slug}
      position={index + 1}
      team={team}
      discipline={discipline}
      onSaved={(saved) => onSaved(discipline.slug, saved)}
      onCancel={() => onCancel({ discipline, team })}
    />
  );

  return (
    <table className="sheet-table">
      <thead>
        <tr>
          <th className="col-gutter" aria-label={t("column.position")} />
          <th>{t("teams.column.team")}</th>
          <th>{t("teams.column.enteringFencer")}</th>
          <th>{t("teams.column.email")}</th>
          <th className="col-center">{t("teams.column.members")}</th>
          <th className="col-center">{t("teams.column.paid")}</th>
          <th className="col-actions" />
        </tr>
      </thead>
      <tbody>
        {seated.map(row)}
        {waiting.length > 0 && (
          <tr className="export-line">
            <td colSpan={COLUMNS}>
              {t("export.line.queue")} · {t("teams.admittedOnQueue")}
            </td>
          </tr>
        )}
        {waiting.map(row)}
      </tbody>
    </table>
  );
}
