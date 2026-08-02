import { IconX } from "@tabler/icons-react";
import {
  Fragment,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Account,
  type Currency,
  type CurrencyMode,
  type Discipline,
  type DisciplineInput,
  type Discount,
  type DiscountCondition,
  type DiscountEffect,
  type ExtraCategory,
  type ExtraItem,
  type ExtraItemInput,
  type Organizer,
  type TeamMember,
  type TournamentDetail,
  api,
  logoUrl,
} from "./api";
import HelpHint from "./HelpHint";
import { showsEur } from "./money";
import SetupPreview from "./SetupPreview";

// design Decision D1 (split-setup-into-tabs); `publish` added last (design D6
// of add-explicit-publishing) — the end of the Setup arc, offered to every
// console team member regardless of ownership
type SetupTab = "tournament" | "disciplines" | "extra" | "payments" | "other" | "publish";
const SETUP_TABS: SetupTab[] = [
  "tournament",
  "disciplines",
  "extra",
  "payments",
  "other",
  "publish",
];

// Keys are exactly those backend/app/setup.py emits (D1); a key absent from
// this map marks no tab so an unrecognized checklist item never breaks the bar.
const MISSING_TAB: Record<string, SetupTab> = {
  location: "tournament",
  organizers: "tournament",
  disciplines: "disciplines",
  discipline_prices: "disciplines",
  extra_item_prices: "extra",
  discount_prices: "payments",
  legacy_fixed_fees_block_eur: "payments",
};

// Fixed flush/registration order, independent of effect-firing order (D7).
const SECTION_ORDER = [
  "identity",
  "organizers",
  "disciplines",
  "extra",
  "currency",
  "vsSeries",
  "discounts",
] as const;

type SaveOutcome = {
  change: string;
  section: string;
  error: string | null;
};

type SectionSaver = {
  pendingCount: number;
  touchesPrice: boolean;
  validate: () => boolean;
  flush: () => Promise<SaveOutcome[]>;
};

/** Holds every mounted section's saver, keyed by section id, and notifies
 * subscribers (the save bar, the dirty-count effect) on any change (D7). */
class SaverRegistry {
  private entries = new Map<string, { tab: SetupTab; saver: SectionSaver }>();
  private version = 0;
  private listeners = new Set<() => void>();

  set(id: string, tab: SetupTab, saver: SectionSaver) {
    // The saver closure is refreshed on every call so flush()/validate() are
    // never stale, but subscribers are only notified when a value they
    // actually display changes — otherwise every keystroke in an
    // already-dirty section would re-render the whole registry's
    // subscribers forever (each re-render re-registers, which would
    // re-notify, which would re-render...).
    const prev = this.entries.get(id);
    this.entries.set(id, { tab, saver });
    if (
      !prev ||
      prev.tab !== tab ||
      prev.saver.pendingCount !== saver.pendingCount ||
      prev.saver.touchesPrice !== saver.touchesPrice
    ) {
      this.version++;
      for (const listener of this.listeners) listener();
    }
  }

  delete(id: string) {
    if (!this.entries.delete(id)) return;
    this.version++;
    for (const listener of this.listeners) listener();
  }

  forTab(tab: SetupTab): { id: string; saver: SectionSaver }[] {
    return [...this.entries.entries()]
      .filter(([, entry]) => entry.tab === tab)
      .map(([id, entry]) => ({ id, saver: entry.saver }))
      .sort(
        (a, b) =>
          SECTION_ORDER.indexOf(a.id as (typeof SECTION_ORDER)[number]) -
          SECTION_ORDER.indexOf(b.id as (typeof SECTION_ORDER)[number]),
      );
  }

  all(): { id: string; tab: SetupTab; saver: SectionSaver }[] {
    return [...this.entries.entries()].map(([id, entry]) => ({ id, ...entry }));
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  getVersion = () => this.version;
}

/** Registers (and, on unmount, unregisters) a section's saver. Sections stay
 * mounted for the life of the Setup phase (D2), so unregistration in
 * practice only happens when SetupPanel itself unmounts. */
function useSectionSaver(registry: SaverRegistry, tab: SetupTab, id: string, saver: SectionSaver) {
  useEffect(() => {
    registry.set(id, tab, saver);
  });
  useEffect(() => () => registry.delete(id), [registry, id]);
}

const CURRENCY_MODES: CurrencyMode[] = ["local", "local_eur", "eur"];
// the only local (non-EUR) currency today (design Decision 6); a picker
// among several local currencies is future scope
const LOCAL_CURRENCY: Currency = "CZK";

/** Fills empty EUR/local price pairs from filled ones at `rate`, rounded
 * half-up to whole units, in either direction — never overwriting a typed
 * value (design Decision 3). The one place `eur_rate` touches money. */
function recalculateMissing(local: string, eur: string, rate: number): [string, string] {
  if (!Number.isFinite(rate) || rate <= 0) return [local, eur];
  if (eur === "" && local !== "" && Number.isFinite(Number(local))) {
    return [local, String(Math.round(Number(local) / rate))];
  }
  if (local === "" && eur !== "" && Number.isFinite(Number(eur))) {
    return [String(Math.round(Number(eur) * rate)), eur];
  }
  return [local, eur];
}

/** Guards a save action behind the price-change confirmation when the
 * tournament already has registrations (design Decision 7): existing
 * registrations keep their quoted amount, amending fencers are repriced,
 * new registrations use the new price. */
function usePriceChangeGuard() {
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  // `shouldWarn` is passed at call time rather than bound once from a hook
  // parameter, so it reflects the state at the moment of saving rather than
  // whatever it was at the caller's last render.
  function guard(shouldWarn: boolean, action: () => void) {
    if (shouldWarn) setPendingAction(() => action);
    else action();
  }
  function confirm() {
    const action = pendingAction;
    setPendingAction(null);
    action?.();
  }
  function cancel() {
    setPendingAction(null);
  }
  return { guard, confirming: pendingAction !== null, confirm, cancel };
}

function PriceChangeWarning({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="rail-card dashed">
      <p>{t("setup.priceChangeWarning.title")}</p>
      <ul className="detail-list">
        <li>{t("setup.priceChangeWarning.existing")}</li>
        <li>{t("setup.priceChangeWarning.amending")}</li>
        <li>{t("setup.priceChangeWarning.new")}</li>
      </ul>
      <p className="rail-hint">{t("setup.priceChangeWarning.badPractice")}</p>
      <div className="modal-actions">
        <button type="button" className="secondary" onClick={onCancel}>
          {t("common.cancel")}
        </button>
        <button type="button" className="btn-primary" onClick={onConfirm}>
          {t("setup.priceChangeWarning.proceed")}
        </button>
      </div>
    </div>
  );
}

/** Option choices are typed as one comma-separated line; the backend trims and
 *  deduplicates, so this only has to split. */
function splitChoices(value: string): string[] {
  return value.split(",").map((choice) => choice.trim()).filter(Boolean);
}

const EXTRA_CATEGORIES: ExtraCategory[] = [
  "seminar",
  "afterparty",
  "other_action",
  "rental",
  "merch",
  "other_item",
];

// action categories happen at a time and place (when/where, no quantity
// limit); item categories are goods (quantity limit, no when/where) — D4
const ACTION_EXTRA_CATEGORIES = new Set<ExtraCategory>(["seminar", "afterparty", "other_action"]);
function isActionCategory(category: ExtraCategory): boolean {
  return ACTION_EXTRA_CATEGORIES.has(category);
}

type DisciplineDraft = {
  capacity: string;
  fee: string;
  fee_eur: string;
  schedule_when: string;
  schedule_where: string;
  ruleset_name: string;
  ruleset_url: string;
};

// Identity fields patched as a whole, mirroring ParamPanel's save pattern
// but for the fields that live in the Setup tab's main content, not the rail.
const IDENTITY_FIELDS = [
  { key: "display_name", type: "text" },
  { key: "subtitle", type: "text" },
  { key: "date", type: "date" },
  { key: "location", type: "text" },
  { key: "description", type: "textarea", markdown: true },
  { key: "registration_opens", type: "date" },
  { key: "registration_closes", type: "date" },
  // shown only on the registration form, unlike description
  {
    key: "registration_instructions",
    type: "textarea",
    hint: "setup.identity.registrationInstructionsHint",
    markdown: true,
  },
] as const;

// rendered as three runs — [display_name, subtitle], [date, location, description],
// [registration_opens, registration_closes, registration_instructions] — with the
// logo block after the first and the qualification block after the second, so the
// section reads name, subtitle, logo, date, location, description, qualification,
// reg. opens, reg. closes, reg. instructions (design D5).
const IDENTITY_RUN_1 = IDENTITY_FIELDS.slice(0, 2);
const IDENTITY_RUN_2 = IDENTITY_FIELDS.slice(2, 5);
const IDENTITY_RUN_3 = IDENTITY_FIELDS.slice(5);

function IdentitySection({
  detail,
  slug,
  onSaved,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState<Record<string, string>>({});
  const [qualificationOpen, setQualificationOpen] = useState(true);
  const [qualificationCriteria, setQualificationCriteria] = useState("");
  const [qualificationError, setQualificationError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);
  // bumped on upload/remove so the <img> re-fetches past the browser cache
  const [logoVersion, setLogoVersion] = useState(0);

  async function uploadLogo(file: File) {
    setLogoBusy(true);
    setLogoError(null);
    try {
      await api.uploadLogo(slug, file);
      setLogoVersion((v) => v + 1);
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && err.status === 413) {
        setLogoError(t("setup.identity.logoTooLarge"));
      } else if (err instanceof ApiError && (err.status === 415 || err.status === 422)) {
        setLogoError(t("setup.identity.logoUnsupportedFormat"));
      } else if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setLogoError(t("setup.identity.logoNotAuthorized"));
      } else if (err instanceof ApiError) {
        setLogoError(t("setup.identity.logoUploadFailed", { status: err.status }));
      } else {
        setLogoError(t("setup.identity.logoUploadFailed", { status: "?" }));
      }
    } finally {
      setLogoBusy(false);
    }
  }

