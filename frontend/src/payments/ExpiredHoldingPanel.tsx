import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Currency, type ExpiredHolding, api } from "../api";
import { formatMoney } from "../money";
import QueueCard from "./QueueCard";

/** Reservations that lapsed while holding money credited to them.
 *
 *  This money is in neither transaction queue — the payment matched and was
 *  credited, and only then did the seat run out of time — so without this card
 *  the console has no sight of it at all.
 *
 *  The list is a work queue, not a log: a reservation since reinstated or
 *  refunded drops off by itself, because the backend filters to those still
 *  expired and still holding credit.
 */
export default function ExpiredHoldingPanel({
  slug,
  reload,
  currency,
}: {
  slug: string;
  /** Bumped by the console whenever the money may have moved — a landing
   *  statement import, the Fio poll, the lifecycle run, a link made or undone.
   *  The queue reloads from it rather than waiting for the organizer. */
  reload: number;

  /** The tournament's own currency: the backend states the credited amount,
   *  not what to call it. */
  currency: Currency;
}) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<ExpiredHolding[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.expiredHolding(slug).then(
      (data) => {
        setRows(data);
        setFailed(false);
      },
      () => {
        setRows([]);
        setFailed(true);
      },
    );
  }, [slug, reload]);

  return (
    <QueueCard
      title={t("payments.expiredHolding.title")}
      count={rows === null ? null : rows.length}
      loading={rows === null}
      failed={failed}
    >
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("payments.expiredHolding.fencer")}</th>
            <th>{t("payments.expiredHolding.vs")}</th>
            <th>{t("payments.expiredHolding.credited")}</th>
            <th>{t("payments.expiredHolding.expiredAt")}</th>
          </tr>
        </thead>
        <tbody>
          {(rows ?? []).map((row) => (
            <tr key={row.registration_id}>
              <td>{row.fencer_name}</td>
              <td>{row.vs}</td>
              <td>
                {formatMoney(row.credited_amount, currency)}
                {row.credited_eur_amount && (
                  <span className="muted"> ({formatMoney(row.credited_eur_amount, "EUR")})</span>
                )}
              </td>
              <td className="muted">{new Date(row.expired_at).toLocaleDateString("cs")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </QueueCard>
  );
}
