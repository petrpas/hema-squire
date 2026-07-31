import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Transaction, api } from "./api";

/** The flagged-transaction queue for the payments phase: every VS-matched
 *  transaction that did not reach paid/reinstated/refunded automatically,
 *  with the organizer's two explicit resolving actions. */
export default function PaymentsPanel({
  slug,
  onChanged,
}: {
  slug: string;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [errorId, setErrorId] = useState<number | null>(null);

  function refresh() {
    api.unmatchedTransactions(slug).then(setTransactions, () => setTransactions([]));
  }

  useEffect(refresh, [slug]);

  const flagged = (transactions ?? []).filter((tx) => tx.status === "flagged");

  async function reinstate(id: number) {
    setBusyId(id);
    setErrorId(null);
    try {
      await api.reinstateTransaction(slug, id);
      refresh();
      onChanged();
    } catch {
      setErrorId(id);
    } finally {
      setBusyId(null);
    }
  }

  async function markForRefund(id: number) {
    setBusyId(id);
    setErrorId(null);
    try {
      await api.markTransactionForRefund(slug, id);
      refresh();
      onChanged();
    } catch {
      setErrorId(id);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("payments.flagged.title")}</h2>
      {transactions === null ? (
        <p className="rail-hint">{t("common.loading")}</p>
      ) : flagged.length === 0 ? (
        <p className="rail-hint">{t("payments.flagged.empty")}</p>
      ) : (
        <table className="sheet-table">
          <thead>
            <tr>
              <th>{t("payments.flagged.vs")}</th>
              <th>{t("payments.flagged.amount")}</th>
              <th>{t("payments.flagged.reason")}</th>
              <th className="col-actions" />
            </tr>
          </thead>
          <tbody>
            {flagged.map((tx) => (
              <tr key={tx.id}>
                <td>{tx.vs ?? "—"}</td>
                <td>
                  {(tx.amount_cents / 100).toLocaleString("cs", { maximumFractionDigits: 2 })}{" "}
                  {tx.currency}
                </td>
                <td className="muted">
                  {t(`payments.flagged.reasons.${tx.status_reason}`, {
                    defaultValue: tx.status_reason ?? "",
                  })}
                </td>
                <td className="col-actions">
                  {tx.reinstate_available && (
                    <button
                      className="row-action"
                      title={t("payments.flagged.reinstate")}
                      disabled={busyId === tx.id}
                      onClick={() => void reinstate(tx.id)}
                    >
                      {t("payments.flagged.reinstate")}
                    </button>
                  )}
                  <button
                    className="row-action"
                    title={t("payments.flagged.markForRefund")}
                    disabled={busyId === tx.id}
                    onClick={() => void markForRefund(tx.id)}
                  >
                    {t("payments.flagged.markForRefund")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {errorId !== null && <p className="login-error">{t("payments.flagged.actionFailed")}</p>}
    </section>
  );
}
