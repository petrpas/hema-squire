import { useTranslation } from "react-i18next";

/** The rail card acting on the open export tab: its active-only switch, the
 *  copy, and — on a discipline — the seeding order and the ratings refresh.
 *
 *  Headed by the tab's name, so the organizer sees which table a switch or a
 *  copy acts on without looking back at the band. The outcome of either action
 *  is stated here, where it was asked for.
 */
export default function TableOperations({
  title,
  active,
  onActiveChange,
  seeded,
  onCopy,
  onRefreshRatings,
  refreshing,
  message,
}: {
  title: string;
  active: boolean;
  onActiveChange: (active: boolean) => void;
  /** The discipline's seeding order by rating — offered on a discipline tab
   *  only, and independent of the active-only switch. */
  seeded?: { checked: boolean; onChange: (seeded: boolean) => void };
  onCopy: () => void;
  /** Offered on a discipline tab only, where the ratings being read are. */
  onRefreshRatings?: () => void;
  refreshing: boolean;
  message: string | null;
}) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h2>{title}</h2>
      <label className="rail-check">
        <input
          type="checkbox"
          checked={active}
          onChange={(event) => onActiveChange(event.currentTarget.checked)}
        />
        <span>{t("export.activeOnly")}</span>
      </label>
      {seeded && (
        <label className="rail-check">
          <input
            type="checkbox"
            checked={seeded.checked}
            onChange={(event) => seeded.onChange(event.currentTarget.checked)}
          />
          <span>{t("export.seedByRating")}</span>
        </label>
      )}
      <button type="button" className="secondary param-save" onClick={onCopy}>
        {t("export.copy")}
      </button>
      {onRefreshRatings && (
        <>
          <button
            type="button"
            className="secondary param-save"
            disabled={refreshing}
            onClick={onRefreshRatings}
          >
            {refreshing ? t("common.loading") : t("export.fetchRatings")}
          </button>
          <p className="rail-hint">{t("export.refreshesTournament")}</p>
        </>
      )}
      {message && <p className="rail-hint">{message}</p>}
    </section>
  );
}
