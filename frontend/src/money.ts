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

/** Whether a second, EUR-denominated figure applies to this tournament. */
export function showsEur(
  tournament: Pick<TournamentDetail, "primary_currency" | "eur_payments_enabled" | "eur_rate">,
): boolean {
  return (
    tournament.eur_payments_enabled &&
    tournament.primary_currency !== "EUR" &&
    Number(tournament.eur_rate) > 0
  );
}

/**
 * An amount in the tournament's currency, with the EUR equivalent in
 * parentheses when the tournament takes EUR alongside it. The single decision
 * point for "is there a EUR figure here", so no call site repeats the condition.
 */
export function formatMoneyWithEur(
  amount: number,
  tournament: Pick<TournamentDetail, "primary_currency" | "eur_payments_enabled" | "eur_rate">,
): string {
  const primary = formatMoney(amount, tournament.primary_currency);
  if (!showsEur(tournament)) return primary;
  const eur = amount / Number(tournament.eur_rate);
  return `${primary} (${formatMoney(eur.toFixed(2), "EUR")})`;
}
