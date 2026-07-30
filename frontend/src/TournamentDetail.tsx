import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import PaidStamp from "./PaidStamp";
import {
  ApiError,
  type Account,
  type Availability,
  type ExtraItem,
  type PaymentInstructions,
  type RegistrationDetail,
  type TournamentDetail as TournamentDetailData,
  api,
  logoUrl,
} from "./api";
import { formatMoney, formatMoneyWithEur } from "./money";

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
    <section className="rail-card detail-info-header">
      {detail.has_logo && (
        <img className="detail-logo" src={logoUrl(detail.slug)} alt="" />
      )}
      <div className="detail-info-heading">
        <h1>{detail.display_name}</h1>
        {detail.subtitle && <p className="detail-subtitle">{detail.subtitle}</p>}
        <div className="home-card-meta">
          {detail.organizers.length > 0 && (
            <span className="meta-cell">
              {detail.organizers.map((organizer, index) => (
                <span key={index}>
                  {index > 0 && ", "}
                  {organizer.link ? (
                    <a
                      className="detail-inline-link"
                      href={organizer.link}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {organizer.name}
                    </a>
                  ) : (
                    organizer.name
                  )}
                </span>
              ))}
            </span>
          )}
          <span className="meta-cell">
            {new Date(detail.date).toLocaleDateString("cs")}
          </span>
          {detail.location && <span className="meta-cell">{detail.location}</span>}
        </div>
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
        <p className="rail-hint">
          {detail.qualification_open
            ? t("detail.qualificationOpen")
            : t("detail.qualificationRequired", { criteria: detail.qualification_criteria })}
        </p>
        {detail.description && <p className="detail-description">{detail.description}</p>}
      </div>
    </section>
  );
}

// the time-and-place ("action") categories, mirroring the backend's
// ACTION_CATEGORIES: shown as informational "other actions" on the information
// screen — where gear lending and merch are deliberately omitted — and grouped
// as the optional programme on the register screen
const ACTION_CATEGORIES = ["seminar", "afterparty", "other_action"] as const;

/** Optional when/where/remark lines shared by discipline and action rows. */
function ScheduleLines({
  when,
  where,
  remark,
}: {
  when?: string | null;
  where?: string | null;
  remark?: string | null;
}) {
  const parts = [when, where].filter(Boolean).join(" · ");
  return (
    <>
      {parts && <span className="muted">{parts}</span>}
      {remark && <span className="muted">{remark}</span>}
    </>
  );
}

