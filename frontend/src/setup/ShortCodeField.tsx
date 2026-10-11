import { useTranslation } from "react-i18next";

import FieldError, { invalidProps } from "../FieldError";
import HelpHint from "../HelpHint";
import { monogram } from "../monogram";
import { checkString, type FieldError as FieldErrorValue } from "../validation";

/** What the field shows: the stored or typed code, or else the monogram of the
 *  name as it now stands, so an untouched field follows a rename (spec
 *  tournament-admin, Tournament short code). `typed` is null while the field
 *  follows the name. */
export function shortCodeShown(typed: string | null, displayName: string): string {
  return typed ?? monogram(displayName);
}

/** Empty is allowed: it clears the code and the card derives it again. */
export function shortCodeCheck(value: string): FieldErrorValue | null {
  return value.trim() === ""
    ? null
    : checkString("short_code", "TournamentUpdate.short_code", value);
}

/** What the save sends: null where the code would only restate the monogram,
 *  so nothing is stored and a later rename keeps updating it. */
export function shortCodePatch(typed: string | null, displayName: string): string | null {
  const value = (typed ?? "").trim();
  return value === "" || value === monogram(displayName) ? null : value;
}

export default function ShortCodeField({
  value,
  error,
  inputRef,
  onChange,
  onBlur,
}: {
  value: string;
  error: FieldErrorValue | undefined;
  inputRef: (el: HTMLInputElement | null) => void;
  onChange: (value: string) => void;
  onBlur: (value: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <label className="form-field">
      <span>
        {t("setup.identity.shortCode")}
        <HelpHint text={t("setup.identity.shortCodeHint")} />
      </span>
      <input
        ref={inputRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={(event) => onBlur(event.target.value)}
        {...invalidProps("short_code", error)}
      />
      <FieldError field="short_code" error={error} />
    </label>
  );
}
