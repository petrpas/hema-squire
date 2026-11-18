import { useTranslation } from "react-i18next";

import type { ExportColumn } from "../../export/columns";
import ExportGrid from "../../export/ExportGrid";
import type { SheetPerson, SheetRow } from "../floorApi";
import { type IndividualLine, individualColumns, PERSON_COLUMNS, type SheetField } from "./columns";
import SheetCell from "./SheetCell";

/** An individual discipline's sheet: the office's grid and columns, in the
 *  order the server sends (seeding order), every person cell correctable
 *  and each row with its own removal while check-in is open (spec
 *  floor-data). A withdrawn entrant stays, struck through. */
export default function SheetTable({
  rows,
  locked,
  onCell,
  onRemove,
  onRestore,
}: {
  rows: SheetRow[];
  locked: boolean;
  onCell: (person: SheetPerson, field: SheetField, raw: string) => void;
  onRemove: (row: SheetRow) => void;
  onRestore: (row: SheetRow) => void;
}) {
  const { t } = useTranslation();
  const lines: IndividualLine[] = rows.map((row) => ({ ...row, id: row.person }));
  const columns = individualColumns(t);

  function cell(row: IndividualLine, column: ExportColumn<IndividualLine>) {
    const person = PERSON_COLUMNS.find((candidate) => candidate.id === column.id);
    if (person !== undefined) {
      return (
        <SheetCell
          person={row}
          field={person.field}
          heading={column.id}
          locked={locked || row.withdrawn}
          onSave={onCell}
        />
      );
    }
    if (column.id !== "action" || locked) return column.id === "action" ? "" : null;
    return row.withdrawn ? (
      <button type="button" className="link-button" onClick={() => onRestore(row)}>
        {t("floor.data.restore")}
      </button>
    ) : (
      <button type="button" className="link-button" onClick={() => onRemove(row)}>
        {t("floor.data.remove")}
      </button>
    );
  }

  return (
    <ExportGrid
      columns={columns}
      rows={lines}
      cell={cell}
      rowClass={(row) => (row.withdrawn ? "row-deleted" : undefined)}
    />
  );
}
