import type { MutableRefObject } from "react";
import { useTranslation } from "react-i18next";

import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import SuggestionAnchor from "../SuggestionAnchor";
import SuggestionList from "../SuggestionList";
import { plainEntries } from "../suggestions";
import { useSuggestions } from "../useSuggestions";
import { checkString, type FieldError as FieldErrorValue } from "../validation";

export function holderCheck(value: string): FieldErrorValue | null {
  return checkString("bank_account_holder", "TournamentUpdate.bank_account_holder", value);
}

/** The account's holder, directly below the account and saved with it. A EUR
 *  payment code is an EPC code, which must name its beneficiary (spec
 *  tournament-admin, The account holder is recorded beside the bank account). */
export default function BankAccountHolderField({
  value,
  error,
  recalled,
  inputRef,
  onChange,
  onBlur,
}: {
  value: string;
  error: FieldErrorValue | undefined;
  recalled: string[];
  inputRef: MutableRefObject<HTMLInputElement | null>;
  onChange: (value: string) => void;
  onBlur: () => void;
}) {
  const { t } = useTranslation();
  const holderSuggestions = useSuggestions(plainEntries(recalled), value, (entry) =>
    onChange(entry.value),
  );

  return (
    <div className="form-field">
      <label htmlFor="bank-account-holder">
        {t("setup.bankAccount.holderLabel")}
        <HelpHint text={t("setup.bankAccount.holderHint")} />
      </label>
      <SuggestionAnchor active>
        <input
          id="bank-account-holder"
          ref={inputRef}
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onBlur={() => {
            holderSuggestions.close();
            onBlur();
          }}
          {...holderSuggestions.inputProps}
          {...invalidProps("bank_account_holder", error)}
        />
        <SuggestionList
          suggestions={holderSuggestions}
          label={t("setup.suggestions.bankAccountHolders")}
        />
      </SuggestionAnchor>
      <FieldError field="bank_account_holder" error={error} />
    </div>
  );
}
