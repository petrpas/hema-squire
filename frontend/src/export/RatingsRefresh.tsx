import { IconRefresh } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import HintedAction from "./HintedAction";

/** The ratings refresh: one outline icon with its hint, waiting without a
 *  spinner while the fetch runs. The office's Export card and the floor's
 *  Data panel both offer it (spec floor-data, The ratings are refreshed for
 *  one discipline), so the control reads the same in both. */
export default function RatingsRefresh({
  onRefresh,
  refreshing,
}: {
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const { t } = useTranslation();
  return (
    <HintedAction hint={t("export.hints.fetchRatings")}>
      {(hintId) => (
        <button
          type="button"
          className="icon-action"
          disabled={refreshing}
          aria-describedby={hintId}
          onClick={onRefresh}
        >
          <IconRefresh size={18} stroke={1.5} />
          <span className="visually-hidden">{t("export.fetchRatings")}</span>
        </button>
      )}
    </HintedAction>
  );
}
