import { IconArrowBackUp } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type CreditedTransaction, type CreditReversal } from "../api";
import Modal from "../Modal";
import { formatTransactionAmount } from "../money";
import QueueCard from "./QueueCard";

/** The transactions holding a live credit — the bank half of the ledger, beside
 *  the hand-recorded half.
 *
 *  Such a transaction sits in none of the resolution queues: the matcher
 *  resolved it and the money was credited, so it is neither unmatched nor
 *  flagged, and a credit an automatic VS match decided leaves no payment link
 *  to list it under. The console could therefore see a credited transaction
 *  only where an organizer had linked it by hand — which is the one case that
 *  already had a way back. This view is where the others get one.
 *
 *  Reversing states what it will do before it is confirmed, and asks the
 *  preflight rather than reading the row it already has: the consequence is a
 *  derivation, and what was true when the list loaded may not be true now.
 */
export default function CreditedPanel({
  slug,
  reload,
  onChanged,
}: {
  slug: string;
  /** Bumped by the console whenever the money may have moved. */
  reload: number;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [transactions, setTransactions] = useState<CreditedTransaction[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [reversing, setReversing] = useState<CreditedTransaction | null>(null);
  const [preflight, setPreflight] = useState<CreditReversal | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);

  function refresh() {
    api.creditedTransactions(slug).then(
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

  function open(transaction: CreditedTransaction) {
    setActionFailed(false);
    setPreflight(null);
    setReversing(transaction);
    api.reversalPreflight(slug, transaction.id).then(setPreflight, () => setPreflight(null));
  }

  function close() {
    setReversing(null);
    setPreflight(null);
  }

  async function reverse(transaction: CreditedTransaction) {
    setBusy(true);
    setActionFailed(false);
    try {
      await api.reverseTransactionCredit(slug, transaction.id);
      close();
      refresh();
      onChanged();
    } catch {
      setActionFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const unsettled = (preflight?.registrations ?? []).filter((row) => row.unsettles);

  return (
    <>
      <QueueCard
        title={t("payments.credited.title")}
        count={transactions === null ? null : transactions.length}
        loading={transactions === null}
        failed={failed}
      >
        <table className="sheet-table">
          <thead>
            <tr>
              <th>{t("payments.credited.date")}</th>
              <th>{t("payments.credited.payer")}</th>
              <th>{t("payments.credited.amount")}</th>
              <th>{t("payments.credited.registrations")}</th>
              <th className="col-actions" />
            </tr>
          </thead>
          <tbody>
            {(transactions ?? []).map((tx) => (
              <tr key={tx.id}>
                <td>{new Date(tx.date).toLocaleDateString("cs")}</td>
                <td>{tx.payer_name ?? "—"}</td>
                <td>{formatTransactionAmount(tx.amount_cents, tx.currency)}</td>
                {/* one transaction may have covered several registrations —
                    that is what a payment link is — and each of them is its own
                    credit, so the row names all of them rather than the one the
                    matcher happened to resolve to */}
                <td className="muted">
                  {tx.credits.map((credit) => credit.fencer_name).join(", ") || "—"}
                </td>
                <td className="col-actions">
                  <button
                    type="button"
                    className="row-action"
                    title={t("payments.credited.reverse")}
                    onClick={() => open(tx)}
                  >
                    <IconArrowBackUp size={16} stroke={1.5} />
                    <span className="visually-hidden">{t("payments.credited.reverse")}</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </QueueCard>
      {reversing && (
        <Modal onClose={close}>
          <div className="modal">
            <h2>{t("payments.credited.reverseTitle")}</h2>
            <p>
              {t("payments.credited.reverseBody", {
                amount: formatTransactionAmount(reversing.amount_cents, reversing.currency),
              })}
            </p>
            {/* the consequence, stated before it happens rather than found
                afterwards on a roster that stopped saying paid */}
            {preflight === null ? (
              <p className="rail-hint">{t("payments.credited.checking")}</p>
            ) : (
              <p className="rail-hint">
                {unsettled.length > 0
                  ? t("payments.credited.reverseUnsettles", {
                      names: unsettled.map((row) => row.fencer_name).join(", "),
                    })
                  : t("payments.credited.reverseNoneUnsettle")}
              </p>
            )}
            {actionFailed && <p className="login-error">{t("payments.credited.actionFailed")}</p>}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={close}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={busy || preflight === null}
                onClick={() => void reverse(reversing)}
              >
                {t("payments.credited.reverseConfirm")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