function DisciplinesInfo({
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
          const taken = a ? a.taken : 0;
          const free = a ? a.free : d.capacity;
          return (
            <li key={d.code}>
              <strong>
                {d.code} — {d.name}
              </strong>
              <span className="muted">
                {d.fee === null ? "—" : formatMoneyWithEur(d.fee, detail)} ·{" "}
                {t("detail.fencersCount", { taken, capacity: d.capacity })}
                {free <= 0 &&
                  ` · ${t("detail.queueLength", { count: a?.queue_length ?? 0 })}`}
              </span>
              <ScheduleLines when={d.schedule_when} where={d.schedule_where} />
              {d.ruleset_name &&
                (d.ruleset_url ? (
                  <a
                    className="detail-inline-link"
                    href={d.ruleset_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("detail.rulesetLabel")}: {d.ruleset_name}
                  </a>
                ) : (
                  <span className="muted">
                    {t("detail.rulesetLabel")}: {d.ruleset_name}
                  </span>
                ))}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function OtherActionsInfo({ detail }: { detail: TournamentDetailData }) {
  const { t } = useTranslation();
  const actions = detail.extra_items.filter((item) =>
    ACTION_CATEGORIES.includes(item.category as (typeof ACTION_CATEGORIES)[number]),
  );
  if (actions.length === 0) return null;
  return (
    <section className="rail-card">
      <h2>{t("detail.otherActions")}</h2>
      <ul className="detail-list">
        {actions.map((item) => (
          <li key={item.id}>
            <strong>{item.name}</strong>
            <ScheduleLines
              when={item.schedule_when}
              where={item.schedule_where}
              remark={item.remark}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

/** One checkbox row of the registration checklist: name, price, and whatever
 *  detail lines and controls the row carries. */
function ChecklistRow({
  name,
  price,
  checked,
  onToggle,
  children,
}: {
  name: string;
  price: string;
  checked: boolean;
  onToggle: () => void;
  children?: React.ReactNode;
}) {
  return (
    <label className="checklist-row">
      <input type="checkbox" checked={checked} onChange={onToggle} />
      <span className="checklist-name">{name}</span>
      <span className="checklist-price">{price}</span>
      {children && <span className="checklist-detail">{children}</span>}
    </label>
  );
}

/** The quantity and option controls a selected purchasable row reveals. */
function ItemControls({
  item,
  qty,
  optionValue,
  onQty,
  onOption,
}: {
  item: ExtraItem;
  qty: number;
  optionValue: string;
  onQty: (qty: number) => void;
  onOption: (value: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <span className="checklist-controls">
      {item.max_qty > 1 && (
        <span className="checklist-control">
          {t("form.quantity")}
          <input
            type="number"
            min={1}
            max={item.max_qty}
            value={qty}
            onChange={(event) =>
              onQty(Math.max(1, Math.min(item.max_qty, Number(event.target.value))))
            }
          />
        </span>
      )}
      {item.option_label && (
        <span className="checklist-control">
          {item.option_label}
          {item.option_choices.length > 0 ? (
            <select value={optionValue} onChange={(event) => onOption(event.target.value)}>
              <option value="">{t("form.chooseOption")}</option>
              {item.option_choices.map((choice) => (
                <option key={choice} value={choice}>
                  {choice}
                </option>
              ))}
            </select>
          ) : (
            <input value={optionValue} onChange={(event) => onOption(event.target.value)} />
          )}
        </span>
      )}
    </span>
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
  const [extraOption, setExtraOption] = useState<Record<number, string>>({});
  const [legacyQty, setLegacyQty] = useState<Record<string, number>>({});
  const [afterparty, setAfterparty] = useState(false);
  const [aftersparring, setAftersparring] = useState(false);
  const [accommodation, setAccommodation] = useState("");
  const [notes, setNotes] = useState("");
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const byCode = new Map(availability.map((a) => [a.code, a]));
  const legacy = detail.extra_items.length === 0;

  function weaponRentals(): string[] {
    return Object.entries(legacyQty).flatMap(([code, qty]) => Array(qty).fill(code));
  }

  function extrasPayload() {
    return Object.entries(extraQty)
      .filter(([, qty]) => qty > 0)
      .map(([id, qty]) => {
        const value = (extraOption[Number(id)] ?? "").trim();
        return {
          extra_item_id: Number(id),
          qty,
          ...(value === "" ? {} : { option_value: value }),
        };
      });
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

  function toggleItem(item: ExtraItem) {
    setExtraQty((prev) => ({ ...prev, [item.id]: prev[item.id] > 0 ? 0 : 1 }));
  }

  // sections follow the action/item category split, so membership is data
  const programmeItems = detail.extra_items.filter((i) =>
    ACTION_CATEGORIES.includes(i.category as (typeof ACTION_CATEGORIES)[number]),
  );
  const optionalItems = detail.extra_items.filter(
    (i) => !ACTION_CATEGORIES.includes(i.category as (typeof ACTION_CATEGORIES)[number]),
  );

  // a full discipline is registered for as a substitute, chosen on its own row
  const selectedFull = detail.disciplines
    .filter((d) => disciplines.has(d.code))
    .filter((d) => (byCode.get(d.code)?.free ?? d.capacity) <= 0)
    .map((d) => d.code);

  /** Rows whose option is declared but unanswered block submission. */
  const unanswered = optionalItems
    .concat(programmeItems)
    .filter((item) => (extraQty[item.id] ?? 0) > 0 && item.option_label)
    .find((item) => (extraOption[item.id] ?? "").trim() === "");

  function itemRow(item: ExtraItem) {
    const qty = extraQty[item.id] ?? 0;
    return (
      <ChecklistRow
        key={item.id}
        name={item.name}
        price={formatMoney(item.price, detail.primary_currency)}
        checked={qty > 0}
        onToggle={() => toggleItem(item)}
      >
        <ScheduleLines
          when={item.schedule_when}
          where={item.schedule_where}
          remark={item.remark}
        />
        {qty > 0 && (
          <ItemControls
            item={item}
            qty={qty}
            optionValue={extraOption[item.id] ?? ""}
            onQty={(next) => setExtraQty({ ...extraQty, [item.id]: next })}
            onOption={(value) => setExtraOption({ ...extraOption, [item.id]: value })}
          />
        )}
      </ChecklistRow>
    );
  }

  async function submit() {
    if (unanswered) {
      setError(
        t("form.optionRequired", {
          label: unanswered.option_label,
          item: unanswered.name,
        }),
      );
      return;
    }
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
        // full rows were chosen knowingly, so substitute placement is accepted
        wait_for_all: selectedFull.length > 0,
        extras: extrasPayload(),
      });
      onRegistered(registration);
    } catch (err) {
      // a discipline can fill between page load and submit; the row-level
      // choice is gone by then, so the fencer re-checks their selection
      if (err instanceof ApiError && err.status === 409) {
        const detailBody = err.detail as { full_disciplines?: string[] } | null;
        if (detailBody?.full_disciplines) {
          setError(t("form.nowFull", { codes: detailBody.full_disciplines.join(", ") }));
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
      <h1>{detail.display_name}</h1>
      {detail.subtitle && <p className="detail-subtitle">{detail.subtitle}</p>}
      {detail.registration_instructions && (
        <p className="registration-instructions">{detail.registration_instructions}</p>
      )}

      <h3 className="register-section">{t("form.sections.tournament")}</h3>
      <div className="checklist">
        {detail.disciplines.map((d) => {
          const a = byCode.get(d.code);
          const taken = a ? a.taken : 0;
          const free = a ? a.free : d.capacity;
          return (
            <ChecklistRow
              key={d.code}
              name={`${d.code} — ${d.name}`}
              price={d.fee === null ? "—" : formatMoney(d.fee, detail.primary_currency)}
              checked={disciplines.has(d.code)}
              onToggle={() => toggleDiscipline(d.code)}
            >
              <ScheduleLines when={d.schedule_when} where={d.schedule_where} />
              {free <= 0 ? (
                <span className="checklist-full">
                  {t("form.full", { taken, capacity: d.capacity })}
                </span>
              ) : (
                <span>{t("form.freePlaces", { free, capacity: d.capacity })}</span>
              )}
            </ChecklistRow>
          );
        })}
      </div>

      {(programmeItems.length > 0 || legacy) && (
        <>
          <h3 className="register-section">{t("form.sections.programme")}</h3>
          <div className="checklist">
            {programmeItems.map(itemRow)}
            {legacy && (
              <ChecklistRow
                name={t("form.afterparty")}
                price={formatMoney(detail.afterparty_fee, detail.primary_currency)}
                checked={afterparty}
                onToggle={() => setAfterparty(!afterparty)}
              />
            )}
          </div>
        </>
      )}

      {(optionalItems.length > 0 || legacy) && (
        <>
          <h3 className="register-section">{t("form.sections.items")}</h3>
          <div className="checklist">
            {optionalItems.map(itemRow)}
            {legacy &&
              Object.entries(LEGACY_WEAPONS).map(([code, name]) => {
                const qty = legacyQty[code] ?? 0;
                return (
                  <ChecklistRow
                    key={code}
                    name={t("form.weaponRental", { weapon: name })}
                    price={formatMoney(detail.weapon_rental_fee, detail.primary_currency)}
                    checked={qty > 0}
                    onToggle={() =>
                      setLegacyQty({ ...legacyQty, [code]: qty > 0 ? 0 : 1 })
                    }
                  >
                    {qty > 0 && (
                      <span className="checklist-controls">
                        <span className="checklist-control">
                          {t("form.quantity")}
                          <input
                            type="number"
                            min={1}
                            max={4}
                            value={qty}
                            onChange={(event) =>
                              setLegacyQty({
                                ...legacyQty,
                                [code]: Math.max(1, Math.min(4, Number(event.target.value))),
                              })
                            }
                          />
                        </span>
                      </span>
                    )}
                  </ChecklistRow>
                );
              })}
          </div>
        </>
      )}

      <p className="form-total">
        {t("form.total", { amount: formatMoneyWithEur(total, detail) })}
      </p>

      {/* non-billable answers: nothing here changes the total */}
      <h3 className="register-section">{t("form.sections.other")}</h3>
      <div className="form-fields">
        <label className="checkbox-chip">
          <input
            type="checkbox"
            checked={aftersparring}
            onChange={(event) => setAftersparring(event.target.checked)}
          />
          {t("form.aftersparring")}
        </label>
        <label className="form-field">
          <span>{t("form.accommodation")}</span>
          <input value={accommodation} onChange={(event) => setAccommodation(event.target.value)} />
        </label>
        <label className="form-field">
          <span>{t("form.remarks")}</span>
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
      </div>

      {error && <p className="login-error">{error}</p>}

      <button
        className="btn-primary param-save"
        disabled={busy || disciplines.size === 0}
        onClick={() => void submit()}
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
      {payment.eur_amount && payment.eur_qr_png_base64 && (
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
          amount: formatMoneyWithEur(registration.total_amount, detail),
        })}
      </p>
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

      <RegistrationLines registration={registration} detail={detail} />

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
  // the detail page is split into an information screen and a separate register
  // screen; information is always the landing view
  const [screen, setScreen] = useState<"information" | "register">("information");

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
  const onRegisterScreen = screen === "register" && canRegister;

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
          onClick={() => (onRegisterScreen ? setScreen("information") : onBack())}
        >
          {onRegisterScreen ? t("detail.backToInfo") : t("detail.back")}
        </button>
        {detail === null || !registrationChecked ? (
          <p>{t("common.loading")}</p>
        ) : onRegisterScreen ? (
          <div className="setup-panel">
            <RegistrationForm
              detail={detail}
              availability={availability}
              onRegistered={(r) => {
                setRegistration(r);
                setScreen("information");
              }}
            />
          </div>
        ) : (
          <div className="setup-panel">
            <InfoHeader detail={detail} />
            <DisciplinesInfo detail={detail} availability={availability} />
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
