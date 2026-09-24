import type { TFunction } from "i18next";

import type { ExportSummaryLine } from "../api";

/** The columns of the summary, as the backend's `SUMMARY_COLUMNS` lists them.
 *  No position column: the summary's order is the offer's, and a number
 *  stating a place in it would state nothing. */
export const SUMMARY_COLUMNS = ["item", "paid", "unpaid"] as const;

/** A line's item cell: `LSM (fronta)`, `Triko – XL`, `Triko – neuvedeno`.
 *  The names are the organizer's and stay as written; only the words Squire
 *  adds follow the language `t` speaks. */
export function summaryLabel(t: TFunction, line: ExportSummaryLine): string {
  if (line.kind === "queue") return t("export.summary.queue", { name: line.name });
  if (line.missing) {
    return t("export.summary.option", {
      name: line.name,
      option: t("export.summary.missing"),
    });
  }
  if (line.option !== null) {
    return t("export.summary.option", { name: line.name, option: line.option });
  }
  return line.name;
}

/** The summary as the copy puts it on the clipboard: a header row, then one
 *  line per row with its counts as digits. */
export function summaryTsv(t: TFunction, lines: ExportSummaryLine[]): string {
  return [
    SUMMARY_COLUMNS.map((id) => t(`export.column.${id}`)).join("\t"),
    ...lines.map((line) => [summaryLabel(t, line), line.paid, line.unpaid].join("\t")),
  ].join("\n");
}
