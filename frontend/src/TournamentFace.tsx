import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Availability,
  type ExtraItem,
  type RegistrationDetail,
  type TournamentDetail as TournamentDetailData,
  api,
  logoUrl,
} from "./api";
import { formatMoney, formatMoneyWithEur } from "./money";
import Prose from "./Prose";

export const LEGACY_WEAPONS: Record<string, string> = {
  LS: "Longsword",
  SA: "Sabre",
  RA: "Single Rapier",
  RD: "Rapier & Dagger",
  SB: "Sword & Buckler",
};

type RegistrationStatus = "open" | "opens_on" | "closed";

export function registrationStatus(detail: TournamentDetailData): RegistrationStatus {
  const today = new Date().toISOString().slice(0, 10);
  if (detail.registration_opens && today < detail.registration_opens) return "opens_on";
  const closes = detail.registration_closes ?? detail.date;
  if (today > closes) return "closed";
  return "open";
}

/** Amendment is closed by every reason registration is, plus its own,
 * earlier `amendments_close` boundary when set (mirrors
 * setup.amendment_availability on the backend). */
export function amendmentOpen(detail: TournamentDetailData): boolean {
  if (registrationStatus(detail) !== "open") return false;
  if (!detail.amendments_close) return true;
  const today = new Date().toISOString().slice(0, 10);
  return today <= detail.amendments_close;
}

export function InfoHeader({ detail }: { detail: TournamentDetailData }) {
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
        <Prose source={detail.description} className="detail-description" />
      </div>
    </section>
  );
}

// the time-and-place ("action") categories, mirroring the backend's
// ACTION_CATEGORIES: shown as informational "other actions" on the information
// screen — where gear lending and merch are deliberately omitted — and grouped
// as the optional programme on the register screen
export const ACTION_CATEGORIES = ["seminar", "afterparty", "other_action"] as const;

