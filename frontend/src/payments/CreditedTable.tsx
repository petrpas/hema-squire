import { IconArrowBackUp } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type CreditedPayment, type CreditReversal } from "../api";
import Modal from "../Modal";
import { formatMoney } from "../money";

/** Every payment holding a live credit: the bank's and the hand-recorded
 *  together, each naming who it credited and why.
 *
 *  One table where the console had three. A transaction the matcher resolved
 *  sat in no resolution queue; a pairing an organizer drew was listed under the
 *  rule that decided it; a cash payment somebody entered had a view of its own.
 *  All three are the same fact, and answering it in three places meant the
 *  pairing view and the credited view listing overlapping rows under different
 *  keys — while a pairing that credited nothing showed as a finished result.
 *
 *  Undo is whole-payment. A payment covering three entries can be reversed and
 *  paired again; reversing one fencer's share alone would want an endpoint of
 *  its own for a case that does not arise, and the rows would then repeat the
 *  date and the payer down the table to no purpose.
 *
 *  Reversing states what it will do before it is confirmed, and asks the
 *  preflight rather than reading the row it already has: the consequence is a
 *  derivation, and what was true when the table loaded may not be true now.
 */
export default function CreditedTable({
  slug,
  payments,
  onChanged,
}: {
  slug: string;
  payments: CreditedPayment[];
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [reversing, setReversing] = useState<CreditedPayment | null>(null);
  const [preflight, setPreflight] = useState<CreditReversal | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);

  /** Only a bank transaction can be reversed through the transaction endpoint;
   *  a hand-recorded payment is removed through its own, which is the same act
   *  under a different address. */
  function open(payment: CreditedPayment) {
    setActionFailed(false);
    setPreflight(null);
    setReversing(payment);
    if (payment.source_kind === "bank_transaction") {
      api.reversalPreflight(slug, payment.source_id).then(setPreflight, () => setPreflight(null));
    } else {
      // a recorded payment credits one registration, and the row already
      // carries what reversing it does — there is no second question to ask
      setPreflight({ transaction_id: payment.source_id, registrations: payment.credits });
    }
  }

  function close() {
    setReversing(null);
    setPreflight(null);
  }

  async function reverse(payment: CreditedPayment) {
    setBusy(true);
    setActionFailed(false);
    try {
      if (payment.source_kind === "bank_transaction") {
        await api.reverseTransactionCredit(slug, payment.source_id);
      } else {
        await api.removeManualPayment(slug, payment.source_id);
      }
      close();
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
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("payments.credited.date")}</th>
            <th>{t("payments.credited.payer")}</th>
            <th>{t("payments.credited.amount")}</th>
            <th>{t("payments.credited.message")}</th>
            <th>{t("payments.credited.registrations")}</th>
            <th>{t("payments.credited.origin")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {payments.map((payment) => (
            <tr key={`${payment.source_kind}-${payment.source_id}`}>
              <td>{new Date(payment.value_date).toLocaleDateString("cs")}</td>
              {/* the bank's counterparty, or the organizer who said so */}
              <td>{payment.payer_name ?? payment.recorded_by ?? "—"}</td>
              <td>{formatMoney(payment.amount, payment.currency)}</td>
              {/* kept here as well as on the uncredited table: the message is
                  how an organizer finds this payment again in their own bank */}
              <td className="muted">{payment.message ?? payment.note ?? "—"}</td>
              {/* one payment may have covered several registrations — that is
                  what a pairing is — and each of them is its own credit, so the
                  row names all of them with their own share */}
              <td>
                {payment.credits.length === 0
                  ? "—"
                  : payment.credits.map((credit) => (
                      <span className="credit-share" key={credit.registration_id}>
                        {credit.fencer_name} {formatMoney(credit.amount, credit.currency)}
                      </span>
                    ))}
              </td>
              <td className="muted">{t(`payments.credited.origins.${payment.origin}`)}</td>
              <td className="col-actions">
                <button
                  type="button"
                  className="row-action"
                  title={t("payments.credited.reverse")}
                  onClick={() => open(payment)}
                >
                  <IconArrowBackUp size={16} stroke={1.5} />
                  <span className="visually-hidden">{t("payments.credited.reverse")}</span>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {reversing && (
        <Modal onClose={close}>
          <div className="modal">
            <h2>{t("payments.credited.reverseTitle")}</h2>
            <p>
              {t("payments.credited.reverseBody", {
                amount: formatMoney(reversing.amount, reversing.currency),
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
