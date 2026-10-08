import type { TFunction } from "i18next";

import type { ExportSummaryLine } from "../api";

/** The count columns of every summary table, as the backend writes them.
 *  The first column has no header of its own: each table is headed by what
 *  it counts. No position column: the summary's order is the offer's, and a
 *  number stating a place in it would state nothing. */
export const SUMMARY_COUNTS = ["paid", "unpaid"] as const;

/** One table of the summary: the disciplines with their queues (`category`
 *  empty), or one category's items. */
export interface SummaryGroup {
  category: string;
  lines: ExportSummaryLine[];
}

/** The summary's lines as the tables they are shown in, in the order the
 *  backend states them. A line names a discipline or an item, never which of
 *  the two it is; one table would leave `Šavle` reading as either. */
export function summaryGroups(lines: ExportSummaryLine[]): SummaryGroup[] {
  const groups: SummaryGroup[] = [];
  for (const line of lines) {
    const last = groups[groups.length - 1];
    if (last?.category === line.category) last.lines.push(line);
    else groups.push({ category: line.category, lines: [line] });
  }
  return groups;
}

/** The head of one summary table: the disciplines, or the category. */
export function summaryGroupTitle(t: TFunction, category: string): string {
  return category ? t(`export.category.${category}`) : t("export.summary.disciplines");
}

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

/** The summary as the copy puts it on the clipboard, as the Summary worksheet
 *  holds it: each table headed by what it counts and the two count columns,
 *  its counts as digits, a blank line between two. */
export function summaryTsv(t: TFunction, lines: ExportSummaryLine[]): string {
  const counts = SUMMARY_COUNTS.map((id) => t(`export.column.${id}`));
  return summaryGroups(lines)
    .map((group) =>
      [
        [summaryGroupTitle(t, group.category), ...counts].join("\t"),
        ...group.lines.map((line) => [summaryLabel(t, line), line.paid, line.unpaid].join("\t")),
      ].join("\n"),
    )
    .join("\n\n");
}
