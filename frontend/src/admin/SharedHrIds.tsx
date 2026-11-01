import { IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type AdminAccount, api } from "../api";
import type { SharedHrGroup } from "./sharedHr";

/** HR IDs bound by more than one account, each with its holders and an unbind
 *  per holder (spec user-roles, Admin panel). A group leaves the list once no
 *  more than one account still holds the ID. */
export default function SharedHrIds({
  groups,
  onChanged,
}: {
  groups: SharedHrGroup[];
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<number | null>(null);

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
    <section className="rail-card dashed">
      <h2>{t("admin.sharedHr.title")}</h2>
      {groups.length === 0 ? (
        <p className="rail-hint">{t("admin.sharedHr.empty")}</p>
      ) : (
        <ul className="edits-list">
          {groups.map((group) => (
            <li key={group.hrId} className="edit-entry admin-shared-hr">
              <div className="edit-body">
                <div>
                  <strong>{t("admin.sharedHr.hrId", { hrId: group.hrId })}</strong>
                </div>
                <ul className="admin-shared-holders">
                  {group.accounts.map((account) => (
                    <li key={account.id}>
                      <span className="edit-meta">
                        {account.display_name}
                        {account.email && ` · ${account.email}`}
                      </span>
                      <button
                        type="button"
                        className="row-action"
                        title={t("admin.accounts.unbind")}
                        disabled={busy === account.id}
                        onClick={() => void unbind(account)}
                      >
                        <IconX size={16} stroke={1.5} />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
