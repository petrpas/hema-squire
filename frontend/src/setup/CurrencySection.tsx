import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type CurrencyMode, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { formatForLocale, parseDecimal } from "../numeric";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkNumeric, type FieldError as FieldErrorValue } from "../validation";
import { CURRENCY_MODES, LOCAL_CURRENCY, type SaverRegistry, useSectionSaver } from "./shared";

// a rate outside this band is almost certainly the inverse or a typo; warn,
// never block — the organizer may know something we do not (design risk note)
const PLAUSIBLE_RATE = { min: 0.5, max: 1000 };

export function CurrencySection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
}) {
  const { t, i18n } = useTranslation();
  const [mode, setMode] = useState<CurrencyMode>("local");
  const [rate, setRate] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();
  const rateRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setMode(detail.currency_mode);
    setRate(detail.eur_rate ? formatForLocale(Number(detail.eur_rate), i18n.language) : "");
    validation.clearAll();
    setError(null);
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  function rateCheck(): FieldErrorValue | null {
    if (mode !== "local_eur") return null;
    return checkNumeric("eur_rate", "TournamentUpdate.eur_rate", rate, { integer: false });
  }

  const parsedRate = parseDecimal(rate);
  const implausible =
    mode === "local_eur" &&
    rate !== "" &&
    parsedRate.ok &&
    (parsedRate.value < PLAUSIBLE_RATE.min || parsedRate.value > PLAUSIBLE_RATE.max);

  useSectionSaver(registry, "payments", "currency", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: true,
    validate: () => validation.validateAll([rateCheck]),
    focusFirstInvalid: () => {
      if (rateCheck()) rateRef.current?.focus();
    },
    flush: async () => {
      try {
        const rateResult = parseDecimal(rate);
        await api.updateTournament(slug, {
          local_currency: mode === "eur" ? "EUR" : LOCAL_CURRENCY,
          eur_payments_enabled: mode !== "local",
          eur_rate: mode === "local_eur" && rateResult.ok ? String(rateResult.value) : null,
        });
        setDirty(false);
        return [{ change: "currency", section: "currency", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        setError(message);
        return [{ change: "currency", section: "currency", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.currency.title")}</h2>
      <div className="form-fields">
        <div className="qualification-control currency-mode-control">
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
              ref={rateRef}
              type="text"
              inputMode="decimal"
              value={rate}
              onChange={(event) => {
                setRate(event.target.value);
                setDirty(true);
                validation.clearIfValid("eur_rate", rateCheck);
              }}
              onBlur={() => validation.touch("eur_rate", rateCheck)}
              {...invalidProps("eur_rate", validation.errors.eur_rate)}
            />
            <FieldError field="eur_rate" error={validation.errors.eur_rate} />
          </label>
        )}
      </div>
      {implausible && <p className="login-error">{t("setup.currency.rateWarning")}</p>}
      {mode === "local_eur" && <p className="rail-hint">{t("setup.currency.rateNote")}</p>}
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
