import type { TFunction } from "i18next";

import type { Currency, ExportReconciliationLine, ExportRevenue, ExportRevenueLine } from "../api";
import { formatMoney } from "../money";

/** The columns of every priced revenue table after its name, as the screen
 *  heads them: one count cell, `12/18`. */
export const REVENUE_COLUMNS = ["price", "count", "paid", "to_pay"] as const;

/** The same columns as the copy and the Revenue worksheet write them: the
 *  count as two cells, so that both stay numbers (design export-revenue D9). */
const REVENUE_TSV_COLUMNS = ["price", "count_paid", "count_all", "paid", "to_pay"] as const;

/** The head of one revenue table: the entry fees, or the category. */
export function revenueBlockTitle(t: TFunction, key: string): string {
  return key ? t(`export.category.${key}`) : t("export.revenue.entry");
}

/** A line's name cell. The organizer's names stay as written; `Sleva`,
 *  `celkem` and the block names follow the language `t` speaks. */
export function revenueLabel(t: TFunction, line: ExportRevenueLine, block: string): string {
  if (line.kind === "total") {
    return t("export.revenue.total", { name: revenueBlockTitle(t, block) });
  }
  if (line.kind === "grand_total") return t("export.revenue.grand_total");
  if (line.kind === "discount") return t("export.revenue.discount", { name: line.name });
  // a legacy flat fee bills no item, and is named by its block
  if (line.kind === "fee") return revenueBlockTitle(t, block);
  return line.name;
}

/** A reconciliation line's label; the EUR lane's says so, since the copy
 *  carries no unit to tell the two lanes apart. */
export function reconciliationLabel(t: TFunction, line: ExportReconciliationLine): string {
  const label = t(`export.revenue.${line.kind}`, { count: line.count ?? 0 });
  return line.lane === "eur" ? t("export.revenue.eur", { label }) : label;
}

/** An amount with its unit and a true minus (`−3 200 Kč`). */
export function signedMoney(amount: number, currency: Currency): string {
  const unsigned = formatMoney(Math.abs(amount), currency);
  return amount < 0 ? `−${unsigned}` : unsigned;
}

/** The price cell on screen: the unit price, a discount's `−400 Kč` or
 *  `−10 %`, nothing on a total. */
export function revenuePrice(line: ExportRevenueLine, currency: Currency): string {
  if (line.price === null) return "";
  if (line.percent) return `${line.price < 0 ? "−" : ""}${Math.abs(line.price)} %`;
  return signedMoney(line.price, currency);
}

/** The count cell on screen, paid over all: `12/18`. */
export function revenueCount(line: ExportRevenueLine): string {
  return `${line.paid_count}/${line.count}`;
}

/** A reconciliation line's amount on screen, in its lane's currency; a
 *  count where the line states one alone. */
export function reconciliationAmount(line: ExportReconciliationLine, currency: Currency): string {
  if (line.amount_cents === null) return String(line.count ?? 0);
  return signedMoney(line.amount_cents / 100, line.lane === "eur" ? "EUR" : currency);
}

function priceCell(line: ExportRevenueLine): string {
  if (line.price === null) return "";
  // a percentage keeps its `%`: read as a number it would be a tenth of a crown
  return line.percent ? `${line.price} %` : String(line.price);
}

function lineCells(t: TFunction, line: ExportRevenueLine, block: string): string {
  return [
    revenueLabel(t, line, block),
    priceCell(line),
    line.paid_count,
    line.count,
    line.paid,
    line.to_pay,
  ].join("\t");
}

/** The revenue as the copy puts it on the clipboard, as the Revenue worksheet
 *  holds it: each block headed by its name and the column labels, the grand
 *  total, then the reconciliation, a blank line between two tables. Amounts
 *  are digits without a unit, so a spreadsheet sums them. */
export function revenueTsv(t: TFunction, revenue: ExportRevenue): string {
  const columns = REVENUE_TSV_COLUMNS.map((id) => t(`export.column.${id}`));
  const tables = revenue.blocks.map((block) =>
    [
      [revenueBlockTitle(t, block.key), ...columns].join("\t"),
      ...block.lines.map((line) => lineCells(t, line, block.key)),
    ].join("\n"),
  );
  tables.push(lineCells(t, revenue.total, ""));
  tables.push(
    [
      [t("export.revenue.reconciliation"), t("export.column.amount")].join("\t"),
      ...revenue.reconciliation.map((line) =>
        [
          reconciliationLabel(t, line),
          line.amount_cents === null ? (line.count ?? 0) : line.amount_cents / 100,
        ].join("\t"),
      ),
    ].join("\n"),
  );
  return tables.join("\n\n");
}

/** How many lines the copy carried, as its confirmation states it. */
export function revenueLineCount(revenue: ExportRevenue): number {
  return (
    revenue.blocks.reduce((sum, block) => sum + block.lines.length, 0) +
    1 +
    revenue.reconciliation.length
  );
}
