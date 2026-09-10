import type { TFunction } from "i18next";

import type { SheetRow } from "../api";

/** The columns of the export tables, declared once.
 *
 *  Three surfaces read them — the tables on screen, the TSV the copy action
 *  puts on the clipboard, and (through the backend's own list of the same
 *  columns) the spreadsheet — so a column is described here and nowhere else:
 *  its heading key, the text it states, and whether it is the organizer's to
 *  correct. A column added to a table without a value function would be a
 *  header with no cells under it, which the type forbids.
 */
export interface ExportColumn {
  /** Stable identity, matching the backend's column ids so the two lists can
   *  be compared by eye. Never the heading, which is a translation. */
  id: string;
  /** The rating cell, and only it, opens for editing (spec export-tables, The
   *  rating is the organizer's to correct). */
  editable?: boolean;
  value: (row: SheetRow) => string;
}

const text = (value: unknown): string =>
  value === null || value === undefined ? "" : String(value);

export const NAME: ExportColumn = { id: "name", value: (row) => text(row.name) };
export const NATIONALITY: ExportColumn = { id: "nat", value: (row) => text(row.nationality) };
export const CLUB: ExportColumn = { id: "club", value: (row) => text(row.club) };
export const HR_ID: ExportColumn = { id: "hr_id", value: (row) => text(row.hr_id) };
export const DISCIPLINES: ExportColumn = {
  id: "disciplines",
  value: (row) => (row.disciplines ?? []).join(", "),
};

/** Yes or no and nothing else. A registration settled short of its total reads
 *  yes here; what it still owes is stated in the Payments phase, which is where
 *  that shortfall is worked — these tables are read by a check-in desk and
 *  consumed by a spreadsheet downstream, where a column that is sometimes a
 *  word and sometimes a sum can be neither counted nor filtered. */
export function paidColumn(t: TFunction): ExportColumn {
  return { id: "paid", value: (row) => t(row.paid ? "export.yes" : "export.no") };
}

export function ratingColumn(slug: string): ExportColumn {
  return {
    id: "rating",
    editable: true,
    value: (row) => text(ratingOf(row, slug)),
  };
}

export function rankColumn(slug: string): ExportColumn {
  return { id: "rank", value: (row) => text(rankOf(row, slug)) };
}

/** What a fencer bought in one category, as the item tab states it: the item,
 *  the answer to its option where it declares one, and the quantity where it is
 *  more than one. */
export function itemsColumn(category: string): ExportColumn {
  return {
    id: "items",
    value: (row) =>
      selectionsOf(row, category)
        .map((selection) => {
          const label =
            selection.option === null || selection.option === undefined || selection.option === ""
              ? selection.name
              : `${selection.name} (${selection.option})`;
          return selection.qty > 1 ? `${label} x${selection.qty}` : label;
        })
        .join(", "),
  };
}

export interface ItemSelection {
  name: string;
  qty: number;
  option: string | null;
}

export function selectionsOf(row: SheetRow, category: string): ItemSelection[] {
  const extras = row.extras as Record<string, ItemSelection[]> | undefined;
  return extras?.[category] ?? [];
}

/** The rating this row states for one discipline: the organizer's correction
 *  where they made one, the fetched figure otherwise. The row carries only the
 *  one value, because the correction is replayed over the fetch before the row
 *  ever leaves the server. */
export function ratingOf(row: SheetRow, slug: string): number | null {
  const ratings = row.ratings as Record<string, number | null> | undefined;
  return ratings?.[slug] ?? null;
}

export function rankOf(row: SheetRow, slug: string): number | null {
  const ranks = row.ranks as Record<string, number | null> | undefined;
  return ranks?.[slug] ?? null;
}

export const FENCERS_COLUMNS = (t: TFunction): ExportColumn[] => [
  NAME,
  NATIONALITY,
  CLUB,
  HR_ID,
  DISCIPLINES,
  paidColumn(t),
];

export const ROSTER_COLUMNS = (t: TFunction, slug: string): ExportColumn[] => [
  NAME,
  NATIONALITY,
  CLUB,
  HR_ID,
  ratingColumn(slug),
  rankColumn(slug),
  paidColumn(t),
];

export const ITEM_COLUMNS = (t: TFunction, category: string): ExportColumn[] => [
  NAME,
  NATIONALITY,
  CLUB,
  itemsColumn(category),
  paidColumn(t),
];

/** The visible table as tab-separated values with a header row, in the order
 *  and with the filter on screen.
 *
 *  Marker and layout do not travel: the capacity line is not a row here, and a
 *  manual-edit marking is not a character. What travels is the values (spec
 *  export-tables, A table leaves by the clipboard). */
export function toTsv(columns: ExportColumn[], rows: SheetRow[], header: (id: string) => string) {
  const lines = [columns.map((column) => header(column.id)).join("\t")];
  for (const row of rows) {
    lines.push(columns.map((column) => column.value(row)).join("\t"));
  }
  return lines.join("\n");
}
