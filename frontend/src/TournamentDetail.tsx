import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import PaidStamp from "./PaidStamp";
import {
  ApiError,
  type Account,
  type Availability,
  type PaymentInstructions,
  type RegistrationDetail,
  type TournamentDetail as TournamentDetailData,
  api,
} from "./api";

const LEGACY_WEAPONS: Record<string, string> = {
  LS: "Longsword",
  SA: "Sabre",
  RA: "Single Rapier",
  RD: "Rapier & Dagger",
  SB: "Sword & Buckler",
};

type RegistrationStatus = "open" | "opens_on" | "closed";

function registrationStatus(detail: TournamentDetailData): RegistrationStatus {
  const today = new Date().toISOString().slice(0, 10);
  if (detail.registration_opens && today < detail.registration_opens) return "opens_on";
  const closes = detail.registration_closes ?? detail.date;
  if (today > closes) return "closed";
  return "open";
}

function InfoHeader({ detail }: { detail: TournamentDetailData }) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h1>{detail.display_name}</h1>
      <p className="rail-hint">
        {detail.organizer_names.join(", ")} · {new Date(detail.date).toLocaleDateString("cs")}
        {detail.location ? ` · ${detail.location}` : ""}
      </p>
      {(detail.registration_opens || detail.registration_closes) && (
        <p className="rail-hint">
          {detail.registration_opens &&
            t("detail.opensOn", {
              date: new Date(detail.registration_opens).toLocaleDateString("cs"),
            })}
          {detail.registration_opens && detail.registration_closes && " · "}
          {detail.registration_closes &&
            t("detail.closesOn", {
              date: new Date(detail.registration_closes).toLocaleDateString("cs"),
            })}
        </p>
      )}
    </section>
  );
}

