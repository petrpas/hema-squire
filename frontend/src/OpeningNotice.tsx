import { useTranslation } from "react-i18next";

import type { TournamentDetail } from "./api";
import { zoneAbbreviation } from "./TournamentFace";
import { formatCountdown } from "./openingMoment";

/** What the fencer reads while registration has not opened yet: the moment it
 *  opens, and — inside the last day — how long is left.
 *
 *  The countdown is a *measured figure*, not an indicator of progress: it is a
 *  line of type in the ordinary ink, updated once a second by re-rendering the
 *  string, at a fixed width so the line does not move as the digits change.
 *  Nothing here animates, fills, or slides (spec: design-system, "A live
 *  figure is text, not an animation"). */
export default function OpeningNotice({
  detail,
  remainingMs,
  counting,
}: {
  detail: TournamentDetail;
  /** Milliseconds until the moment, measured against the server's clock. */
  remainingMs: number | null;
  /** Whether the moment is close enough for a countdown to be worth watching. */
  counting: boolean;
}) {
  const { t } = useTranslation();
  const opensOn = detail.registration_opens;

  return (
    <section className="rail-card dashed">
      <p className="rail-hint">
        {opensOn
          ? detail.registration_opens_time
            ? t("detail.opensAtNotice", {
                date: new Date(opensOn).toLocaleDateString("cs"),
                time: detail.registration_opens_time.slice(0, 5),
                zone: zoneAbbreviation(detail),
              })
            : t("detail.opensOnNotice", { date: new Date(opensOn).toLocaleDateString("cs") })
          : t("detail.notYetOpen")}
      </p>
      {counting && remainingMs !== null && (
        <p className="rail-hint opening-countdown">
          {t("detail.opensIn", { countdown: formatCountdown(remainingMs) })}
        </p>
      )}
    </section>
  );
}
