import { IconTrash } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ManualPayment } from "../api";
import Modal from "../Modal";
import { formatMoney } from "../money";
import QueueCard from "./QueueCard";

/** The payments the organizer recorded by hand — money that arrived where the
 *  bank feed does not reach.
 *
 *  A view of its own beside the four resolution queues, because it is not a
 *  queue: nothing in it is waiting for a decision. It is the ledger's other
 *  half, and the only place the credits no statement explains can be read or
 *  taken back.
 *
 *  Removal states what it will do before it is confirmed. Reversing a payment
 *  may unsettle a registration the roster already shows as paid, and that is
 *  not a consequence to discover afterwards.
 */
export default function RecordedPaymentsPanel({
  slug,
  reload,
  onChanged,
}: {
  slug: string;
  reload: number;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [payments, setPayments] = useState<ManualPayment[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [removing, setRemoving] = useState<ManualPayment | null>(null);
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.manualPayments(slug).then(
      (data) => {
        setPayments(data);
        setFailed(false);
      },
      () => {
        setPayments([]);
        setFailed(true);
      },
    );
  }

  useEffect(refresh, [slug, reload]);

  async function remove(payment: ManualPayment) {
    setBusy(true);
    try {
      await api.removeManualPayment(slug, payment.id);
      setRemoving(null);
      refresh();
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <QueueCard
        title={t("payments.recorded.title")}
        count={payments === null ? null : payments.length}
        loading={payments === null}
        failed={failed}
      >
        <table className="sheet-table">
          <thead>
            <tr>
              <th>{t("payments.recorded.date")}</th>
              <th>{t("payments.recorded.fencer")}</th>
              <th>{t("payments.recorded.amount")}</th>
              <th>{t("payments.recorded.method")}</th>
              <th>{t("payments.recorded.note")}</th>
              <th>{t("payments.recorded.recordedBy")}</th>
              <th className="col-actions" />
            </tr>
          </thead>
          <tbody>
            {(payments ?? []).map((payment) => (
              <tr key={payment.id}>
                <td>{new Date(payment.received_on).toLocaleDateString("cs")}</td>
                <td>{payment.fencer_name}</td>
                <td>{formatMoney(payment.amount, payment.currency)}</td>
                <td>{t(`payments.record.method.${payment.method}`)}</td>
                <td className="muted">{payment.note ?? "—"}</td>
                <td className="muted">{payment.recorded_by}</td>
                <td className="col-actions">
                  <button
                    type="button"
                    className="row-action"
                    title={t("payments.recorded.remove")}
                    onClick={() => setRemoving(payment)}
                  >
                    <IconTrash size={16} stroke={1.5} />
                    <span className="visually-hidden">{t("payments.recorded.remove")}</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </QueueCard>
      {removing && (
        <Modal onClose={() => setRemoving(null)}>
          <div className="modal">
            <h2>{t("payments.recorded.removeTitle")}</h2>
            <p>
              {t("payments.recorded.removeBody", {
                amount: formatMoney(removing.amount, removing.currency),
                name: removing.fencer_name,
              })}
            </p>
            {/* the consequence, stated before it happens rather than found
                afterwards on a roster that stopped saying paid */}
            {removing.removal_unsettles && (
              <p className="rail-hint">{t("payments.recorded.removeUnsettles")}</p>
            )}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setRemoving(null)}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={busy}
                onClick={() => void remove(removing)}
              >
                {t("payments.recorded.removeConfirm")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
