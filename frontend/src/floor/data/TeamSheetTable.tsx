import { useTranslation } from "react-i18next";

import type { ExportColumn } from "../../export/columns";
import ExportGrid from "../../export/ExportGrid";
import type { SheetPerson, SheetTeam } from "../floorApi";
import { PERSON_COLUMNS, paidText, type SheetField, shown } from "./columns";
import SheetCell from "./SheetCell";

/** A line of the team sheet: a team, numbered, or one of its members
 *  beneath it, as the office's team tab reads (spec floor-data). */
type TeamLine = { id: string; number?: number; team: SheetTeam; member?: SheetPerson };

/** A team discipline's sheet: each team with its paid mark and its own
 *  removal, its members beneath it with their correctable cells. Who fences
 *  for a team on the day is its lineup, set at the desk. */
export default function TeamSheetTable({
  teams,
  locked,
  onCell,
  onRemove,
  onRestore,
}: {
  teams: SheetTeam[];
  locked: boolean;
  onCell: (person: SheetPerson, field: SheetField, raw: string) => void;
  onRemove: (team: SheetTeam) => void;
  onRestore: (team: SheetTeam) => void;
}) {
  const { t } = useTranslation();
  const lines: TeamLine[] = teams.flatMap((team, index) => [
    { id: team.key, number: index + 1, team },
    ...team.members.map((member) => ({ id: `${team.key}/${member.person}`, team, member })),
  ]);
  const columns: ExportColumn<TeamLine>[] = [
    { id: "position", numeric: true, value: (line) => (line.number ? String(line.number) : "") },
    ...PERSON_COLUMNS.map((column) => ({
      id: column.id,
      numeric: column.numeric,
      centered: column.centered,
      value: (line: TeamLine) =>
        line.member
          ? shown(line.member, column.field)
          : column.field === "name"
            ? line.team.name
            : "",
    })),
    {
      id: "paid",
      centered: true,
      value: (line) => (line.member ? "" : paidText(t, line.team.paid)),
    },
    { id: "action", value: () => "" },
  ];

  function cell(line: TeamLine, column: ExportColumn<TeamLine>, index: number) {
    const person = PERSON_COLUMNS.find((candidate) => candidate.id === column.id);
    if (line.member === undefined) {
      if (column.id === "name")
        return <strong className="team-name">{column.value(line, index)}</strong>;
      if (column.id !== "action") return null;
      if (locked) return "";
      return line.team.withdrawn ? (
        <button type="button" className="link-button" onClick={() => onRestore(line.team)}>
          {t("floor.data.restore")}
        </button>
      ) : (
        <button type="button" className="link-button" onClick={() => onRemove(line.team)}>
          {t("floor.data.remove")}
        </button>
      );
    }
    if (person === undefined) return null;
    return (
      <SheetCell
        person={line.member}
        field={person.field}
        heading={column.id}
        locked={locked || line.team.withdrawn}
        onSave={onCell}
      />
    );
  }

  return (
    <ExportGrid
      columns={columns}
      rows={lines}
      cell={cell}
      rowClass={(line) => (line.team.withdrawn ? "row-deleted" : undefined)}
    />
  );
}
