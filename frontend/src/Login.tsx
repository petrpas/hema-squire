import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import FieldError, { invalidProps } from "./FieldError";
import HRSearchPicker from "./HRSearch";
import HRSearchStep from "./HRSearchStep";
import { ApiError, type HRProfile, api, setToken } from "./api";
import i18n from "./i18n";
import { useFieldValidation } from "./useFieldValidation";
import { useWideViewport } from "./useWideViewport";
import { apiErrors, checkPassword, checkString } from "./validation";

const IMPLEMENTED_LANGUAGES = Object.keys(i18n.options.resources ?? {});

function SignupForm({ onSignedUp, onCancel }: { onSignedUp: () => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en");

  // The app's global i18n instance defaults to Czech; sync it to the
  // signup window's own English default the moment the window opens, so
  // the form actually renders in English rather than just pre-selecting
  // it in the dropdown.
  useEffect(() => {
    void i18n.changeLanguage("en");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [hrProfile, setHrProfile] = useState<HRProfile | null>(null);
  // a candidate the fencer picked but has not yet confirmed as their own
  const [pendingHr, setPendingHr] = useState<HRProfile | null>(null);
  const [showHrSearch, setShowHrSearch] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const validation = useFieldValidation();
  const wide = useWideViewport();

  function passwordCheck() {
    return checkPassword("password", "SignupIn.password", password);
  }
  function nameCheck() {
    return checkString("name", "SignupIn.display_name", name, { required: true });
  }

  function changeLanguage(value: string) {
    setLanguage(value);
    void i18n.changeLanguage(value);
  }

  function confirmHr(profile: HRProfile) {
    setHrProfile(profile);
    setName(profile.name);
    setPendingHr(null);
    setShowHrSearch(false);
  }

  function clearHr() {
    setHrProfile(null);
    setName("");
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (validation.validateAll([passwordCheck, nameCheck]) > 0) return;
    setBusy(true);
    setError(null);
    try {
      const { token } = await api.signup({
        email,
        password,
        display_name: name,
        hr_id: hrProfile ? hrProfile.hr_id : undefined,
        language,
      });
      setToken(token);
      void i18n.changeLanguage(language);
      onSignedUp();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = typeof err.detail === "string" ? err.detail : null;
        const fieldErrors = apiErrors(err);
        if (detail === "email_already_registered") setError(t("signup.errors.emailTaken"));
        else if (detail === "hr_profile_not_found") setError(t("signup.errors.hrNotFound"));
        else if (fieldErrors.length > 0) validation.applyApiErrors(fieldErrors);
        else if (err.status === 422) setError(t("signup.errors.invalid"));
        else setError(t("signup.errors.failed"));
      } else {
        setError(t("signup.errors.failed"));
      }
    } finally {
      setBusy(false);
    }
  }

  // The HR picker, configured the way signup needs it. Built once here so the
  // inline placement and the full-screen step below cannot drift apart.
  const picker = (
    <HRSearchPicker
      onConfirm={setPendingHr}
      onCancel={() => setShowHrSearch(false)}
      lockedQuery={name}
      requireNationality
    />
  );

  return (
    /* Its own <form>, with an id of its own: sign-in renders a different form
       at this position, and while React already replaces the DOM node across
       that switch (a component type against a host type never reconciles),
       the stable id gives a password manager a durable identity for each and
       stops one form's fields being attributed to the other. */
    <form id="signup-form" className="login-card" onSubmit={submit}>
      <h1>{t("app.title")}</h1>
      <p className="login-subtitle">{t("signup.subtitle")}</p>
      <div className="tiskopis-row">
        <span className="tiskopis-number">{t("signup.formTitle")}</span>
        <span className="tiskopis-number">{t("signup.formNumber")}</span>
      </div>
      <label>
        {t("login.email")}
        <input
          name="email"
          type="email"
          /* "username" on the signup form too: it is the signal that tells a
             password manager this is the account identifier, and without it
             no manager offers to save the new pair. */
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
          autoComplete="new-password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            validation.clearIfValid("password", passwordCheck);
          }}
          onBlur={() => validation.touch("password", passwordCheck)}
          required
          minLength={8}
          {...invalidProps("password", validation.errors.password)}
        />
        <FieldError field="password" error={validation.errors.password} />
      </label>
      <label>
        {t("signup.name")}
        <input
          name="display_name"
          autoComplete="name"
          autoCapitalize="words"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            validation.clearIfValid("name", nameCheck);
          }}
          onBlur={() => validation.touch("name", nameCheck)}
          required
          readOnly={hrProfile !== null}
          {...invalidProps("name", validation.errors.name)}
        />
        <FieldError field="name" error={validation.errors.name} />
      </label>
      <label>
        {t("signup.language")}
        <select value={language} onChange={(e) => changeLanguage(e.target.value)}>
          {IMPLEMENTED_LANGUAGES.map((code) => (
            <option key={code} value={code}>
              {t(`languages.${code}`)}
            </option>
          ))}
        </select>
      </label>

      {hrProfile ? (
        <p className="signup-hr-confirmed">
          {t("signup.hr.confirmed", { name: hrProfile.name, hrId: hrProfile.hr_id })}{" "}
          <button type="button" className="link-button" onClick={clearHr}>
            {t("signup.hr.clear")}
          </button>
          {hrProfile.claimed && (
            <span className="hr-claimed-notice">{t("profile.hr.claimedNotice")}</span>
          )}
        </p>
      ) : pendingHr ? (
        <section className="rail-card hr-confirm">
          <h2>{t("signup.hr.confirmTitle")}</h2>
          <p className="hr-confirm-name">{pendingHr.name}</p>
          <p className="muted">
            {pendingHr.club ?? "—"} · {pendingHr.nationality ?? "—"} · #{pendingHr.hr_id}
          </p>
          <a
            className="hr-confirm-link"
            href={`https://hemaratings.com/fighters/details/${pendingHr.hr_id}/`}
            target="_blank"
            rel="noreferrer"
          >
            {t("signup.hr.viewProfile")}
          </a>
          {pendingHr.claimed && (
            <p className="hr-claimed-notice">{t("profile.hr.claimedNotice")}</p>
          )}
          <p className="rail-hint">{t("signup.hr.confirmPrompt")}</p>
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={() => setPendingHr(null)}>
              {t("common.cancel")}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => confirmHr(pendingHr)}
            >
              {t("signup.hr.confirmButton")}
            </button>
          </div>
        </section>
      ) : showHrSearch ? (
        wide ? (
          <section className="rail-card">
            <h2>{t("profile.hr.title")}</h2>
            {picker}
          </section>
        ) : (
          /* Rendered here, inside the form's own component, so opening the
             step unmounts nothing: e-mail, password, name and language are
             all still held above and survive the round trip. A route of its
             own would discard them. */
          <HRSearchStep
            title={t("profile.hr.title")}
            /* The picker is locked to the form's name field and shows no
               query input, so the step has to say what it is searching for. */
            subtitle={t("signup.hr.searchingFor", { name })}
            backLabel={t("signup.hr.stepBack")}
            onBack={() => setShowHrSearch(false)}
          >
            {picker}
          </HRSearchStep>
        )
      ) : (
        <button type="button" className="secondary" onClick={() => setShowHrSearch(true)}>
          {t("signup.hr.find")}
        </button>
      )}

      {/* The slot is always in the layout, so a message arriving cannot push
          the submit button out from under a thumb already on its way down. */}
      <p className="login-error" role="alert">
        {error}
      </p>
      <button type="submit" disabled={busy}>
        {busy ? t("signup.submitting") : t("signup.submit")}
      </button>
      <button type="button" className="link-button" onClick={onCancel}>
        {t("signup.backToLogin")}
      </button>
    </form>
  );
}

export default function Login({ onLogin }: { onLogin: () => void }) {
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
      <form id="login-form" className="login-card" onSubmit={submit}>
        <h1>{t("app.title")}</h1>
        <p className="login-subtitle">{t("login.subtitle")}</p>
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
        <button type="button" className="link-button" onClick={() => setMode("signup")}>
          {t("login.createAccount")}
        </button>
      </form>
    </div>
  );
}
