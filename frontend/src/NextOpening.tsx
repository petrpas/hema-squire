import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { logoUrl, type OpenTournament } from "./api";
import { monogram } from "./monogram";
import { formatCountdown, openingHourIn, openingMomentMs } from "./openingMoment";
import { detail } from "./routes";
import { useOpeningMoment } from "./useOpeningMoment";

/** How far ahead an opening is worth announcing on the list. Past this the
 *  strip is not rendered at all: a live figure is shown only while it is worth
 *  watching (spec design-system). */
const ANNOUNCE_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

/** The announced tournament whose registration opens soonest, or null. */
function soonest(announced: OpenTournament[]): OpenTournament | null {
  let best: OpenTournament | null = null;
  let bestAt = Number.POSITIVE_INFINITY;
  for (const tournament of announced) {
    if (tournament.registration_status !== "opens_on") continue;
    const at = openingMomentMs(tournament.registration_opens_at);
    if (at !== null && at < bestAt) {
      best = tournament;
      bestAt = at;
    }
  }
  return best;
}

/** The strip above the tab band naming the next registration opening (spec
 *  `fencer-home`, The list announces the next registration opening).
 *
 *  It runs on the detail page's clock, `useOpeningMoment`, so it is measured
 *  against the server, costs no request while it waits, and re-checks when the
 *  page is looked at again. Inside the last day it counts down once a second;
 *  before that it states the opening day and hour, as the detail does. At the
 *  moment `onOpened` refreshes the list once, the tournament moves to the Open
 *  tab, and the next opening, if any, takes the strip. */
export default function NextOpening({
  announced,
  onOpened,
}: {
  announced: OpenTournament[];
  onOpened: () => void;
}) {
  const tournament = soonest(announced);
  const moment = useOpeningMoment(tournament, onOpened);
  if (tournament === null || moment.remainingMs === null) return null;
  // at zero the strip stops rather than show a stale or negative figure; the
  // refresh the moment triggered is what moves it on
  if (moment.remainingMs === 0 || moment.remainingMs > ANNOUNCE_WINDOW_MS) return null;
  return (
    <Strip tournament={tournament} remainingMs={moment.remainingMs} counting={moment.counting} />
  );
}

function Strip({
  tournament,
  remainingMs,
  counting,
}: {
  tournament: OpenTournament;
  remainingMs: number;
  counting: boolean;
}) {
  const { t } = useTranslation();
  const day = tournament.registration_opens_on
    ? new Date(tournament.registration_opens_on).toLocaleDateString("cs", {
        day: "numeric",
        month: "numeric",
      })
    : "";
  const hour = openingHourIn(tournament.registration_opens_at, tournament.timezone);
  return (
    <section className="next-opening">
      {/* unringed: no ring stands beside a live figure (spec design-system) */}
      <span className="next-opening-plate" data-logo={tournament.has_logo || undefined}>
        {tournament.has_logo ? (
          <img src={logoUrl(tournament.slug)} alt="" />
        ) : (
          <span aria-hidden="true">
            {tournament.short_code ?? monogram(tournament.display_name)}
          </span>
        )}
      </span>
      <div className="next-opening-name">
        <span className="next-opening-label">{t("home.nextOpening.label")}</span>
        <span>{tournament.display_name}</span>
      </div>
      <span className="next-opening-figure">
        {counting
          ? formatCountdown(remainingMs)
          : hour
            ? t("home.nextOpening.at", { date: day, time: hour })
            : day}
      </span>
      <Link className="button-pill" to={detail(tournament.slug)} state={{ tab: "announced" }}>
        {t("home.nextOpening.show")}
      </Link>
    </section>
  );
}
