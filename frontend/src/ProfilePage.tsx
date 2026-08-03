import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import FieldError, { invalidProps } from "./FieldError";
import HRSearchPicker from "./HRSearch";
import PleaSection from "./PleaSection";
import { useAuth } from "./RequireAuth";
import { ApiError, type Account, type HRProfile, type Plea, api } from "./api";
import i18n from "./i18n";
import { useFieldValidation } from "./useFieldValidation";
import { apiErrors, checkString } from "./validation";

const IMPLEMENTED_LANGUAGES = Object.keys(i18n.options.resources ?? {});

function AccountSection({
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
  const validation = useFieldValidation();

  useEffect(() => {
    setEmail(account.email);
    setDisplayName(account.display_name);
    setLanguage(account.language);
    validation.clearAll();
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [account]);

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
      <h2>{t("profile.account.title")}</h2>
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
      <button className="secondary param-save" onClick={() => void save()} disabled={!dirty || busy}>
        {t("rail.save")}
      </button>
    </section>
  );
}

function RoleSection({ account }: { account: Account }) {
  const { t } = useTranslation();
  const [plea, setPlea] = useState<Plea | null>(null);
  const isPlainFencer = account.role === "fencer" && !account.is_deployment_owner;

  useEffect(() => {
    if (isPlainFencer) api.myPlea().then(setPlea, () => setPlea(null));
  }, [isPlainFencer]);

  const roleLabel = account.is_deployment_owner
    ? t("admin.accounts.owner")
    : t(`admin.accounts.roles.${account.role}`);

  return (
    <section className="rail-card">
      <h2>{t("profile.role.title")}</h2>
      <p className="tag tag-file-blue">{roleLabel}</p>
      {isPlainFencer && plea && <PleaSection plea={plea} onPleaChange={setPlea} />}
    </section>
  );
}

function HRBoundSection({ account }: { account: Account }) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h2>{t("profile.hr.title")}</h2>
      <div className="param-fields">
        <div className="param-field">
          <span>{t("admin.accounts.hrId")}</span>
          <strong>{account.hr_id}</strong>
        </div>
        <div className="param-field">
          <span>{t("column.name")}</span>
          <strong>{account.display_name}</strong>
        </div>
        <div className="param-field">
          <span>{t("column.club")}</span>
          <strong>{account.club ?? "—"}</strong>
        </div>
        <div className="param-field">
          <span>{t("column.nationality")}</span>
          <strong>{account.nationality ?? "—"}</strong>
        </div>
      </div>
      <a
        className="hr-profile-link"
        href={`https://hemaratings.com/fighters/details/${account.hr_id}/`}
        target="_blank"
        rel="noreferrer"
      >
        {t("profile.hr.viewProfile")}
      </a>
    </section>
  );
}

function HRMatchSection({
  account,
  onBound,
}: {
  account: Account;
  onBound: (account: Account) => void;
}) {
  const { t } = useTranslation();
  const [pending, setPending] = useState<HRProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function select(profile: HRProfile) {
    setPending(profile);
    setError(null);
  }

  async function confirmBinding() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      const account = await api.bindHr(pending.hr_id);
      onBound(account);
    } catch {
      setError(t("profile.hr.bindFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("profile.hr.title")}</h2>
      {pending ? (
        <div className="signup-hr-confirmed">
          <p>{t("signup.hr.confirmed", { name: pending.name })}</p>
          {pending.claimed && (
            <span className="hr-claimed-notice">{t("profile.hr.claimedNotice")}</span>
          )}
          {error && <p className="login-error">{error}</p>}
          <button
            type="button"
            className="btn-primary"
            onClick={() => void confirmBinding()}
            disabled={busy}
          >
            {t("profile.hr.confirmBind")}
          </button>
          <button
            type="button"
            className="link-button"
            onClick={() => setPending(null)}
            disabled={busy}
          >
            {t("common.cancel")}
          </button>
        </div>
      ) : (
        <>
          <p className="rail-hint">{t("profile.hr.unboundHint")}</p>
          <HRSearchPicker onConfirm={select} busy={busy} initialQuery={account.display_name} />
        </>
      )}
    </section>
  );
}

export default function ProfilePage() {
  const { t } = useTranslation();
  const { onLogout } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.account().then(setAccount, () => setError(true));
  }, []);

  return (
    <div className="login-page">
      <div className="page-menu-corner">
        <AccountMenu account={account} onLogout={onLogout} />
      </div>
      <div className="login-card wide-card">
        <h1>{t("profile.title")}</h1>
        {error ? (
          <p className="login-error">{t("profile.loadFailed")}</p>
        ) : account === null ? (
          <p>{t("common.loading")}</p>
        ) : (
          <div className="page-card-body">
            <AccountSection account={account} onUpdated={setAccount} />
            <RoleSection account={account} />
            {account.hr_id !== null ? (
              <HRBoundSection account={account} />
            ) : (
              <HRMatchSection account={account} onBound={setAccount} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
