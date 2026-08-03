import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Phase } from "./Console";
import FieldError, { invalidProps } from "./FieldError";
import { type TournamentDetail, api } from "./api";
import { parseInteger } from "./numeric";
import { useFieldValidation } from "./useFieldValidation";
import {
  apiErrors,
  checkMoney,
  checkNumeric,
  checkPercent,
  checkString,
  checkUrl,
  type FieldError as FieldErrorValue,
} from "./validation";

type FieldType = "number" | "date" | "text";

interface ParamField {
  key: keyof TournamentDetail & string;
  type: FieldType;
}

// Which tournament parameters belong to which phase view.
const PHASE_PARAMS: Record<Phase, ParamField[]> = {
  setup: [],
  load: [
    { key: "early_bird_until", type: "date" },
    { key: "weapon_rental_fee", type: "number" },
    { key: "afterparty_fee", type: "number" },
  ],
  parsing: [],
  matching: [],
  dedup: [],
  payments: [
    { key: "reservation_validity_days", type: "number" },
    { key: "reminder_day", type: "number" },
    { key: "amount_tolerance_percent", type: "number" },
    { key: "refundable_until", type: "date" },
    { key: "bank_account", type: "text" },
    { key: "expiry_grace_hours", type: "number" },
    { key: "amendments_close", type: "date" },
  ],
  export: [{ key: "output_sheet_url", type: "text" }],
  teams: [],
};

// per-field checks against TournamentUpdate's bounds (design
// `add-field-validation`); money fields resolve their ceiling from the
// tournament's own currency (2.4a) rather than a static bound
function fieldCheck(
  key: string,
  raw: string,
  currency: TournamentDetail["local_currency"],
): FieldErrorValue | null {
  switch (key) {
    case "weapon_rental_fee":
    case "afterparty_fee":
      return checkMoney(key, raw, currency);
    case "reservation_validity_days":
      return checkNumeric(key, "TournamentUpdate.reservation_validity_days", raw);
    case "reminder_day":
      return checkNumeric(key, "TournamentUpdate.reminder_day", raw);
    case "amount_tolerance_percent":
      return checkPercent(key, raw);
    case "expiry_grace_hours":
      return checkNumeric(key, "TournamentUpdate.expiry_grace_hours", raw);
    case "bank_account":
      return checkString(key, "TournamentUpdate.bank_account", raw);
    case "output_sheet_url":
      return checkUrl(key, "TournamentUpdate.output_sheet_url", raw);
    default:
      return null;
  }
}

export default function ParamPanel({
  phase,
  detail,
  slug,
  onSaved,
}: {
  phase: Phase;
  detail: TournamentDetail | null;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const fields = PHASE_PARAMS[phase];
  const [values, setValues] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const validation = useFieldValidation();
  const currency = detail?.local_currency ?? "CZK";

  useEffect(() => {
    if (detail === null) return;
    const next: Record<string, string> = {};
    for (const field of fields) {
      const value = detail[field.key];
      next[field.key] = value === null || value === undefined ? "" : String(value);
    }
    setValues(next);
    validation.clearAll();
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail, phase]);

  if (fields.length === 0) {
    return (
      <section className="rail-card">
        <h2>{t("rail.generalRules")}</h2>
        <p className="rail-hint">{t("rail.rulesHint")}</p>
      </section>
    );
  }

  async function save() {
    const checks = fields.map((field) => () => fieldCheck(field.key, values[field.key] ?? "", currency));
    if (validation.validateAll(checks) > 0) return;
    setBusy(true);
    try {
      const patch: Record<string, unknown> = {};
      for (const field of fields) {
        const raw = values[field.key] ?? "";
        if (raw === "") {
          patch[field.key] = null;
        } else if (field.type === "number") {
          const result = parseInteger(raw);
          patch[field.key] = result.ok ? result.value : null;
        } else {
          patch[field.key] = raw;
        }
      }
      await api.updateTournament(slug, patch);
      setDirty(false);
      onSaved();
    } catch (err) {
      validation.applyApiErrors(apiErrors(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("rail.parameters")}</h2>
      <div className="param-fields">
        {fields.map((field) => {
          const check = () => fieldCheck(field.key, values[field.key] ?? "", currency);
          return (
          <label key={field.key} className="param-field">
            {/* fee labels name the tournament's currency rather than baking it in */}
            <span>
              {t(`param.${field.key}`, { currency: detail?.local_currency ?? "CZK" })}
            </span>
            <input
              type={field.type === "number" ? "text" : field.type}
              inputMode={field.type === "number" ? "numeric" : undefined}
              value={values[field.key] ?? ""}
              onChange={(event) => {
                setValues({ ...values, [field.key]: event.target.value });
                setDirty(true);
                validation.clearIfValid(field.key, check);
              }}
              onBlur={() => validation.touch(field.key, check)}
              {...invalidProps(field.key, validation.errors[field.key])}
            />
            <FieldError field={field.key} error={validation.errors[field.key]} />
          </label>
          );
        })}
      </div>
      <button className="secondary param-save" onClick={save} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}
