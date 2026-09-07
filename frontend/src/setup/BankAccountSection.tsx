import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { isFioAccount } from "../accounts";
import { ApiError, type SetupSuggestions, type TournamentDetail, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import SuggestionAnchor from "../SuggestionAnchor";
import SuggestionList from "../SuggestionList";
import { plainEntries } from "../suggestions";
import { useFieldValidation } from "../useFieldValidation";
import { useSuggestions } from "../useSuggestions";
import { apiErrors, checkString, type FieldError as FieldErrorValue } from "../validation";
import FeedTokenDialog from "./FeedTokenDialog";
import { type SaverRegistry, useSectionSaver } from "./shared";

export function BankAccountSection({
  detail,
  slug,
  registry,
  suggestions,
  onSaved,
}: {
  detail: TournamentDetail;
  slug: string;
  registry: SaverRegistry;
  suggestions: SetupSuggestions;
  /** Refetches the tournament. The feed token is written by its own dialog
   *  rather than by this section's save, and the deposit mode and the intake
   *  poll action both read `fio_token_configured`, so they have to be told. */
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();
  const fieldRef = useRef<HTMLInputElement | null>(null);
  const [tokenOpen, setTokenOpen] = useState(false);
  // set when a token was stored without the bank answering. Not an error — the
  // token is on file — so it is stated once, beside the action, and cleared
  // when the dialog is opened again
  const [unchecked, setUnchecked] = useState(false);
  // the account being typed, not the saved one: an account that has just become
  // a Fio one enables the action at once. The action shares the field's line,
  // so nothing moves when it does (spec tournament-admin)
  const fio = isFioAccount(value);

  useEffect(() => {
    setValue(detail.bank_account ?? "");
    validation.clearAll();
    setError(null);
    setDirty(false);
    setUnchecked(false);
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
        {/* a div rather than a label: the token action is interactive content,
            which a label may not wrap — it would forward its own clicks to the
            account field. The label is explicit instead */}
        <div className="form-field">
          <div className="field-label-row">
            <label htmlFor="bank-account">
              {t("setup.bankAccount.label")}
              <HelpHint text={t("setup.bankAccount.hint")} />
            </label>
            {/* on the label's own line, so becoming available moves nothing */}
            {fio ? (
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setUnchecked(false);
                  setTokenOpen(true);
                }}
              >
                {detail.fio_token_configured
                  ? t("setup.feedToken.reset")
                  : t("setup.feedToken.set")}
              </button>
            ) : (
              <span className="rail-hint">{t("setup.feedToken.fioOnly")}</span>
            )}
          </div>
          <SuggestionAnchor active>
            <input
              id="bank-account"
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
        </div>
        {fio && (
          <p className="rail-hint">
            {detail.fio_token_configured
              ? t("setup.feedToken.state.recorded")
              : t("setup.feedToken.state.none")}
          </p>
        )}
        {unchecked && <p className="rail-hint">{t("setup.feedToken.unchecked")}</p>}
      </div>
      {error && <p className="login-error">{error}</p>}
      {tokenOpen && (
        <FeedTokenDialog
          slug={slug}
          configured={detail.fio_token_configured}
          onDone={(state) => {
            setUnchecked(state.configured && !state.verified);
            onSaved();
          }}
          onClose={() => setTokenOpen(false)}
        />
      )}
    </section>
  );
}
