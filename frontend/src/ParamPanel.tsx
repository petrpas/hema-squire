import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Phase } from "./Console";
import { type TournamentDetail, api } from "./api";

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
  ],
  export: [{ key: "output_sheet_url", type: "text" }],
};

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

  useEffect(() => {
    if (detail === null) return;
    const next: Record<string, string> = {};
    for (const field of fields) {
      const value = detail[field.key];
      next[field.key] = value === null || value === undefined ? "" : String(value);
    }
    setValues(next);
    setDirty(false);
  }, [detail, phase]); // eslint-disable-line react-hooks/exhaustive-deps

  if (fields.length === 0) {
    return (
      <section className="rail-card">
        <h2>{t("rail.generalRules")}</h2>
        <p className="rail-hint">{t("rail.rulesHint")}</p>
      </section>
    );
  }

  async function save() {
    setBusy(true);
    try {
      const patch: Record<string, unknown> = {};
      for (const field of fields) {
        const raw = values[field.key] ?? "";
        if (raw === "") {
          patch[field.key] = null;
        } else {
          patch[field.key] = field.type === "number" ? Number(raw) : raw;
        }
      }
      await api.updateTournament(slug, patch);
      setDirty(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("rail.parameters")}</h2>
      <div className="param-fields">
        {fields.map((field) => (
          <label key={field.key} className="param-field">
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
        ))}
      </div>
      <button className="secondary param-save" onClick={save} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}
