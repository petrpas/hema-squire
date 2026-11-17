import { useState } from "react";
import { useTranslation } from "react-i18next";

import Modal from "../../Modal";
import { poolsApi, type StatsRow } from "../floorApi";
import { openPdf } from "../pdf";
import type { ViewProps } from "./DrawView";
import { PoolSheet } from "./PoolSheet";
import { StatsTable } from "./StatsTable";

/** The pools while they run and once complete: each pool's sheet and
 *  standings, the warnings, the call list, printing, and the close gate
 *  (spec floor-pools). */
export function RunningView({ slug, discipline, view, name, pistes, onChanged }: ViewProps) {
  const { t } = useTranslation();
  const [closing, setClosing] = useState<{ ranking: StatsRow[]; advance: number } | null>(null);
  const draw = view.draw;
  if (draw === null) return null;
  const standings = view.standings;

  return (
    <>
      {view.call_list && view.call_list.length > 0 && (
        <section className="rail-card">
          <h2>{t("floor.pools.callList")}</h2>
          <ul>
            {view.call_list.map((call) => (
              <li key={call.pool}>
                {t("floor.pools.pool", { number: call.pool })}
                {call.piste_id !== null && `, ${pistes.get(call.piste_id) ?? call.piste_id}`}
                {call.planned_start !== null &&
                  `, ${new Date(call.planned_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`}
                : {call.members.map(name).join(", ")}
              </li>
            ))}
          </ul>
        </section>
      )}

      {standings && standings.warnings.length > 0 && (
        <ul className="floor-obstacles">
          {standings.warnings.map((w) => (
            <li key={`${w.pool}-${w.code}-${w.subject}`} className="floor-missing">
              {t(`floor.pools.warnings.${w.code}`, {
                pool: w.pool,
                name: name(w.subject),
                expected: w.expected,
                found: w.found,
              })}
            </li>
          ))}
        </ul>
      )}

      {draw.pools.map((pool) => (
        <section key={pool.number} className="rail-card">
          <h2>
            {t("floor.pools.pool", { number: pool.number })}{" "}
            <span className="muted">
              {pool.piste_id !== null && (pistes.get(pool.piste_id) ?? pool.piste_id)}
            </span>{" "}
            <button
              type="button"
              className="secondary"
              onClick={() => void openPdf(poolsApi.sheetUrl(slug, discipline, pool.number))}
            >
              {t("floor.pools.print")}
            </button>
          </h2>
          <PoolSheet
            slug={slug}
            discipline={discipline}
            pool={pool}
            name={name}
            locked={false}
            onChanged={onChanged}
          />
          {standings?.pools.find((p) => p.number === pool.number) && (
            <StatsTable
              rows={standings.pools.find((p) => p.number === pool.number)?.stats ?? []}
              name={name}
            />
          )}
        </section>
      ))}

      {view.state === "complete" && (
        <button
          type="button"
          className="btn-primary"
          onClick={() => void poolsApi.closePreview(slug, discipline).then(setClosing)}
        >
          {t("floor.pools.close")}
        </button>
      )}

      {closing !== null && (
        <Modal onClose={() => setClosing(null)}>
          <div className="modal">
            <h2>{t("floor.pools.close")}</h2>
            <p>
              {t("floor.pools.advanceCount", {
                count: closing.advance,
                total: closing.ranking.length,
              })}
            </p>
            <StatsTable rows={closing.ranking} name={name} cut={closing.advance} />
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setClosing(null)}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() =>
                  void poolsApi.close(slug, discipline).then(() => {
                    setClosing(null);
                    onChanged();
                  })
                }
              >
                {t("floor.pools.close")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
