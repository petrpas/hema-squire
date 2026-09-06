import { IconArrowBackUp, IconReceiptRefund } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Transaction, api } from "../api";
import { formatMoney } from "../money";
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
                  {/* what settled this registration, where a person did. The
                      organizer is deciding whether this is further money or
                      the same money arriving twice, and that decision needs
                      the earlier act in front of it (spec payments-console) */}
                  {tx.settled_by_recorded_payment && (
                    <div>
                      {t("payments.flagged.settledByPayment", {
                        amount: formatMoney(
                          tx.settled_by_recorded_payment.amount,
                          tx.settled_by_recorded_payment.currency,
                        ),
                        date: new Date(
                          tx.settled_by_recorded_payment.received_on,
                        ).toLocaleDateString("cs"),
                      })}
                    </div>
                  )}
                  {tx.settled_by_hand_reason && (
                    <div>
                      {t("payments.flagged.settledByHand", {
                        reason: tx.settled_by_hand_reason,
                      })}
                    </div>
                  )}
                </td>
                <td className="col-actions">
                  <div className="row-actions">
                    {tx.reinstate_available && (
                      <button
                        className="row-action"
                        title={t("payments.flagged.reinstate")}
                        disabled={busyId === tx.id}
                        onClick={() => void reinstate(tx.id)}
                      >
                        <IconArrowBackUp size={16} stroke={1.5} />
                        <span className="visually-hidden">
                          {t("payments.flagged.reinstate")}
                        </span>
                      </button>
                    )}
                    <button
                      className="row-action"
                      title={t("payments.flagged.markForRefund")}
                      disabled={busyId === tx.id}
                      onClick={() => void markForRefund(tx.id)}
                    >
                      <IconReceiptRefund size={16} stroke={1.5} />
                      <span className="visually-hidden">
                        {t("payments.flagged.markForRefund")}
                      </span>
                    </button>
                  </div>
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
