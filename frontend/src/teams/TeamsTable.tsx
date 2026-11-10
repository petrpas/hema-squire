import { useTranslation } from "react-i18next";

import type { ConsoleTeam, ConsoleTeamDiscipline } from "../api";
import TeamTableRow from "./TeamTableRow";

/** One team per discipline, flattened: the row and the discipline it belongs
 *  to, since the table states both and the API nests one inside the other. */
export interface TeamEntry {
  discipline: ConsoleTeamDiscipline;
  team: ConsoleTeam;
}

/** The tournament's teams as one table, read the way the fencer list is read:
 *  a row per team stating its discipline, the fencer who entered it, its
 *  member count against the discipline's bounds, its waitlist position where
 *  it waits, and the payment standing of the registration it was entered on
 *  (spec team-disciplines, Organizer's teams view).
 *
 *  The roster is reachable from its team's row rather than printed under every
 *  row: a tournament of eighteen teams is a list to be read, and a roster
 *  under each would make it four pages. */
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

  return (
    <table className="sheet-table">
      <thead>
        <tr>
          <th>{t("teams.column.team")}</th>
          <th>{t("teams.column.discipline")}</th>
          <th>{t("teams.column.enteringFencer")}</th>
          <th>{t("teams.column.members")}</th>
          <th>{t("teams.column.waitlist")}</th>
          <th>{t("teams.column.paid")}</th>
          <th className="col-actions" />
        </tr>
      </thead>
      <tbody>
        {entries.map(({ discipline, team }) => (
          <TeamTableRow
            key={team.id}
            slug={slug}
            team={team}
            discipline={discipline}
            onSaved={(saved) => onSaved(discipline.slug, saved)}
            onCancel={() => onCancel({ discipline, team })}
          />
        ))}
      </tbody>
    </table>
  );
}
