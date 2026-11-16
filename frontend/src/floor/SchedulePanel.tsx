import { useTranslation } from "react-i18next";

/** The schedule beside the work, or the narrow screen's last tab. Until a
 *  plan exists it states that none has been made (spec floor-console, A
 *  schedule panel stands beside the work); `floor-plan` draws the schedule
 *  here. */
export default function SchedulePanel({
  planPublished,
  asTabPanel,
}: {
  planPublished: boolean;
  asTabPanel: boolean;
}) {
  const { t } = useTranslation();
  return (
    <aside
      className="floor-schedule"
      {...(asTabPanel
        ? {
            role: "tabpanel",
            id: "floor-tabpanel-schedule",
            "aria-labelledby": "floor-tab-schedule",
          }
        : { "aria-label": t("floor.schedule.title") })}
    >
      <h2>{t("floor.schedule.title")}</h2>
      <p className="muted">
        {planPublished ? t("floor.schedule.later") : t("floor.schedule.none")}
      </p>
    </aside>
  );
}
