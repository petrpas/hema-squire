import type { Currency, TournamentDetail } from "./api";

// The unit written after an amount, per currency code. Adding a currency means
// extending this table — no locale message carries a unit (design D2).
const CURRENCY_SYMBOLS: Record<Currency, string> = {
  CZK: "Kč",
  EUR: "€",
};

/** An amount with its currency unit, grouped for the active locale. */
export function formatMoney(amount: number | string, currency: Currency): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  const grouped = Number.isFinite(value)
    ? value.toLocaleString("cs", { maximumFractionDigits: 2 })
    : String(amount);
  return `${grouped} ${CURRENCY_SYMBOLS[currency]}`;
}

/** Whether EUR is an accepted second currency alongside the local one. False
 *  for an EUR-priced tournament — its local figure already is the EUR one.
 *  Does not depend on eur_rate, which is a Setup convenience only. */
export function showsEur(
  tournament: Pick<TournamentDetail, "local_currency" | "eur_payments_enabled">,
): boolean {
  return tournament.eur_payments_enabled && tournament.local_currency !== "EUR";
}

/**
 * A stored local-currency amount with the stored EUR amount in parentheses
 * when the tournament takes EUR alongside it. Neither figure is ever computed
 * from the other — both are passed in as already-stored amounts. The single
 * decision point for "is there a EUR figure here", so no call site repeats
 * the condition.
 */
export function formatMoneyWithEur(
  localAmount: number | string,
  eurAmount: number | string | null | undefined,
  tournament: Pick<TournamentDetail, "local_currency" | "eur_payments_enabled">,
): string {
  const primary = formatMoney(localAmount, tournament.local_currency);
  if (!showsEur(tournament) || eurAmount === null || eurAmount === undefined) return primary;
  return `${primary} (${formatMoney(eurAmount, "EUR")})`;
}
