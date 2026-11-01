import { IconCheck, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type PleaQueueItem } from "../api";

export default function PleaQueue({
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
                type="button"
                className="row-action"
                title={t("admin.pleas.grant")}
                disabled={busy === plea.id}
                onClick={() => void decide(plea, true)}
              >
                <IconCheck size={16} stroke={1.5} />
              </button>
              <button
                type="button"
                className="row-action"
                title={t("admin.pleas.deny")}
                disabled={busy === plea.id}
                onClick={() => void decide(plea, false)}
              >
                <IconX size={16} stroke={1.5} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
