import { useTranslation } from "react-i18next";

import type { Currency, ExportRevenue, ExportRevenueLine } from "../api";
import HelpHint from "../HelpHint";
import {
  REVENUE_COLUMNS,
  reconciliationAmount,
  reconciliationLabel,
  revenueBlockTitle,
  revenueCount,
  revenueLabel,
  revenuePrice,
  signedMoney,
} from "./revenue";

function Columns() {
  return (
    <colgroup>
      <col />
      <col className="revenue-col-price" />
      <col className="revenue-col-count" />
      <col className="revenue-col-money" />
      <col className="revenue-col-money" />
    </colgroup>
  );
}

function Line({
  line,
  block,
  currency,
}: {
  line: ExportRevenueLine;
  block: string;
  currency: Currency;
}) {
  const { t } = useTranslation();
  const total = line.kind === "total" || line.kind === "grand_total";
  return (
    <tr className={total ? "revenue-total" : undefined}>
      <td>{revenueLabel(t, line, block)}</td>
      <td className="col-number">{revenuePrice(line, currency)}</td>
      <td className="col-number">{revenueCount(line)}</td>
      <td className="col-number">{signedMoney(line.paid, currency)}</td>
      <td className="col-number">{signedMoney(line.to_pay, currency)}</td>
    </tr>
  );
}

/** The Revenue tab: what each discipline, item and discount has brought in
 *  and has still to bring, then the paid figure reconciled with the payment
 *  journal (spec export-revenue).
 *
 *  One table per block on the Summary's layout: every table has the same
 *  fixed width and the same fixed columns but the name, so every figure stands
 *  under the figure of its kind in the table above. A total is set off by the
 *  strong rule above it, not by weight. */
export default function RevenueTable({ revenue }: { revenue: ExportRevenue | null }) {
  const { t } = useTranslation();
  if (revenue === null) return null;
  const currency = revenue.local_currency;
  return (
    <div className="sheet-scroll summary-scroll">
      {revenue.blocks.map((block) => (
        <table key={block.key} className="sheet-table revenue-table">
          <Columns />
          <thead>
            <tr>
              <th>{revenueBlockTitle(t, block.key)}</th>
              {REVENUE_COLUMNS.map((id) => (
                <th key={id} className="col-number">
                  {t(`export.column.${id}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.lines.map((line, index) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: two lines may share name and price; the block is re-read whole, never reordered
              <Line key={index} line={line} block={block.key} currency={currency} />
            ))}
          </tbody>
        </table>
      ))}
      <table className="sheet-table revenue-table">
        <Columns />
        <tbody>
          <Line line={revenue.total} block="" currency={currency} />
        </tbody>
      </table>
      <table className="sheet-table revenue-table">
        <colgroup>
          <col />
          <col className="revenue-col-money" />
        </colgroup>
        <thead>
          <tr>
            <th>{t("export.revenue.reconciliation")}</th>
            <th className="col-number">{t("export.column.amount")}</th>
          </tr>
        </thead>
        <tbody>
          {revenue.reconciliation.map((line) => (
            <tr
              key={`${line.kind}:${line.lane}`}
              className={line.kind === "journal" ? "revenue-total" : undefined}
            >
              <td>
                {reconciliationLabel(t, line)}
                {/* the labels are short by necessity; what each amount is,
                    and why it stands apart from the lines above, is here */}
                <HelpHint text={t(`export.revenue.hint.${line.kind}`)} />
              </td>
              <td className="col-number">{reconciliationAmount(line, currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
