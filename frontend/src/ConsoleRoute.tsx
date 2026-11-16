import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { ApiError, api, type TournamentDetail } from "./api";
import Console, { DEFAULT_PHASE, offeredPhases, PHASES, type Phase } from "./Console";
import NotFound from "./NotFound";
import OrganizerTermsDialog from "./OrganizerTermsDialog";
import * as routes from "./routes";

function isPhase(value: string | undefined): value is Phase {
  return value !== undefined && (PHASES as readonly string[]).includes(value);
}

/** Resolves the console's tournament from the URL alone (design D8): no
 *  picker hand-off is assumed, so a deep link works the same as a link
 *  followed from the picker.
 *
 *  The server answers no console request to an owner who has not accepted the
 *  current organizer data terms (spec privacy), so the terms are put here,
 *  before the console exists, and accepting loads it. */
export default function ConsoleRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { slug = "", phase: phaseParam } = useParams();
  const [tournament, setTournament] = useState<TournamentDetail | null | "error" | "terms">(null);

  const load = useCallback(() => {
    setTournament(null);
    api
      .consoleTournament(slug)
      .then(setTournament, (error) =>
        setTournament(
          error instanceof ApiError && error.detail === "organizer_terms_due" ? "terms" : "error",
        ),
      );
  }, [slug]);

  useEffect(load, [load]);

  if (phaseParam !== undefined && !isPhase(phaseParam)) return <NotFound />;
  if (tournament === "error") return <NotFound />;
  if (tournament === "terms") {
    return <OrganizerTermsDialog onAccepted={load} onLeave={() => navigate(routes.picker())} />;
  }
  if (tournament === null) return <p>{t("common.loading")}</p>;

  // A phase the mode does not offer is not reachable by its URL either: a
  // bookmark saved before a feature was turned off lands on the default phase
  // rather than on an empty view (spec: etl-console).
  const phase = phaseParam ?? DEFAULT_PHASE;
  if (!offeredPhases(tournament).includes(phase)) {
    return <Navigate to={routes.consolePath(slug, DEFAULT_PHASE)} replace />;
  }

  return <Console tournament={tournament} phase={phase} />;
}
