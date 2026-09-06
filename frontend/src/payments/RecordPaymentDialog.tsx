import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type Currency, type PaymentMethod, type SheetRow, api } from "../api";
import { formatMoney } from "../money";

const METHODS: PaymentMethod[] = ["cash", "transfer", "card", "other"];

/** Recording a payment that arrived outside the bank feed.
 *
 *  Opened from a registration's own row rather than from a queue: the queues
 *  hold money looking for a registration, and this is a registration whose
 *  money never arrived in a statement (spec payments-console).
 *
 *  It states what the registration is owed before anything is typed, so the
 *  organizer records against a balance rather than from memory — and, having
 *  stated it, offers it as the amount. A refusal keeps the dialog open with
 *  what was typed intact, as the link dialog does.
 */
export default function RecordPaymentDialog({
  slug,
  row,
  currency,
  eurOffered,
  onRecorded,
  onClose,
}: {
  slug: string;
  row: SheetRow;
  /** The tournament's local currency; the second lane is offered only where it
   *  prices in one, because a currency the tournament does not price in is
   *  refused by the endpoint. */
  currency: Currency;
  eurOffered: boolean;
  onRecorded: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  // the row carries one balance and the currency it is stated in — the lane
  // the money arrived in, the local one where none has (see `SheetRow`). So
  // the balance is offered in its own currency, and changing the currency
  // stops offering it rather than converting anything
  const stated: Currency = row.outstanding_currency ?? currency;
  const [chosenCurrency, setChosenCurrency] = useState<Currency>(stated);
  const outstanding = chosenCurrency === stated ? row.outstanding_amount : undefined;
  const [amount, setAmount] = useState<string>(row.outstanding_amount ?? "");
  const [receivedOn, setReceivedOn] = useState(new Date().toISOString().slice(0, 10));
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [note, setNote] = useState("");
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const registrationId = row.registration_id;

  async function confirm() {
    if (typeof registrationId !== "number") return;
    setBusy(true);
    setFailed(null);
    try {
      await api.recordManualPayment(slug, {
        registration_id: registrationId,
        amount: amount.replace(",", "."),
        currency: chosenCurrency,
        received_on: receivedOn,
        method,
        note: note.trim() || null,
      });
      onRecorded();
      onClose();
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : null;
      setFailed(typeof detail === "string" ? detail : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>{t("payments.record.title")}</h2>
        <p className="muted link-context">{row.name}</p>
        <p className="rail-hint">
          {outstanding === undefined
            ? t("payments.record.noBalance")
            : t("payments.record.outstanding", {
                amount: formatMoney(outstanding, chosenCurrency),
              })}
        </p>

        <div className="form-fields">
          <label className="form-field">
            <span>{t("payments.record.amount")}</span>
            <input
              autoFocus
              value={amount}
              inputMode="decimal"
              onChange={(event) => setAmount(event.target.value)}
            />
          </label>

          {eurOffered && (
            <label className="form-field">
              <span>{t("payments.record.currency")}</span>
              <select
                value={chosenCurrency}
                onChange={(event) => setChosenCurrency(event.target.value as Currency)}
              >
                <option value={currency}>{currency}</option>
                <option value="EUR">EUR</option>
              </select>
            </label>
          )}

          <label className="form-field">
            <span>{t("payments.record.receivedOn")}</span>
            <input
              type="date"
              value={receivedOn}
              onChange={(event) => setReceivedOn(event.target.value)}
            />
          </label>

          <label className="form-field">
            <span>{t("payments.record.methodLabel")}</span>
            <select
              value={method}
              onChange={(event) => setMethod(event.target.value as PaymentMethod)}
            >
              {METHODS.map((value) => (
                <option key={value} value={value}>
                  {t(`payments.record.method.${value}`)}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>{t("payments.record.note")}</span>
            <input value={note} onChange={(event) => setNote(event.target.value)} />
          </label>
        </div>

        {failed && (
          <p className="login-error">
            {t(`payments.record.error.${failed}`, {
              defaultValue: t("payments.record.error.failed"),
            })}
          </p>
        )}

        <div className="modal-actions">
          <button className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            className="btn-primary"
            disabled={busy || !amount.trim()}
            onClick={() => void confirm()}
          >
            {t("payments.record.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
