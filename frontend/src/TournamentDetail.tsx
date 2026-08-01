import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import PaidStamp from "./PaidStamp";
import {
  type Account,
  type Availability,
  type PaymentInstructions,
  type RegistrationDetail,
  type TournamentDetail as TournamentDetailData,
  api,
} from "./api";
import { formatMoney, formatMoneyWithEur } from "./money";
import {
  DiscountList,
  DisciplinesInfo,
  InfoHeader,
  OtherActionsInfo,
  RegistrationForm,
  amendmentOpen,
  registrationStatus,
} from "./TournamentFace";

function PaymentPanel({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [payment, setPayment] = useState<PaymentInstructions | null>(null);

  useEffect(() => {
    api.paymentInstructions(slug).then(setPayment, () => setPayment(null));
  }, [slug]);

  if (!payment) return null;

  return (
    <section className="payment-slip">
      <h2 className="payment-slip-title">{t("payment.title")}</h2>
      <img
        className="payment-qr"
        src={`data:image/png;base64,${payment.qr_png_base64}`}
        alt={t("payment.title")}
      />
      <div className="param-fields">
        <div className="param-field">
          <span>{t("payment.amount")}</span>
          <strong className="data-value">
            {formatMoney(payment.amount, payment.currency)}
          </strong>
        </div>
        <div className="param-field">
          <span>{t("payment.iban")}</span>
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
      <p className="rail-hint">{t("payment.vsInMessage", { vs: payment.vs })}</p>

      {/* the same registration, payable in EUR against the same account */}
      {payment.eur_amount !== null && payment.eur_qr_png_base64 && (
        <>
          <h3 className="register-section">{t("payment.eurTitle")}</h3>
          <img
            className="payment-qr"
            src={`data:image/png;base64,${payment.eur_qr_png_base64}`}
            alt={t("payment.eurTitle")}
          />
          <div className="param-field">
            <span>{t("payment.eurAmount")}</span>
            <strong className="data-value">{formatMoney(payment.eur_amount, "EUR")}</strong>
          </div>
          <p className="rail-hint">{t("payment.eurHint")}</p>
        </>
      )}
    </section>
  );
}

function RegistrationStateTag({ registration }: { registration: RegistrationDetail }) {
  const { t } = useTranslation();
  const label = t(`registration.state.${registration.state}`);
  if (registration.state === "paid") return <PaidStamp id={registration.vs} label={label} />;
  if (registration.state === "reserved") return <span className="tag tag-form-yellow">{label}</span>;
  return <span className="state-text">{label}</span>;
}

/** What a registration holds and what it owes — shared by the read-only summary
 *  and the owner's panel, so the two can never disagree. */
function RegistrationLines({
  registration,
  detail,
}: {
  registration: RegistrationDetail;
  detail: TournamentDetailData;
}) {
  const { t } = useTranslation();
  const active = registration.entries.filter((e) => !e.is_substitute);
  const substitutes = registration.entries.filter((e) => e.is_substitute);

  return (
    <>
      <ul className="detail-list">
        {active.map((e) => (
          <li key={e.code}>{e.code}</li>
        ))}
        {substitutes.map((e) => (
          <li key={e.code} className="muted">
            {e.code} — {t("registration.queuePosition", { position: e.queue_position })}
          </li>
        ))}
        {registration.extras.map((extra) => (
          <li key={extra.extra_item_id}>
            {extra.name} × {extra.qty}
            {extra.option_value && ` (${extra.option_label}: ${extra.option_value})`}
          </li>
        ))}
      </ul>
      <p className="form-total">
        {t("form.total", {
          amount: formatMoneyWithEur(registration.total_amount, registration.total_eur, detail),
        })}
      </p>
      {(Number(registration.outstanding_amount) !== 0 ||
        Number(registration.outstanding_eur_amount ?? 0) !== 0) && (
        <p className="rail-hint">
          {t("registration.outstanding", {
            amount: formatMoneyWithEur(
              registration.outstanding_amount,
              registration.outstanding_eur_amount,
              detail,
            ),
          })}
        </p>
      )}
    </>
  );
}

function RegistrationSummary({
  registration,
  detail,
}: {
  registration: RegistrationDetail;
  detail: TournamentDetailData;
}) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h2>{t("registration.title")}</h2>
      <RegistrationStateTag registration={registration} />
      <RegistrationLines registration={registration} detail={detail} />
    </section>
  );
}

