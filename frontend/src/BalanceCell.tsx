import { useTranslation } from "react-i18next";

import type { Currency } from "./api";
import { formatMoney } from "./money";

/** What a registration's balance reads in the Payments table.
 *
 *  Three facts share one column, and only one of them is a debt.
 *
 *  **A shortfall states its figure.** A euro transfer the payer's bank
 *  converted lands twenty or forty crowns under the local price; the tolerance
 *  accepts it and the registration reads as paid, and the organizer is still
 *  owed the truth about what reached the account (spec payments).
 *
 *  **An overpayment states that it is one.** It used to print as the negative
 *  figure it is — *−200 Kč* in a column of amounts owed — which is accurate and
 *  unreadable: a reader scanning for what is missing has to stop at every minus
 *  sign and work out that this one means the opposite. The sign carried the
 *  whole meaning and nothing named it (owner decision, 2026-09-10).
 *
 *  **A settled balance states nothing.** A column of *0 Kč* is a column of
 *  noise: every row that is finished looks like a row with a figure to read,
 *  and the handful that want attention stop standing out. Empty says "nothing
 *  here" faster than a zero does, and the fencer's own registration page has
 *  hidden a zero balance all along (owner decision, 2026-09-10).
 *
 *  A row with no registration behind it — an imported line nobody has issued —
 *  keeps its dash. It owes nothing *and has no balance at all*, which is not
 *  the same fact as a balance that came to zero.
 */
export default function BalanceCell({
  amount,
  currency,
}: {
  /** The balance as the backend states it: positive owed, negative over. A
   *  decimal string, as every money figure the API states is. */
  amount: string;
  /** Null until the tournament's detail has arrived beside the sheet, as every
   *  other money cell is — the figure then reads unitless rather than in a
   *  currency nobody has confirmed. */
  currency: Currency | null;
}) {
  const { t } = useTranslation();
  const value = Number(amount);

  // an unparseable figure is written back as it arrived rather than swallowed:
  // a balance the reader cannot see is worse than one they cannot explain
  if (!Number.isFinite(value)) return <>{amount}</>;

  if (value === 0) return null;

  if (value < 0) {
    const over = currency === null ? String(-value) : formatMoney(-value, currency);
    return <span className="balance-over">{t("console.overpaid", { amount: over })}</span>;
  }

  return <>{currency === null ? amount : formatMoney(amount, currency)}</>;
}
