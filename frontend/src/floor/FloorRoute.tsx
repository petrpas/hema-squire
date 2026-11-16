import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError, api, type TournamentDetail } from "../api";
import NotFound from "../NotFound";
import OrganizerTermsDialog from "../OrganizerTermsDialog";
import * as routes from "../routes";
import FloorConsole from "./FloorConsole";
import { type FloorSummary, floorApi } from "./floorApi";
import { defaultTab, isFloorTab } from "./tabs";

type Loaded = { tournament: TournamentDetail; summary: FloorSummary };

/** What a failed load ends at: the terms dialog, the not-found screen for an
 *  address with no floor behind it (unknown tournament, an event, a refusal),
 *  and a plain failure otherwise, which is not a missing page. */
function failure(error: unknown): "terms" | "missing" | "failed" {
  if (!(error instanceof ApiError)) return "failed";
  if (error.detail === "organizer_terms_due") return "terms";
  return error.status === 404 || error.status === 403 ? "missing" : "failed";
}

/** Resolves the floor console from its address alone, as `ConsoleRoute` does
 *  the office console's: the same gate, the same terms dialog, and a
 *  discipline-less event ending at the not-found screen (spec floor-console). */
export default function FloorRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { slug = "", tab, discipline } = useParams();
  const [loaded, setLoaded] = useState<Loaded | null | "missing" | "failed" | "terms">(null);

  const load = useCallback(() => {
    setLoaded(null);
    Promise.all([api.consoleTournament(slug), floorApi.summary(slug)]).then(
      ([tournament, summary]) => setLoaded({ tournament, summary }),
      (error) => setLoaded(failure(error)),
    );
  }, [slug]);

  useEffect(load, [load]);

  if (loaded === "missing") return <NotFound />;
  if (loaded === "failed") return <p className="floor-not-yet muted">{t("floor.loadFailed")}</p>;
  if (loaded === "terms") {
    return <OrganizerTermsDialog onAccepted={load} onLeave={() => navigate(routes.picker())} />;
  }
  if (loaded === null) return <p>{t("common.loading")}</p>;

  // no tab, or one that does not exist, lands on the default one
  if (!isFloorTab(tab)) {
    return (
      <Navigate to={routes.floorPath(slug, defaultTab(loaded.summary.plan_published))} replace />
    );
  }

  return (
    <FloorConsole
      tournament={loaded.tournament}
      summary={loaded.summary}
      tab={tab}
      discipline={discipline}
      onChanged={() =>
        floorApi
          .summary(slug)
          .then((summary) =>
            setLoaded((current) =>
              current !== null && typeof current === "object" ? { ...current, summary } : current,
            ),
          )
      }
    />
  );
}