function RegistrationPanel({
  slug,
  detail,
  registration,
  canAmend,
  onAmend,
  onCancelled,
}: {
  slug: string;
  detail: TournamentDetailData;
  registration: RegistrationDetail;
  canAmend: boolean;
  onAmend: () => void;
  onCancelled: () => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const active = registration.entries.filter((e) => !e.is_substitute);
  const substitutes = registration.entries.filter((e) => e.is_substitute);
  const fullyQueued = active.length === 0 && substitutes.length > 0;

  async function cancel() {
    setBusy(true);
    try {
      await api.cancelRegistration(slug);
      onCancelled();
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  }

  const refundable =
    registration.state === "paid" &&
    detail.refundable_until !== null &&
    new Date().toISOString().slice(0, 10) <= detail.refundable_until;

  return (
    <section className="rail-card">
      <h2>{t("registration.title")}</h2>
      <RegistrationStateTag registration={registration} />

      <RegistrationLines registration={registration} detail={detail} />

      {registration.state === "reserved" && !fullyQueued && <PaymentPanel slug={slug} />}
      {registration.state === "reserved" && fullyQueued && (
        <p className="rail-hint">{t("registration.fullyQueuedHint")}</p>
      )}

      {canAmend && (
        <button className="secondary" onClick={onAmend}>
          {t("registration.amend")}
        </button>
      )}

      {registration.state !== "cancelled" && (
        <>
          {confirming ? (
            <div className="rail-card dashed">
              <p>
                {registration.state === "paid"
                  ? refundable
                    ? t("cancel.refundable")
                    : t("cancel.notRefundable")
                  : t("cancel.confirm")}
              </p>
              <div className="modal-actions">
                <button className="secondary" onClick={() => setConfirming(false)}>
                  {t("common.cancel")}
                </button>
                <button className="btn-primary" disabled={busy} onClick={() => void cancel()}>
                  {t("cancel.confirmButton")}
                </button>
              </div>
            </div>
          ) : (
            <button className="secondary" onClick={() => setConfirming(true)}>
              {t("cancel.button")}
            </button>
          )}
        </>
      )}
    </section>
  );
}

export default function TournamentDetail({
  slug,
  readOnly = false,
  onBack,
  onProfile,
  onAdmin,
  onOrganizer,
  onLogout,
}: {
  slug: string;
  readOnly?: boolean;
  onBack: () => void;
  onProfile: () => void;
  onAdmin: () => void;
  onOrganizer: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<TournamentDetailData | null>(null);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [registration, setRegistration] = useState<RegistrationDetail | null>(null);
  const [registrationChecked, setRegistrationChecked] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);
  // the detail page is split into an information screen and a separate
  // register/amend screen; information is always the landing view
  const [screen, setScreen] = useState<"information" | "register" | "amend">("information");

  function refresh() {
    api.tournament(slug).then(setDetail, () => setDetail(null));
    api.availability(slug).then(setAvailability, () => setAvailability([]));
    api.myRegistration(slug).then(
      (r) => {
        setRegistration(r);
        setRegistrationChecked(true);
      },
      () => {
        setRegistration(null);
        setRegistrationChecked(true);
      },
    );
  }

  useEffect(refresh, [slug]);
  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const hasActive = registration !== null && registration.state !== "cancelled";
  // register is offered only when open and at least one discipline or item has
  // an open slot (extra items carry no capacity, so their presence counts)
  const hasOpenSlot =
    detail !== null &&
    (availability.some((a) => a.free > 0) || detail.extra_items.length > 0);
  const canRegister =
    !readOnly &&
    !hasActive &&
    detail !== null &&
    registrationStatus(detail) === "open" &&
    hasOpenSlot;
  const canAmend =
    !readOnly &&
    detail !== null &&
    registration !== null &&
    (registration.state === "reserved" || registration.state === "paid") &&
    amendmentOpen(detail);
  const onRegisterScreen = screen === "register" && canRegister;
  const onAmendScreen = screen === "amend" && canAmend;
  const showingForm = onRegisterScreen || onAmendScreen;

  return (
    <div className="login-page">
      <div className="page-menu-corner">
        <AccountMenu
          account={account}
          onProfile={onProfile}
          onAdmin={onAdmin}
          onFencer={onBack}
          onOrganizer={onOrganizer}
          onLogout={onLogout}
        />
      </div>
      <div className="login-card wide-card">
        <button
          className="link-button"
          onClick={() => (showingForm ? setScreen("information") : onBack())}
        >
          {showingForm ? t("detail.backToInfo") : t("detail.back")}
        </button>
        {detail === null || !registrationChecked ? (
          <p>{t("common.loading")}</p>
        ) : showingForm ? (
          <div className="setup-panel">
            <RegistrationForm
              detail={detail}
              availability={availability}
              mode={
                onAmendScreen && registration
                  ? {
                      kind: "amend",
                      initial: registration,
                      onRegistered: (r) => {
                        setRegistration(r);
                        setScreen("information");
                      },
                    }
                  : {
                      kind: "register",
                      onRegistered: (r) => {
                        setRegistration(r);
                        setScreen("information");
                      },
                    }
              }
            />
          </div>
        ) : (
          <div className="setup-panel">
            <InfoHeader detail={detail} />
            <DisciplinesInfo detail={detail} availability={availability} />
            <DiscountList detail={detail} />
            <OtherActionsInfo detail={detail} />
            {readOnly ? (
              hasActive && registration && (
                <RegistrationSummary registration={registration} detail={detail} />
              )
            ) : hasActive && registration ? (
              <RegistrationPanel
                slug={slug}
                detail={detail}
                registration={registration}
                canAmend={canAmend}
                onAmend={() => setScreen("amend")}
                onCancelled={refresh}
              />
            ) : canRegister ? (
              <button className="btn-primary param-save" onClick={() => setScreen("register")}>
                {t("detail.register")}
              </button>
            ) : (
              <section className="rail-card dashed">
                <p className="rail-hint">
                  {registrationStatus(detail) === "opens_on"
                    ? t("detail.notYetOpen")
                    : t("detail.closedNotice")}
                </p>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
