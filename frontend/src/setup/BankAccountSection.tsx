import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkString, type FieldError as FieldErrorValue } from "../validation";
import { type SaverRegistry, useSectionSaver } from "./shared";

export function BankAccountSection({
  detail,
  slug,
  registry,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();
  const fieldRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setValue(detail.bank_account ?? "");
    validation.clearAll();
    setError(null);
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  function check(): FieldErrorValue | null {
    return checkString("bank_account", "TournamentUpdate.bank_account", value);
  }

  useSectionSaver(registry, "payments", "bankAccount", {
    pendingCount: dirty ? 1 : 0,
    touchesPrice: false,
    validate: () => validation.validateAll([check]),
    focusFirstInvalid: () => {
      if (check()) fieldRef.current?.focus();
    },
    flush: async () => {
      try {
        await api.updateTournament(slug, { bank_account: value === "" ? null : value });
        setDirty(false);
        return [{ change: "bankAccount", section: "bankAccount", error: null }];
      } catch (err) {
        const fieldErrors = apiErrors(err);
        validation.applyApiErrors(fieldErrors);
        const message =
          fieldErrors.length > 0
            ? fieldErrors.map((e) => t(`validation.${e.code}`, e.params)).join(" ")
            : t("setup.saveBar.genericError", { status: err instanceof ApiError ? err.status : "?" });
        setError(message);
        return [{ change: "bankAccount", section: "bankAccount", error: message }];
      }
    },
  });

  return (
    <section className="rail-card">
      <h2>{t("setup.bankAccount.title")}</h2>
      <div className="form-fields">
        <label className="form-field">
          <span>
            {t("setup.bankAccount.label")}
            <HelpHint text={t("setup.bankAccount.hint")} />
          </span>
          <input
            ref={fieldRef}
            type="text"
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              setDirty(true);
              validation.clearIfValid("bank_account", check);
            }}
            onBlur={() => validation.touch("bank_account", check)}
            {...invalidProps("bank_account", validation.errors.bank_account)}
          />
          <FieldError field="bank_account" error={validation.errors.bank_account} />
        </label>
      </div>
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