  async function removeLogo() {
    setLogoBusy(true);
    setLogoError(null);
    try {
      await api.deleteLogo(slug);
      setLogoVersion((v) => v + 1);
      onSaved();
    } finally {
      setLogoBusy(false);
    }
  }

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const field of IDENTITY_FIELDS) {
      const value = detail[field.key];
      next[field.key] = value === null || value === undefined ? "" : String(value);
    }
    setValues(next);
    setQualificationOpen(detail.qualification_open);
    setQualificationCriteria(detail.qualification_criteria ?? "");
    setQualificationError(null);
    setDirty(false);
  }, [detail]);

  useSectionSaver(registry, "tournament", "identity", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: false,
    validate: () => true,
    flush: async () => {
      setQualificationError(null);
      try {
        const patch: Record<string, unknown> = {};
        for (const field of IDENTITY_FIELDS) {
          const raw = values[field.key] ?? "";
          patch[field.key] = raw === "" ? null : raw;
        }
        patch.qualification_open = qualificationOpen;
        patch.qualification_criteria = qualificationOpen ? null : qualificationCriteria || null;
        await api.updateTournament(slug, patch);
        setDirty(false);
        return [{ change: "identity", section: "identity", error: null }];
      } catch (err) {
        const message =
          err instanceof ApiError && err.detail === "qualification_criteria_required"
            ? t("setup.identity.qualificationCriteriaRequired")
            : err instanceof ApiError && typeof err.detail === "string"
              ? err.detail
              : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        setQualificationError(message);
        return [{ change: "identity", section: "identity", error: message }];
      }
    },
  });

  function renderField(field: (typeof IDENTITY_FIELDS)[number]) {
    return field.type === "textarea" ? (
      <label key={field.key} className="form-field">
        <span>
          {t(`param.${field.key}`)}
          {"hint" in field && <HelpHint text={t(field.hint)} />}
        </span>
        <textarea
          className={"markdown" in field && field.markdown ? "markdown-input" : undefined}
          value={values[field.key] ?? ""}
          onChange={(event) => {
            setValues({ ...values, [field.key]: event.target.value });
            setDirty(true);
          }}
        />
        {"markdown" in field && field.markdown && (
          <span className="markdown-hint">{t("setup.identity.markdownHint")}</span>
        )}
      </label>
    ) : (
      <label key={field.key} className="form-field">
        <span>{t(`param.${field.key}`)}</span>
        <input
          type={field.type}
          value={values[field.key] ?? ""}
          onChange={(event) => {
            setValues({ ...values, [field.key]: event.target.value });
            setDirty(true);
          }}
        />
      </label>
    );
  }

  return (
    <section className="rail-card">
      <div className="form-fields">{IDENTITY_RUN_1.map(renderField)}</div>
      <div className="logo-control">
        <span className="logo-control-label">{t("setup.identity.logo")}</span>
        {detail.has_logo && (
          <img
            className="logo-preview"
            src={`${logoUrl(slug)}?v=${logoVersion}`}
            alt={t("setup.identity.logo")}
          />
        )}
        <div className="logo-control-actions">
          <label className="logo-upload">
            {t("setup.identity.logoUpload")}
            <input
              type="file"
              accept="image/*"
              disabled={logoBusy}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadLogo(file);
                event.target.value = "";
              }}
            />
          </label>
          {detail.has_logo && (
            <button
              type="button"
              className="link-button"
              disabled={logoBusy}
              onClick={() => void removeLogo()}
            >
              {t("setup.identity.logoRemove")}
            </button>
          )}
        </div>
        <span className="rail-hint">{t("setup.identity.logoHint")}</span>
        {logoError && <span className="login-error">{logoError}</span>}
      </div>
      <div className="form-fields">{IDENTITY_RUN_2.map(renderField)}</div>
      <div className="form-field qualification-control">
        <span>{t("setup.identity.qualification")}</span>
        <label className="qualification-option">
          <input
            type="radio"
            name={`${slug}-qualification`}
            checked={qualificationOpen}
            onChange={() => {
              setQualificationOpen(true);
              setDirty(true);
            }}
          />
          {t("setup.identity.qualificationOpen")}
        </label>
        <label className="qualification-option">
          <input
            type="radio"
            name={`${slug}-qualification`}
            checked={!qualificationOpen}
            onChange={() => {
              setQualificationOpen(false);
              setDirty(true);
            }}
          />
          {t("setup.identity.qualificationRequired")}
        </label>
        {!qualificationOpen && (
          <label className="form-field">
            <span>
              {t("setup.identity.qualificationCriteria")}
              <HelpHint text={t("setup.identity.qualificationCriteriaHint")} />
            </span>
            <input
              value={qualificationCriteria}
              onChange={(event) => {
                setQualificationCriteria(event.target.value);
                setDirty(true);
              }}
            />
          </label>
        )}
        {qualificationError && <span className="login-error">{qualificationError}</span>}
      </div>
      <div className="form-fields">{IDENTITY_RUN_3.map(renderField)}</div>
    </section>
  );
}