/** Optional when/where/remark lines shared by discipline and action rows. */
export function ScheduleLines({
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

export function DisciplinesInfo({
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
                {d.fee === null ? "—" : formatMoneyWithEur(d.fee, d.fee_eur, detail)} ·{" "}
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

export function OtherActionsInfo({ detail }: { detail: TournamentDetailData }) {
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
export function ChecklistRow({
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
export function ItemControls({
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

/** How `RegistrationForm` behaves: creating a fresh registration, amending an
 *  existing one, or previewed from the console — explorable but unable to
 *  submit, so "no interaction creates a registration" is a type-level fact. */
export type FormMode =
  | { kind: "register"; onRegistered: (registration: RegistrationDetail) => void }
  | { kind: "amend"; initial: RegistrationDetail; onRegistered: (registration: RegistrationDetail) => void }
  | { kind: "preview" };

export function RegistrationForm({
  detail,
  availability,
  mode,
}: {
  detail: TournamentDetailData;
  availability: Availability[];
  mode: FormMode;
}) {
  const { t } = useTranslation();
  const amending = mode.kind === "amend";
  const initial = mode.kind === "amend" ? mode.initial : undefined;
  const [disciplines, setDisciplines] = useState<Set<string>>(
    () => new Set(initial?.entries.map((e) => e.code) ?? []),
  );
  const [extraQty, setExtraQty] = useState<Record<number, number>>(() => {
    const map: Record<number, number> = {};
    for (const extra of initial?.extras ?? []) map[extra.extra_item_id] = extra.qty;
    return map;
  });
  const [extraOption, setExtraOption] = useState<Record<number, string>>(() => {
    const map: Record<number, string> = {};
    for (const extra of initial?.extras ?? []) {
      if (extra.option_value) map[extra.extra_item_id] = extra.option_value;
    }
    return map;
  });
  const [legacyQty, setLegacyQty] = useState<Record<string, number>>(() => {
    const map: Record<string, number> = {};
    for (const weapon of initial?.weapon_rentals ?? []) map[weapon] = (map[weapon] ?? 0) + 1;
    return map;
  });
  const [afterparty, setAfterparty] = useState(initial?.afterparty ?? false);
  const [aftersparring, setAftersparring] = useState(initial?.aftersparring ?? false);
  const [accommodation, setAccommodation] = useState(initial?.accommodation ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [total, setTotal] = useState(initial?.total_amount ?? 0);
  const [eurTotal, setEurTotal] = useState<number | null>(initial?.total_eur ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const byCode = new Map(availability.map((a) => [a.code, a]));
  const legacy = detail.extra_items.length === 0;

  // trial selections made against a since-changed tournament (the preview's
  // `detail` can change identity mid-session) must not keep keys the
  // tournament no longer has — a stale id 422s at price-preview and blanks
  // the total
  useEffect(() => {
    const validCodes = new Set(detail.disciplines.map((d) => d.code));
    const validItemIds = new Set(detail.extra_items.map((i) => i.id));
    setDisciplines((prev) => {
      const next = new Set([...prev].filter((code) => validCodes.has(code)));
      return next.size === prev.size ? prev : next;
    });
    setExtraQty((prev) => {
      const next = Object.fromEntries(
        Object.entries(prev).filter(([id]) => validItemIds.has(Number(id))),
      );
      return Object.keys(next).length === Object.keys(prev).length ? prev : next;
    });
    setExtraOption((prev) => {
      const next = Object.fromEntries(
        Object.entries(prev).filter(([id]) => validItemIds.has(Number(id))),
      );
      return Object.keys(next).length === Object.keys(prev).length ? prev : next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  // an already-held (non-substitute) discipline still counts itself as taken
  // in `availability` — amending frees it before re-claiming it, so it must
  // not read as full just because this registration already occupies it
  function freePlaces(code: string): number {
    const a = byCode.get(code);
    const free = a ? a.free : 999999;
    const alreadyHeld = initial?.entries.some((e) => e.code === code && !e.is_substitute);
    return alreadyHeld ? free + 1 : free;
  }

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
      setEurTotal(null);
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
        .then(
          (result) => {
            setTotal(result.total);
            setEurTotal(result.eur_total);
          },
          () => {
            setTotal(0);
            setEurTotal(null);
          },
        );
    }, 300);
    return () => clearTimeout(handle);
    // `detail` is a dep too: the preview's `detail` changes identity on every
    // save (a fencer's never does mid-form), and a saved price change must
    // reach the running total, not just the per-row price
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disciplines, extraQty, legacyQty, afterparty, detail]);

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
    .filter((d) => freePlaces(d.code) <= 0)
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
        price={formatMoneyWithEur(item.price, item.price_eur, detail)}
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
    if (mode.kind === "preview") return;
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
      const payload = {
        disciplines: [...disciplines],
        weapon_rentals: weaponRentals(),
        afterparty,
        aftersparring,
        accommodation: accommodation.trim() === "" ? null : accommodation,
        notes: notes.trim() === "" ? null : notes,
        // full rows were chosen knowingly, so substitute placement is accepted
        wait_for_all: selectedFull.length > 0,
        extras: extrasPayload(),
      };
      const registration = amending
        ? await api.amendRegistration(detail.slug, payload)
        : await api.registerForTournament(detail.slug, payload);
      mode.onRegistered(registration);
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
      <h2>{amending ? t("form.amendTitle") : t("form.title")}</h2>
      <p className="tiskopis-number">{t("form.formNumber")}</p>
      <h1>{detail.display_name}</h1>
      {detail.subtitle && <p className="detail-subtitle">{detail.subtitle}</p>}
      <Prose source={detail.registration_instructions} className="registration-instructions" />

      <h3 className="register-section">{t("form.sections.tournament")}</h3>
      <div className="checklist">
        {detail.disciplines.map((d) => {
          const a = byCode.get(d.code);
          const taken = a ? a.taken : 0;
          const free = freePlaces(d.code);
          return (
            <ChecklistRow
              key={d.code}
              name={`${d.code} — ${d.name}`}
              price={d.fee === null ? "—" : formatMoneyWithEur(d.fee, d.fee_eur, detail)}
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
                price={formatMoney(detail.afterparty_fee, detail.local_currency)}
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
                    price={formatMoney(detail.weapon_rental_fee, detail.local_currency)}
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
        {t("form.total", { amount: formatMoneyWithEur(total, eurTotal, detail) })}
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

      {mode.kind === "preview" ? (
        <p className="rail-hint">{t("preview.cannotSubmit")}</p>
      ) : (
        <button
          className="btn-primary param-save"
          disabled={busy || disciplines.size === 0}
          onClick={() => void submit()}
        >
          {amending ? t("form.amendSubmit") : t("form.submit")}
        </button>
      )}
    </section>
  );
}
