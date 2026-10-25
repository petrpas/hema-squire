import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api, type GuestIdentity, type HRProfile } from "./api";
import FieldError, { invalidProps } from "./FieldError";
import HelpHint from "./HelpHint";
import i18n from "./i18n";
import SignupHrStep from "./SignupHrStep";
import useEscape from "./useEscape";
import { useFieldValidation } from "./useFieldValidation";
import { useWideViewport } from "./useWideViewport";
import { apiErrors, checkPassword, checkString } from "./validation";

const IMPLEMENTED_LANGUAGES = Object.keys(i18n.options.resources ?? {});

/** Which form this is. The account variant creates an account once its
 *  address is verified; the guest variant is the same form without a
 *  password, completed by handing the identity back to the page (spec
 *  `guest-registration`). */
export type SignupVariant =
  | {
      kind: "account";
      /** where the verification link lands, as a path of this application */
      returnTo?: string;
    }
  | {
      kind: "guest";
      onGuest: (identity: GuestIdentity) => void;
      /** the identity being changed, when the form is reopened from the
       *  registration form's "registering as" line */
      initial?: GuestIdentity;
    };

/** Account creation, reached from the sign-in screen and leaving by the same
 *  door: `onCancel` returns to it, whether it is taken by the control at the
 *  foot of the form or by Escape. */
export default function SignupForm({
  variant,
  onCancel,
}: {
  variant: SignupVariant;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const guest = variant.kind === "guest";
  const initial = variant.kind === "guest" ? variant.initial : undefined;
  const [email, setEmail] = useState(initial?.email ?? "");
  const [password, setPassword] = useState("");
  const [name, setName] = useState(initial?.display_name ?? "");
  const [language, setLanguage] = useState(initial?.language ?? "en");

  // The window carries its own language, which the selector below changes:
  // the global instance follows the dropdown from the moment the window opens,
  // so the form renders in the language the dropdown shows.
  useEffect(() => {
    void i18n.changeLanguage(language);
  }, [language]);
  const [hrProfile, setHrProfile] = useState<HRProfile | null>(null);
  // a candidate the fencer picked but has not yet confirmed as their own
  const [pendingHr, setPendingHr] = useState<HRProfile | null>(null);
  const [showHrSearch, setShowHrSearch] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // a guest whose address turns out to have an account is offered sign-in
  const [hasAccount, setHasAccount] = useState(false);
  // the address a verification link went to, once the signup is pending
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const validation = useFieldValidation();
  const wide = useWideViewport();
  // Escape closes what is open over the form before it closes the form: a
  // candidate awaiting confirmation, then the hemaratings search, and only
  // with neither of those standing does it go back to sign-in.
  useEscape(() => {
    if (pendingHr !== null) setPendingHr(null);
    else if (showHrSearch) setShowHrSearch(false);
    else onCancel();
  });

  function passwordCheck() {
    return checkPassword("password", "SignupIn.password", password);
  }
  function nameCheck() {
    return checkString("name", "SignupIn.display_name", name, { required: true });
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
    const checks = guest ? [nameCheck] : [passwordCheck, nameCheck];
    if (validation.validateAll(checks) > 0) return;
    setBusy(true);
    setError(null);
    setHasAccount(false);
    try {
      if (variant.kind === "guest") {
        // checked now, so a visitor is not left to fill in a checklist they
        // cannot submit; nothing is created on the server
        await api.guestCheck(email);
        variant.onGuest({
          email,
          display_name: name,
          hr_id: hrProfile ? hrProfile.hr_id : undefined,
          language,
        });
        return;
      }
      await api.signup({
        email,
        password,
        display_name: name,
        hr_id: hrProfile ? hrProfile.hr_id : undefined,
        language,
        return_to: variant.returnTo,
      });
      setSentTo(email);
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = typeof err.detail === "string" ? err.detail : null;
        const fieldErrors = apiErrors(err);
        if (detail === "email_has_account") {
          setError(t("guest.errors.hasAccount"));
          setHasAccount(true);
        } else if (detail === "email_already_registered") setError(t("signup.errors.emailTaken"));
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

  if (sentTo !== null) {
    // the account does not exist yet: the statement takes the form's place,
    // static, and the way back is the way to sign in once the link is followed
    return (
      <section id="signup-sent" className="login-card">
        <h1>{t("app.title")}</h1>
        <p className="login-subtitle">{t("signup.subtitle")}</p>
        <p className="login-notice">{t("signup.sent", { email: sentTo })}</p>
        <button type="button" className="link-button" onClick={onCancel}>
          {t("signup.backToLogin")}
        </button>
      </section>
    );
  }

  return (
    /* Its own <form>, with an id of its own: sign-in renders a different form
       at this position, and while React already replaces the DOM node across
       that switch (a component type against a host type never reconciles),
       the stable id gives a password manager a durable identity for each and
       stops one form's fields being attributed to the other. The guest
       variant is a third identity, holding no credential at all. */
    <form id={guest ? "guest-form" : "signup-form"} className="login-card" onSubmit={submit}>
      <h1>{t("app.title")}</h1>
      <p className="login-subtitle">
        {guest ? t("guest.title") : t("signup.subtitle")}{" "}
        <HelpHint text={guest ? t("guest.subtitle") : t("signup.hint")} align="center" />
      </p>
      <div className="tiskopis-row">
        <span className="tiskopis-number">
          {guest ? t("guest.formTitle") : t("signup.formTitle")}
        </span>
        <span className="tiskopis-number">
          {guest ? t("guest.formNumber") : t("signup.formNumber")}
        </span>
      </div>
      <label>
        {t("login.email")}
        <input
          name="email"
          type="email"
          /* "username" on the account form: it is the signal that tells a
             password manager this is the account identifier, and without it
             no manager offers to save the new pair. The guest form has no
             account, so its address declares itself an address. */
          autoComplete={guest ? "email" : "username"}
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
      {!guest && (
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
      )}
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
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          {IMPLEMENTED_LANGUAGES.map((code) => (
            <option key={code} value={code}>
              {t(`languages.${code}`)}
            </option>
          ))}
        </select>
      </label>

      <SignupHrStep
        name={name}
        hrProfile={hrProfile}
        pendingHr={pendingHr}
        showHrSearch={showHrSearch}
        onPick={setPendingHr}
        onConfirm={confirmHr}
        onClear={clearHr}
        onShowSearch={setShowHrSearch}
      />

      {/* The slot is always in the layout, so a message arriving cannot push
          the submit button out from under a thumb already on its way down. */}
      <p className="login-error" role="alert">
        {error}
        {hasAccount && (
          <>
            {" "}
            <button type="button" className="link-button" onClick={onCancel}>
              {t("login.submit")}
            </button>
          </>
        )}
      </p>
      <button type="submit" disabled={busy}>
        {guest
          ? busy
            ? t("guest.submitting")
            : t("guest.submit")
          : busy
            ? t("signup.submitting")
            : t("signup.submit")}
      </button>
      <button type="button" className="link-button" onClick={onCancel}>
        {t("signup.backToLogin")}
      </button>
    </form>
  );
}
