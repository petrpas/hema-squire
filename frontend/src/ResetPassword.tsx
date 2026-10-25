import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useOutletContext } from "react-router-dom";
import { ApiError, api, setToken } from "./api";
import type { FencerOutletContext } from "./FencerHome";
import FieldError, { invalidProps } from "./FieldError";
import { home } from "./routes";
import { credentialChanged } from "./session";
import { useFieldValidation } from "./useFieldValidation";
import { useWideViewport } from "./useWideViewport";
import { apiErrors, checkPassword } from "./validation";

/** Following a reset link: a new password, then signed in on this browser
 *  and landed on the list (spec `password-reset`, The reset link sets a new
 *  password once).
 *
 *  The key is inspected before the form is offered, consuming nothing, so a
 *  link that no longer works is stated before anyone types a password; the
 *  address it answers fills the identifier a password manager files the new
 *  password under (design D6). A dead link is stated, not reported as an
 *  error, and offers a new request. */
export default function ResetPassword() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { onSignIn } = useOutletContext<FencerOutletContext>();
  const key = location.hash.slice(1);
  // `undefined` while the key is being inspected, `null` for a dead link
  const [email, setEmail] = useState<string | null | undefined>(undefined);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const validation = useFieldValidation();
  const wide = useWideViewport();

  useEffect(() => {
    if (key === "") {
      setEmail(null);
      return;
    }
    // inspecting consumes nothing, so development's double-mounted effect
    // needs no guard here, unlike VerifyScreen's
    api.inspectPasswordReset(key).then(
      (it) => setEmail(it.email),
      () => setEmail(null),
    );
  }, [key]);

  function passwordCheck() {
    return checkPassword("password", "PasswordResetConfirmIn.password", password);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (validation.validateAll([passwordCheck]) > 0) return;
    setBusy(true);
    setError(null);
    try {
      const { token } = await api.confirmPasswordReset(key, password);
      setToken(token);
      credentialChanged();
      navigate(home(), { replace: true });
    } catch (err) {
      const fieldErrors = apiErrors(err);
      if (err instanceof ApiError && err.status === 410) setEmail(null);
      else if (fieldErrors.length > 0) validation.applyApiErrors(fieldErrors);
      else setError(t("reset.failed"));
    } finally {
      setBusy(false);
    }
  }

  if (email === undefined) return <p>{t("common.loading")}</p>;

  if (email === null) {
    return (
      <div className="workspace">
        <section className="rail-card dashed reset-invalid">
          <p className="rail-hint">{t("reset.invalid")}</p>
          <div className="action-pair">
            <button
              type="button"
              className="secondary"
              onClick={() => onSignIn(undefined, undefined, "forgot")}
            >
              {t("reset.requestNew")}
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="login-page">
      <form id="reset-password" className="login-card" onSubmit={submit}>
        <h1>{t("app.title")}</h1>
        <p className="login-subtitle">{t("reset.subtitle")}</p>
        {/* the account the new password belongs to, inside the form, so a
            password manager updates that credential rather than filing a
            new one under no name */}
        <label>
          {t("login.email")}
          <input name="email" type="email" autoComplete="username" value={email} readOnly />
        </label>
        <label>
          {t("reset.newPassword")}
          <input
            name="new-password"
            type="password"
            autoComplete="new-password"
            enterKeyHint="go"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              validation.clearIfValid("password", passwordCheck);
            }}
            onBlur={() => validation.touch("password", passwordCheck)}
            required
            minLength={8}
            autoFocus={wide}
            {...invalidProps("password", validation.errors.password)}
          />
          <FieldError field="password" error={validation.errors.password} />
        </label>
        <p className="login-error" role="alert">
          {error}
        </p>
        <button type="submit" disabled={busy}>
          {busy ? t("reset.submitting") : t("reset.submit")}
        </button>
      </form>
    </div>
  );
}
