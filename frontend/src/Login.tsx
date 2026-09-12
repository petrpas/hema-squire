import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api, setToken } from "./api";
import SignupForm from "./SignupForm";
import useEscape from "./useEscape";
import { useWideViewport } from "./useWideViewport";

export default function Login({
  onLogin,
  notice,
  onCancel,
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
}) {
  // Sign-in has no account context yet, so it always renders in English —
  // pinned per-hook rather than via i18n.changeLanguage, so it can't leak
  // into or be clobbered by the signup form's own language switching.
  const { t } = useTranslation(undefined, { lng: "en" });
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const wide = useWideViewport();
  // Only while sign-in itself is showing: the signup form hears Escape on its
  // own and returns here, and both listening would skip this screen entirely.
  useEscape(mode === "login" ? (onCancel ?? null) : null);

  if (mode === "signup") {
    return (
      <div className="login-page">
        <SignupForm onSignedUp={onLogin} onCancel={() => setMode("login")} />
      </div>
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { token } = await api.login(email, password);
      setToken(token);
      onLogin();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401 ? t("login.invalid") : t("login.failed"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form id="login-form" className="login-card" onSubmit={submit}>
        <h1>{t("app.title")}</h1>
        <p className="login-subtitle">{t("login.subtitle")}</p>
        {notice && <p className="login-notice">{t(notice)}</p>}
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
        {onCancel && (
          <button type="button" className="link-button login-back" onClick={onCancel}>
            {t("login.back")}
          </button>
        )}
      </form>
    </div>
  );
}
