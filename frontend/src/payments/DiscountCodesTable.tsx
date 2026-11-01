import { useTranslation } from "react-i18next";

import type { DiscountCodeRedemption, DiscountCodeUses } from "../api";
import { formatMoney } from "../money";

/** A code's uses against its limit: `3 / 10`, or `3` where it has none. */
export function usesLine(code: DiscountCodeUses): string {
  const uses = code.max_uses === null ? `${code.uses}` : `${code.uses} / ${code.max_uses}`;
  return `${code.name} ${uses}`;
}

/** Who holds which code and what it took off. Live registrations only, so the
 *  rows always agree with the uses stated beside the tabs. */
export default function DiscountCodesTable({ rows }: { rows: DiscountCodeRedemption[] }) {
  const { t } = useTranslation();
  return (
    <table className="sheet-table">
      <thead>
        <tr>
          <th>{t("payments.codes.fencer")}</th>
          <th>{t("payments.codes.name")}</th>
          <th>{t("payments.codes.code")}</th>
          <th className="col-number">{t("payments.codes.deducted")}</th>
          <th>{t("payments.codes.paid")}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.registration_id}>
            <td>{row.fencer}</td>
            <td>{row.name}</td>
            <td>{row.code}</td>
            <td className="col-number">{formatMoney(row.deducted, row.currency)}</td>
            <td>{row.paid ? t("payments.codes.yes") : t("payments.codes.no")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
