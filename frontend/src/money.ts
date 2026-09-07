import type { Currency, TournamentDetail } from "./api";

// The unit written after an amount, per currency code. Adding a currency means
// extending this table — no locale message carries a unit (design D2).
const CURRENCY_SYMBOLS: Record<Currency, string> = {
  CZK: "Kč",
  EUR: "€",
};

/** The figure alone, grouped for the active locale. A value that is not a
 *  number is written back as it arrived rather than as `NaN`. */
function grouped(amount: number | string): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  return Number.isFinite(value)
    ? value.toLocaleString("cs", { maximumFractionDigits: 2 })
    : String(amount);
}

/** An amount with its currency unit, grouped for the active locale. */
export function formatMoney(amount: number | string, currency: Currency): string {
  return `${grouped(amount)} ${CURRENCY_SYMBOLS[currency]}`;
}

function isKnownCurrency(code: string): code is Currency {
  return code in CURRENCY_SYMBOLS;
}

/** A bank transaction's amount, in the currency the statement named it in.
 *
 *  Separate from `formatMoney` because the two currencies are not the same
 *  kind of thing. A tournament prices in a closed set the app holds a unit
 *  for; a statement carries whatever the bank sent, and a CZK account can
 *  receive a transfer in any currency at all. A code with no unit here is
 *  written out as itself — the organizer needs to see that a payment arrived
 *  in something other than what the tournament prices in, and the code is the
 *  only thing that says so.
 *
 *  Takes haléře/cents, the unit bank amounts are stored in. */
export function formatTransactionAmount(amountCents: number, currency: string): string {
  const amount = amountCents / 100;
  return isKnownCurrency(currency)
    ? formatMoney(amount, currency)
    : `${grouped(amount)} ${currency}`;
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
