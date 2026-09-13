import { useTranslation } from "react-i18next";

import FieldError, { invalidProps } from "../FieldError";
import type { FieldError as FieldErrorValue } from "../validation";

/** The address the seat carries from now on.
 *
 *  Required where Squire keeps the registrations and writes to the people
 *  holding them; optional where the organizer keeps them, since Squire sends
 *  such a tournament nothing at all. The address the seat already has is
 *  offered to keep — a club that entered three people under one address keeps
 *  that address — and where the seat has none there is nothing to keep and one
 *  must be typed (spec `fencer-substitution`, An automatic tournament requires
 *  an address for the seat).
 *
 *  The notice is standing text, read before confirming rather than after: it
 *  says where the word of this substitution is about to go. */
export default function SubstituteContactSection({
  automatic,
  current,
  keeping,
  onKeeping,
  email,
  onEmail,
  error,
  onBlur,
}: {
  automatic: boolean;
  /** The address the seat carries today, null where it carries none. */
  current: string | null;
  keeping: boolean;
  onKeeping: (keep: boolean) => void;
  email: string;
  onEmail: (value: string) => void;
  error: FieldErrorValue | undefined;
  onBlur: () => void;
}) {
  const { t } = useTranslation();
  const destination = keeping && current !== null ? current : email.trim();

  return (
    <>
      {/* Typing the substitute's own address is the ordinary case and so is the
          default. Keeping the one the seat came with is the exception a club
          needs, offered under the field it replaces rather than as a fork above
          it. */}
      <label className="form-field">
        <span>{t("substitute.email")}</span>
        <input
          value={keeping && current !== null ? current : email}
          disabled={keeping && current !== null}
          onChange={(event) => onEmail(event.target.value)}
          onBlur={onBlur}
          {...invalidProps("email", error)}
        />
        <FieldError field="email" error={error} />
      </label>

      {current !== null && (
        <label className="checkbox-line">
          <input
            type="checkbox"
            checked={keeping}
            onChange={(event) => onKeeping(event.target.checked)}
          />
          <span>{t("substitute.keepAddress", { address: current })}</span>
        </label>
      )}

      {automatic && (
        <p className="rail-hint">
          {destination === ""
            ? t("substitute.mailNoticeBlank")
            : t("substitute.mailNotice", { address: destination })}
        </p>
      )}
    </>
  );
}
