import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { Currency } from "./api";
import { formatMoney } from "./money";

/** What a hand-settled registration's balance reads.
 *
 *  Nothing is due, so the figure the outstanding column would otherwise show
 *  is not what the row owes. Showing the full total there reads as a fault in
 *  every roster it appears in, so the column says what is actually the case
 *  (spec etl-console).
 *
 *  **How much was forgiven, where that is not everything.** A waiver forgives
 *  whatever stood when it was given, and money may already have arrived
 *  against the price: a fencer who paid 1 250 Kč of 1 750 Kč and had the rest
 *  written off had a cell reading the same *odpuštěno* as one who paid
 *  nothing, and the two are not the same fact. So the cell names the sum where
 *  a payment stands behind it — *odpuštěno 500 Kč* — and says *odpuštěno vše*
 *  where the whole price was forgiven (owner decision, 2026-09-06). Nothing
 *  about the registration changes; this is the wording only.
 *
 *  `amount` is what the waiver forgave, null where it forgave the whole price.
 *  A waiver written on a registration the money had already covered has
 *  nothing left to name and reads as the bare word.
 *
 *  **The reason on hover.** A reason is the organizer's own sentence and runs
 *  as long as one — *volný vstup za čtvrté místo dosažené v loňském roce* —
 *  and a money column set to the width of the longest of them stops being a
 *  money column. The cell states the fact, which is the only part the table is
 *  reading for; the sentence behind it opens where it is asked for.
 *
 *  The word is its own marker, in `HelpHint`'s idiom but carrying none of its
 *  marking — no glyph, no underline, no help cursor. The words in a column of
 *  figures are conspicuous enough to be tried, and each of those would have
 *  been a second mark saying only that the first one has more behind it. A row
 *  waived without a reason — which the organizer may do where Squire collects
 *  nothing — has nothing to open at all.
 */
export default function WaivedBalance({
  reason,
  amount = null,
  currency = null,
}: {
  reason: string | null;
  amount?: string | null;
  currency?: Currency | null;
}) {
  const { t } = useTranslation();
  const hintId = useId();
  const word = waivedWord(amount, currency, t);

  if (!reason) return <span className="waived-balance">{word}</span>;

  return (
    <span className="help-hint waived-hint">
      {/* biome-ignore lint/a11y/noNoninteractiveTabindex: a tooltip trigger must be focusable to be read, and activates nothing */}
      <span className="waived-balance waived-marker" tabIndex={0} aria-describedby={hintId}>
        {word}
      </span>
      <span role="tooltip" id={hintId} className="help-hint-box">
        {reason}
      </span>
    </span>
  );
}

function waivedWord(
  amount: string | null,
  currency: Currency | null,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (amount === null) return t("console.waived_all");
  // a waiver written where the money had already covered the price forgave
  // nothing, and there is no sum to name
  const value = Number(amount);
  if (!Number.isFinite(value) || value <= 0) return t("console.waived");
  // unitless until the tournament's detail has arrived beside the sheet, as
  // every other money cell is
  return t("console.waived_amount", {
    amount: currency === null ? amount : formatMoney(amount, currency),
  });
}