function DisciplinesAndExtras({
  detail,
  availability,
}: {
  detail: TournamentDetailData;
  availability: Availability[];
}) {
  const { t } = useTranslation();
  const byCode = new Map(availability.map((a) => [a.code, a]));
  return (
    <section className="rail-card">
      <h2>{t("detail.disciplines")}</h2>
      <ul className="detail-list">
        {detail.disciplines.map((d) => {
          const a = byCode.get(d.code);
          const free = a ? a.free : d.capacity;
          return (
            <li key={d.code}>
              <strong>
                {d.code} — {d.name}
              </strong>
              <span className="muted">
                {d.fee ?? "—"} Kč ·{" "}
                {free > 0
                  ? t("detail.freePlaces", { count: free })
                  : t("detail.queueLength", { count: a?.queue_length ?? 0 })}
              </span>
            </li>
          );
        })}
      </ul>
      {detail.extra_items.length > 0 && (
        <>
          <h2>{t("detail.extras")}</h2>
          <ul className="detail-list">
            {detail.extra_items.map((item) => (
              <li key={item.id}>
                <strong>{item.name}</strong>
                <span className="muted">
                  {item.price} Kč · {t(`setup.extras.categories.${item.category}`)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function RegistrationForm({
  detail,
  availability,
  onRegistered,
}: {
  detail: TournamentDetailData;
  availability: Availability[];
  onRegistered: (registration: RegistrationDetail) => void;
}) {
  const { t } = useTranslation();
  const [disciplines, setDisciplines] = useState<Set<string>>(new Set());
  const [extraQty, setExtraQty] = useState<Record<number, number>>({});
  const [legacyQty, setLegacyQty] = useState<Record<string, number>>({});
  const [afterparty, setAfterparty] = useState(false);
  const [aftersparring, setAftersparring] = useState(false);
  const [accommodation, setAccommodation] = useState("");
  const [notes, setNotes] = useState("");
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullDisciplines, setFullDisciplines] = useState<string[] | null>(null);

  const byCode = new Map(availability.map((a) => [a.code, a]));
  const legacy = detail.extra_items.length === 0;

  function weaponRentals(): string[] {
    return Object.entries(legacyQty).flatMap(([code, qty]) => Array(qty).fill(code));
  }

  function extrasPayload() {
    return Object.entries(extraQty)
      .filter(([, qty]) => qty > 0)
      .map(([id, qty]) => ({ extra_item_id: Number(id), qty }));
  }

  useEffect(() => {
    if (disciplines.size === 0) {
      setTotal(0);
      return;
    }
    const handle = setTimeout(() => {
      api
        .pricePreview(detail.slug, {
          disciplines: [...disciplines],
          weapon_rentals: weaponRentals(),
          afterparty,
          extras: extrasPayload(),
        })
        .then((result) => setTotal(result.total), () => setTotal(0));
    }, 300);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disciplines, extraQty, legacyQty, afterparty]);

  function toggleDiscipline(code: string) {
    setDisciplines((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  async function submit(waitForAll: boolean) {
    setBusy(true);
    setError(null);
    try {
      const registration = await api.registerForTournament(detail.slug, {
        disciplines: [...disciplines],
        weapon_rentals: weaponRentals(),
        afterparty,
        aftersparring,
        accommodation: accommodation.trim() === "" ? null : accommodation,
        notes: notes.trim() === "" ? null : notes,
        wait_for_all: waitForAll,
        extras: extrasPayload(),
      });
      setFullDisciplines(null);
      onRegistered(registration);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const detailBody = err.detail as { full_disciplines?: string[] } | null;
        if (detailBody?.full_disciplines) {
          setFullDisciplines(detailBody.full_disciplines);
          return;
        }
      }
      setError(t("form.submitFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("form.title")}</h2>
      <p className="tiskopis-number">{t("form.formNumber")}</p>
      <div className="chips">
        {detail.disciplines.map((d) => {
          const a = byCode.get(d.code);
          const free = a ? a.free : d.capacity;
          return (
            <label key={d.code} className="checkbox-chip">
              <input
                type="checkbox"
                checked={disciplines.has(d.code)}
                onChange={() => toggleDiscipline(d.code)}
              />
              {d.code} ({d.fee ?? "—"} Kč, {free > 0 ? t("detail.freePlaces", { count: free }) : t("detail.queueLength", { count: a?.queue_length ?? 0 })})
            </label>
          );
        })}
      </div>

      {!legacy && detail.extra_items.length > 0 && (
        <div className="param-fields">
          {detail.extra_items.map((item) => (
            <label key={item.id} className="param-field">
              <span>
                {item.name} ({item.price} Kč)
              </span>
              <input
                type="number"
                min={0}
                max={item.max_qty}
                value={extraQty[item.id] ?? 0}
                onChange={(event) =>
                  setExtraQty({
                    ...extraQty,
                    [item.id]: Math.max(0, Math.min(item.max_qty, Number(event.target.value))),
                  })
                }
              />
            </label>
          ))}
        </div>
      )}

      {legacy && (
        <div className="param-fields">
          {Object.entries(LEGACY_WEAPONS).map(([code, name]) => (
            <label key={code} className="param-field">
              <span>{name}</span>
              <input
                type="number"
                min={0}
                max={4}
                value={legacyQty[code] ?? 0}
                onChange={(event) =>
                  setLegacyQty({
                    ...legacyQty,
                    [code]: Math.max(0, Math.min(4, Number(event.target.value))),
                  })
                }
              />
            </label>
          ))}
          <label className="checkbox-chip">
            <input
              type="checkbox"
              checked={afterparty}
              onChange={(event) => setAfterparty(event.target.checked)}
            />
            {t("form.afterparty")}
          </label>
        </div>
      )}

      <div className="param-fields">
        <label className="checkbox-chip">
          <input
            type="checkbox"
            checked={aftersparring}
            onChange={(event) => setAftersparring(event.target.checked)}
          />
          {t("form.aftersparring")}
        </label>
        <label className="param-field">
          <span>{t("form.accommodation")}</span>
          <input value={accommodation} onChange={(event) => setAccommodation(event.target.value)} />
        </label>
        <label className="param-field">
          <span>{t("form.notes")}</span>
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
      </div>

      <p className="form-total">{t("form.total", { total })}</p>

      {error && <p className="login-error">{error}</p>}

      {fullDisciplines && (
        <div className="rail-card dashed">
          <p>{t("form.fullDisciplines", { codes: fullDisciplines.join(", ") })}</p>
          <div className="modal-actions">
            <button
              className="secondary"
              disabled={busy}
              onClick={() => {
                setDisciplines((prev) => {
                  const next = new Set(prev);
                  for (const code of fullDisciplines) next.delete(code);
                  return next;
                });
                setFullDisciplines(null);
              }}
            >
              {t("form.dropFull")}
            </button>
            <button className="secondary" disabled={busy} onClick={() => void submit(true)}>
              {t("form.joinQueue")}
            </button>
          </div>
        </div>
      )}

      <button
        className="btn-primary param-save"
        disabled={busy || disciplines.size === 0}
        onClick={() => void submit(false)}
      >
        {t("form.submit")}
      </button>
    </section>
  );
}

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
          <strong className="data-value">{payment.amount} Kč</strong>
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

function RegistrationSummary({ registration }: { registration: RegistrationDetail }) {
  const { t } = useTranslation();
  const active = registration.entries.filter((e) => !e.is_substitute);
  const substitutes = registration.entries.filter((e) => e.is_substitute);

  return (
    <section className="rail-card">
      <h2>{t("registration.title")}</h2>
      <RegistrationStateTag registration={registration} />
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
          </li>
        ))}
      </ul>
      <p className="form-total">{t("form.total", { total: registration.total_amount })}</p>
    </section>
  );
}

function RegistrationPanel({
  slug,
  detail,
  registration,
  onCancelled,
}: {
  slug: string;
  detail: TournamentDetailData;
  registration: RegistrationDetail;
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
          </li>
        ))}
      </ul>
      <p className="form-total">{t("form.total", { total: registration.total_amount })}</p>

      {registration.state === "reserved" && !fullyQueued && <PaymentPanel slug={slug} />}
      {registration.state === "reserved" && fullyQueued && (
        <p className="rail-hint">{t("registration.fullyQueuedHint")}</p>
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
        <button className="link-button" onClick={onBack}>
          {t("detail.back")}
        </button>
        {detail === null || !registrationChecked ? (
          <p>{t("common.loading")}</p>
        ) : (
          <div className="setup-panel">
            <InfoHeader detail={detail} />
            <DisciplinesAndExtras detail={detail} availability={availability} />
            {readOnly ? (
              hasActive && registration && <RegistrationSummary registration={registration} />
            ) : hasActive && registration ? (
              <RegistrationPanel
                slug={slug}
                detail={detail}
                registration={registration}
                onCancelled={refresh}
              />
            ) : registrationStatus(detail) === "open" ? (
              <RegistrationForm
                detail={detail}
                availability={availability}
                onRegistered={(r) => setRegistration(r)}
              />
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
