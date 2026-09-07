import { IconLink } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Transaction } from "../api";
import { formatTransactionAmount } from "../money";
import LinkDialog from "./LinkDialog";
import QueueCard from "./QueueCard";

/** Transactions carrying no VS that resolves to a registration: money that
 *  arrived and belongs to nobody yet.
 *
 *  The message text is shown in full, not truncated — it is usually the only
 *  thing naming who paid, and judging that is the whole of the organizer's
 *  work here.
 */
export default function UnmatchedPanel({
  slug,
  reload,
  onChanged,
}: {
  slug: string;
  /** Bumped by the console whenever the money may have moved — a landing
   *  statement import, the Fio poll, the lifecycle run, a link made or undone.
   *  The queue reloads from it rather than waiting for the organizer. */
  reload: number;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [linking, setLinking] = useState<Transaction | null>(null);

  function refresh() {
    api.unmatchedTransactions(slug).then(
      (data) => {
        setTransactions(data);
        setFailed(false);
      },
      () => {
        setTransactions([]);
        setFailed(true);
      },
    );
  }

  useEffect(refresh, [slug, reload]);

  const unmatched = (transactions ?? []).filter((tx) => tx.status === "unmatched");

  return (
    <>
      <QueueCard
        title={t("payments.unmatched.title")}
        count={transactions === null ? null : unmatched.length}
        loading={transactions === null}
        failed={failed}
      >
        <table className="sheet-table">
          <thead>
            <tr>
              <th>{t("payments.unmatched.date")}</th>
              <th>{t("payments.unmatched.payer")}</th>
              <th>{t("payments.unmatched.amount")}</th>
              <th>{t("payments.unmatched.message")}</th>
              <th className="col-actions" />
            </tr>
          </thead>
          <tbody>
            {unmatched.map((tx) => (
              <tr key={tx.id}>
                <td>{new Date(tx.date).toLocaleDateString("cs")}</td>
                <td>{tx.payer_name ?? "—"}</td>
                <td>{formatTransactionAmount(tx.amount_cents, tx.currency)}</td>
                <td className="muted">{tx.message ?? "—"}</td>
                <td className="col-actions">
                  <button
                    type="button"
                    className="row-action"
                    title={t("payments.unmatched.link")}
                    onClick={() => setLinking(tx)}
                  >
                    <IconLink size={16} stroke={1.5} />
                    <span className="visually-hidden">{t("payments.unmatched.link")}</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </QueueCard>
      {linking && (
        <LinkDialog
          slug={slug}
          transaction={linking}
          onLinked={() => {
            refresh();
            onChanged();
          }}
          onClose={() => setLinking(null)}
        />
      )}
    </>
  );
}
