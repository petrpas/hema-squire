import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Account, ApiError, api } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import i18n from "../i18n";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkString } from "../validation";
import PasswordDialog from "./PasswordDialog";

const IMPLEMENTED_LANGUAGES = Object.keys(i18n.options.resources ?? {});

export default function AccountSection({
  account,
  onUpdated,
}: {
  account: Account;
  onUpdated: (account: Account) => void;
}) {
  const { t } = useTranslation();
  const [email, setEmail] = useState(account.email);
  const [displayName, setDisplayName] = useState(account.display_name);
  const [language, setLanguage] = useState(account.language);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // a quiet link rather than a section of its own: hardly anyone changes it
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordChanged, setPasswordChanged] = useState(false);
  const validation = useFieldValidation();

  useEffect(() => {
    setEmail(account.email);
    setDisplayName(account.display_name);
    setLanguage(account.language);
    validation.clearAll();
    setDirty(false);
  }, [account, validation.clearAll]);

  function displayNameCheck() {
    return checkString("display_name", "AccountUpdate.display_name", displayName, {
      required: true,
    });
  }

  async function save() {
    if (validation.validateAll([displayNameCheck]) > 0) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateAccount({ email, display_name: displayName, language });
      onUpdated(updated);
      void i18n.changeLanguage(updated.language);
      setDirty(false);
    } catch (err) {
      const fieldErrors = apiErrors(err);
      if (fieldErrors.length > 0) {
        validation.applyApiErrors(fieldErrors);
      } else {
        setError(
          err instanceof ApiError && err.status === 409
            ? t("profile.account.emailTaken")
            : t("profile.account.saveFailed"),
        );
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      {/* beside the heading, in the quiet place a rarely used action takes */}
      <div className="rail-card-heading">
        <h2>{t("profile.account.title")}</h2>
        <button
          type="button"
          className="link-button change-password"
          onClick={() => {
            setPasswordChanged(false);
            setChangingPassword(true);
          }}
        >
          {t("profile.password.open")}
        </button>
      </div>
      <div className="param-fields">
        <label className="param-field">
          <span>{t("profile.account.email")}</span>
          <input
            type="email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setDirty(true);
            }}
          />
        </label>
        <label className="param-field">
          <span>{t("profile.account.displayName")}</span>
          <input
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value);
              setDirty(true);
              validation.clearIfValid("display_name", displayNameCheck);
            }}
            onBlur={() => validation.touch("display_name", displayNameCheck)}
            {...invalidProps("display_name", validation.errors.display_name)}
          />
          <FieldError field="display_name" error={validation.errors.display_name} />
        </label>
        <label className="param-field">
          <span>{t("profile.account.language")}</span>
          <select
            value={language}
            onChange={(event) => {
              setLanguage(event.target.value);
              setDirty(true);
            }}
          >
            {IMPLEMENTED_LANGUAGES.map((code) => (
              <option key={code} value={code}>
                {t(`languages.${code}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="login-error">{error}</p>}
      <button
        type="button"
        className="secondary param-save"
        onClick={() => void save()}
        disabled={!dirty || busy}
      >
        {t("rail.save")}
      </button>
      {passwordChanged && (
        <p className="rail-hint password-changed">{t("profile.password.changed")}</p>
      )}
      {changingPassword && (
        <PasswordDialog
          email={account.email}
          onClose={() => setChangingPassword(false)}
          onChanged={() => {
            setChangingPassword(false);
            setPasswordChanged(true);
          }}
        />
      )}
    </section>
  );
}
