import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api } from "./api";
import useEscape from "./useEscape";
import { useWideViewport } from "./useWideViewport";

/** Asking for a reset link (spec `password-reset`). A mode of the sign-in
 *  screen rather than a screen of its own, as account creation is: sign-in
 *  renders in place over whatever URL raised it, and leaving that URL would
 *  lose the page the visitor is to return to.
 *
 *  An address with no account is told so, with account creation offered,
 *  rather than answered as if a link had gone out (owner decision
 *  2026-10-25): signup already reveals which addresses have accounts. */
export default function ForgotPassword({
  initialEmail,
  onBack,
  onCreateAccount,
}: {
  /** what the sign-in form's e-mail field held */
  initialEmail: string;
  onBack: () => void;
  onCreateAccount: () => void;
}) {
  // pinned to English for the reason sign-in is: there is no account yet
  // whose language would apply
  const { t } = useTranslation(undefined, { lng: "en" });
  const [email, setEmail] = useState(initialEmail);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [noAccount, setNoAccount] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const wide = useWideViewport();
  // as account creation does: Escape returns to sign-in, which then hears its own
  useEscape(onBack);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNoAccount(false);
    try {
      const sent = await api.requestPasswordReset(email);
      setSentTo(sent.email);
    } catch (err) {
      if (err instanceof ApiError && err.detail === "no_account") setNoAccount(true);
      else setError(t("forgot.failed"));
    } finally {
      setBusy(false);
    }
  }

  if (sentTo !== null) {
    // nothing changes until the link is followed: the statement takes the
    // form's place, and the way back is sign-in, where the old password works
    return (
      <section id="forgot-password-sent" className="login-card">
        <h1>{t("app.title")}</h1>
        <p className="login-subtitle">{t("forgot.subtitle")}</p>
        <p className="login-notice">{t("forgot.sent", { email: sentTo })}</p>
        <button type="button" className="link-button" onClick={onBack}>
          {t("signup.backToLogin")}
        </button>
      </section>
    );
  }

  return (
    <form id="forgot-password" className="login-card" onSubmit={submit}>
      <h1>{t("app.title")}</h1>
      <p className="login-subtitle">{t("forgot.subtitle")}</p>
      <label>
        {t("login.email")}
        <input
          name="email"
          type="email"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          inputMode="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus={wide}
        />
      </label>
      {noAccount && (
        <p className="login-notice forgot-no-account">
          {t("forgot.noAccount")}{" "}
          <button type="button" className="link-button" onClick={onCreateAccount}>
            {t("login.createAccount")}
          </button>
        </p>
      )}
      <p className="login-error" role="alert">
        {error}
      </p>
      <button type="submit" disabled={busy}>
        {busy ? t("forgot.submitting") : t("forgot.submit")}
      </button>
      <button type="button" className="link-button" onClick={onBack}>
        {t("signup.backToLogin")}
      </button>
    </form>
  );
}
