import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type PaymentInstructions, api } from "./api";
import { formatMoney } from "./money";

// the endpoint's three named refusals, plus a catch-all for anything else
// (network error, unexpected status) — every case is shown, never silently
// dropped (design fix-payment-instructions-visibility)
type PaymentRefusal = "no_payment_due" | "no_bank_account" | "not_unpaid" | "generic";

type PaymentPanelState =
  | { kind: "loading" }
  | { kind: "ready"; payment: PaymentInstructions }
  | { kind: "refused"; reason: PaymentRefusal; status?: number };

type PaymentTab = "local" | "eur";

export default function PaymentPanel({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [state, setState] = useState<PaymentPanelState>({ kind: "loading" });
  const [tab, setTab] = useState<PaymentTab>("local");

  useEffect(() => {
    setState({ kind: "loading" });
    api.paymentInstructions(slug).then(
      (payment) => setState({ kind: "ready", payment }),
      (err) => {
        const detail = err instanceof ApiError ? err.detail : null;
        if (detail === "no_payment_due" || detail === "no_bank_account" || detail === "not_unpaid") {
          setState({ kind: "refused", reason: detail });
        } else {
          setState({
            kind: "refused",
            reason: "generic",
            status: err instanceof ApiError ? err.status : undefined,
          });
        }
      },
    );
  }, [slug]);

  if (state.kind === "loading") return null;

  if (state.kind === "refused") {
    if (state.reason === "generic") {
      return (
        <p className="login-error">
          {t("payment.reason.generic", { status: state.status ?? "?" })}
        </p>
      );
    }
    // no_payment_due keeps registration.fullyQueuedHint's key so the Czech
    // translation moves with the behaviour rather than being re-authored
    const key =
      state.reason === "no_payment_due" ? "registration.fullyQueuedHint" : `payment.reason.${state.reason}`;
    return <p className="rail-hint">{t(key)}</p>;
  }

  const payment = state.payment;
  // the same registration, payable in EUR against the same account — only
  // offered as a second tab when the organizer enabled it (currency mode
  // local_eur)
  const eur =
    payment.eur_amount !== null && payment.eur_qr_png_base64 !== null
      ? { amount: payment.eur_amount, qrBase64: payment.eur_qr_png_base64 }
      : null;

  return (
    <section className="payment-slip">
      <div className="payment-slip-heading">
        <h2 className="payment-slip-title">{t("payment.title")}</h2>

        {eur && (
          <nav className="stage-control" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={tab === "local"}
              className={tab === "local" ? "active" : ""}
              onClick={() => setTab("local")}
            >
              {payment.currency}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "eur"}
              className={tab === "eur" ? "active" : ""}
              onClick={() => setTab("eur")}
            >
              EUR
            </button>
          </nav>
        )}
      </div>

      {(!eur || tab === "local") && (
        <>
          <div className="payment-block">
            <div className="param-fields">
              <div className="param-field">
                <span>{t("payment.amount")}</span>
                <strong className="data-value">
                  {formatMoney(payment.amount, payment.currency)}
                </strong>
              </div>
              {payment.account_domestic && (
                <div className="param-field">
                  <span>{t("payment.account")}</span>
                  <strong className="data-value">{payment.account_domestic}</strong>
                </div>
              )}
              <div className="param-field">
                <span>{payment.account_domestic ? t("payment.ibanLabel") : t("payment.account")}</span>
                <strong className="data-value">{payment.iban}</strong>
              </div>
              <div className="param-field">
                <span>{t("payment.vs")}</span>
                <strong className="data-value">{payment.vs}</strong>
              </div>
              <div className="param-field">
                <span>{t("payment.expiresAt")}</span>
                <strong>{new Date(payment.expires_at ?? "").toLocaleDateString("cs")}</strong>
              </div>
            </div>
            <img
              className="payment-qr"
              src={`data:image/png;base64,${payment.qr_png_base64}`}
              alt={t("payment.title")}
            />
          </div>
          <p className="rail-hint">{t("payment.vsInMessage", { vs: payment.vs })}</p>
        </>
      )}

      {eur && tab === "eur" && (
        <>
          <div className="payment-block">
            <div className="param-fields">
              <div className="param-field">
                <span>{t("payment.eurAmount")}</span>
                <strong className="data-value">{formatMoney(eur.amount, "EUR")}</strong>
              </div>
              <div className="param-field">
                <span>{t("payment.ibanLabel")}</span>
                <strong className="data-value">{payment.iban}</strong>
              </div>
              <div className="param-field">
                <span>{t("payment.message")}</span>
                <strong className="data-value">{payment.message}</strong>
              </div>
              <div className="param-field">
                <span>{t("payment.expiresAt")}</span>
                <strong>{new Date(payment.expires_at ?? "").toLocaleDateString("cs")}</strong>
              </div>
            </div>
            <img
              className="payment-qr"
              src={`data:image/png;base64,${eur.qrBase64}`}
              alt={t("payment.eurTitle")}
            />
          </div>
          <p className="rail-hint">{t("payment.eurHint")}</p>
        </>
      )}
    </section>
  );
}
