import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, setToken } from "../api";
import FieldError, { invalidProps } from "../FieldError";
import Modal from "../Modal";
import { credentialChanged } from "../session";
import { useFieldValidation } from "../useFieldValidation";
import { apiErrors, checkPassword } from "../validation";

/** Changing the password from the profile (spec `profile-page`, Password
 *  change). A dialog behind a quiet link rather than a section of the page:
 *  hardly anyone uses it, and its fields rendered on the page were filled by
 *  a password manager on every visit, which read as the page displaying the
 *  password.
 *
 *  The current password is the proof; every other session ends, and the token
 *  the change returns replaces this browser's, so this one stays signed in. A
 *  wrong current password is refused in place: it is a 403, never a 401, so
 *  the session is not lost over a typo. */
export default function PasswordDialog({
  email,
  onClose,
  onChanged,
}: {
  email: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const validation = useFieldValidation();

  function newPasswordCheck() {
    return checkPassword("new_password", "PasswordChangeIn.new_password", next);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (validation.validateAll([newPasswordCheck]) > 0) return;
    setBusy(true);
    setError(null);
    try {
      const { token } = await api.changePassword(current, next);
      setToken(token);
      credentialChanged();
      onChanged();
    } catch (err) {
      const fieldErrors = apiErrors(err);
      if (err instanceof ApiError && err.detail === "wrong_password") {
        setError(t("profile.password.wrong"));
      } else if (fieldErrors.length > 0) {
        validation.applyApiErrors(fieldErrors);
      } else {
        setError(t("profile.password.failed"));
      }
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      {/* its own form with its own id, carrying the account's address, so a
          password manager updates that credential */}
      <form id="change-password" className="modal" onSubmit={submit}>
        <h2>{t("profile.password.title")}</h2>
        <input name="email" type="email" autoComplete="username" value={email} readOnly hidden />
        <div className="form-fields">
          <label className="form-field">
            <span>{t("profile.password.current")}</span>
            <input
              name="current-password"
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              required
              autoFocus
            />
          </label>
          <label className="form-field">
            <span>{t("profile.password.new")}</span>
            <input
              name="new-password"
              type="password"
              autoComplete="new-password"
              value={next}
              onChange={(event) => {
                setNext(event.target.value);
                validation.clearIfValid("new_password", newPasswordCheck);
              }}
              onBlur={() => validation.touch("new_password", newPasswordCheck)}
              required
              minLength={8}
              {...invalidProps("new_password", validation.errors.new_password)}
            />
            <FieldError field="new_password" error={validation.errors.new_password} />
          </label>
        </div>
        {error && <p className="login-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>
            {t("common.cancel")}
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? t("profile.password.submitting") : t("profile.password.submit")}
          </button>
        </div>
      </form>
    </Modal>
  );
}
