import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api, type GuestIdentity, setToken } from "./api";
import ForgotPassword from "./ForgotPassword";
import HelpHint from "./HelpHint";
import SignupForm from "./SignupForm";
import useEscape from "./useEscape";
import { useWideViewport } from "./useWideViewport";

export type LoginMode = "login" | "signup" | "guest" | "forgot";

export default function Login({
  onLogin,
  notice,
  onCancel,
  onGuest,
  guest,
  returnTo,
  initialMode = "login",
}: {
  onLogin: () => void;
  /** Locale key for one line saying why sign-in was reached — what a public
   *  screen states when an action needed an account (spec `public-browsing`).
   *  A key rather than a string, because this screen renders in English
   *  whatever the visitor was reading a moment ago, and the caller's `t` is
   *  not pinned to it. */
  notice?: string;
  /** The way back out, for the caller that put this screen in front of
   *  something. Sign-in renders over the URL the visitor was already on, so
   *  the browser's own Back leads away from that page rather than off this
   *  screen; without this there is no way to decline signing in and stay
   *  where they were (spec `public-browsing`). */
  onCancel?: () => void;
  /** Offered only where Register raised this screen: registering without
   *  signing up opens the guest form, and its identity is handed back here
   *  rather than created anywhere (spec `guest-registration`). A gated URL
   *  passes none, since what it guards needs an account. */
  onGuest?: (identity: GuestIdentity) => void;
  /** the identity being changed, reopening the guest form filled in */
  guest?: GuestIdentity;
  /** where a signup's verification link lands: the screen it was started on */
  returnTo?: string;
  initialMode?: LoginMode;
}) {
  // Sign-in has no account context yet, so it always renders in English —
  // pinned per-hook rather than via i18n.changeLanguage, so it can't leak
  // into or be clobbered by the signup form's own language switching.
  const { t } = useTranslation(undefined, { lng: "en" });
  const [mode, setMode] = useState<LoginMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  // a signup on this address waits for its link: stated, not an error, with
  // the link offered again — `sent` once it has been
  const [pending, setPending] = useState<"unverified" | "sent" | null>(null);
  const [busy, setBusy] = useState(false);
  const wide = useWideViewport();
  // Only while sign-in itself is showing: the signup form hears Escape on its
  // own and returns here, and both listening would skip this screen entirely.
  useEscape(mode === "login" ? (onCancel ?? null) : null);

  if (mode === "forgot") {
    return (
      <div className="login-page">
        <ForgotPassword
          initialEmail={email}
          onBack={() => setMode("login")}
          onCreateAccount={() => setMode("signup")}
        />
      </div>
    );
  }

  if (mode === "signup" || (mode === "guest" && onGuest)) {
    return (
      <div className="login-page">
        <SignupForm
          variant={
            mode === "guest" && onGuest
              ? { kind: "guest", onGuest, initial: guest }
              : { kind: "account", returnTo }
          }
          onCancel={() => setMode("login")}
        />
      </div>
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setPending(null);
    try {
      const { token } = await api.login(email, password);
      setToken(token);
      onLogin();
    } catch (err) {
      if (err instanceof ApiError && err.detail === "email_not_verified") {
        setPending("unverified");
        return;
      }
      setError(
        err instanceof ApiError && err.status === 401 ? t("login.invalid") : t("login.failed"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setBusy(true);
    try {
      await api.resendVerification(email, password);
      setPending("sent");
    } catch {
      setError(t("login.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form id="login-form" className="login-card" onSubmit={submit}>
        <h1>{t("app.title")}</h1>
        {/* why sign-in was reached sits behind the marker rather than as a
            line of its own, so the form reads as fields first */}
        <p className="login-subtitle">
          {t("login.subtitle")}
          {notice && (
            <>
              {" "}
              <HelpHint text={t(notice)} align="center" />
            </>
          )}
        </p>
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
        <label>
          {t("login.password")}
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            enterKeyHint="go"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {/* beside the field it is about; carries the typed address along, so
            it is not asked for twice */}
        <button
          type="button"
          className="link-button login-forgot"
          onClick={() => setMode("forgot")}
        >
          {t("forgot.entry")}
        </button>
        {pending !== null && (
          <p className="login-notice login-pending">
            {pending === "sent" ? t("login.verificationResent") : t("login.notVerified")}{" "}
            {pending === "unverified" && (
              <button
                type="button"
                className="link-button login-resend"
                disabled={busy}
                onClick={() => void resend()}
              >
                {t("login.resendVerification")}
              </button>
            )}
          </p>
        )}
        <p className="login-error" role="alert">
          {error}
        </p>
        <button type="submit" disabled={busy}>
          {busy ? t("login.submitting") : t("login.submit")}
        </button>
        <button
          type="button"
          className="link-button login-create"
          onClick={() => setMode("signup")}
        >
          {t("login.createAccount")}
        </button>
        {onGuest && (
          <button
            type="button"
            className="link-button login-guest"
            onClick={() => setMode("guest")}
          >
            {t("guest.entry")}
          </button>
        )}
        {onCancel && (
          <button type="button" className="link-button login-back" onClick={onCancel}>
            {t("login.back")}
          </button>
        )}
      </form>
    </div>
  );
}