function VsSeriesSection({ detail }: { detail: TournamentDetail }) {
  const { t } = useTranslation();

  return (
    <section className="rail-card">
      <h2>{t("setup.vsSeries.title")}</h2>
      <p className="rail-hint">{t("setup.vsSeries.prefix", { prefix: detail.vs_prefix })}</p>
    </section>
  );
}

// a rate outside this band is almost certainly the inverse or a typo; warn,
// never block — the organizer may know something we do not (design risk note)
const PLAUSIBLE_RATE = { min: 0.5, max: 1000 };

function CurrencySection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<CurrencyMode>("local");
  const [rate, setRate] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMode(detail.currency_mode);
    setRate(detail.eur_rate ?? "");
    setError(null);
    setDirty(false);
  }, [detail]);

  const rateNumber = Number(rate);
  const implausible =
    mode === "local_eur" &&
    rate !== "" &&
    Number.isFinite(rateNumber) &&
    (rateNumber < PLAUSIBLE_RATE.min || rateNumber > PLAUSIBLE_RATE.max);

  useSectionSaver(registry, "payments", "currency", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: true,
    validate: () => true,
    flush: async () => {
      setError(null);
      try {
        await api.updateTournament(slug, {
          local_currency: mode === "eur" ? "EUR" : LOCAL_CURRENCY,
          eur_payments_enabled: mode !== "local",
          eur_rate: mode === "local_eur" && rate !== "" ? rate : null,
        });
        setDirty(false);
        return [{ change: "currency", section: "currency", error: null }];
      } catch (err) {
        const message =
          err instanceof ApiError && err.detail === "legacy_fixed_fees_block_eur"
            ? t("setup.currency.legacyFixedFeesBlockEur")
            : t("setup.saveBar.genericError", {
                status: err instanceof ApiError ? err.status : "?",
              });
        setError(message);
        return [{ change: "currency", section: "currency", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.currency.title")}</h2>
      <div className="form-fields">
        <div className="qualification-control">
          {CURRENCY_MODES.map((m) => (
            <label key={m} className="qualification-option">
              <input
                type="radio"
                name={`${slug}-currency-mode`}
                checked={mode === m}
                onChange={() => {
                  setMode(m);
                  setDirty(true);
                }}
              />
              {t(`setup.currency.mode.${m}`)}
            </label>
          ))}
        </div>
        {mode === "local_eur" && (
          <label className="form-field">
            <span>
              {t("setup.currency.rate")}
              <HelpHint text={t("setup.currency.rateHint")} />
            </span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={rate}
              onChange={(event) => {
                setRate(event.target.value);
                setDirty(true);
              }}
            />
          </label>
        )}
      </div>
      {implausible && <p className="login-error">{t("setup.currency.rateWarning")}</p>}
      {mode === "local_eur" && <p className="rail-hint">{t("setup.currency.rateNote")}</p>}
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}

function OrganizersSection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [organizers, setOrganizers] = useState<Organizer[]>(detail.organizers);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setOrganizers(detail.organizers);
    setDirty(false);
  }, [detail]);

  function patch(index: number, fields: Partial<Organizer>) {
    const next = [...organizers];
    next[index] = { ...next[index], ...fields };
    setOrganizers(next);
    setDirty(true);
  }

  useSectionSaver(registry, "tournament", "organizers", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: false,
    validate: () => true,
    flush: async () => {
      try {
        await api.updateTournament(slug, {
          organizers: organizers
            .map((o) => ({ name: o.name.trim(), link: o.link?.trim() || null }))
            .filter((o) => o.name.length > 0),
        });
        setDirty(false);
        return [{ change: "organizers", section: "organizers", error: null }];
      } catch (err) {
        const message = t("setup.saveBar.genericError", {
          status: err instanceof ApiError ? err.status : "?",
        });
        return [{ change: "organizers", section: "organizers", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.organizers.title")}</h2>
      <table className="sheet-table">
        <tbody>
          {organizers.map((organizer, index) => (
            <tr key={index}>
              <td>
                <input
                  className="cell-input"
                  value={organizer.name}
                  placeholder={t("setup.organizers.placeholder")}
                  onChange={(event) => patch(index, { name: event.target.value })}
                />
              </td>
              <td>
                <input
                  className="cell-input"
                  value={organizer.link ?? ""}
                  placeholder={t("setup.organizers.linkPlaceholder")}
                  onChange={(event) => patch(index, { link: event.target.value })}
                />
              </td>
              <td className="col-actions">
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  onClick={() => {
                    setOrganizers(organizers.filter((_, i) => i !== index));
                    setDirty(true);
                  }}
                >
                  <IconX size={16} stroke={1.5} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="link-button"
        onClick={() => {
          setOrganizers([...organizers, { name: "", link: null }]);
          setDirty(true);
        }}
      >
        + {t("setup.organizers.add")}
      </button>
    </section>
  );
}

type DisciplineRow = DisciplineDraft & {
  rowId: string;
  code: string;
  isNew: boolean;
  error: string | null;
};

function disciplineToRow(d: Discipline): DisciplineRow {
  return {
    rowId: d.code,
    code: d.code,
    isNew: false,
    error: null,
    capacity: String(d.capacity),
    fee: d.fee === null ? "" : String(d.fee),
    fee_eur: d.fee_eur === null ? "" : String(d.fee_eur),
    schedule_when: d.schedule_when ?? "",
    schedule_where: d.schedule_where ?? "",
    ruleset_name: d.ruleset_name ?? "",
    ruleset_url: d.ruleset_url ?? "",
  };
}

function disciplineRowDirty(row: DisciplineRow, detail: TournamentDetail): boolean {
  const original = detail.disciplines.find((d) => d.code === row.code);
  if (!original) return false;
  return (
    String(original.capacity) !== row.capacity ||
    (original.fee === null ? "" : String(original.fee)) !== row.fee ||
    (original.fee_eur === null ? "" : String(original.fee_eur)) !== row.fee_eur ||
    (original.schedule_when ?? "") !== row.schedule_when ||
    (original.schedule_where ?? "") !== row.schedule_where ||
    (original.ruleset_name ?? "") !== row.ruleset_name ||
    (original.ruleset_url ?? "") !== row.ruleset_url
  );
}

function disciplineRowInput(row: DisciplineRow): DisciplineInput {
  return {
    code: row.code,
    capacity: Number(row.capacity),
    fee: row.fee === "" ? null : Number(row.fee),
    fee_eur: row.fee_eur === "" ? null : Number(row.fee_eur),
    schedule_when: row.schedule_when || null,
    schedule_where: row.schedule_where || null,
    ruleset_name: row.ruleset_name || null,
    ruleset_url: row.ruleset_url || null,
  };
}

// The price-change warning is about prices specifically, not any edit to a
// row (schedule/ruleset changes are informational, not pricing) — a new row
// necessarily introduces a price, so it always counts.
function disciplineRowTouchesPrice(row: DisciplineRow, detail: TournamentDetail): boolean {
  if (row.isNew) return true;
  const original = detail.disciplines.find((d) => d.code === row.code);
  if (!original) return false;
  return (
    (original.fee === null ? "" : String(original.fee)) !== row.fee ||
    (original.fee_eur === null ? "" : String(original.fee_eur)) !== row.fee_eur
  );
}

function blankDisciplineRow(rowId: string): DisciplineRow {
  return {
    rowId,
    code: "",
    isNew: true,
    error: null,
    capacity: "",
    fee: "",
    fee_eur: "",
    schedule_when: "",
    schedule_where: "",
    ruleset_name: "",
    ruleset_url: "",
  };
}

function DisciplinesSection({
  detail,
  slug,
  pricingWarning,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  pricingWarning: boolean;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [taxonomy, setTaxonomy] = useState<Record<string, string>>({});
  const [rows, setRows] = useState<DisciplineRow[]>(() => detail.disciplines.map(disciplineToRow));
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);
  const nextTempId = useRef(0);

  const rowsRef = useRef(rows);
  rowsRef.current = rows;
  const removedRef = useRef(removed);
  removedRef.current = removed;

  useEffect(() => {
    api.taxonomy().then(setTaxonomy, () => setTaxonomy({}));
  }, []);

  // Reseed from the freshly saved detail only while the section holds no
  // pending changes, so a refetch triggered by another tab's save (or by
  // this tab's own save) cannot stomp still-pending drafts (D8).
  useEffect(() => {
    const clean =
      removedRef.current.size === 0 &&
      rowsRef.current.every((row) => !row.isNew && !disciplineRowDirty(row, detail));
    if (clean) {
      setRows(detail.disciplines.map(disciplineToRow));
      setRemoved(new Set());
    }
  }, [detail]);

  function patchRow(rowId: string, patch: Partial<DisciplineRow>) {
    setRows((prev) => prev.map((row) => (row.rowId === rowId ? { ...row, ...patch } : row)));
  }

  function removeRow(row: DisciplineRow) {
    setRows((prev) => prev.filter((r) => r.rowId !== row.rowId));
    if (!row.isNew) setRemoved((prev) => new Set(prev).add(row.code));
  }

  function addRow() {
    setRows((prev) => [...prev, blankDisciplineRow(`new-${nextTempId.current++}`)]);
  }

  function recalculateAll() {
    setRows((prev) =>
      prev.map((row) => {
        const [fee, fee_eur] = recalculateMissing(row.fee, row.fee_eur, rate);
        return { ...row, fee, fee_eur };
      }),
    );
  }

  const pendingDisciplineCount =
    removed.size + rows.filter((row) => row.isNew || disciplineRowDirty(row, detail)).length;

  useSectionSaver(registry, "disciplines", "disciplines", {
    pendingCount: pendingDisciplineCount,
    touchesPrice: rows.some((row) => disciplineRowTouchesPrice(row, detail)),
    validate: () => {
      let ok = true;
      setRows((prev) =>
        prev.map((row) => {
          const invalid =
            !row.code || row.capacity.trim() === "" || !Number.isFinite(Number(row.capacity));
          if (invalid) ok = false;
          return { ...row, error: invalid ? t("setup.disciplines.rowInvalid") : null };
        }),
      );
      return ok;
    },
    flush: async () => {
      const outcomes: SaveOutcome[] = [];
      const stillRemoved = new Set<string>();
      for (const code of removed) {
        try {
          await api.deleteDiscipline(slug, code);
          outcomes.push({ change: code, section: "disciplines", error: null });
        } catch (err) {
          stillRemoved.add(code);
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          outcomes.push({ change: code, section: "disciplines", error: message });
        }
      }

      const results = new Map<string, string | null>();
      for (const row of rowsRef.current.filter(
        (row) => !row.isNew && disciplineRowDirty(row, detail),
      )) {
        try {
          await api.updateDiscipline(slug, row.code, disciplineRowInput(row));
          results.set(row.rowId, null);
          outcomes.push({ change: row.code, section: "disciplines", error: null });
        } catch (err) {
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          results.set(row.rowId, message);
          outcomes.push({ change: row.code, section: "disciplines", error: message });
        }
      }
      for (const row of rowsRef.current.filter((row) => row.isNew)) {
        try {
          await api.addDiscipline(slug, disciplineRowInput(row));
          results.set(row.rowId, null);
          outcomes.push({ change: row.code, section: "disciplines", error: null });
        } catch (err) {
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          results.set(row.rowId, message);
          outcomes.push({ change: row.code, section: "disciplines", error: message });
        }
      }

      setRemoved(stillRemoved);
      setRows((prev) =>
        prev.map((row) => {
          const result = results.get(row.rowId);
          if (result === undefined) return row;
          return result === null ? { ...row, isNew: false, error: null } : { ...row, error: result };
        }),
      );
      return outcomes;
    },
  });

  const usedCodes = new Set(rows.map((row) => row.code));
  const availableCodes = Object.keys(taxonomy).filter((code) => !usedCodes.has(code));

  return (
    <section className="rail-card">
      <h2>{t("setup.disciplines.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.disciplines.code")}</th>
            <th>{t("setup.disciplines.capacity")}</th>
            <th>{t("setup.disciplines.fee", { currency: detail.local_currency })}</th>
            {eur && <th>{t("setup.disciplines.feeEur")}</th>}
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <Fragment key={row.rowId}>
              <tr>
                <td>
                  {row.code === "" ? (
                    <select
                      value={row.code}
                      onChange={(event) => patchRow(row.rowId, { code: event.target.value })}
                    >
                      <option value="">—</option>
                      {availableCodes.map((code) => (
                        <option key={code} value={code}>
                          {code} — {taxonomy[code]}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <strong>
                      {row.code} — {taxonomy[row.code] ?? row.code}
                    </strong>
                  )}
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="number"
                    min={1}
                    value={row.capacity}
                    onChange={(event) => patchRow(row.rowId, { capacity: event.target.value })}
                  />
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="number"
                    min={0}
                    value={row.fee}
                    onChange={(event) => patchRow(row.rowId, { fee: event.target.value })}
                  />
                </td>
                {eur && (
                  <td>
                    <input
                      className="cell-input"
                      type="number"
                      min={0}
                      value={row.fee_eur}
                      onChange={(event) => patchRow(row.rowId, { fee_eur: event.target.value })}
                    />
                  </td>
                )}
                <td className="col-actions">
                  <button
                    className="row-action"
                    title={t("actions.delete")}
                    onClick={() => removeRow(row)}
                  >
                    <IconX size={16} stroke={1.5} />
                  </button>
                </td>
              </tr>
              <tr className="detail-subrow">
                <td colSpan={eur ? 5 : 4}>
                  <div className="param-fields">
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.when")}
                        <HelpHint text={t("setup.disciplines.whenHint")} />
                      </span>
                      <input
                        value={row.schedule_when}
                        onChange={(event) =>
                          patchRow(row.rowId, { schedule_when: event.target.value })
                        }
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.where")}
                        <HelpHint text={t("setup.disciplines.whereHint")} />
                      </span>
                      <input
                        value={row.schedule_where}
                        onChange={(event) =>
                          patchRow(row.rowId, { schedule_where: event.target.value })
                        }
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.rulesetName")}
                        <HelpHint text={t("setup.disciplines.rulesetNameHint")} />
                      </span>
                      <input
                        value={row.ruleset_name}
                        onChange={(event) =>
                          patchRow(row.rowId, { ruleset_name: event.target.value })
                        }
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.rulesetUrl")}
                        <HelpHint text={t("setup.disciplines.rulesetUrlHint")} />
                      </span>
                      <input
                        value={row.ruleset_url}
                        onChange={(event) =>
                          patchRow(row.rowId, { ruleset_url: event.target.value })
                        }
                      />
                    </label>
                  </div>
                  {row.error && <span className="login-error">{row.error}</span>}
                </td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
      <button className="link-button" onClick={addRow}>
        + {t("setup.disciplines.add")}
      </button>
      {eur && (
        <button
          className="link-button"
          disabled={!Number.isFinite(rate) || rate <= 0}
          onClick={recalculateAll}
        >
          {t("setup.recalculateMissing")}
        </button>
      )}
    </section>
  );
}

type ExtraRow = Omit<ExtraItem, "id"> & {
  rowId: string;
  id: number | null;
  isNew: boolean;
  error: string | null;
  // The raw text of the choices input, kept separate from the parsed
  // `option_choices` array so typing a comma isn't immediately stripped by
  // re-deriving the field's displayed value from the trimmed/filtered array.
  optionChoicesText: string;
};

function extraItemToRow(item: ExtraItem): ExtraRow {
  return {
    ...item,
    rowId: String(item.id),
    isNew: false,
    error: null,
    optionChoicesText: item.option_choices.join(", "),
  };
}

function blankExtraRow(rowId: string): ExtraRow {
  return {
    rowId,
    id: null,
    isNew: true,
    error: null,
    name: "",
    category: "rental",
    price: 0,
    price_eur: null,
    max_qty: 1,
    schedule_when: null,
    schedule_where: null,
    remark: null,
    option_label: null,
    option_choices: [],
    optionChoicesText: "",
  };
}

function extraRowDirty(row: ExtraRow, detail: TournamentDetail): boolean {
  const item = detail.extra_items.find((i) => i.id === row.id);
  if (!item) return false;
  return (
    row.name !== item.name ||
    row.category !== item.category ||
    row.price !== item.price ||
    row.price_eur !== item.price_eur ||
    row.max_qty !== item.max_qty ||
    (row.schedule_when ?? "") !== (item.schedule_when ?? "") ||
    (row.schedule_where ?? "") !== (item.schedule_where ?? "") ||
    (row.remark ?? "") !== (item.remark ?? "") ||
    (row.option_label ?? "") !== (item.option_label ?? "") ||
    row.option_choices.join(",") !== item.option_choices.join(",")
  );
}

function extraRowTouchesPrice(row: ExtraRow, detail: TournamentDetail): boolean {
  if (row.isNew) return true;
  const item = detail.extra_items.find((i) => i.id === row.id);
  if (!item) return false;
  return row.price !== item.price || row.price_eur !== item.price_eur;
}

function extraRowInput(row: ExtraRow): ExtraItemInput {
  return {
    name: row.name,
    category: row.category,
    price: row.price,
    price_eur: row.price_eur,
    max_qty: row.max_qty,
    schedule_when: row.schedule_when || null,
    schedule_where: row.schedule_where || null,
    remark: row.remark || null,
    option_label: row.option_label || null,
    // an option-less item must not carry leftover choices
    option_choices: row.option_label ? row.option_choices : [],
  };
}

function ExtraItemsSection({
  detail,
  slug,
  pricingWarning,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  pricingWarning: boolean;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<ExtraRow[]>(() => detail.extra_items.map(extraItemToRow));
  const [removed, setRemoved] = useState<Set<number>>(new Set());
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);
  const nextTempId = useRef(0);

  const rowsRef = useRef(rows);
  rowsRef.current = rows;
  const removedRef = useRef(removed);
  removedRef.current = removed;

  // Reseed from the freshly saved detail only while the section holds no
  // pending changes (D8), matching the discipline table's guard.
  useEffect(() => {
    const clean =
      removedRef.current.size === 0 &&
      rowsRef.current.every((row) => !row.isNew && !extraRowDirty(row, detail));
    if (clean) {
      setRows(detail.extra_items.map(extraItemToRow));
      setRemoved(new Set());
    }
  }, [detail]);

  function patchRow(rowId: string, patch: Partial<ExtraRow>) {
    setRows((prev) => prev.map((row) => (row.rowId === rowId ? { ...row, ...patch } : row)));
  }

  function removeRow(row: ExtraRow) {
    setRows((prev) => prev.filter((r) => r.rowId !== row.rowId));
    if (!row.isNew && row.id !== null) setRemoved((prev) => new Set(prev).add(row.id!));
  }

  function addRow() {
    setRows((prev) => [...prev, blankExtraRow(`new-${nextTempId.current++}`)]);
  }

  function recalculateAll() {
    setRows((prev) =>
      prev.map((row) => {
        const [price, price_eur] = recalculateMissing(
          String(row.price),
          row.price_eur === null ? "" : String(row.price_eur),
          rate,
        );
        return { ...row, price: Number(price), price_eur: price_eur === "" ? null : Number(price_eur) };
      }),
    );
  }

  const pendingExtraCount =
    removed.size + rows.filter((row) => row.isNew || extraRowDirty(row, detail)).length;

  useSectionSaver(registry, "extra", "extra", {
    pendingCount: pendingExtraCount,
    touchesPrice: rows.some((row) => extraRowTouchesPrice(row, detail)),
    validate: () => {
      let ok = true;
      setRows((prev) =>
        prev.map((row) => {
          const invalid = !row.name.trim() || !(row.price > 0);
          if (invalid) ok = false;
          return { ...row, error: invalid ? t("setup.extras.rowInvalid") : null };
        }),
      );
      return ok;
    },
    flush: async () => {
      const outcomes: SaveOutcome[] = [];
      const stillRemoved = new Set<number>();
      for (const id of removed) {
        try {
          await api.deleteExtraItem(slug, id);
          outcomes.push({ change: String(id), section: "extra", error: null });
        } catch (err) {
          stillRemoved.add(id);
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          outcomes.push({ change: String(id), section: "extra", error: message });
        }
      }

      const results = new Map<string, string | null>();
      for (const row of rowsRef.current.filter((row) => !row.isNew && extraRowDirty(row, detail))) {
        try {
          await api.updateExtraItem(slug, row.id!, extraRowInput(row));
          results.set(row.rowId, null);
          outcomes.push({ change: row.name, section: "extra", error: null });
        } catch (err) {
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          results.set(row.rowId, message);
          outcomes.push({ change: row.name, section: "extra", error: message });
        }
      }
      for (const row of rowsRef.current.filter((row) => row.isNew)) {
        try {
          await api.addExtraItem(slug, extraRowInput(row));
          results.set(row.rowId, null);
          outcomes.push({ change: row.name, section: "extra", error: null });
        } catch (err) {
          const message = t("setup.saveBar.genericError", {
            status: err instanceof ApiError ? err.status : "?",
          });
          results.set(row.rowId, message);
          outcomes.push({ change: row.name, section: "extra", error: message });
        }
      }

      setRemoved(stillRemoved);
      setRows((prev) =>
        prev.map((row) => {
          const result = results.get(row.rowId);
          if (result === undefined) return row;
          return result === null ? { ...row, isNew: false, error: null } : { ...row, error: result };
        }),
      );
      return outcomes;
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.extras.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.extras.name")}</th>
            <th>{t("setup.extras.category")}</th>
            <th>{t("setup.extras.price", { currency: detail.local_currency })}</th>
            {eur && <th>{t("setup.extras.priceEur")}</th>}
            <th>{t("setup.extras.maxQty")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <Fragment key={row.rowId}>
              <tr>
                <td>
                  <input
                    className="cell-input"
                    value={row.name}
                    onChange={(event) => patchRow(row.rowId, { name: event.target.value })}
                  />
                </td>
                <td>
                  <select
                    value={row.category}
                    onChange={(event) => {
                      const category = event.target.value as ExtraCategory;
                      const action = isActionCategory(category);
                      patchRow(row.rowId, {
                        category,
                        max_qty: action ? 1 : row.max_qty,
                        schedule_when: action ? row.schedule_when : null,
                        schedule_where: action ? row.schedule_where : null,
                      });
                    }}
                  >
                    {EXTRA_CATEGORIES.map((category) => (
                      <option key={category} value={category}>
                        {t(`setup.extras.categories.${category}`)}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="number"
                    min={0}
                    value={row.price}
                    onChange={(event) => patchRow(row.rowId, { price: Number(event.target.value) })}
                  />
                </td>
                {eur && (
                  <td>
                    <input
                      className="cell-input"
                      type="number"
                      min={0}
                      value={row.price_eur ?? ""}
                      onChange={(event) =>
                        patchRow(row.rowId, {
                          price_eur: event.target.value === "" ? null : Number(event.target.value),
                        })
                      }
                    />
                  </td>
                )}
                <td>
                  {!isActionCategory(row.category) && (
                    <input
                      className="cell-input"
                      type="number"
                      min={1}
                      value={row.max_qty}
                      onChange={(event) =>
                        patchRow(row.rowId, { max_qty: Number(event.target.value) })
                      }
                    />
                  )}
                </td>
                <td className="col-actions">
                  <button
                    className="row-action"
                    title={t("actions.delete")}
                    onClick={() => removeRow(row)}
                  >
                    <IconX size={16} stroke={1.5} />
                  </button>
                </td>
              </tr>
              <tr className="detail-subrow">
                <td colSpan={eur ? 6 : 5}>
                  <div className="param-fields">
                    {isActionCategory(row.category) && (
                      <>
                        <label className="param-field">
                          <span>{t("setup.extras.when")}</span>
                          <input
                            value={row.schedule_when ?? ""}
                            onChange={(event) =>
                              patchRow(row.rowId, { schedule_when: event.target.value })
                            }
                          />
                        </label>
                        <label className="param-field">
                          <span>{t("setup.extras.where")}</span>
                          <input
                            value={row.schedule_where ?? ""}
                            onChange={(event) =>
                              patchRow(row.rowId, { schedule_where: event.target.value })
                            }
                          />
                        </label>
                      </>
                    )}
                    <label className="param-field">
                      <span>{t("setup.extras.remark")}</span>
                      <input
                        value={row.remark ?? ""}
                        onChange={(event) => patchRow(row.rowId, { remark: event.target.value })}
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.extras.optionLabel")}
                        <HelpHint text={t("setup.extras.optionLabelHint")} />
                      </span>
                      <input
                        value={row.option_label ?? ""}
                        onChange={(event) =>
                          patchRow(row.rowId, { option_label: event.target.value })
                        }
                      />
                    </label>
                    {row.option_label && (
                      <label className="param-field">
                        <span>
                          {t("setup.extras.optionChoices")}
                          <HelpHint text={t("setup.extras.optionChoicesHint")} />
                        </span>
                        <input
                          value={row.optionChoicesText}
                          onChange={(event) =>
                            patchRow(row.rowId, {
                              optionChoicesText: event.target.value,
                              option_choices: splitChoices(event.target.value),
                            })
                          }
                        />
                      </label>
                    )}
                  </div>
                  {row.error && <span className="login-error">{row.error}</span>}
                </td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
      <button className="link-button" onClick={addRow}>
        + {t("setup.extras.add")}
      </button>
      {eur && (
        <button
          className="link-button"
          disabled={!Number.isFinite(rate) || rate <= 0}
          onClick={recalculateAll}
        >
          {t("setup.recalculateMissing")}
        </button>
      )}
    </section>
  );
}

function emptyDiscount(): Discount {
  return {
    name: "",
    condition: { kind: "discipline_count", count: 2 },
    effect: { kind: "fixed", value: 0 },
    scope: ["discipline"],
  };
}

function DiscountsSection({
  detail,
  slug,
  pricingWarning,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  pricingWarning: boolean;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Discount[]>(detail.discounts);
  const [dirty, setDirty] = useState(false);
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);

  useEffect(() => {
    setDrafts(detail.discounts);
    setDirty(false);
  }, [detail]);

  function update(index: number, patch: Partial<Discount>) {
    const next = [...drafts];
    next[index] = { ...next[index], ...patch };
    setDrafts(next);
    setDirty(true);
  }

  function updateCondition(index: number, patch: Partial<DiscountCondition>) {
    update(index, { condition: { ...drafts[index].condition, ...patch } });
  }

  function updateEffect(index: number, patch: Partial<DiscountEffect>) {
    update(index, { effect: { ...drafts[index].effect, ...patch } });
  }

  function recalculateAll() {
    setDrafts((prev) =>
      prev.map((discount) => {
        if (discount.effect.kind !== "fixed") return discount;
        const [value, valueEur] = recalculateMissing(
          String(discount.effect.value),
          discount.effect.value_eur === null || discount.effect.value_eur === undefined
            ? ""
            : String(discount.effect.value_eur),
          rate,
        );
        return {
          ...discount,
          effect: { ...discount.effect, value: Number(value), value_eur: valueEur === "" ? null : Number(valueEur) },
        };
      }),
    );
    setDirty(true);
  }

  useSectionSaver(registry, "payments", "discounts", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: true,
    validate: () => true,
    flush: async () => {
      try {
        await api.updateTournament(slug, { discounts: drafts });
        setDirty(false);
        return [{ change: "discounts", section: "discounts", error: null }];
      } catch (err) {
        const message = t("setup.saveBar.genericError", {
          status: err instanceof ApiError ? err.status : "?",
        });
        return [{ change: "discounts", section: "discounts", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.discounts.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.discounts.name")}</th>
            <th>{t("setup.discounts.condition")}</th>
            <th>{t("setup.discounts.effect")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {drafts.map((discount, index) => (
            <tr key={index}>
              <td>
                <input
                  className="cell-input"
                  value={discount.name}
                  onChange={(event) => update(index, { name: event.target.value })}
                />
              </td>
              <td>
                <div className="param-fields">
                  <select
                    value={discount.condition.kind}
                    onChange={(event) =>
                      updateCondition(index, {
                        kind: event.target.value as DiscountCondition["kind"],
                      })
                    }
                  >
                    <option value="discipline_count">
                      {t("setup.discounts.conditionCount")}
                    </option>
                    <option value="early">{t("setup.discounts.conditionEarly")}</option>
                  </select>
                  {discount.condition.kind === "discipline_count" ? (
                    <input
                      className="cell-input"
                      type="number"
                      min={1}
                      value={discount.condition.count ?? ""}
                      onChange={(event) =>
                        updateCondition(index, { count: Number(event.target.value) })
                      }
                    />
                  ) : (
                    <input
                      className="cell-input"
                      type="date"
                      value={discount.condition.until ?? ""}
                      onChange={(event) =>
                        updateCondition(index, { until: event.target.value })
                      }
                    />
                  )}
                </div>
              </td>
              <td>
                <div className="param-fields">
                  <select
                    value={discount.effect.kind}
                    onChange={(event) => {
                      const kind = event.target.value as DiscountEffect["kind"];
                      // a percent effect is currency-neutral and carries no
                      // second value (design Decision 1)
                      updateEffect(index, { kind, value_eur: kind === "fixed" ? discount.effect.value_eur : null });
                    }}
                  >
                    <option value="fixed">
                      {t("setup.discounts.fixed", { currency: detail.local_currency })}
                    </option>
                    <option value="percent">{t("setup.discounts.percent")}</option>
                  </select>
                  <input
                    className="cell-input"
                    type="number"
                    min={0}
                    value={discount.effect.value}
                    onChange={(event) =>
                      updateEffect(index, { value: Number(event.target.value) })
                    }
                  />
                  {eur && discount.effect.kind === "fixed" && (
                    <input
                      className="cell-input"
                      type="number"
                      min={0}
                      placeholder={t("setup.discounts.fixedEur")}
                      value={discount.effect.value_eur ?? ""}
                      onChange={(event) =>
                        updateEffect(index, {
                          value_eur:
                            event.target.value === "" ? null : Number(event.target.value),
                        })
                      }
                    />
                  )}
                </div>
              </td>
              <td className="col-actions">
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  onClick={() => {
                    setDrafts(drafts.filter((_, i) => i !== index));
                    setDirty(true);
                  }}
                >
                  <IconX size={16} stroke={1.5} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="link-button"
        onClick={() => {
          setDrafts([...drafts, emptyDiscount()]);
          setDirty(true);
        }}
      >
        + {t("setup.discounts.add")}
      </button>
      {eur && (
        <button
          className="link-button"
          disabled={!Number.isFinite(rate) || rate <= 0}
          onClick={recalculateAll}
        >
          {t("setup.recalculateMissing")}
        </button>
      )}
    </section>
  );
}

function TeamSection({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [team, setTeam] = useState<TeamMember[] | null>(null);
  const [email, setEmail] = useState("");
  const [transferEmail, setTransferEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refreshTeam() {
    api.team(slug).then(setTeam, () => setTeam([]));
  }

  useEffect(refreshTeam, [slug]);

  async function add() {
    setBusy(true);
    setError(null);
    try {
      await api.addTeamMember(slug, email.trim());
      setEmail("");
      refreshTeam();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? t("setup.team.unknownEmail")
          : err instanceof ApiError && err.status === 409
            ? t("setup.team.alreadyMember")
            : t("setup.team.addFailed"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function remove(fencerId: number) {
    setBusy(true);
    try {
      await api.removeTeamMember(slug, fencerId);
      refreshTeam();
    } finally {
      setBusy(false);
    }
  }

  async function transfer() {
    setBusy(true);
    setError(null);
    try {
      await api.transferOwnership(slug, transferEmail.trim());
      setTransferEmail("");
      refreshTeam();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? t("setup.team.transferNotMember")
          : err instanceof ApiError && err.status === 404
            ? t("setup.team.unknownEmail")
            : t("setup.team.transferFailed"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.team.title")}</h2>
      {error && <p className="login-error">{error}</p>}
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("setup.team.email")}</th>
            <th>{t("setup.team.displayName")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {(team ?? []).map((member) => (
            <tr key={member.fencer_id}>
              <td>{member.email}</td>
              <td>{member.display_name}</td>
              <td className="col-actions">
                <button
                  className="row-action"
                  title={t("actions.delete")}
                  disabled={busy}
                  onClick={() => void remove(member.fencer_id)}
                >
                  <IconX size={16} stroke={1.5} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="rail-hint">{t("setup.team.addPlaceholder")}</p>
      <div className="inline-form">
        <input
          type="email"
          value={email}
          placeholder={t("setup.team.addPlaceholder")}
          onChange={(event) => setEmail(event.target.value)}
        />
        <button className="secondary" disabled={busy || !email} onClick={() => void add()}>
          {t("setup.team.add")}
        </button>
      </div>
      <p className="rail-hint">{t("setup.team.transferHint")}</p>
      <div className="inline-form">
        <input
          type="email"
          value={transferEmail}
          placeholder={t("setup.team.transferPlaceholder")}
          onChange={(event) => setTransferEmail(event.target.value)}
        />
        <button
          className="secondary"
          disabled={busy || !transferEmail}
          onClick={() => void transfer()}
        >
          {t("setup.team.transfer")}
        </button>
      </div>
    </section>
  );
}

function DangerZoneSection({
  slug,
  hasRegistrations,
  cancelled,
  onDeleted,
  onCancelled,
}: {
  slug: string;
  hasRegistrations: boolean;
  cancelled: boolean;
  onDeleted: () => void;
  onCancelled: () => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act() {
    setBusy(true);
    setError(null);
    try {
      if (hasRegistrations) {
        await api.cancelTournament(slug);
        onCancelled();
      } else {
        await api.deleteTournament(slug);
        onDeleted();
      }
    } catch {
      setError(t("setup.danger.failed"));
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  }

  if (cancelled) {
    return (
      <section className="rail-card danger-zone">
        <h2>{t("setup.danger.title")}</h2>
        <p className="rail-hint">{t("setup.danger.alreadyCancelled")}</p>
      </section>
    );
  }

  return (
    <section className="rail-card danger-zone">
      <h2>{t("setup.danger.title")}</h2>
      <p className="rail-hint">
        {hasRegistrations ? t("setup.danger.cancelHint") : t("setup.danger.deleteHint")}
      </p>
      {error && <p className="login-error">{error}</p>}
      {confirming ? (
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={() => setConfirming(false)}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn-primary" disabled={busy} onClick={() => void act()}>
            {hasRegistrations ? t("setup.danger.cancelButton") : t("setup.danger.deleteButton")}
          </button>
        </div>
      ) : (
        <button className="secondary" onClick={() => setConfirming(true)}>
          {hasRegistrations ? t("setup.danger.cancelButton") : t("setup.danger.deleteButton")}
        </button>
      )}
    </section>
  );
}

function PublishSection({
  slug,
  detail,
  hasUnsavedChanges,
  onPublished,
}: {
  slug: string;
  detail: TournamentDetail;
  hasUnsavedChanges: boolean;
  onPublished: () => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const missing = detail.setup_missing ?? [];

  async function act() {
    setBusy(true);
    setError(null);
    try {
      await api.publishTournament(slug);
      onPublished();
    } catch (err) {
      const reason =
        err instanceof ApiError && typeof err.detail === "string"
          ? err.detail
          : err instanceof ApiError &&
              typeof err.detail === "object" &&
              err.detail !== null &&
              (err.detail as { reason?: string }).reason === "setup_incomplete"
            ? "setup_incomplete"
            : null;
      setError(
        reason === "already_published"
          ? t("setup.publish.failedAlreadyPublished")
          : reason === "cancelled"
            ? t("setup.publish.failedCancelled")
            : reason === "setup_incomplete"
              ? t("setup.publish.failedIncomplete")
              : t("setup.publish.failedGeneric"),
      );
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  }

  if (detail.published_at !== null) {
    return (
      <section className="rail-card dashed">
        <h2>{t("setup.tabs.publish")}</h2>
        <p className="rail-hint">
          {t("setup.publish.published", {
            date: new Date(detail.published_at).toLocaleDateString("cs"),
          })}
        </p>
      </section>
    );
  }

  if (detail.cancelled_at !== null) {
    return (
      <section className="rail-card dashed">
        <h2>{t("setup.tabs.publish")}</h2>
        <p className="rail-hint">{t("setup.publish.cancelled")}</p>
      </section>
    );
  }

  return (
    <section className="rail-card dashed">
      <h2>{t("setup.tabs.publish")}</h2>
      <p className="rail-hint">{t("setup.publish.draftStatement")}</p>
      {missing.length > 0 && (
        <>
          <div className="chips">
            {missing.map((key) => (
              <span key={key} className="chip">
                {t(`setup.missing.${key}`)}
              </span>
            ))}
          </div>
          <p className="rail-hint">{t("setup.publish.blockedHint")}</p>
        </>
      )}
      {hasUnsavedChanges && <p className="rail-hint">{t("setup.publish.unsavedNote")}</p>}
      {error && <p className="login-error">{error}</p>}
      {confirming ? (
        <>
          <p className="rail-hint">{t("setup.publish.confirmBody")}</p>
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </button>
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void act()}>
              {t("setup.publish.confirmButton")}
            </button>
          </div>
        </>
      ) : (
        <button
          className="btn-primary"
          disabled={missing.length > 0}
          onClick={() => setConfirming(true)}
        >
          {t("setup.publish.publishButton")}
        </button>
      )}
    </section>
  );
}

function SetupTabBar({
  tabs,
  tab,
  onSelect,
  markedTabs,
}: {
  tabs: SetupTab[];
  tab: SetupTab;
  onSelect: (tab: SetupTab) => void;
  markedTabs: Set<SetupTab>;
}) {
  const { t } = useTranslation();

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      onSelect(tabs[(index + 1) % tabs.length]);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      onSelect(tabs[(index - 1 + tabs.length) % tabs.length]);
    }
  }

  return (
    <nav className="stage-control setup-tabs" role="tablist">
      {tabs.map((id, index) => (
        <button
          key={id}
          type="button"
          role="tab"
          id={`setup-tab-${id}`}
          aria-selected={tab === id}
          aria-controls={`setup-tabpanel-${id}`}
          className={tab === id ? "active" : ""}
          onClick={() => onSelect(id)}
          onKeyDown={(event) => onKeyDown(event, index)}
        >
          {t(`setup.tabs.${id}`)}
          {markedTabs.has(id) && (
            <span className="tab-mark">
              <span className="visually-hidden">{t("setup.tabs.incomplete")}</span>
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}

function SetupSaveBar({
  tab,
  registry,
  hasRegistrations,
  onSaved,
}: {
  tab: SetupTab;
  registry: SaverRegistry;
  hasRegistrations: boolean;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  useSyncExternalStore(registry.subscribe, registry.getVersion);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<{
    written: number;
    total: number;
    failures: SaveOutcome[];
  } | null>(null);

  const entries = registry.forTab(tab);
  const pendingCount = entries.reduce((sum, entry) => sum + entry.saver.pendingCount, 0);
  const { guard, confirming, confirm, cancel } = usePriceChangeGuard();

  useEffect(() => {
    setReport(null);
  }, [tab]);

  async function doSave() {
    // Re-read the registry live rather than trusting `entries` captured at
    // the last render: notify only fires when a saver's pendingCount or
    // touchesPrice actually changes, so a section that has been dirty for a
    // while (typing more into an already-dirty field, editing another field
    // on an already-dirty row) never re-renders this bar — its closure here
    // would otherwise be stale and flush() would write an old value.
    const liveEntries = registry.forTab(tab);
    setBusy(true);
    setReport(null);
    try {
      const outcomes: SaveOutcome[] = [];
      for (const entry of liveEntries) {
        if (entry.saver.pendingCount === 0) continue;
        outcomes.push(...(await entry.saver.flush()));
      }
      onSaved();
      const failures = outcomes.filter((outcome) => outcome.error !== null);
      setReport({ written: outcomes.length - failures.length, total: outcomes.length, failures });
    } finally {
      setBusy(false);
    }
  }

  function attemptSave() {
    const liveEntries = registry.forTab(tab);
    let anyInvalid = false;
    for (const entry of liveEntries) {
      if (!entry.saver.validate()) anyInvalid = true;
    }
    if (anyInvalid) return;
    const touchesPriceNow = liveEntries.some(
      (entry) => entry.saver.touchesPrice && entry.saver.pendingCount > 0,
    );
    guard(touchesPriceNow && hasRegistrations, () => void doSave());
  }

  if (entries.length === 0) return null;

  return (
    <div className="setup-save-bar">
      {confirming && <PriceChangeWarning onConfirm={confirm} onCancel={cancel} />}
      {report && report.failures.length > 0 && (
        <div className="rail-hint">
          <p>
            {t("setup.saveBar.partial", {
              written: report.written,
              total: report.total,
              pending: report.failures.length,
            })}
          </p>
          <ul className="detail-list">
            {report.failures.map((failure, index) => (
              <li key={index}>
                {failure.change}: {failure.error}
              </li>
            ))}
          </ul>
        </div>
      )}
      <button
        type="button"
        className="btn-primary"
        disabled={busy || pendingCount === 0}
        onClick={attemptSave}
      >
        {pendingCount === 0
          ? t("setup.saveBar.nothingToSave")
          : t("setup.saveBar.save", { count: pendingCount })}
      </button>
    </div>
  );
}

export default function SetupPanel({
  detail,
  slug,
  onSaved,
  hasRegistrations,
  onDeleted,
  onDirtyChange,
}: {
  detail: TournamentDetail | null;
  slug: string;
  onSaved: () => void;
  hasRegistrations: boolean;
  onDeleted: () => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useTranslation();
  const [account, setAccount] = useState<Account | null>(null);
  const [tab, setTab] = useState<SetupTab>("tournament");
  const registry = useRef(new SaverRegistry()).current;
  useSyncExternalStore(registry.subscribe, registry.getVersion);

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const totalPending = registry
    .all()
    .reduce((sum, entry) => sum + entry.saver.pendingCount, 0);

  useEffect(() => {
    onDirtyChange(totalPending > 0);
  }, [totalPending, onDirtyChange]);

  if (detail === null) return <p>{t("common.loading")}</p>;

  const isOwner = account !== null && account.id === detail.owner_id;
  const offeredTabs = isOwner ? SETUP_TABS : SETUP_TABS.filter((setupTab) => setupTab !== "other");
  const missing = detail.setup_missing ?? [];
  const markedTabs = new Set(
    missing
      .map((key) => MISSING_TAB[key])
      .filter((value): value is SetupTab => value !== undefined),
  );
  // PUBLISH carries a marker whenever any other tab does — it is where the
  // items are listed (design D7)
  if (markedTabs.size > 0) markedTabs.add("publish");

  return (
    <div className="setup-split">
      <div className="setup-panel">
        <div className="setup-panel-header">
          <SetupTabBar tabs={offeredTabs} tab={tab} onSelect={setTab} markedTabs={markedTabs} />
        </div>
        <div className="setup-panel-body">
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-tournament"
            role="tabpanel"
            aria-labelledby="setup-tab-tournament"
            hidden={tab !== "tournament"}
          >
            <IdentitySection detail={detail} slug={slug} onSaved={onSaved} registry={registry} />
            <OrganizersSection detail={detail} slug={slug} registry={registry} />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-disciplines"
            role="tabpanel"
            aria-labelledby="setup-tab-disciplines"
            hidden={tab !== "disciplines"}
          >
            <DisciplinesSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
            />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-extra"
            role="tabpanel"
            aria-labelledby="setup-tab-extra"
            hidden={tab !== "extra"}
          >
            <ExtraItemsSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
            />
          </div>
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-payments"
            role="tabpanel"
            aria-labelledby="setup-tab-payments"
            hidden={tab !== "payments"}
          >
            <CurrencySection detail={detail} slug={slug} registry={registry} />
            <VsSeriesSection detail={detail} />
            <DiscountsSection
              detail={detail}
              slug={slug}
              pricingWarning={hasRegistrations}
              registry={registry}
            />
          </div>
          {isOwner && (
            <div
              className="setup-tabpanel"
              id="setup-tabpanel-other"
              role="tabpanel"
              aria-labelledby="setup-tab-other"
              hidden={tab !== "other"}
            >
              <TeamSection slug={slug} />
              <DangerZoneSection
                slug={slug}
                hasRegistrations={hasRegistrations}
                cancelled={detail.cancelled_at !== null}
                onDeleted={onDeleted}
                onCancelled={onSaved}
              />
            </div>
          )}
          <div
            className="setup-tabpanel"
            id="setup-tabpanel-publish"
            role="tabpanel"
            aria-labelledby="setup-tab-publish"
            hidden={tab !== "publish"}
          >
            <PublishSection
              slug={slug}
              detail={detail}
              hasUnsavedChanges={totalPending > 0}
              onPublished={onSaved}
            />
          </div>
          <SetupSaveBar
            tab={tab}
            registry={registry}
            hasRegistrations={hasRegistrations}
            onSaved={onSaved}
          />
        </div>
      </div>
      <SetupPreview detail={detail} slug={slug} />
    </div>
  );
}
