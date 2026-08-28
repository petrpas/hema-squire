import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type SetupSuggestions, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import SuggestionAnchor from "../SuggestionAnchor";
import SuggestionList from "../SuggestionList";
import { plainEntries } from "../suggestions";
import { useFieldValidation } from "../useFieldValidation";
import { useSuggestions } from "../useSuggestions";
import { apiErrors, checkString, type FieldError as FieldErrorValue } from "../validation";
import { type SaverRegistry, useSectionSaver } from "./shared";

export function BankAccountSection({
  detail,
  slug,
  registry,
  suggestions,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
  suggestions: SetupSuggestions;
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

  // The accounts this organizer has used before. A chosen one is validated
  // exactly as a typed one is — these are stored canonical IBANs, so a
  // suggestion that no longer passes says so rather than saving quietly.
  const accountSuggestions = useSuggestions(
    plainEntries(suggestions.bank_accounts),
    value,
    (entry) => {
      setValue(entry.value);
      setDirty(true);
      validation.clearIfValid("bank_account", () =>
        checkString("bank_account", "TournamentUpdate.bank_account", entry.value),
      );
    },
  );

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
          <SuggestionAnchor active>
            <input
              ref={fieldRef}
              type="text"
              value={value}
              onChange={(event) => {
                setValue(event.target.value);
                setDirty(true);
                validation.clearIfValid("bank_account", check);
              }}
              onBlur={() => {
                accountSuggestions.close();
                validation.touch("bank_account", check);
              }}
              {...accountSuggestions.inputProps}
              {...invalidProps("bank_account", validation.errors.bank_account)}
            />
            <SuggestionList
              suggestions={accountSuggestions}
              label={t("setup.suggestions.bankAccounts")}
            />
          </SuggestionAnchor>
          <FieldError field="bank_account" error={validation.errors.bank_account} />
        </label>
      </div>
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
