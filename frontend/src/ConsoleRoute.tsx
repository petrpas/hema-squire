import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useParams } from "react-router-dom";

import Console, { DEFAULT_PHASE, offeredPhases, PHASES, type Phase } from "./Console";
import NotFound from "./NotFound";
import * as routes from "./routes";
import { type Tournament, api } from "./api";

function isPhase(value: string | undefined): value is Phase {
  return value !== undefined && (PHASES as readonly string[]).includes(value);
}

/** Resolves the console's tournament from the URL alone (design D8): no
 *  picker hand-off is assumed, so a deep link works the same as a link
 *  followed from the picker. */
export default function ConsoleRoute() {
  const { t } = useTranslation();
  const { slug = "", phase: phaseParam } = useParams();
  const [tournament, setTournament] = useState<Tournament | null | "error">(null);

  useEffect(() => {
    setTournament(null);
    api.tournament(slug).then(setTournament, () => setTournament("error"));
  }, [slug]);

  if (phaseParam !== undefined && !isPhase(phaseParam)) return <NotFound />;
  if (tournament === "error") return <NotFound />;
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
