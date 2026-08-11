import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { type TournamentDetail, api } from "./api";
import FieldError, { invalidProps } from "./FieldError";
import HelpHint from "./HelpHint";
import { parseInteger } from "./numeric";
import { useFieldValidation } from "./useFieldValidation";
import { apiErrors, checkPercent } from "./validation";

/** The one genuine operation parameter of the payments phase: the amount
 *  tolerance matching compares against. It stays in the console rather than
 *  Setup because it is tuned against transactions that already exist, while
 *  reconciliation is running — not decided before publication (design
 *  regroup-setup-parameters Decision 8).
 *
 *  Its own card rather than part of the flagged queue, which
 *  `add-payments-console-ui` narrows to that queue alone. */
export default function TolerancePanel({
  detail,
  slug,
  onSaved,
}: {
  detail: TournamentDetail | null;
  slug: string;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const validation = useFieldValidation();
  const fieldRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (detail === null) return;
    setValue(String(detail.amount_tolerance_percent));
    validation.clearAll();
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  if (detail === null) return null;

  const check = () => checkPercent("amount_tolerance_percent", value);

  async function save() {
    if (validation.validateAll([check]) > 0) {
      fieldRef.current?.focus();
      return;
    }
    setBusy(true);
    try {
      const parsed = parseInteger(value);
      await api.updateTournament(slug, {
        amount_tolerance_percent: parsed.ok ? parsed.value : null,
      });
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
      <h2>{t("payments.tolerance.title")}</h2>
      <div className="param-fields">
        <label className="param-field">
          <span>
            {t("param.amount_tolerance_percent")}
            <HelpHint text={t("payments.tolerance.hint")} />
          </span>
          <input
            ref={fieldRef}
            type="text"
            inputMode="numeric"
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              setDirty(true);
              validation.clearIfValid("amount_tolerance_percent", check);
            }}
            onBlur={() => validation.touch("amount_tolerance_percent", check)}
            {...invalidProps("amount_tolerance_percent", validation.errors.amount_tolerance_percent)}
          />
          <FieldError
            field="amount_tolerance_percent"
            error={validation.errors.amount_tolerance_percent}
          />
        </label>
      </div>
      <button
        className="secondary param-save"
        onClick={() => void save()}
        disabled={!dirty || busy}
      >
        {t("rail.save")}
      </button>
    </section>
  );
}
