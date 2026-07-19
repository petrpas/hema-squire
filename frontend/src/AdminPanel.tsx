import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type AdminAccount, type PleaQueueItem, type Role, api } from "./api";

const ROLES: Role[] = ["fencer", "organizer", "admin"];

function AccountsSection({
  accounts,
  onChanged,
}: {
  accounts: AdminAccount[];
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<number | null>(null);

  async function changeRole(account: AdminAccount, role: Role) {
    setBusy(account.id);
    try {
      await api.adminSetRole(account.id, role);
      onChanged();
    } finally {
      setBusy(null);
    }
  }

  async function unbind(account: AdminAccount) {
    setBusy(account.id);
    try {
      await api.adminHrUnbind(account.id);
      onChanged();
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("admin.accounts.title")}</h2>
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("admin.accounts.email")}</th>
            <th>{t("admin.accounts.displayName")}</th>
            <th>{t("admin.accounts.role")}</th>
            <th>{t("admin.accounts.hrId")}</th>
            <th>{t("admin.accounts.plea")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id}>
              <td>{account.email}</td>
              <td>{account.display_name}</td>
              <td>
                {account.is_deployment_owner ? (
                  <span className="chip">{t("admin.accounts.owner")}</span>
                ) : (
                  <select
                    value={account.role}
                    disabled={busy === account.id}
                    onChange={(event) => void changeRole(account, event.target.value as Role)}
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>
                        {t(`admin.accounts.roles.${role}`)}
                      </option>
                    ))}
                  </select>
                )}
              </td>
              <td>{account.hr_id ?? "—"}</td>
              <td>{account.has_pending_plea ? t("admin.accounts.pleaPending") : "—"}</td>
              <td className="col-actions">
                {account.hr_id !== null && (
                  <button
                    className="row-action"
                    title={t("admin.accounts.unbind")}
                    disabled={busy === account.id}
                    onClick={() => void unbind(account)}
                  >
                    ⤬
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function PleaQueueSection({
  pleas,
  onChanged,
}: {
  pleas: PleaQueueItem[];
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<number | null>(null);

  async function decide(plea: PleaQueueItem, grant: boolean) {
    setBusy(plea.id);
    try {
      if (grant) await api.adminGrantPlea(plea.id);
      else await api.adminDenyPlea(plea.id);
      onChanged();
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rail-card dashed">
      <h2>{t("admin.pleas.title")}</h2>
      {pleas.length === 0 ? (
        <p className="rail-hint">{t("admin.pleas.empty")}</p>
      ) : (
        <ul className="edits-list">
          {pleas.map((plea) => (
            <li key={plea.id} className="edit-entry">
              <div className="edit-body">
                <div>
                  <strong>{plea.display_name}</strong> · {plea.email}
                </div>
                {plea.message && <div className="edit-meta">{plea.message}</div>}
              </div>
              <button
                className="row-action"
                title={t("admin.pleas.grant")}
                disabled={busy === plea.id}
                onClick={() => void decide(plea, true)}
              >
                ✓
              </button>
              <button
                className="row-action"
                title={t("admin.pleas.deny")}
                disabled={busy === plea.id}
                onClick={() => void decide(plea, false)}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function AdminPanel({ onBack }: { onBack: () => void }) {
  const { t } = useTranslation();
  const [accounts, setAccounts] = useState<AdminAccount[] | null>(null);
  const [pleas, setPleas] = useState<PleaQueueItem[] | null>(null);
  const [error, setError] = useState(false);

  function refresh() {
    api.adminAccounts().then(setAccounts, () => setError(true));
    api.adminPleas().then(setPleas, () => setError(true));
  }

  useEffect(refresh, []);

  return (
    <div className="login-page">
      <div className="login-card wide-card">
        <h1>{t("admin.title")}</h1>
        {error ? (
          <p className="login-error">{t("admin.error")}</p>
        ) : accounts === null || pleas === null ? (
          <p>{t("common.loading")}</p>
        ) : (
          <div className="setup-panel">
            <PleaQueueSection pleas={pleas} onChanged={refresh} />
            <AccountsSection accounts={accounts} onChanged={refresh} />
          </div>
        )}
        <button className="link-button" onClick={onBack}>
          {t("admin.back")}
        </button>
      </div>
    </div>
  );
}
