import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Transaction, api } from "../api";
import QueueCard from "./QueueCard";

/** The flagged-transaction queue: every VS-matched transaction that did not
 *  reach paid/reinstated/refunded automatically, with the organizer's two
 *  explicit resolving actions.
 *
 *  One queue of the payments phase, not the phase itself — the name it used to
 *  carry claimed the whole domain while implementing this one list. */
export default function FlaggedPanel({
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
  const [busyId, setBusyId] = useState<number | null>(null);
  const [errorId, setErrorId] = useState<number | null>(null);

  const [failed, setFailed] = useState(false);

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
    <QueueCard
      title={t("payments.flagged.title")}
      count={transactions === null ? null : flagged.length}
      loading={transactions === null}
      failed={failed}
    >
      <>
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
        {errorId !== null && <p className="login-error">{t("payments.flagged.actionFailed")}</p>}
      </>
    </QueueCard>
  );
}
