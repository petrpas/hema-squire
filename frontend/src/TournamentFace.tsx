import { IconX } from "@tabler/icons-react";
import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Availability,
  type Discount,
  type DiscountBreakdown,
  type DiscountCondition,
  type DisciplineGender,
  type DisciplineMaterial,
  type ExtraItem,
  type RegistrationDetail,
  type TournamentDetail as TournamentDetailData,
  api,
  logoUrl,
} from "./api";
import { FIELD_CONSTRAINTS } from "./constraints";
import DotJoined from "./DotJoined";
import { groupGoods, isAction } from "./extraItems";
import InlineProse from "./InlineProse";
import { formatMoneyWithEur } from "./money";
import { parseInteger } from "./numeric";
import { openingMomentMs } from "./openingMoment";
import Prose from "./Prose";

export const LEGACY_WEAPONS: Record<string, string> = {
  LS: "Longsword",
  SA: "Sabre",
  RA: "Single Rapier",
  RD: "Rapier & Dagger",
  SB: "Sword & Buckler",
};

const TAXONOMY_GENDERS: Record<string, string> = { "": "Open", W: "Women", M: "Men" };
const TAXONOMY_MATERIALS: Record<string, string> = { "": "Steel", Plastic: "Plastic" };

/** Port of backend/app/taxonomy.py:taxonomy_code (design
 * discipline-identity-modal D3), kept beside LEGACY_WEAPONS as the one place
 * this duplication lives. Meaningful even for a weapon outside the taxonomy. */
export function taxonomyCode(
  weapon: string,
  gender: DisciplineGender,
  material: DisciplineMaterial,
): string {
  const materialPrefix = material === "" ? "" : material;
  const genderSuffix = gender === "W" || gender === "M" ? gender : "";
  return `${materialPrefix} ${weapon}${genderSuffix}`.trim();
}

function taxonomyName(
  weapon: string,
  gender: DisciplineGender,
  material: DisciplineMaterial,
): string | null {
  const weaponName = LEGACY_WEAPONS[weapon];
  if (weaponName === undefined) return null;
  const genderName = TAXONOMY_GENDERS[gender === "W" || gender === "M" ? gender : ""];
  const name = `${weaponName} ${genderName}`;
  return material === "Plastic" ? `${name} (${TAXONOMY_MATERIALS.Plastic})` : name;
}

/** The generated name for a discipline, marked as a team discipline when it
 * is one - port of backend/app/taxonomy.py:discipline_name (design
 * discipline-identity-modal D8). Null for a weapon outside the taxonomy,
 * which requires an explicit name. */
export function disciplineName(
  weapon: string,
  gender: DisciplineGender,
  material: DisciplineMaterial,
  isTeam: boolean,
): string | null {
  const name = taxonomyName(weapon, gender, material);
  if (name === null) return null;
  return isTeam ? `Team ${name}` : name;
}

// combining diacritical marks left behind by NFKD decomposition (design
// discipline-identity-modal D4) - matches Python's unicodedata fold
const COMBINING_MARKS = /[̀-ͯ]/g;

/** Port of backend/app/taxonomy.py:normalize_slug - case-preserving (design
 * discipline-identity-modal D4). May return the empty string; the caller
 * decides the fallback. */
export function normalizeSlug(value: string): string {
  const folded = value.normalize("NFKD").replace(COMBINING_MARKS, "");
  const ascii = folded.replace(/[^\x00-\x7F]/g, "");
  const collapsed = ascii.replace(/[^A-Za-z0-9-]+/g, "-");
  return collapsed.replace(/^-+|-+$/g, "");
}

/** How the tournament's zone is named beside its opening hour — the short
 *  form the zone itself uses on that date ("SELČ", "CEST"), which is what a
 *  reader recognizes, falling back to the identifier when the browser cannot
 *  produce one. */
export function zoneAbbreviation(detail: TournamentDetailData): string {
  const at = openingMomentMs(detail.registration_opens_at);
  if (at === null) return detail.timezone;
  try {
    const parts = new Intl.DateTimeFormat(undefined, {
      timeZone: detail.timezone,
      timeZoneName: "short",
    }).formatToParts(new Date(at));
    return parts.find((part) => part.type === "timeZoneName")?.value ?? detail.timezone;
  } catch {
    return detail.timezone;
  }
}

