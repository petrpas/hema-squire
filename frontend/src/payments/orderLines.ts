import type { OrderLine } from "../api";

type Translate = (key: string, opts?: Record<string, unknown>) => string;

/** Kinds that are something the order bought rather than a discount on it. */
const ITEM_KINDS = new Set<OrderLine["kind"]>(["item", "rental", "afterparty"]);

/** What an order holds, in a few words: one team named, several counted; each
 *  individual discipline by its short name; the items as how many pieces.
 *  Only what is billed is stated — a placement in a queue is not (spec
 *  payments-console, The registration table states what each order holds).
 *  Null where nothing is billed, which the table reads as absent. */
export function orderSummary(lines: OrderLine[], t: Translate): string | null {
  const billed = lines.filter((line) => !line.queued);
  const teams = billed.filter((line) => line.kind === "team");
  const disciplines = billed.filter((line) => line.kind === "discipline");
  const pieces = billed
    .filter((line) => ITEM_KINDS.has(line.kind))
    .reduce((sum, line) => sum + line.qty, 0);
  const parts: string[] = [];
  const [onlyTeam] = teams;
  if (teams.length === 1 && onlyTeam) parts.push(onlyTeam.label ?? "");
  else if (teams.length > 1) parts.push(t("payments.order.teams", { count: teams.length }));
  for (const line of disciplines) parts.push(line.discipline_slug ?? "");
  if (pieces > 0) parts.push(t("payments.order.items", { count: pieces }));
  const stated = parts.filter(Boolean);
  return stated.length > 0 ? stated.join(" · ") : null;
}

/** The words a line is read by. A team names its discipline beside it, since
 *  a team name says nothing of what it fights in. */
export function lineLabel(line: OrderLine, t: Translate): string {
  switch (line.kind) {
    case "team":
      return `${line.label ?? ""} (${line.discipline_slug ?? ""})`;
    case "discipline":
      return line.discipline_slug ?? "";
    case "item":
      return line.label ?? "";
    case "rental":
      return t("payments.order.rental");
    case "afterparty":
      return t("payments.order.afterparty");
    case "discount":
      return line.label || t("payments.order.discount");
    case "code":
      return t("payments.order.code", { name: line.label ?? "" });
  }
}

/** What the counted lines come to. */
export function countedSum(lines: OrderLine[]): number {
  return lines.filter((line) => !line.queued).reduce((sum, line) => sum + line.amount, 0);
}

/** How far the lines, priced as things stand, are from the total the order
 *  was issued at — non-zero only where a price changed after issuing (spec
 *  payments-console, A difference to the issued total is stated, not hidden).
 *  Null where there is no issued total to compare with. */
export function differenceToIssued(lines: OrderLine[], issued: number | null): number | null {
  if (issued === null) return null;
  return countedSum(lines) - issued;
}
