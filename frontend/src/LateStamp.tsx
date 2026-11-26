import { useTranslation } from "react-i18next";

import type { LatePayment, SheetRow } from "./api";
import { dayIn } from "./momentText";
import { formatMoney } from "./money";
import PaidStamp from "./PaidStamp";

/** The mark an expired registration with money against it carries in its
 *  state cell: the paid stamp's shape in a faded ink, reading "Pozdě".
 *
 *  Never the paid stamp. The registration is expired and the lifecycle wins
 *  over the money (spec `payment-ledger`); the mark exists so the organizer
 *  finds the money, which otherwise sits only in a table nobody is pointed at
 *  (spec `payments-console`, An expired registration holding money is marked
 *  late).
 *
 *  A button only where `onOpen` is given — the Payments phase, where the money
 *  tables are. Elsewhere it states the same fact and leads nowhere. */
export default function LateStamp({
  row,
  late,
  onOpen,
}: {
  row: SheetRow;
  late: LatePayment;
  onOpen?: (late: LatePayment) => void;
}) {
  const { t } = useTranslation();
  const amount = formatMoney(late.amount, late.currency);
  let title: string;
  if (late.table === "uncredited") {
    // a bare day as the bank stated it, spelled the way the uncredited table
    // beside it spells the same date
    const day = late.day ? new Date(late.day).toLocaleDateString("cs") : "—";
    title =
      late.count > 1
        ? t("console.late.uncreditedSeveral", { count: late.count, day, amount })
        : t("console.late.uncredited", { day, amount });
  } else {
    title = row.expires_at
      ? t("console.expiredHolding.title", { day: dayIn(row.expires_at, null), amount })
      : t("console.expiredHolding.titleUndated", { amount });
  }
  const stamp = <PaidStamp id={row.id} label={t("console.late.label")} muted />;
  if (!onOpen) {
    return (
      <span className="late-stamp" title={title}>
        {stamp}
      </span>
    );
  }
  return (
    <button type="button" className="late-stamp" title={title} onClick={() => onOpen(late)}>
      {stamp}
    </button>
  );
}
