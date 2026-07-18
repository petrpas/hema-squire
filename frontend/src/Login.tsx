import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, setToken } from "./api";

export default function Login({ onLogin }: { onLogin: () => void }) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
        err instanceof ApiError && err.status === 401
          ? t("login.invalid")
          : t("login.failed"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <h1>{t("app.title")}</h1>
        <p className="login-subtitle">{t("login.subtitle")}</p>
        <label>
          {t("login.email")}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          {t("login.password")}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="login-error">{error}</p>}
        <button type="submit" disabled={busy}>
          {t("login.submit")}
        </button>
      </form>
    </div>
  );
}
