import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import Console, { PHASES, type Phase } from "./Console";
import NotFound from "./NotFound";
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

  return <Console tournament={tournament} phase={phaseParam ?? "load"} />;
}
