import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type PaymentMode, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { showsEur } from "../money";
import { useFieldValidation } from "../useFieldValidation";
import {
  apiErrors,
  checkMoney,
  checkNumeric,
  type FieldError as FieldErrorValue,
} from "../validation";
import { _int, type SaverRegistry, useSectionSaver } from "./shared";

const MODES: PaymentMode[] = ["immediate", "deposit", "reservation"];
const UNPAID_TREATMENTS = ["greyed", "hidden"] as const;

/** The date the seating deadline actually falls on, with the fallback that
 *  produced it — unset it resolves to the registration close, which itself
 *  resolves to the tournament date (setup.py::seating_deadline_for). Read
 *  from saved state: an unsaved edit on TIMELINE has not happened yet. */
function effectiveDeadline(detail: TournamentDetail): { date: string; via: "own" | "close" | "date" } {
  if (detail.seating_deadline) return { date: detail.seating_deadline, via: "own" };
  if (detail.registration_closes) return { date: detail.registration_closes, via: "close" };
  return { date: detail.date, via: "date" };
}

export function PaymentModeSection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<PaymentMode>(detail.payment_mode);
  const [depositLocal, setDepositLocal] = useState("");
  const [depositEur, setDepositEur] = useState("");
  const [windowDays, setWindowDays] = useState("");
  const [reminderDay, setReminderDay] = useState("");
  const [unpaidTreatment, setUnpaidTreatment] = useState("greyed");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();
  const fieldRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const eur = showsEur(detail);
  const currency = detail.local_currency;
  const deadline = effectiveDeadline(detail);
  const deadlineText = t(`setup.paymentMode.deadline.${deadline.via}`, {
    date: new Date(deadline.date).toLocaleDateString("cs"),
  });

  useEffect(() => {
    setMode(detail.payment_mode);
    setDepositLocal(detail.deposit_amount === null ? "" : String(detail.deposit_amount));
    setDepositEur(detail.deposit_amount_eur === null ? "" : String(detail.deposit_amount_eur));
    setWindowDays(String(detail.reservation_validity_days));
    setReminderDay(String(detail.reminder_day));
    setUnpaidTreatment(detail.unpaid_list_treatment);
    validation.clearAll();
    setError(null);
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  const checks: Record<string, () => FieldErrorValue | null> = {
    reservation_validity_days: () =>
      checkNumeric("reservation_validity_days", "TournamentUpdate.reservation_validity_days", windowDays),
    reminder_day: () => checkNumeric("reminder_day", "TournamentUpdate.reminder_day", reminderDay),
  };
  // the deposit is only a field — and only checkable — in deposit mode
  if (mode === "deposit") {
    checks.deposit_amount = () => checkMoney("deposit_amount", depositLocal, currency);
    if (eur) checks.deposit_amount_eur = () => checkMoney("deposit_amount_eur", depositEur, "EUR");
  }

  useSectionSaver(registry, "payments", "paymentMode", {
    pendingCount: dirty ? 1 : 0,
    // the deposit is a price, so changing it warns like any other price change
    touchesPrice: true,
    validate: () => validation.validateAll(Object.values(checks)),
    focusFirstInvalid: () => {
      for (const [key, check] of Object.entries(checks)) {
        if (check()) {
          fieldRefs.current[key]?.focus();
          return;
        }
      }
    },
    flush: async () => {
      try {
        // flush runs only after validate() passed, so every parse here succeeds
        const patch: Record<string, unknown> = {
          payment_mode: mode,
          reservation_validity_days: _int(windowDays),
          reminder_day: _int(reminderDay),
          unpaid_list_treatment: unpaidTreatment,
        };
        // outside deposit mode the amounts mean nothing and are left alone
        if (mode === "deposit") {
          patch.deposit_amount = _int(depositLocal);
          if (eur) patch.deposit_amount_eur = _int(depositEur);
        }
        await api.updateTournament(slug, patch);
        setDirty(false);
        return [{ change: "paymentMode", section: "paymentMode", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        setError(message);
        return [{ change: "paymentMode", section: "paymentMode", error: message }];
      }
    },
  });

  function depositField(key: "deposit_amount" | "deposit_amount_eur") {
    const isEur = key === "deposit_amount_eur";
    const value = isEur ? depositEur : depositLocal;
    const setValue = isEur ? setDepositEur : setDepositLocal;
    const check = checks[key];
    return (
      <label className="form-field" key={key}>
        <span>{t(`param.${key}`, { currency })}</span>
        <input
          ref={(el) => {
            fieldRefs.current[key] = el;
          }}
          type="text"
          inputMode="numeric"
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setDirty(true);
            if (check) validation.clearIfValid(key, check);
          }}
          onBlur={() => check && validation.touch(key, check)}
          {...invalidProps(key, validation.errors[key])}
        />
        <FieldError field={key} error={validation.errors[key]} />
      </label>
    );
  }

  function numberField(key: "reservation_validity_days" | "reminder_day", hint?: string) {
    const value = key === "reminder_day" ? reminderDay : windowDays;
    const setValue = key === "reminder_day" ? setReminderDay : setWindowDays;
    const check = checks[key];
    return (
      <label className="form-field">
        <span>
          {t(`param.${key}`)}
          {hint && <HelpHint text={t(hint)} />}
        </span>
        <input
          ref={(el) => {
            fieldRefs.current[key] = el;
          }}
          type="text"
          inputMode="numeric"
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setDirty(true);
            validation.clearIfValid(key, check);
          }}
          onBlur={() => validation.touch(key, check)}
          {...invalidProps(key, validation.errors[key])}
        />
        <FieldError field={key} error={validation.errors[key]} />
      </label>
    );
  }

  return (
    <section className="rail-card">
      <h2>{t("setup.paymentMode.title")}</h2>
      <div className="mode-options">
        {MODES.map((option) => (
          <div className="mode-option" key={option}>
            <label className="qualification-option">
              <input
                type="radio"
                name={`${slug}-payment-mode`}
                checked={mode === option}
                onChange={() => {
                  setMode(option);
                  setDirty(true);
                }}
              />
              {t(`param.payment_mode.${option}`)}
            </label>
            {/* the consequence, in the tournament's own values — changing the
                payment window or the seating deadline rewrites all three */}
            <p className="rail-hint">
              {t(`setup.paymentMode.effect.${option}`, {
                days: windowDays || detail.reservation_validity_days,
                deadline: deadlineText,
              })}
            </p>
            {option === "deposit" && mode === "deposit" && (
              <div className="form-fields">
                {depositField("deposit_amount")}
                {eur && depositField("deposit_amount_eur")}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="form-fields">
        {numberField("reservation_validity_days", "param.hint.reservation_validity_days")}
        {numberField("reminder_day")}
        <label className="form-field">
          <span>
            {t("param.unpaid_list_treatment")}
            <HelpHint text={t("param.hint.unpaid_list_treatment")} />
          </span>
          <select
            value={unpaidTreatment}
            onChange={(event) => {
              setUnpaidTreatment(event.target.value);
              setDirty(true);
            }}
          >
            {UNPAID_TREATMENTS.map((option) => (
              <option key={option} value={option}>
                {t(`param.unpaid_list_treatment.${option}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
