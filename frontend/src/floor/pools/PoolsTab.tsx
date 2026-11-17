import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import * as routes from "../../routes";
import { type FloorSetup, floorApi, type PoolsView, poolsApi } from "../floorApi";
import { usePolled } from "../usePolled";
import { ClosedView } from "./ClosedView";
import { DrawView } from "./DrawView";
import { RingKeys } from "./RingKeys";
import { RunningView } from "./RunningView";

/** Skupiny: the selected discipline in its state — the draw, the pools
 *  running or complete, or closed — and the piste screens' links (spec
 *  floor-pools). Refreshed every fifteen seconds, as results come in from
 *  the pistes. */
export default function PoolsTab({ slug, discipline }: { slug: string; discipline?: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [setup, setSetup] = useState<FloorSetup | null>(null);

  useEffect(() => {
    floorApi.setup(slug).then(setSetup, () => setSetup(null));
  }, [slug]);

  const selected =
    setup?.disciplines.find((d) => d.slug === discipline) ?? setup?.disciplines[0] ?? null;
  const fetchView = useCallback(
    (): Promise<PoolsView | null> =>
      selected === null ? Promise.resolve(null) : poolsApi.view(slug, selected.id),
    [slug, selected],
  );
  const { data, failed, reload } = usePolled(fetchView, selected?.id);

  if (setup === null || selected === null) return <p>{t("common.loading")}</p>;

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

  return (
    <div className="floor-data floor-pools">
      <label className="floor-search">
        {t("floor.pools.discipline")}
        <select
          value={selected.slug}
          onChange={(event) => navigate(routes.floorPath(slug, "pools", event.target.value))}
        >
          {setup.disciplines.map((d) => (
            <option key={d.id} value={d.slug}>
              {d.name}
            </option>
          ))}
        </select>
      </label>

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

      <RingKeys slug={slug} />
    </div>
  );
}
