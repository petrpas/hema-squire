import { IconX } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { type AdminAccount, api, type Role } from "../api";
import SortHeader from "./SortHeader";
import { adminMatches } from "./search";
import { type SortValue, useSort } from "./useSort";

const ROLES: Role[] = ["fencer", "organizer", "admin"];

type Column = "email" | "name" | "role" | "hrId" | "plea" | "created";

function columnValue(account: AdminAccount, column: Column): SortValue {
  switch (column) {
    case "email":
      return account.email;
    case "name":
      return account.display_name;
    case "role":
      // the Owner ranks above every role the ladder stores
      return account.is_deployment_owner ? ROLES.length : ROLES.indexOf(account.role);
    case "hrId":
      return account.hr_id;
    case "plea":
      return account.has_pending_plea ? 0 : 1;
    case "created":
      return account.created_at;
  }
}

/** Every fencer record, searchable and sortable, with the role and HR unbind
 *  controls (spec user-roles, Admin panel). */
export default function PeopleTab({
  accounts,
  onChanged,
}: {
  accounts: AdminAccount[];
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<number | null>(null);
  const [query, setQuery] = useState("");

  const matching = useMemo(
    () =>
      accounts.filter((account) =>
        adminMatches(
          query,
          [account.display_name],
          [account.email, account.hr_id === null ? null : String(account.hr_id)],
        ),
      ),
    [accounts, query],
  );
  const { sorted, sort, choose } = useSort<AdminAccount, Column>(matching, columnValue, {
    key: "name",
    direction: "ascending",
  });

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

  const header = (column: Column, label: string, numeric = false) => (
    <SortHeader column={column} label={label} sort={sort} onSort={choose} numeric={numeric} />
  );

  return (
    <section className="rail-card">
      <h2>{t("admin.accounts.title")}</h2>
      <input
        type="search"
        className="link-filter admin-search"
        value={query}
        placeholder={t("admin.accounts.search")}
        aria-label={t("admin.accounts.search")}
        onChange={(event) => setQuery(event.target.value)}
      />
      {sorted.length === 0 ? (
        <p className="rail-hint">{t("admin.noMatch")}</p>
      ) : (
        <table className="sheet-table">
          <thead>
            <tr>
              {header("email", t("admin.accounts.email"))}
              {header("name", t("admin.accounts.displayName"))}
              {header("role", t("admin.accounts.role"))}
              {header("hrId", t("admin.accounts.hrId"), true)}
              {header("plea", t("admin.accounts.plea"))}
              {header("created", t("admin.accounts.created"))}
              <th className="col-actions" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((account) => (
              <tr key={account.id}>
                <td>{account.email ?? "—"}</td>
                <td>{account.display_name}</td>
                <td>
                  {account.is_deployment_owner ? (
                    <span className="tag tag-file-blue">{t("admin.accounts.owner")}</span>
                  ) : (
                    <select
                      value={account.role}
                      disabled={busy === account.id}
                      aria-label={t("admin.accounts.role")}
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
                <td className="col-number">
                  {account.hr_id ?? "—"}
                  {account.hr_shared && (
                    <span
                      className="tag tag-form-yellow hr-shared-badge"
                      title={t("admin.accounts.hrShared")}
                    >
                      {t("admin.accounts.shared")}
                    </span>
                  )}
                </td>
                <td>{account.has_pending_plea ? t("admin.accounts.pleaPending") : "—"}</td>
                <td>{new Date(account.created_at).toLocaleDateString("cs")}</td>
                <td className="col-actions">
                  {account.hr_id !== null && (
                    <button
                      type="button"
                      className="row-action"
                      title={t("admin.accounts.unbind")}
                      disabled={busy === account.id}
                      onClick={() => void unbind(account)}
                    >
                      <IconX size={16} stroke={1.5} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