export function InfoHeader({ detail }: { detail: TournamentDetailData }) {
  const { t } = useTranslation();
  // the tournament states itself as consecutive lines, in this order: title,
  // subtitle, date · place · qualification, the registration window, the
  // titular organizers, the description. A line whose every part is absent is
  // not rendered — DotJoined returns null rather than an empty rule.
  return (
    <section className="rail-card detail-info-header">
      {detail.has_logo && (
        <img className="detail-logo" src={logoUrl(detail.slug)} alt="" />
      )}
      <div className="detail-info-heading">
        <h1>{detail.display_name}</h1>
        {detail.subtitle && <p className="detail-subtitle">{detail.subtitle}</p>}
        <DotJoined
          className="detail-facts"
          parts={[
            new Date(detail.date).toLocaleDateString("cs"),
            detail.location?.trim() ? <InlineProse source={detail.location} /> : null,
            detail.qualification_open
              ? t("detail.qualificationOpen")
              : t("detail.qualificationRequired", { criteria: detail.qualification_criteria }),
          ]}
        />
        <DotJoined
          className="rail-hint"
          parts={[
            detail.registration_opens &&
              (detail.registration_opens_time
                ? // the hour the organizer named, with the zone it is named in:
                  // without the zone the hour is only true where the tournament
                  // is (spec: fencer-home)
                  t("detail.opensAt", {
                    date: new Date(detail.registration_opens).toLocaleDateString("cs"),
                    time: detail.registration_opens_time.slice(0, 5),
                    zone: zoneAbbreviation(detail),
                  })
                : t("detail.opensOn", {
                    date: new Date(detail.registration_opens).toLocaleDateString("cs"),
                  })),
            detail.registration_closes &&
              t("detail.closesOn", {
                date: new Date(detail.registration_closes).toLocaleDateString("cs"),
              }),
          ]}
        />
        {detail.organizers.length > 0 && (
          <p className="rail-hint">
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
          </p>
        )}
        <Prose source={detail.description} className="detail-description" />
      </div>
    </section>
  );
}

/** Optional when/where/remark line shared by discipline and action rows. The
 * caller decides how it's set off (the tournament face wraps it in a
 * `.detail-extra` line; the registration form's checklist already has its
 * own indented detail block, so it renders this plain). */
export function ScheduleLines({
  when,
  where,
  remark,
}: {
  when?: string | null;
  where?: string | null;
  remark?: string | null;
}) {
  return <DotJoined parts={[when, where, remark]} />;
}

