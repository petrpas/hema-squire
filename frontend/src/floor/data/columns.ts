import type { TFunction } from "i18next";

import { type ExportColumn, POSITION } from "../../export/columns";
import type { SheetPerson, SheetRow } from "../floorApi";

/** A cell of the Data sheet the organizer may correct (spec floor-data, The
 *  sheet is the floor's to correct). The paid mark is not one of them. */
export type SheetField = "name" | "nationality" | "club" | "hr_id" | "rating" | "rank";

/** The person cells of the office Export's discipline columns, in its order
 *  and under its ids, so the headings are `export.column.*` (spec floor-data,
 *  Data shows who the floor will work with). */
export const PERSON_COLUMNS: {
  id: string;
  field: SheetField;
  numeric?: boolean;
  centered?: boolean;
}[] = [
  { id: "name", field: "name" },
  { id: "nat", field: "nationality", centered: true },
  { id: "club", field: "club" },
  { id: "hr_id", field: "hr_id", numeric: true },
  { id: "rating", field: "rating", numeric: true },
  { id: "rank", field: "rank", numeric: true },
];

export function shown(person: SheetPerson, field: SheetField): string {
  const value = person[field];
  return value === null || value === undefined ? "" : String(value);
}

export function paidText(t: TFunction, paid: boolean | null): string {
  return paid === null ? "" : t(paid ? "export.yes" : "export.no");
}

/** A row the grid draws: the person's own row on an individual sheet. */
export type IndividualLine = SheetRow & { id: string };

export function individualColumns(t: TFunction): ExportColumn<IndividualLine>[] {
  return [
    POSITION,
    ...PERSON_COLUMNS.map((column) => ({
      id: column.id,
      numeric: column.numeric,
      centered: column.centered,
      editable: true,
      value: (row: IndividualLine) => shown(row, column.field),
    })),
    { id: "paid", centered: true, value: (row) => paidText(t, row.paid) },
    { id: "action", value: () => "" },
  ];
}

/** Parses what was typed into a cell into what the server stores: a number
 *  for the numeric cells, the text otherwise, and null for an emptied cell,
 *  which returns it to what lies beneath. */
export function parsed(field: SheetField, raw: string): string | number | null {
  const typed = raw.trim();
  if (typed === "") return null;
  if (field === "rating") return Number(typed.replace(",", "."));
  if (field === "hr_id" || field === "rank") return Number(typed);
  return typed;
}

/** An integer cell holds a whole positive number, a rating any number. */
export function validCell(field: SheetField, raw: string) {
  const value = parsed(field, raw);
  if (value === null || typeof value === "string") return null;
  const whole = field === "hr_id" || field === "rank";
  const ok = Number.isFinite(value) && (!whole || (Number.isInteger(value) && value >= 1));
  return ok ? null : { field, code: "not_a_number", params: {} };
}
