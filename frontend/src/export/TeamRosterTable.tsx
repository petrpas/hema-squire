import { useTranslation } from "react-i18next";

import type { SheetRow } from "../api";
import EditableCell from "../EditableCell";
import { type ExportColumn, ratingOf, TEAM_COLUMNS } from "./columns";
import ExportGrid from "./ExportGrid";
import { teamOrder } from "./ordering";
import { validateRating } from "./rating";

/** A team discipline's tab: its teams, each with its fighters beneath it.
 *
 *  The thing being seeded is a team, and a flat list of fighters with a team
 *  column would hide which four numbers belong together — so the tab is read
 *  as a list of teams and numbered as one (spec export-tables, A team tab
 *  reads as teams with their fighters).
 *
 *  The ratings are the fighters'. A team carries none of its own, and nothing
 *  here computes one from its roster: what a tournament makes of four
 *  fighters' ratings when it seeds is the tournament's decision, and the
 *  organizer seeds with the numbers this tab hands them. That is also why
 *  there is no seeding tick — there is nothing on a team row to order by.
 */
export default function TeamRosterTable({
  rows,
  slug,
  lineKind,
  edited,
  onRate,
}: {
  rows: SheetRow[];
  slug: string;
  lineKind: "queue" | "capacity";
  /** Whether this row's rating carries an organizer's correction, marked the
   *  way every other manual edit is. */
  edited: (row: SheetRow) => boolean;
  onRate: (row: SheetRow, raw: string) => void;
}) {
  const { t } = useTranslation();
  const { rows: ordered, line, numbers } = teamOrder(rows, lineKind);
  const columns = TEAM_COLUMNS(t, slug, numbers);

  function cell(row: SheetRow, column: ExportColumn, index: number) {
    const isTeam = row._team !== undefined;
    // the team's own line of the tab, read as the head of the rows under it
    if (isTeam) {
      // the rating cell does not open on a team row: a team has no rating, and
      // a correction typed there would be a figure of nobody's
      return column.id === "name" ? <strong>{column.value(row, index)}</strong> : null;
    }
    if (!column.editable) return null;
    const display = column.value(row, index);
    return (
      <EditableCell
        label={t("export.column.rating")}
        display={edited(row) ? <span className="cell-edited">{display}</span> : display || "—"}
        value={ratingOf(row, slug)}
        onSave={(raw) => onRate(row, raw)}
        validate={validateRating}
      />
    );
  }

  return <ExportGrid columns={columns} rows={ordered} line={line} cell={cell} />;
}
