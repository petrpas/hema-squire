import { useTranslation } from "react-i18next";

import type { OrderLines } from "../api";
import { formatMoney } from "../money";
import { differenceToIssued, lineLabel } from "./orderLines";

/** An unfolded order: one row per line under the order's own row, each amount
 *  standing in the table's amount column so the lines read as what the
 *  order's amount is made of (spec payments-console, Every order unfolds into
 *  its priced lines).
 *
 *  A queued placement is listed with the price it would carry, faded and in
 *  italic, and counted in nothing. Where the lines, priced as things stand, do
 *  not come to the issued total, a closing line states by how much: the total
 *  stays what it was issued at, and the organizer settles the gap with the
 *  tools that exist for it (design payments-roster-by-order D5). */
export default function OrderLineRows({
  order,
  issued,
  columns,
  trailing,
}: {
  order: OrderLines;
  /** the order's issued local total, null where it has none */
  issued: number | null;
  /** the table's data columns, so each line can put its amount under the
   *  amount column */
  columns: string[];
  /** cells after the data columns, the row-actions column where there is one */
  trailing: number;
}) {
  const { t } = useTranslation();
  const amountAt = columns.indexOf("total_amount");
  // the columns before the amount hold the line's words; those after it, and
  // the actions, are blank
  const before = Math.max(amountAt, 1);
  const after = columns.length - amountAt - 1 + trailing;
  const difference = differenceToIssued(order.lines, issued);

  const showsDifference = difference !== null && difference !== 0;
  const lastKey = showsDifference ? "difference" : `line-${order.lines.length - 1}`;

  function row(key: string, label: string, amount: number, queued = false) {
    // the last line closes the order with the table's rule, so the next
    // registration does not read as one more of its lines
    const className = [
      "order-line",
      queued ? "order-line-queued" : "",
      key === lastKey ? "order-line-last" : "",
    ]
      .filter(Boolean)
      .join(" ");
    return (
      <tr key={key} className={className}>
        <td className="col-gutter" />
        <td className="col-index" />
        <td colSpan={before}>
          {label}
          {/* the fading says it to the eye; this says it to a reader */}
          {queued && <span className="visually-hidden"> {t("payments.order.queued")}</span>}
        </td>
        <td className="col-number">{formatMoney(amount, order.currency)}</td>
        {after > 0 && <td colSpan={after} />}
      </tr>
    );
  }

  return (
    <>
      {order.lines.map((line, index) =>
        row(
          `line-${index}`,
          line.qty > 1 ? `${lineLabel(line, t)} × ${line.qty}` : lineLabel(line, t),
          line.amount,
          line.queued,
        ),
      )}
      {showsDifference && row("difference", t("payments.order.difference"), -difference)}
    </>
  );
}
