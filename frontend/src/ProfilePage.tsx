import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import HRSearchPicker from "./HRSearch";
import PleaSection from "./PleaSection";
import { ApiError, type Account, type HRProfile, type Plea, api } from "./api";
import i18n from "./i18n";

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

  useEffect(() => {
    setEmail(account.email);
    setDisplayName(account.display_name);
    setLanguage(account.language);
    setDirty(false);
  }, [account]);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateAccount({ email, display_name: displayName, language });
      onUpdated(updated);
      void i18n.changeLanguage(updated.language);
      setDirty(false);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? t("profile.account.emailTaken")
          : t("profile.account.saveFailed"),
      );
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
            }}
          />
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
      <p className="chip">{roleLabel}</p>
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
        className="secondary hr-profile-link"
        href={`https://hemaratings.com/fighters/details/${account.hr_id}/`}
        target="_blank"
        rel="noreferrer"
      >
        {t("profile.hr.viewProfile")}
      </a>
    </section>
  );
}

function HRMatchSection({ onBound }: { onBound: (account: Account) => void }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm(profile: HRProfile) {
    setBusy(true);
    setError(null);
    try {
      const account = await api.bindHr(profile.hr_id);
      onBound(account);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? t("profile.hr.conflict")
          : t("profile.hr.bindFailed"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("profile.hr.title")}</h2>
      <p className="rail-hint">{t("profile.hr.unboundHint")}</p>
      <HRSearchPicker onConfirm={(profile) => void confirm(profile)} busy={busy} />
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}

export default function ProfilePage({
  onAdmin,
  onOrganizer,
  onFencer,
  onLogout,
}: {
  onAdmin: () => void;
  onOrganizer: () => void;
  onFencer: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.account().then(setAccount, () => setError(true));
  }, []);

  return (
    <div className="login-page">
      <div className="page-menu-corner">
        <AccountMenu
          account={account}
          onProfile={() => {}}
          onAdmin={onAdmin}
          onFencer={onFencer}
          onOrganizer={onOrganizer}
          onLogout={onLogout}
        />
      </div>
      <div className="login-card wide-card">
        <h1>{t("profile.title")}</h1>
        {error ? (
          <p className="login-error">{t("profile.loadFailed")}</p>
        ) : account === null ? (
          <p>{t("common.loading")}</p>
        ) : (
          <div className="setup-panel">
            <AccountSection account={account} onUpdated={setAccount} />
            <RoleSection account={account} />
            {account.hr_id !== null ? (
              <HRBoundSection account={account} />
            ) : (
              <HRMatchSection onBound={setAccount} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
