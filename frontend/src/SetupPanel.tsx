import { IconCheck, IconPlus, IconX } from "@tabler/icons-react";
import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  type Account,
  type Currency,
  type CurrencyMode,
  type Discount,
  type DiscountCondition,
  type DiscountEffect,
  type ExtraCategory,
  type ExtraItem,
  type Organizer,
  type TeamMember,
  type TournamentDetail,
  api,
  logoUrl,
} from "./api";
import HelpHint from "./HelpHint";
import { showsEur } from "./money";

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
function usePriceChangeGuard(pricingWarning: boolean) {
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  function guard(action: () => void) {
    if (pricingWarning) setPendingAction(() => action);
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
  { key: "description", type: "textarea" },
  { key: "date", type: "date" },
  { key: "location", type: "text" },
  { key: "language", type: "text" },
  { key: "registration_opens", type: "date" },
  { key: "registration_closes", type: "date" },
  // shown only on the registration form, unlike description
  {
    key: "registration_instructions",
    type: "textarea",
    hint: "setup.identity.registrationInstructionsHint",
  },
] as const;

function IdentitySection({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState<Record<string, string>>({});
  const [qualificationOpen, setQualificationOpen] = useState(true);
  const [qualificationCriteria, setQualificationCriteria] = useState("");
  const [qualificationError, setQualificationError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
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

  async function save() {
    setBusy(true);
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
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && err.detail === "qualification_criteria_required") {
        setQualificationError(t("setup.identity.qualificationCriteriaRequired"));
      } else {
        throw err;
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <div className="form-fields">
        {IDENTITY_FIELDS.map((field) =>
          field.type === "textarea" ? (
            <label key={field.key} className="form-field">
              <span>
                {t(`param.${field.key}`)}
                {"hint" in field && <HelpHint text={t(field.hint)} />}
              </span>
              <textarea
                value={values[field.key] ?? ""}
                onChange={(event) => {
                  setValues({ ...values, [field.key]: event.target.value });
                  setDirty(true);
                }}
              />
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
          ),
        )}
      </div>
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
          <label className="secondary logo-upload">
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
              className="secondary"
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
      <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}

function VsSeriesSection({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [series, setSeries] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSeries(String(detail.vs_series));
    setError(null);
    setDirty(false);
  }, [detail]);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api.updateTournament(slug, { vs_series: Number(series) });
      setDirty(false);
      onSaved();
    } catch (err) {
      if (
        err instanceof ApiError &&
        typeof err.detail === "string" &&
        err.detail.startsWith("vs_series_taken")
      ) {
        setError(t("setup.vsSeries.taken"));
      } else if (err instanceof ApiError && err.detail === "vs_series_frozen") {
        setError(t("setup.vsSeries.frozen"));
      } else {
        throw err;
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.vsSeries.title")}</h2>
      {detail.vs_series_editable ? (
        <div className="form-fields">
          <label className="form-field">
            <span>
              {t("setup.vsSeries.series")}
              <HelpHint text={t("setup.vsSeries.seriesHint")} />
            </span>
            <input
              type="number"
              min={1}
              max={99}
              value={series}
              onChange={(event) => {
                setSeries(event.target.value);
                setDirty(true);
              }}
            />
          </label>
        </div>
      ) : (
        <p className="rail-hint">{t("setup.vsSeries.frozenHint")}</p>
      )}
      <p className="rail-hint">{t("setup.vsSeries.prefix", { prefix: detail.vs_prefix })}</p>
      {error && <p className="login-error">{error}</p>}
      {detail.vs_series_editable && (
        <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
          {t("rail.save")}
        </button>
      )}
    </section>
  );
}

// a rate outside this band is almost certainly the inverse or a typo; warn,
// never block — the organizer may know something we do not (design risk note)
const PLAUSIBLE_RATE = { min: 0.5, max: 1000 };

function CurrencySection({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<CurrencyMode>("local");
  const [rate, setRate] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
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

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api.updateTournament(slug, {
        local_currency: mode === "eur" ? "EUR" : LOCAL_CURRENCY,
        eur_payments_enabled: mode !== "local",
        eur_rate: mode === "local_eur" && rate !== "" ? rate : null,
      });
      setDirty(false);
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && err.detail === "legacy_fixed_fees_block_eur") {
        setError(t("setup.currency.legacyFixedFeesBlockEur"));
      } else {
        throw err;
      }
    } finally {
      setBusy(false);
    }
  }

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
      <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}

function OrganizersSection({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [organizers, setOrganizers] = useState<Organizer[]>(detail.organizers);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

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

  async function save() {
    setBusy(true);
    try {
      await api.updateTournament(slug, {
        organizers: organizers
          .map((o) => ({ name: o.name.trim(), link: o.link?.trim() || null }))
          .filter((o) => o.name.length > 0),
      });
      setDirty(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

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
        className="secondary param-save"
        onClick={() => {
          setOrganizers([...organizers, { name: "", link: null }]);
          setDirty(true);
        }}
      >
        + {t("setup.organizers.add")}
      </button>
      <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}

function DisciplinesSection({
  detail,
  slug,
  onSaved,
  pricingWarning,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  pricingWarning: boolean;
}) {
  const { t } = useTranslation();
  const [taxonomy, setTaxonomy] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, DisciplineDraft>>({});
  const [newCode, setNewCode] = useState("");
  const [newCapacity, setNewCapacity] = useState("");
  const [newFee, setNewFee] = useState("");
  const [newFeeEur, setNewFeeEur] = useState("");
  const [busy, setBusy] = useState(false);
  const { guard, confirming, confirm, cancel } = usePriceChangeGuard(pricingWarning);
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);

  useEffect(() => {
    api.taxonomy().then(setTaxonomy, () => setTaxonomy({}));
  }, []);

  useEffect(() => {
    const next: Record<string, DisciplineDraft> = {};
    for (const d of detail.disciplines) {
      next[d.code] = {
        capacity: String(d.capacity),
        fee: d.fee === null ? "" : String(d.fee),
        fee_eur: d.fee_eur === null ? "" : String(d.fee_eur),
        schedule_when: d.schedule_when ?? "",
        schedule_where: d.schedule_where ?? "",
        ruleset_name: d.ruleset_name ?? "",
        ruleset_url: d.ruleset_url ?? "",
      };
    }
    setDrafts(next);
  }, [detail]);

  function dirty(code: string): boolean {
    const original = detail.disciplines.find((d) => d.code === code);
    const draft = drafts[code];
    if (!original || !draft) return false;
    return (
      String(original.capacity) !== draft.capacity ||
      (original.fee === null ? "" : String(original.fee)) !== draft.fee ||
      (original.fee_eur === null ? "" : String(original.fee_eur)) !== draft.fee_eur ||
      (original.schedule_when ?? "") !== draft.schedule_when ||
      (original.schedule_where ?? "") !== draft.schedule_where ||
      (original.ruleset_name ?? "") !== draft.ruleset_name ||
      (original.ruleset_url ?? "") !== draft.ruleset_url
    );
  }

  function patchDraft(code: string, patch: Partial<DisciplineDraft>) {
    setDrafts((prev) => ({ ...prev, [code]: { ...prev[code], ...patch } }));
  }

  function recalculateRow(code: string) {
    const draft = drafts[code];
    if (!draft) return;
    const [fee, fee_eur] = recalculateMissing(draft.fee, draft.fee_eur, rate);
    patchDraft(code, { fee, fee_eur });
  }

  async function saveRow(code: string) {
    const draft = drafts[code];
    setBusy(true);
    try {
      await api.updateDiscipline(slug, code, {
        code,
        capacity: Number(draft.capacity),
        fee: draft.fee === "" ? null : Number(draft.fee),
        fee_eur: draft.fee_eur === "" ? null : Number(draft.fee_eur),
        schedule_when: draft.schedule_when || null,
        schedule_where: draft.schedule_where || null,
        ruleset_name: draft.ruleset_name || null,
        ruleset_url: draft.ruleset_url || null,
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function removeRow(code: string) {
    setBusy(true);
    try {
      await api.deleteDiscipline(slug, code);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function addRow() {
    setBusy(true);
    try {
      await api.addDiscipline(slug, {
        code: newCode,
        capacity: Number(newCapacity),
        fee: newFee === "" ? null : Number(newFee),
        fee_eur: newFeeEur === "" ? null : Number(newFeeEur),
      });
      setNewCode("");
      setNewCapacity("");
      setNewFee("");
      setNewFeeEur("");
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  const usedCodes = new Set(detail.disciplines.map((d) => d.code));
  const availableCodes = Object.keys(taxonomy).filter((code) => !usedCodes.has(code));

  return (
    <section className="rail-card">
      <h2>{t("setup.disciplines.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      {confirming && <PriceChangeWarning onConfirm={confirm} onCancel={cancel} />}
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
          {detail.disciplines.map((d) => (
            <Fragment key={d.code}>
              <tr>
                <td>
                  <strong>
                    {d.code} — {d.name}
                  </strong>
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="number"
                    min={1}
                    value={drafts[d.code]?.capacity ?? ""}
                    onChange={(event) => patchDraft(d.code, { capacity: event.target.value })}
                  />
                </td>
                <td>
                  <input
                    className="cell-input"
                    type="number"
                    min={0}
                    value={drafts[d.code]?.fee ?? ""}
                    onChange={(event) => patchDraft(d.code, { fee: event.target.value })}
                  />
                </td>
                {eur && (
                  <td>
                    <input
                      className="cell-input"
                      type="number"
                      min={0}
                      value={drafts[d.code]?.fee_eur ?? ""}
                      onChange={(event) => patchDraft(d.code, { fee_eur: event.target.value })}
                    />
                  </td>
                )}
                <td className="col-actions">
                  {dirty(d.code) && (
                    <button
                      className="row-action"
                      title={t("rail.save")}
                      disabled={busy}
                      onClick={() => guard(() => void saveRow(d.code))}
                    >
                      <IconCheck size={16} stroke={1.5} />
                    </button>
                  )}
                  <button
                    className="row-action"
                    title={t("actions.delete")}
                    disabled={busy}
                    onClick={() => void removeRow(d.code)}
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
                        value={drafts[d.code]?.schedule_when ?? ""}
                        onChange={(event) =>
                          patchDraft(d.code, { schedule_when: event.target.value })
                        }
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.where")}
                        <HelpHint text={t("setup.disciplines.whereHint")} />
                      </span>
                      <input
                        value={drafts[d.code]?.schedule_where ?? ""}
                        onChange={(event) =>
                          patchDraft(d.code, { schedule_where: event.target.value })
                        }
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.rulesetName")}
                        <HelpHint text={t("setup.disciplines.rulesetNameHint")} />
                      </span>
                      <input
                        value={drafts[d.code]?.ruleset_name ?? ""}
                        onChange={(event) =>
                          patchDraft(d.code, { ruleset_name: event.target.value })
                        }
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.disciplines.rulesetUrl")}
                        <HelpHint text={t("setup.disciplines.rulesetUrlHint")} />
                      </span>
                      <input
                        value={drafts[d.code]?.ruleset_url ?? ""}
                        onChange={(event) =>
                          patchDraft(d.code, { ruleset_url: event.target.value })
                        }
                      />
                    </label>
                  </div>
                </td>
              </tr>
            </Fragment>
          ))}
          <tr>
            <td>
              <select value={newCode} onChange={(event) => setNewCode(event.target.value)}>
                <option value="">—</option>
                {availableCodes.map((code) => (
                  <option key={code} value={code}>
                    {code} — {taxonomy[code]}
                  </option>
                ))}
              </select>
            </td>
            <td>
              <input
                className="cell-input"
                type="number"
                min={1}
                value={newCapacity}
                onChange={(event) => setNewCapacity(event.target.value)}
              />
            </td>
            <td>
              <input
                className="cell-input"
                type="number"
                min={0}
                value={newFee}
                onChange={(event) => setNewFee(event.target.value)}
              />
            </td>
            {eur && (
              <td>
                <input
                  className="cell-input"
                  type="number"
                  min={0}
                  value={newFeeEur}
                  onChange={(event) => setNewFeeEur(event.target.value)}
                />
              </td>
            )}
            <td className="col-actions">
              <button
                className="row-action"
                title={t("setup.disciplines.add")}
                disabled={busy || !newCode || !newCapacity}
                onClick={() => void addRow()}
              >
                <IconPlus size={16} stroke={1.5} />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      {eur && (
        <button
          className="secondary param-save"
          disabled={!Number.isFinite(rate) || rate <= 0}
          onClick={() => {
            for (const d of detail.disciplines) recalculateRow(d.code);
          }}
        >
          {t("setup.recalculateMissing")}
        </button>
      )}
    </section>
  );
}

function ExtraItemsSection({
  detail,
  slug,
  onSaved,
  pricingWarning,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  pricingWarning: boolean;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Record<number, ExtraItem>>({});
  const [newItem, setNewItem] = useState({
    name: "",
    category: "rental" as ExtraCategory,
    price: "",
    price_eur: "",
    max_qty: "1",
  });
  const [busy, setBusy] = useState(false);
  const { guard, confirming, confirm, cancel } = usePriceChangeGuard(pricingWarning);
  const eur = showsEur(detail);
  const rate = Number(detail.eur_rate);

  useEffect(() => {
    const next: Record<number, ExtraItem> = {};
    for (const item of detail.extra_items) next[item.id] = { ...item };
    setDrafts(next);
  }, [detail]);

  function dirty(item: ExtraItem): boolean {
    const draft = drafts[item.id];
    if (!draft) return false;
    return (
      draft.name !== item.name ||
      draft.category !== item.category ||
      draft.price !== item.price ||
      draft.price_eur !== item.price_eur ||
      draft.max_qty !== item.max_qty ||
      (draft.schedule_when ?? "") !== (item.schedule_when ?? "") ||
      (draft.schedule_where ?? "") !== (item.schedule_where ?? "") ||
      (draft.remark ?? "") !== (item.remark ?? "") ||
      (draft.option_label ?? "") !== (item.option_label ?? "") ||
      draft.option_choices.join(",") !== item.option_choices.join(",")
    );
  }

  function recalculateRow(id: number) {
    const draft = drafts[id];
    if (!draft) return;
    const [price, price_eur] = recalculateMissing(
      String(draft.price),
      draft.price_eur === null ? "" : String(draft.price_eur),
      rate,
    );
    setDrafts((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        price: Number(price),
        price_eur: price_eur === "" ? null : Number(price_eur),
      },
    }));
  }

  async function saveRow(id: number) {
    const draft = drafts[id];
    setBusy(true);
    try {
      await api.updateExtraItem(slug, id, {
        name: draft.name,
        category: draft.category,
        price: draft.price,
        price_eur: draft.price_eur,
        max_qty: draft.max_qty,
        schedule_when: draft.schedule_when || null,
        schedule_where: draft.schedule_where || null,
        remark: draft.remark || null,
        option_label: draft.option_label || null,
        // an option-less item must not carry leftover choices
        option_choices: draft.option_label ? draft.option_choices : [],
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function removeRow(id: number) {
    setBusy(true);
    try {
      await api.deleteExtraItem(slug, id);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  async function addRow() {
    setBusy(true);
    try {
      await api.addExtraItem(slug, {
        name: newItem.name,
        category: newItem.category,
        price: Number(newItem.price),
        price_eur: newItem.price_eur === "" ? null : Number(newItem.price_eur),
        max_qty: Number(newItem.max_qty) || 1,
      });
      setNewItem({ name: "", category: "rental", price: "", price_eur: "", max_qty: "1" });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.extras.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      {confirming && <PriceChangeWarning onConfirm={confirm} onCancel={cancel} />}
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
          {detail.extra_items.map((item) => {
            const draft = drafts[item.id] ?? item;
            return (
              <Fragment key={item.id}>
              <tr>
                <td>
                  <input
                    className="cell-input"
                    value={draft.name}
                    onChange={(event) =>
                      setDrafts({ ...drafts, [item.id]: { ...draft, name: event.target.value } })
                    }
                  />
                </td>
                <td>
                  <select
                    value={draft.category}
                    onChange={(event) => {
                      const category = event.target.value as ExtraCategory;
                      const action = isActionCategory(category);
                      setDrafts({
                        ...drafts,
                        [item.id]: {
                          ...draft,
                          category,
                          max_qty: action ? 1 : draft.max_qty,
                          schedule_when: action ? draft.schedule_when : null,
                          schedule_where: action ? draft.schedule_where : null,
                        },
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
                    value={draft.price}
                    onChange={(event) =>
                      setDrafts({
                        ...drafts,
                        [item.id]: { ...draft, price: Number(event.target.value) },
                      })
                    }
                  />
                </td>
                {eur && (
                  <td>
                    <input
                      className="cell-input"
                      type="number"
                      min={0}
                      value={draft.price_eur ?? ""}
                      onChange={(event) =>
                        setDrafts({
                          ...drafts,
                          [item.id]: {
                            ...draft,
                            price_eur:
                              event.target.value === "" ? null : Number(event.target.value),
                          },
                        })
                      }
                    />
                  </td>
                )}
                <td>
                  {!isActionCategory(draft.category) && (
                    <input
                      className="cell-input"
                      type="number"
                      min={1}
                      value={draft.max_qty}
                      onChange={(event) =>
                        setDrafts({
                          ...drafts,
                          [item.id]: { ...draft, max_qty: Number(event.target.value) },
                        })
                      }
                    />
                  )}
                </td>
                <td className="col-actions">
                  {dirty(item) && (
                    <button
                      className="row-action"
                      title={t("rail.save")}
                      disabled={busy}
                      onClick={() => guard(() => void saveRow(item.id))}
                    >
                      <IconCheck size={16} stroke={1.5} />
                    </button>
                  )}
                  <button
                    className="row-action"
                    title={t("actions.delete")}
                    disabled={busy}
                    onClick={() => void removeRow(item.id)}
                  >
                    <IconX size={16} stroke={1.5} />
                  </button>
                </td>
              </tr>
              <tr className="detail-subrow">
                <td colSpan={eur ? 6 : 5}>
                  <div className="param-fields">
                    {isActionCategory(draft.category) && (
                      <>
                        <label className="param-field">
                          <span>{t("setup.extras.when")}</span>
                          <input
                            value={draft.schedule_when ?? ""}
                            onChange={(event) =>
                              setDrafts({
                                ...drafts,
                                [item.id]: { ...draft, schedule_when: event.target.value },
                              })
                            }
                          />
                        </label>
                        <label className="param-field">
                          <span>{t("setup.extras.where")}</span>
                          <input
                            value={draft.schedule_where ?? ""}
                            onChange={(event) =>
                              setDrafts({
                                ...drafts,
                                [item.id]: { ...draft, schedule_where: event.target.value },
                              })
                            }
                          />
                        </label>
                      </>
                    )}
                    <label className="param-field">
                      <span>{t("setup.extras.remark")}</span>
                      <input
                        value={draft.remark ?? ""}
                        onChange={(event) =>
                          setDrafts({
                            ...drafts,
                            [item.id]: { ...draft, remark: event.target.value },
                          })
                        }
                      />
                    </label>
                    <label className="param-field">
                      <span>
                        {t("setup.extras.optionLabel")}
                        <HelpHint text={t("setup.extras.optionLabelHint")} />
                      </span>
                      <input
                        value={draft.option_label ?? ""}
                        onChange={(event) =>
                          setDrafts({
                            ...drafts,
                            [item.id]: { ...draft, option_label: event.target.value },
                          })
                        }
                      />
                    </label>
                    {draft.option_label && (
                      <label className="param-field">
                        <span>
                          {t("setup.extras.optionChoices")}
                          <HelpHint text={t("setup.extras.optionChoicesHint")} />
                        </span>
                        <input
                          value={draft.option_choices.join(", ")}
                          onChange={(event) =>
                            setDrafts({
                              ...drafts,
                              [item.id]: {
                                ...draft,
                                option_choices: splitChoices(event.target.value),
                              },
                            })
                          }
                        />
                      </label>
                    )}
                  </div>
                </td>
              </tr>
              </Fragment>
            );
          })}
          <tr>
            <td>
              <input
                className="cell-input"
                value={newItem.name}
                onChange={(event) => setNewItem({ ...newItem, name: event.target.value })}
              />
            </td>
            <td>
              <select
                value={newItem.category}
                onChange={(event) => {
                  const category = event.target.value as ExtraCategory;
                  setNewItem({
                    ...newItem,
                    category,
                    max_qty: isActionCategory(category) ? "1" : newItem.max_qty,
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
                value={newItem.price}
                onChange={(event) => setNewItem({ ...newItem, price: event.target.value })}
              />
            </td>
            {eur && (
              <td>
                <input
                  className="cell-input"
                  type="number"
                  min={0}
                  value={newItem.price_eur}
                  onChange={(event) => setNewItem({ ...newItem, price_eur: event.target.value })}
                />
              </td>
            )}
            <td>
              {!isActionCategory(newItem.category) && (
                <input
                  className="cell-input"
                  type="number"
                  min={1}
                  value={newItem.max_qty}
                  onChange={(event) => setNewItem({ ...newItem, max_qty: event.target.value })}
                />
              )}
            </td>
            <td className="col-actions">
              <button
                className="row-action"
                title={t("setup.extras.add")}
                disabled={busy || !newItem.name || !newItem.price}
                onClick={() => void addRow()}
              >
                <IconPlus size={16} stroke={1.5} />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      {eur && (
        <button
          className="secondary param-save"
          disabled={!Number.isFinite(rate) || rate <= 0}
          onClick={() => {
            for (const item of detail.extra_items) recalculateRow(item.id);
          }}
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
  onSaved,
  pricingWarning,
}: {
  detail: TournamentDetail;
  slug: string;
  onSaved: () => void;
  pricingWarning: boolean;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Discount[]>(detail.discounts);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const { guard, confirming, confirm, cancel } = usePriceChangeGuard(pricingWarning);
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

  async function save() {
    setBusy(true);
    try {
      await api.updateTournament(slug, { discounts: drafts });
      setDirty(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.discounts.title")}</h2>
      {pricingWarning && <p className="login-error">{t("setup.pricingWarning")}</p>}
      {confirming && <PriceChangeWarning onConfirm={confirm} onCancel={cancel} />}
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
        className="secondary param-save"
        onClick={() => {
          setDrafts([...drafts, emptyDiscount()]);
          setDirty(true);
        }}
      >
        + {t("setup.discounts.add")}
      </button>
      {eur && (
        <button
          className="secondary param-save"
          disabled={!Number.isFinite(rate) || rate <= 0}
          onClick={recalculateAll}
        >
          {t("setup.recalculateMissing")}
        </button>
      )}
      <button
        className="secondary param-save"
        onClick={() => guard(() => void save())}
        disabled={!dirty || busy}
      >
        {t("rail.save")}
      </button>
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

function ChecklistSection({ detail }: { detail: TournamentDetail }) {
  const { t } = useTranslation();
  const missing = detail.setup_missing ?? [];
  return (
    <section className="rail-card dashed">
      <h2>{t("setup.checklist.title")}</h2>
      {missing.length === 0 ? (
        <p className="rail-hint">{t("setup.checklist.ready")}</p>
      ) : (
        <div className="chips">
          {missing.map((key) => (
            <span key={key} className="chip">
              {t(`setup.missing.${key}`)}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

export default function SetupPanel({
  detail,
  slug,
  onSaved,
  hasRegistrations,
  onDeleted,
}: {
  detail: TournamentDetail | null;
  slug: string;
  onSaved: () => void;
  hasRegistrations: boolean;
  onDeleted: () => void;
}) {
  const { t } = useTranslation();
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  if (detail === null) return <p>{t("common.loading")}</p>;

  const isOwner = account !== null && account.id === detail.owner_id;

  return (
    <div className="setup-panel">
      <ChecklistSection detail={detail} />
      <IdentitySection detail={detail} slug={slug} onSaved={onSaved} />
      <VsSeriesSection detail={detail} slug={slug} onSaved={onSaved} />
      <CurrencySection detail={detail} slug={slug} onSaved={onSaved} />
      <OrganizersSection detail={detail} slug={slug} onSaved={onSaved} />
      <DisciplinesSection
        detail={detail}
        slug={slug}
        onSaved={onSaved}
        pricingWarning={hasRegistrations}
      />
      <ExtraItemsSection
        detail={detail}
        slug={slug}
        onSaved={onSaved}
        pricingWarning={hasRegistrations}
      />
      <DiscountsSection
        detail={detail}
        slug={slug}
        onSaved={onSaved}
        pricingWarning={hasRegistrations}
      />
      {isOwner && <TeamSection slug={slug} />}
      {isOwner && (
        <DangerZoneSection
          slug={slug}
          hasRegistrations={hasRegistrations}
          cancelled={detail.cancelled_at !== null}
          onDeleted={onDeleted}
          onCancelled={onSaved}
        />
      )}
    </div>
  );
}
