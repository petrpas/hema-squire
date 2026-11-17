import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { ApiError } from "../../api";
import { type Outcome, type RingWork, ringApi } from "../floorApi";
import { POLL_MS } from "../usePolled";

/** A piste's screen: its current pool's bouts, the next unrecorded first,
 *  with touch-sized score controls (spec floor-ring). Opened by a link whose
 *  key is in the fragment; no account, no organizer layout. */
export default function RingScreen() {
  const { t } = useTranslation();
  const location = useLocation();
  const key = location.hash.length > 1 ? location.hash.slice(1) : "";
  const [work, setWork] = useState<RingWork | null | "invalid">(null);
  const [scores, setScores] = useState<Record<number, [number, number]>>({});

  const load = useCallback(() => {
    if (key === "") {
      setWork("invalid");
      return;
    }
    ringApi
      .current(key)
      .then(setWork, (error) =>
        setWork(error instanceof ApiError && error.status === 404 ? "invalid" : null),
      );
  }, [key]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  if (work === "invalid") {
    return (
      <main className="floor-ring">
        <p>{t("floor.ring.invalid")}</p>
      </main>
    );
  }
  if (work === null) {
    return (
      <main className="floor-ring">
        <p>{t("common.loading")}</p>
      </main>
    );
  }
  const pool = work.pool;
  // a pool's bouts, the next unrecorded first; or, where no pool runs, the
  // piste's next elimination bout
  const bouts = pool
    ? [...pool.bouts].sort(
        (x, y) => Number(x.score_a !== null) - Number(y.score_a !== null) || x.ordinal - y.ordinal,
      )
    : work.bout
      ? [{ ...work.bout, ordinal: 1, outcome_a: null, outcome_b: null }]
      : [];

  function bump(id: number, side: 0 | 1, by: number, start: [number, number]) {
    const current = scores[id] ?? start;
    const next: [number, number] = [current[0], current[1]];
    next[side] = Math.max(0, next[side] + by);
    setScores({ ...scores, [id]: next });
  }

  async function save(id: number, version: number, value: [number, number]) {
    const [a, b] = value;
    const outcomes: [Outcome, Outcome] =
      a > b ? ["win", "loss"] : a < b ? ["loss", "win"] : ["draw", "draw"];
    await ringApi.record(key, id, {
      score_a: a,
      score_b: b,
      outcome_a: outcomes[0],
      outcome_b: outcomes[1],
      version,
    });
    const rest = { ...scores };
    delete rest[id];
    setScores(rest);
    load();
  }

  return (
    <main className="floor-ring">
      <h1>{t("floor.ring.piste", { name: work.piste })}</h1>
      {bouts.length === 0 ? (
        <p>{t("floor.ring.nothing")}</p>
      ) : (
        <>
          <h2>
            {pool ? t("floor.pools.pool", { number: pool.number }) : t("floor.ring.elimination")}
          </h2>
          <ol className="floor-ring-bouts">
            {bouts.map((bout) => {
              const start: [number, number] = [bout.score_a ?? 0, bout.score_b ?? 0];
              const value = scores[bout.id] ?? start;
              return (
                <li key={bout.id} className={bout.score_a === null ? "" : "floor-recorded"}>
                  <span className="floor-ring-side">
                    {bout.a}
                    <span className="floor-ring-controls">
                      <button
                        type="button"
                        onClick={() => bump(bout.id, 0, -1, start)}
                        aria-label={t("floor.ring.minus", { name: bout.a })}
                      >
                        −
                      </button>
                      <strong>{value[0]}</strong>
                      <button
                        type="button"
                        onClick={() => bump(bout.id, 0, 1, start)}
                        aria-label={t("floor.ring.plus", { name: bout.a })}
                      >
                        +
                      </button>
                    </span>
                  </span>
                  <span className="floor-ring-side">
                    {bout.b}
                    <span className="floor-ring-controls">
                      <button
                        type="button"
                        onClick={() => bump(bout.id, 1, -1, start)}
                        aria-label={t("floor.ring.minus", { name: bout.b })}
                      >
                        −
                      </button>
                      <strong>{value[1]}</strong>
                      <button
                        type="button"
                        onClick={() => bump(bout.id, 1, 1, start)}
                        aria-label={t("floor.ring.plus", { name: bout.b })}
                      >
                        +
                      </button>
                    </span>
                  </span>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => void save(bout.id, bout.version, value)}
                  >
                    {bout.score_a === null ? t("floor.ring.record") : t("floor.ring.correct")}
                  </button>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </main>
  );
}
