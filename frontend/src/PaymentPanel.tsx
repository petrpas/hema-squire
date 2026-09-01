import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import PaymentSlipBlock, { type SlipField } from "./PaymentSlipBlock";
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

type Translate = (key: string, opts?: Record<string, unknown>) => string;

function expiry(payment: PaymentInstructions): string {
  return new Date(payment.expires_at ?? "").toLocaleDateString("cs");
}

/** What a fencer must put into their bank for the local-currency transfer.
 *  `copy` is the bare value a payment form wants, which is not always what is
 *  shown: an amount reads "1 200 Kč" on the slip and must paste as "1200". */
function localFields(payment: PaymentInstructions, t: Translate): SlipField[] {
  const fields: SlipField[] = [
    {
      key: "amount",
      label: t("payment.amount"),
      shown: formatMoney(payment.amount, payment.currency),
      copy: String(payment.amount),
    },
  ];
  if (payment.account_domestic) {
    fields.push({
      key: "account",
      label: t("payment.account"),
      shown: payment.account_domestic,
      copy: payment.account_domestic,
    });
  }
  fields.push(
    {
      key: "iban",
      label: payment.account_domestic ? t("payment.ibanLabel") : t("payment.account"),
      shown: payment.iban,
      copy: payment.iban,
    },
    {
      key: "vs",
      label: t("payment.vs"),
      shown: String(payment.vs),
      copy: String(payment.vs),
    },
    // nothing to copy: a date is read, never entered into a transfer
    { key: "expires", label: t("payment.expiresAt"), shown: expiry(payment) },
  );
  return fields;
}

/** The same registration payable in EUR: no domestic account number, and the
 *  VS travels in the message because a SEPA transfer has no VS field. */
function eurFields(payment: PaymentInstructions, amount: number, t: Translate): SlipField[] {
  return [
    {
      key: "amount",
      label: t("payment.eurAmount"),
      shown: formatMoney(amount, "EUR"),
      copy: String(amount),
    },
    { key: "iban", label: t("payment.ibanLabel"), shown: payment.iban, copy: payment.iban },
    {
      key: "message",
      label: t("payment.message"),
      shown: payment.message,
      copy: payment.message,
    },
    { key: "expires", label: t("payment.expiresAt"), shown: expiry(payment) },
  ];
}

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
          <PaymentSlipBlock
            fields={localFields(payment, t)}
            qrBase64={payment.qr_png_base64}
            qrAlt={t("payment.title")}
            qrFilename={`qr-${payment.vs}.png`}
          />
          <p className="rail-hint">{t("payment.vsInMessage", { vs: payment.vs })}</p>
        </>
      )}

      {eur && tab === "eur" && (
        <>
          <PaymentSlipBlock
            fields={eurFields(payment, eur.amount, t)}
            qrBase64={eur.qrBase64}
            qrAlt={t("payment.eurTitle")}
            qrFilename={`qr-eur-${payment.vs}.png`}
          />
          <p className="rail-hint">{t("payment.eurHint")}</p>
        </>
      )}
    </section>
  );
}
