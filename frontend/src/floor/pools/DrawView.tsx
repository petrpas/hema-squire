import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api";
import { type DrawScore, type PoolsView, poolsApi } from "../floorApi";

export interface ViewProps {
  slug: string;
  discipline: number;
  view: PoolsView;
  name: (key: string) => string;
  pistes: Map<number, string>;
  /** Whether a schedule is planned; without one there are no waves (spec
   *  floor-draw). */
  schedule: boolean;
  onChanged: () => void;
}

/** Before the draw is announced: pool by pool with each fencer's seed, the
 *  score broken down, swaps (pick two), a redraw, and "Vyhlásit los" (spec
 *  floor-draw). */
export function DrawView({ slug, discipline, view, name, pistes, schedule, onChanged }: ViewProps) {
  const { t } = useTranslation();
  const [picked, setPicked] = useState<string | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);

  async function act(action: () => Promise<unknown>) {
    setRefusal(null);
    try {
      await action();
    } catch (error) {
      setRefusal(
        error instanceof ApiError && typeof error.detail === "string" ? error.detail : "failed",
      );
    }
    onChanged();
  }

  function pick(key: string) {
    if (picked === null) {
      setPicked(key);
      return;
    }
    const first = picked;
    setPicked(null);
    if (first !== key) void act(() => poolsApi.swap(slug, discipline, first, key));
  }

  const draw = view.draw;
  return (
    <section className="rail-card">
      <h2>{t("floor.pools.drawTitle")}</h2>
      {draw === null ? (
        <button
          type="button"
          className="btn-primary"
          onClick={() => void act(() => poolsApi.draw(slug, discipline))}
        >
          {t("floor.pools.draw")}
        </button>
      ) : (
        <>
          <ScoreLine label={t("floor.pools.score")} score={draw.score} waves={schedule} />
          {draw.previous_score && (
            <ScoreLine
              label={t("floor.pools.previousScore")}
              score={draw.previous_score}
              waves={schedule}
            />
          )}
          <p className="muted">{t("floor.pools.swapHint")}</p>
          <div className="floor-pool-grid">
            {draw.pools.map((pool) => (
              <article key={pool.number} className="floor-pool">
                <h3>
                  {t("floor.pools.pool", { number: pool.number })}{" "}
                  {schedule && (
                    <span className="muted">
                      {t("floor.pools.wave", { wave: pool.wave })}
                      {pool.piste_id !== null && `, ${pistes.get(pool.piste_id) ?? pool.piste_id}`}
                    </span>
                  )}
                </h3>
                <ol>
                  {pool.members.map((member) => (
                    <li key={member.key}>
                      <button
                        type="button"
                        className={picked === member.key ? "secondary active" : "secondary"}
                        aria-pressed={picked === member.key}
                        onClick={() => pick(member.key)}
                      >
                        {member.seed}. {name(member.key)}
                      </button>
                    </li>
                  ))}
                </ol>
              </article>
            ))}
          </div>
          <div className="floor-row-actions">
            <button
              type="button"
              className="secondary"
              onClick={() => void act(() => poolsApi.draw(slug, discipline))}
            >
              {t("floor.pools.redraw")}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => void act(() => poolsApi.announce(slug, discipline))}
            >
              {t("floor.pools.announce")}
            </button>
          </div>
        </>
      )}
      {refusal !== null && (
        <p className="floor-missing" role="alert">
          {t(`floor.pools.refusals.${refusal}`, { defaultValue: t("floor.plan.failed") })}
        </p>
      )}
    </section>
  );
}

function ScoreLine({ label, score, waves }: { label: string; score: DrawScore; waves: boolean }) {
  const { t } = useTranslation();
  return (
    <p>
      {label}: {score.total.toFixed(1)} ({t("floor.pools.snake")} {score.snake.toFixed(1)},{" "}
      {t("floor.pools.club")} {score.club.toFixed(1)}, {t("floor.pools.nationality")}{" "}
      {score.nationality.toFixed(1)}
      {waves && `, ${t("floor.pools.waveScore")} ${score.wave.toFixed(1)}`})
    </p>
  );
}
