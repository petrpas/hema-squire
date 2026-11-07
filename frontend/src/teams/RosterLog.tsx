import { useTranslation } from "react-i18next";
import type { RosterChange } from "../api";

/** One roster's whole story: the entering fencer's edits and the organizer's
 *  in one log, each entry naming what changed, who changed it, and when (spec
 *  team-disciplines, Every roster change is recorded in one log).
 *
 *  Append-only, so the list is a reading surface and nothing here edits it. A
 *  team with no entries is not a team nobody ever touched — the history begins
 *  where it was first kept, which the empty line says rather than implying
 *  the roster was never changed. */
export default function RosterLog({ entries }: { entries: RosterChange[] }) {
  const { t } = useTranslation();

  if (entries.length === 0) return <p className="muted">{t("teams.log.empty")}</p>;

  return (
    <ul className="detail-list">
      {entries.map((entry) => (
        <li key={entry.id} className="muted">
          <div className="detail-row">
            <span>
              {entry.kind === "edited" && entry.field !== null
                ? t("teams.log.edited", {
                    member: entry.member_name,
                    field: t(`teams.log.field.${entry.field}`),
                    before: entry.before ?? t("teams.log.blank"),
                    after: entry.after ?? t("teams.log.blank"),
                  })
                : t(`teams.log.${entry.kind}`, { member: entry.member_name })}
            </span>
            <span>
              {t("teams.log.by", {
                actor: entry.actor,
                at: new Date(entry.created_at).toLocaleString(),
              })}
              {entry.by_organizer && ` · ${t("teams.log.byOrganizer")}`}
              {entry.after_deadline && ` · ${t("teams.log.afterDeadline")}`}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
