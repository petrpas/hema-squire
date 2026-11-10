import { useTranslation } from "react-i18next";

import type { AdminDeferredDeletion } from "../api";

/** Deletions past their seven days that something holds back (spec
 *  `account-deletion`, Deletion is refused while the account holds
 *  responsibility). Each waits until what blocks it is handed over; nothing
 *  here acts, it says what to resolve. */
export default function DeferredDeletions({ deletions }: { deletions: AdminDeferredDeletion[] }) {
  const { t } = useTranslation();
  if (deletions.length === 0) return null;
  return (
    <section className="rail-card">
      <h2>{t("admin.deletions.title")}</h2>
      <ul className="deletion-impact">
        {deletions.map((deletion) => (
          <li key={deletion.fencer_id}>
            <strong>{deletion.display_name}</strong> {deletion.email ?? ""} —{" "}
            {deletion.blockers
              .map((blocker) =>
                t(`profile.deletion.blocker.${blocker.kind}`, {
                  tournaments: blocker.tournaments.join(", "),
                }),
              )
              .join(" ")}
          </li>
        ))}
      </ul>
    </section>
  );
}