export function DisciplinesInfo({
  detail,
  availability,
}: {
  detail: TournamentDetailData;
  availability: Availability[];
}) {
  const { t } = useTranslation();
  const bySlug = new Map(availability.map((a) => [a.slug, a]));
  const hasTeamDiscipline = detail.disciplines.some((d) => d.kind === "team");
  return (
    <section className="rail-card">
      <h2>{t("detail.disciplines")}</h2>
      <ul className="detail-list">
        {detail.disciplines.map((d) => {
          const a = bySlug.get(d.slug);
          const taken = a ? a.taken : 0;
          const free = a ? a.free : d.capacity;
          // the label stays plain text beside the field: the ruleset is inline
          // markdown and carries its own links, one per language it names
          const ruleset = d.ruleset?.trim() ? (
            <>
              {t("detail.rulesetLabel")}: <InlineProse source={d.ruleset} />
            </>
          ) : null;
          const hasExtra = Boolean(d.schedule_when || d.schedule_where || ruleset);
          const isTeam = d.kind === "team";
          return (
            <li key={d.slug}>
              <div className="detail-row">
                <strong>
                  {d.name}
                  {isTeam && <span className="tag tag-file-blue team-flag">{t("detail.teamEvent")}</span>}
                </strong>
                <DotJoined
                  parts={[
                    d.fee === null
                      ? "—"
                      : isTeam
                        ? t("detail.perTeamFee", {
                            amount: formatMoneyWithEur(d.fee, d.fee_eur, detail),
                          })
                        : formatMoneyWithEur(d.fee, d.fee_eur, detail),
                    isTeam
                      ? t("detail.rosterBounds", { min: d.team_min, max: d.team_max })
                      : null,
                    isTeam
                      ? t("detail.teamsCount", { taken, capacity: d.capacity })
                      : t("detail.fencersCount", { taken, capacity: d.capacity }),
                    free <= 0
                      ? t("detail.queueLength", { count: a?.queue_length ?? 0 })
                      : null,
                  ]}
                />
              </div>
              {hasExtra && (
                <div className="detail-extra">
                  <DotJoined
                    className=""
                    parts={[d.schedule_when, d.schedule_where, ruleset]}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {hasTeamDiscipline && detail.team_composition_deadline && (
        <p className="rail-hint">
          {t("detail.compositionDeadline", {
            date: new Date(detail.team_composition_deadline).toLocaleDateString("cs"),
          })}
        </p>
      )}
    </section>
  );
}

export function OtherActionsInfo({ detail }: { detail: TournamentDetailData }) {
  const { t } = useTranslation();
  const actions = detail.extra_items.filter(isAction);
  if (actions.length === 0) return null;
  return (
    <section className="rail-card">
      <h2>{t("detail.otherActions")}</h2>
      <ul className="detail-list">
        {actions.map((item) => {
          const hasExtra = Boolean(item.schedule_when || item.schedule_where || item.remark);
          return (
            <li key={item.id}>
              <div className="detail-row">
                <strong>{item.name}</strong>
              </div>
              {hasExtra && (
                <div className="detail-extra">
                  <DotJoined
                    className=""
                    parts={[item.schedule_when, item.schedule_where, item.remark]}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

type Translate = ReturnType<typeof useTranslation>["t"];

/** A discount's condition as localized text, from its `kind` and parameter —
 *  the sibling of the marker on the register screen, spelled out here because
 *  the information screen carries no selection to make the terms evident. */
function discountCondition(t: Translate, condition: DiscountCondition): string {
  if (condition.kind === "discipline_count") {
    return t("discounts.conditionDisciplineCount", { count: condition.count ?? 0 });
  }
  return t("discounts.conditionEarly", {
    date: condition.until ? new Date(condition.until).toLocaleDateString("cs") : "",
  });
}

/** A discount's row value: the organizer's configured figure, not the
 *  realized deduction (design Decision 4) — the same promise on both faces. */
function discountValue(t: Translate, discount: Discount, detail: TournamentDetailData): string {
  if (discount.effect.kind === "percent") {
    return t("discounts.percentValue", { value: discount.effect.value });
  }
  return t("discounts.amountValue", {
    amount: formatMoneyWithEur(discount.effect.value, discount.effect.value_eur, detail),
  });
}

/** The tournament's configured discounts (design Decision 5 — one component,
 *  two renderings). Given a `breakdown` (the register form's live price
 *  preview) each row leads with a disabled checkbox stating whether the
 *  current selection activates it. Without one (the information screen)
 *  rows carry no marker and spell out their condition instead. Renders
 *  nothing when the tournament configures no discounts (design Decision 8). */
export function DiscountList({
  detail,
  breakdown,
}: {
  detail: TournamentDetailData;
  breakdown?: DiscountBreakdown[];
}) {
  const { t } = useTranslation();
  if (detail.discounts.length === 0) return null;

  if (breakdown) {
    // inline within the register form's own rail-card, matching its other
    // sections (Tournament/programme/items) rather than nesting a card
    return (
      <>
        <h3 className="register-section">{t("discounts.title")}</h3>
        <div className="checklist">
          {detail.discounts.map((discount, index) => (
            <label key={index} className="checklist-row discount-row">
              <input type="checkbox" disabled checked={breakdown[index]?.applied ?? false} />
              <span className="checklist-name">{discount.name}</span>
              <span className="checklist-price">{discountValue(t, discount, detail)}</span>
            </label>
          ))}
        </div>
      </>
    );
  }

  return (
    <section className="rail-card">
      <h2>{t("discounts.title")}</h2>
      <ul className="detail-list">
        {detail.discounts.map((discount, index) => (
          <li key={index}>
            <div className="detail-row">
              <strong>{discount.name}</strong>
              <span>{discountValue(t, discount, detail)}</span>
            </div>
            <div className="detail-extra">{discountCondition(t, discount.condition)}</div>
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
            type="text"
            inputMode="numeric"
            value={qty}
            onChange={(event) => {
              const result = parseInteger(event.target.value);
              if (result.ok) onQty(Math.max(1, Math.min(item.max_qty, result.value)));
            }}
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
            <input
              value={optionValue}
              maxLength={FIELD_CONSTRAINTS["ExtraSelectionIn.option_value"]?.maxLength}
              onChange={(event) => onOption(event.target.value)}
            />
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
  | {
      kind: "register";
      onRegistered: (registration: RegistrationDetail) => void;
      /** The gate refused the submission as not yet open — a fast finger, or a
       *  device clock the correction could not save. The page returns to
       *  presenting the wait rather than showing a generic failure (spec:
       *  registration, fencer-home). */
      onNotYetOpen: () => void;
    }
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
    () => new Set(initial?.entries.map((e) => e.slug) ?? []),
  );
  // teams are named, not checked — a discipline row may carry several,
  // each priced separately (spec: "Team section rendered"). `id` present
  // means an already-entered team whose roster is kept on amendment; absent
  // means a freshly added one (design team-disciplines 4.3)
  const [teams, setTeams] = useState<{ id?: number; slug: string; name: string }[]>(
    () => (initial?.teams ?? []).map((team) => ({ id: team.id, slug: team.slug, name: team.name })),
  );
  const [newTeamName, setNewTeamName] = useState<Record<string, string>>({});
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
  // Neither rentals nor afterparty are offered by this form (design D4 —
  // `refine-detail-and-setup-ui`), but an amendment must not drop what an
  // older registration already carries, so the seeded state still flows
  // into the price preview and the submit payload below.
  const [legacyQty] = useState<Record<string, number>>(() => {
    const map: Record<string, number> = {};
    for (const weapon of initial?.weapon_rentals ?? []) map[weapon] = (map[weapon] ?? 0) + 1;
    return map;
  });
  const [afterparty] = useState(initial?.afterparty ?? false);
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [total, setTotal] = useState(initial?.total_amount ?? 0);
  const [eurTotal, setEurTotal] = useState<number | null>(initial?.total_eur ?? null);
  const [discounts, setDiscounts] = useState<DiscountBreakdown[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bySlug = new Map(availability.map((a) => [a.slug, a]));

  // trial selections made against a since-changed tournament (the preview's
  // `detail` can change identity mid-session) must not keep keys the
  // tournament no longer has — a stale id 422s at price-preview and blanks
  // the total
  useEffect(() => {
    const validSlugs = new Set(detail.disciplines.map((d) => d.slug));
    const validItemIds = new Set(detail.extra_items.map((i) => i.id));
    setDisciplines((prev) => {
      const next = new Set([...prev].filter((slug) => validSlugs.has(slug)));
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
  function freePlaces(slug: string): number {
    const a = bySlug.get(slug);
    const free = a ? a.free : 999999;
    const alreadyHeld = initial?.entries.some((e) => e.slug === slug && !e.is_substitute);
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
    if (disciplines.size === 0 && teams.length === 0) {
      setTotal(0);
      setEurTotal(null);
      setDiscounts([]);
      return;
    }
    const handle = setTimeout(() => {
      api
        .pricePreview(detail.slug, {
          disciplines: [...disciplines],
          weapon_rentals: weaponRentals(),
          afterparty,
          extras: extrasPayload(),
          teams: teams.map((team) => ({ slug: team.slug })),
        })
        .then(
          (result) => {
            setTotal(result.total);
            setEurTotal(result.eur_total);
            setDiscounts(result.discounts);
          },
          () => {
            setTotal(0);
            setEurTotal(null);
            setDiscounts([]);
          },
        );
    }, 300);
    return () => clearTimeout(handle);
    // `detail` is a dep too: the preview's `detail` changes identity on every
    // save (a fencer's never does mid-form), and a saved price change must
    // reach the running total, not just the per-row price
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disciplines, teams, extraQty, legacyQty, afterparty, detail]);

  function addTeam(slug: string) {
    const name = (newTeamName[slug] ?? "").trim();
    if (!name) return;
    setTeams((prev) => [...prev, { slug, name }]);
    setNewTeamName((prev) => ({ ...prev, [slug]: "" }));
  }

  function removeTeam(index: number) {
    setTeams((prev) => prev.filter((_, i) => i !== index));
  }

  function toggleDiscipline(slug: string) {
    setDisciplines((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }

  function toggleItem(item: ExtraItem) {
    setExtraQty((prev) => ({ ...prev, [item.id]: prev[item.id] > 0 ? 0 : 1 }));
  }

  // sections follow the item categories, so membership is data: the actions
  // gather into the one optional programme, the goods head a section each
  const programmeItems = detail.extra_items.filter(isAction);
  const goods = groupGoods(detail.extra_items);
  const teamDisciplines = detail.disciplines.filter((d) => d.kind === "team");

  /** Rows whose option is declared but unanswered block submission — every
   *  extra item is a candidate, wherever on the form it renders. */
  const unanswered = detail.extra_items
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
        // the API keeps both fields for the table-import path; the in-app
        // form no longer offers either (design D9)
        aftersparring: false,
        accommodation: null,
        notes: notes.trim() === "" ? null : notes,
        extras: extrasPayload(),
        teams: teams.map((team) => ({
          ...(team.id ? { id: team.id } : {}),
          slug: team.slug,
          name: team.name,
        })),
      };
      const registration = amending
        ? await api.amendRegistration(detail.slug, payload)
        : await api.registerForTournament(detail.slug, payload);
      mode.onRegistered(registration);
    } catch (err) {
      // the gate is the authority, and it may still refuse: registration had
      // not opened when the submission landed. The page goes back to stating
      // the moment, with the countdown recomputed from the fresh response
      if (err instanceof ApiError && err.status === 403 && mode.kind === "register") {
        const refusal = err.detail as { reason?: string } | null;
        if (refusal?.reason === "not_yet_open") {
          mode.onNotYetOpen();
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
        {detail.disciplines
          .filter((d) => d.kind === "individual")
          .map((d) => {
          const a = bySlug.get(d.slug);
          const taken = a ? a.taken : 0;
          const free = freePlaces(d.slug);
          return (
            <ChecklistRow
              key={d.slug}
              name={d.name}
              price={d.fee === null ? "—" : formatMoneyWithEur(d.fee, d.fee_eur, detail)}
              checked={disciplines.has(d.slug)}
              onToggle={() => toggleDiscipline(d.slug)}
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

      {teamDisciplines.length > 0 && (
        <>
          <h3 className="register-section">{t("form.sections.teams")}</h3>
          <div className="checklist">
            {teamDisciplines.map((d) => {
              const fee = d.fee === null ? "—" : formatMoneyWithEur(d.fee, d.fee_eur, detail);
              return (
                <div key={d.slug} className="team-discipline-block">
                  <div className="detail-row">
                    <strong>{d.name}</strong>
                    <DotJoined
                      parts={[
                        d.fee === null ? "—" : t("form.teams.perTeamFee", { amount: fee }),
                        t("form.teams.rosterBounds", { min: d.team_min, max: d.team_max }),
                      ]}
                    />
                  </div>
                  {teams.map((team, index) =>
                    team.slug === d.slug ? (
                      <div key={index} className="checklist-row team-row">
                        <span className="checklist-name">{team.name}</span>
                        <span className="checklist-price">{fee}</span>
                        <button
                          type="button"
                          className="row-action"
                          title={t("actions.delete")}
                          onClick={() => removeTeam(index)}
                        >
                          <IconX size={16} stroke={1.5} />
                        </button>
                      </div>
                    ) : null,
                  )}
                  <div className="team-add-row">
                    <input
                      value={newTeamName[d.slug] ?? ""}
                      placeholder={t("form.teams.namePlaceholder")}
                      onChange={(event) =>
                        setNewTeamName((prev) => ({ ...prev, [d.slug]: event.target.value }))
                      }
                    />
                    <button
                      type="button"
                      className="secondary"
                      disabled={!(newTeamName[d.slug] ?? "").trim()}
                      onClick={() => addTeam(d.slug)}
                    >
                      {t("form.teams.add")}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          {detail.team_composition_deadline && (
            <p className="rail-hint">
              {t("form.teams.deadlineNote", {
                date: new Date(detail.team_composition_deadline).toLocaleDateString("cs"),
              })}
            </p>
          )}
        </>
      )}

      {programmeItems.length > 0 && (
        <>
          <h3 className="register-section">{t("form.sections.programme")}</h3>
          <div className="checklist">{programmeItems.map(itemRow)}</div>
        </>
      )}

      {goods.map((group) => (
        <Fragment key={group.category}>
          <h3 className="register-section">{t(`form.sections.goods.${group.category}`)}</h3>
          <div className="checklist">{group.items.map(itemRow)}</div>
        </Fragment>
      ))}

      <DiscountList detail={detail} breakdown={discounts} />

      <p className="form-total">
        {t("form.total", { amount: formatMoneyWithEur(total, eurTotal, detail) })}
      </p>

      {/* non-billable answer: nothing here changes the total */}
      <h3 className="register-section">{t("form.sections.other")}</h3>
      <div className="form-fields">
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
          disabled={busy || (disciplines.size === 0 && teams.length === 0)}
          onClick={() => void submit()}
        >
          {amending ? t("form.amendSubmit") : t("form.submit")}
        </button>
      )}
    </section>
  );
}
