import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import { poolsApi } from "../floorApi";
import type { ViewProps } from "./DrawView";
import { StatsTable } from "./StatsTable";

/** Closed pools: the frozen ranking that seeds the elimination. Reopening
 *  is the tab's operation (ClosedActions). */
export function ClosedView({ view, name }: ViewProps) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h2>{t("floor.pools.closedTitle")}</h2>
      <StatsTable rows={view.standings?.ranking ?? []} name={name} />
    </section>
  );
}

/** Reopening closed pools, in the panel; refused once an elimination bout
 *  has a result. */
export function ClosedActions({ slug, discipline, onChanged }: ViewProps) {
  const { t } = useTranslation();
  const [refused, setRefused] = useState(false);

  return (
    <section className="rail-card">
      <h2>{t("floor.pools.closedTitle")}</h2>
      <button
        type="button"
        className="secondary"
        onClick={() =>
          void poolsApi
            .reopenPools(slug, discipline)
            .then(onChanged, (error) => setRefused(error instanceof ApiError))
        }
      >
        {t("floor.pools.reopenPools")}
      </button>
      {refused && (
        <p className="floor-missing" role="alert">
          {t("floor.pools.reopenRefused")}
        </p>
      )}
    </section>
  );
}
