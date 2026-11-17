import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import * as routes from "../../routes";
import { DisciplineStrip } from "../DisciplineStrip";
import { FloorLayout } from "../FloorLayout";
import { type FloorSetup, floorApi, type PoolsView, poolsApi } from "../floorApi";
import { usePolled } from "../usePolled";
import { ClosedActions, ClosedView } from "./ClosedView";
import { DrawActions, DrawView } from "./DrawView";
import { RingKeys } from "./RingKeys";
import { RunningActions, RunningView } from "./RunningView";

/** Skupiny: the selected discipline in its state — the draw, the pools
 *  running or complete, or closed — in the work, and the state's operations
 *  with the piste screens' links in the panel (spec floor-pools, spec
 *  floor-console). Refreshed every fifteen seconds, as results come in from
 *  the pistes. */
export default function PoolsTab({
  slug,
  discipline,
  fallback,
}: {
  slug: string;
  discipline?: string;
  /** The discipline kept across the console, for an address naming none. */
  fallback?: string;
}) {
  const { t } = useTranslation();
  const [setup, setSetup] = useState<FloorSetup | null>(null);

  useEffect(() => {
    floorApi.setup(slug).then(setSetup, () => setSetup(null));
  }, [slug]);

  const selected =
    setup?.disciplines.find((d) => d.slug === discipline) ??
    setup?.disciplines.find((d) => d.slug === fallback) ??
    setup?.disciplines[0] ??
    null;
  const fetchView = useCallback(
    (): Promise<PoolsView | null> =>
      selected === null ? Promise.resolve(null) : poolsApi.view(slug, selected.id),
    [slug, selected],
  );
  const { data, failed, reload } = usePolled(fetchView, selected?.id);

  if (setup === null || selected === null) {
    return (
      <FloorLayout tab="pools">
        <p>{t("common.loading")}</p>
      </FloorLayout>
    );
  }

  const pistes = new Map(setup.pistes.map((p) => [p.id ?? 0, p.name]));
  // a discipline that takes over fences no pools of its own (spec floor-pools)
  const sourceId = setup.formats.find((f) => f.discipline_id === selected.id)?.takes_pools_from;
  const source = setup.disciplines.find((d) => d.id === sourceId);
  const name = (key: string) => data?.names[key] ?? key;
  const schedule = setup.scope.plan_schedule;
  const common = {
    slug,
    discipline: selected.id,
    view: data,
    name,
    pistes,
    schedule,
    onChanged: reload,
  };

  const head = (
    <DisciplineStrip
      slug={slug}
      tab="pools"
      disciplines={setup.disciplines}
      current={selected.slug}
    />
  );
  const actions =
    source !== undefined ? (
      <p className="rail-hint">{t("floor.ops.idle.takenOver")}</p>
    ) : data === null ? null : !data.checkin_closed ? (
      <p className="rail-hint">{t("floor.ops.idle.checkinOpen")}</p>
    ) : data.state === "waiting" ? (
      <DrawActions {...common} view={data} />
    ) : data.state === "closed" ? (
      <ClosedActions {...common} view={data} />
    ) : (
      <RunningActions {...common} view={data} />
    );

  return (
    <FloorLayout
      tab="pools"
      className="floor-data floor-pools"
      head={head}
      rail={
        <>
          {actions}
          <RingKeys slug={slug} />
        </>
      }
    >
      {source !== undefined ? (
        <p>
          {t("floor.pools.takenOver", { name: source.name })}{" "}
          <Link to={routes.floorPath(slug, "pools", source.slug)}>{source.name}</Link>
        </p>
      ) : data === null ? (
        <p className="muted">{failed ? t("floor.pools.failed") : t("common.loading")}</p>
      ) : !data.checkin_closed ? (
        <p>
          {t("floor.pools.checkinOpen")}{" "}
          <Link to={routes.floorPath(slug, "checkin", selected.slug)}>
            {t("floor.tabs.checkin")}
          </Link>
        </p>
      ) : data.state === "waiting" ? (
        <DrawView {...common} view={data} />
      ) : data.state === "closed" ? (
        <ClosedView {...common} view={data} />
      ) : (
        <RunningView {...common} view={data} />
      )}
    </FloorLayout>
  );
}
