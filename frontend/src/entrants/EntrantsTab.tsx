import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api, type Entrants, type Roster } from "../api";
import { registeredMoment } from "../momentText";
import NotFound from "../NotFound";
import { entrantsEvent, entrants as entrantsPath } from "../routes";
import { useTabBand } from "../useTabBand";
import IndividualRoster from "./IndividualRoster";
import TeamRoster from "./TeamRoster";

/** Where a roster lives: a discipline by its slug, a side event under a
 *  segment of its own. */
function rosterPath(slug: string, roster: Roster): string {
  return roster.kind === "event"
    ? entrantsEvent(slug, roster.slug)
    : entrantsPath(slug, roster.slug);
}

/** The detail page's Entrants tab: one roster per discipline in the
 *  tournament's own order, then one per listed side event, each at its own
 *  address (spec public-entrants).
 *
 *  Every roster arrives in one answer, already decided — what each Paid cell
 *  says, what is faded, whether a line and a queue are drawn. This tab draws
 *  them and restates none of the rules behind them. */
export default function EntrantsTab({
  slug,
  discipline,
  event,
  timezone,
}: {
  slug: string;
  /** The discipline the address names. */
  discipline: string | undefined;
  /** The side event the address names. Where it names neither, the first
   *  roster is shown. */
  event: string | undefined;
  timezone: string | null;
}) {
  const { t } = useTranslation();
  const [entrants, setEntrants] = useState<Entrants | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.entrants(slug).then(setEntrants, () => setFailed(true));
  }, [slug]);

  const named = discipline !== undefined || event !== undefined;
  const roster = entrants?.rosters.find((candidate) =>
    event !== undefined
      ? candidate.kind === "event" && candidate.slug === event
      : discipline !== undefined
        ? candidate.kind !== "event" && candidate.slug === discipline
        : true,
  );
  const band = useTabBand(roster === undefined ? "" : rosterPath(slug, roster));

  if (failed) return <NotFound />;
  if (entrants === null) return <p>{t("common.loading")}</p>;
  // an address naming a roster the tournament does not have names no screen
  // (spec routing)
  if (named && roster === undefined) return <NotFound />;

  return (
    <section className="entrants">
      {entrants.as_of !== null && (
        <p className="rail-hint">
          {t("entrants.asOf", { moment: registeredMoment(entrants.as_of, timezone) })}
        </p>
      )}
      <nav className="stage-control stage-control-band entrants-band" ref={band}>
        {entrants.rosters.map((candidate) => (
          <Link
            key={rosterPath(slug, candidate)}
            to={rosterPath(slug, candidate)}
            className={candidate === roster ? "active" : ""}
            aria-current={candidate === roster ? "page" : undefined}
          >
            {candidate.name}
          </Link>
        ))}
      </nav>
      {roster === undefined ? null : roster.kind === "team" ? (
        <TeamRoster roster={roster} />
      ) : (
        <IndividualRoster roster={roster} />
      )}
    </section>
  );
}
